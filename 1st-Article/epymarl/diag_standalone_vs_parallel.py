"""Diagnostic: compare standalone (batch_size=1) vs GAPF-style MAC evaluation.

Tests whether the PDR discrepancy is caused by:
  A) Single-env vs multi-env (parallel runner)
  B) How GAPF calls mac.forward() vs mac.select_actions()
"""
import os, sys, time
import numpy as np
import torch as th

os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

_src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from controllers.basic_controller import BasicMAC
from components.episode_buffer import EpisodeBatch
from components.transforms import OneHot
from envs import REGISTRY as env_REGISTRY
import glob
from types import SimpleNamespace as SN
from functools import partial
from torch.distributions import Categorical

EPISODE_LIMIT = 30
N_EPISODES = 30
MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "models")


def find_checkpoint(algo_prefix):
    pattern = os.path.join(MODELS_DIR, f"{algo_prefix}_seed*")
    dirs = sorted(glob.glob(pattern))
    if not dirs:
        raise FileNotFoundError(f"No checkpoint matching {pattern}")
    model_dir = dirs[-1]
    steps = []
    for name in os.listdir(model_dir):
        try:
            steps.append(int(name))
        except ValueError:
            continue
    if not steps:
        raise FileNotFoundError(f"No step subdirs in {model_dir}")
    return os.path.join(model_dir, str(max(steps)))


def make_env(seed=42):
    env = env_REGISTRY["gymma"](
        key="gym_examples:WSNRouting-v0",
        time_limit=EPISODE_LIMIT,
        pretrained_wrapper=None,
        seed=seed,
    )
    return env


def make_mac(env, checkpoint_path):
    info = env.get_env_info()
    n_agents = info["n_agents"]
    n_actions = info["n_actions"]
    obs_shape = info["obs_shape"]
    state_shape = info["state_shape"]

    scheme = {
        "state": {"vshape": state_shape},
        "obs": {"vshape": obs_shape, "group": "agents"},
        "actions": {"vshape": (1,), "group": "agents", "dtype": th.long},
        "avail_actions": {"vshape": (n_actions,), "group": "agents", "dtype": th.int},
        "reward": {"vshape": (1,)},
        "terminated": {"vshape": (1,), "dtype": th.uint8},
    }
    groups = {"agents": n_agents}
    preprocess = {"actions": ("actions_onehot", [OneHot(out_dim=n_actions)])}

    # Build scheme with actions_onehot for MAC (same as GAPF)
    mac_scheme = dict(scheme)
    mac_scheme["actions_onehot"] = {"vshape": (n_actions,), "dtype": th.float32, "group": "agents"}

    args = SN(
        n_agents=n_agents, n_actions=n_actions, obs_shape=None,
        hidden_dim=64, use_rnn=True, agent="rnn",
        obs_last_action=True, obs_agent_id=True,
        agent_output_type="q", action_selector="epsilon_greedy",
        epsilon_start=0.01, epsilon_finish=0.01, epsilon_anneal_time=1,
        evaluation_epsilon=0.01, mask_before_softmax=True, device="cpu",
    )

    mac = BasicMAC(mac_scheme, groups, args)
    mac.load_models(checkpoint_path)
    for p in mac.parameters():
        p.requires_grad_(False)
    mac.agent.eval()

    return mac, scheme, groups, preprocess, info


def run_episode_select_actions(env, mac, scheme, groups, preprocess, info):
    """Run episode using mac.select_actions() — same as EpisodeRunner."""
    env.reset()
    mac.init_hidden(batch_size=1)

    new_batch = partial(EpisodeBatch, scheme, groups, 1, EPISODE_LIMIT + 1,
                        preprocess=preprocess, device="cpu")
    batch = new_batch()

    episode_return = 0.0
    terminated = False
    t = 0

    while not terminated:
        pre = {
            "state": [env.get_state()],
            "avail_actions": [env.get_avail_actions()],
            "obs": [env.get_obs()],
        }
        batch.update(pre, ts=t)

        # This is exactly what EpisodeRunner does
        actions = mac.select_actions(batch, t_ep=t, t_env=200000, test_mode=True)

        reward, terminated, info_step = env.step(actions[0])
        episode_return += reward

        post = {
            "actions": actions,
            "reward": [(reward,)],
            "terminated": [(terminated != info_step.get("episode_limit", False),)],
        }
        batch.update(post, ts=t)
        t += 1

    perf = env.original_env.__dict__['env'].__dict__
    pdr = perf['packet_delivery_ratio']
    return episode_return, pdr, t


def run_episode_forward_greedy(env, mac, scheme, groups, preprocess, info):
    """Run episode using mac.forward() + manual greedy — same as GAPF CAS."""
    env.reset()
    mac.init_hidden(batch_size=1)

    batch = EpisodeBatch(scheme, groups, batch_size=1,
                         max_seq_length=EPISODE_LIMIT + 1,
                         preprocess=preprocess, device="cpu")

    episode_return = 0.0
    terminated = False

    for t in range(EPISODE_LIMIT):
        if terminated:
            break

        batch.update({
            "state": [env.get_state()],
            "avail_actions": [env.get_avail_actions()],
            "obs": [env.get_obs()],
        }, ts=t)

        with th.no_grad():
            q = mac.forward(batch, t)

        avail = batch["avail_actions"][:, t].float()
        q_masked = q.clone()
        q_masked[avail == 0] = -float("inf")
        actions = q_masked.max(dim=2)[1]

        # MPS fix
        invalid = (actions < 0)
        if invalid.any():
            safe_avail = avail.clone()
            safe_avail[(safe_avail.sum(dim=-1, keepdim=True) == 0).expand_as(safe_avail)] = 1.0
            fallback = Categorical(safe_avail).sample().long()
            actions[invalid] = fallback[invalid]

        reward, terminated, info_step = env.step(actions[0])
        episode_return += reward

        batch.update({
            "actions": actions.unsqueeze(-1),
            "reward": [(reward,)],
            "terminated": [(terminated != info_step.get("episode_limit", False),)],
        }, ts=t)

    perf = env.original_env.__dict__['env'].__dict__
    pdr = perf['packet_delivery_ratio']
    return episode_return, pdr, t


def run_episode_select_actions_detailed(env, mac, scheme, groups, preprocess, info):
    """Same as select_actions but with detailed step-by-step logging for first episode."""
    env.reset()
    mac.init_hidden(batch_size=1)

    new_batch = partial(EpisodeBatch, scheme, groups, 1, EPISODE_LIMIT + 1,
                        preprocess=preprocess, device="cpu")
    batch = new_batch()

    episode_return = 0.0
    terminated = False
    t = 0

    perf = env.original_env.__dict__['env'].__dict__
    print(f"\n  Initial state: remaining_energy mean={perf['remaining_energy'].mean():.4f}, "
          f"packets_delivered={perf['packets_delivered']}")

    while not terminated:
        pre = {
            "state": [env.get_state()],
            "avail_actions": [env.get_avail_actions()],
            "obs": [env.get_obs()],
        }
        batch.update(pre, ts=t)

        # Check avail actions
        avail = batch["avail_actions"][:, t]  # (1, n_agents, n_actions)
        avail_counts = avail.sum(dim=-1).squeeze(0)  # per agent

        actions = mac.select_actions(batch, t_ep=t, t_env=200000, test_mode=True)

        if t < 3 or t == EPISODE_LIMIT - 1:
            print(f"  Step {t}: avail_per_agent=[{avail_counts.min():.0f}-{avail_counts.max():.0f}] "
                  f"actions_sample=[{actions[0,:5].tolist()}] "
                  f"action_range=[{actions.min()},{actions.max()}]")

        reward, terminated, info_step = env.step(actions[0])
        episode_return += reward

        if t < 3 or t == EPISODE_LIMIT - 1:
            print(f"         reward={reward:.4f} terminated={terminated} "
                  f"pkts_delivered={perf['packets_delivered']}")

        post = {
            "actions": actions,
            "reward": [(reward,)],
            "terminated": [(terminated != info_step.get("episode_limit", False),)],
        }
        batch.update(post, ts=t)
        t += 1

    pdr = perf['packet_delivery_ratio']
    return episode_return, pdr, t


def main():
    th.manual_seed(42)
    np.random.seed(42)

    # Load QTRAN checkpoint
    qtran_path = find_checkpoint("qtran")
    print(f"QTRAN checkpoint: {qtran_path}")

    # =====================================================================
    # Test A: select_actions (like EpisodeRunner)
    # =====================================================================
    print(f"\n{'='*60}")
    print("Test A: select_actions (EpisodeRunner-style), {N_EPISODES} episodes")
    print(f"{'='*60}")

    env = make_env(seed=42)
    mac, scheme, groups, preprocess, info = make_mac(env, qtran_path)

    # Detailed first episode
    print("\nDetailed first episode:")
    ret, pdr, steps = run_episode_select_actions_detailed(env, mac, scheme, groups, preprocess, info)
    print(f"  Episode 0: ret={ret:.2f}, PDR={pdr*100:.1f}%, steps={steps}")

    pdrs_a = [pdr]
    rets_a = [ret]

    for ep in range(1, N_EPISODES):
        ret, pdr, steps = run_episode_select_actions(env, mac, scheme, groups, preprocess, info)
        pdrs_a.append(pdr)
        rets_a.append(ret)

    print(f"\n  Mean PDR = {np.mean(pdrs_a)*100:.1f}% (±{np.std(pdrs_a)*100:.1f}%)")
    print(f"  Mean Ret = {np.mean(rets_a):.2f}")
    print(f"  Non-zero PDR episodes: {sum(1 for p in pdrs_a if p > 0)}/{N_EPISODES}")

    # =====================================================================
    # Test B: forward + manual greedy (GAPF-style)
    # =====================================================================
    print(f"\n{'='*60}")
    print("Test B: forward + greedy (GAPF-style), {N_EPISODES} episodes")
    print(f"{'='*60}")

    env2 = make_env(seed=42)
    mac2, scheme2, groups2, preprocess2, info2 = make_mac(env2, qtran_path)

    pdrs_b = []
    rets_b = []

    for ep in range(N_EPISODES):
        ret, pdr, steps = run_episode_forward_greedy(env2, mac2, scheme2, groups2, preprocess2, info2)
        pdrs_b.append(pdr)
        rets_b.append(ret)

    print(f"\n  Mean PDR = {np.mean(pdrs_b)*100:.1f}% (±{np.std(pdrs_b)*100:.1f}%)")
    print(f"  Mean Ret = {np.mean(rets_b):.2f}")
    print(f"  Non-zero PDR episodes: {sum(1 for p in pdrs_b if p > 0)}/{N_EPISODES}")

    # =====================================================================
    # Test C: Same as A but different seed
    # =====================================================================
    print(f"\n{'='*60}")
    print("Test C: select_actions, seed=100, {N_EPISODES} episodes")
    print(f"{'='*60}")

    env3 = make_env(seed=100)
    mac3, scheme3, groups3, preprocess3, info3 = make_mac(env3, qtran_path)

    pdrs_c = []
    for ep in range(N_EPISODES):
        ret, pdr, steps = run_episode_select_actions(env3, mac3, scheme3, groups3, preprocess3, info3)
        pdrs_c.append(pdr)

    print(f"\n  Mean PDR = {np.mean(pdrs_c)*100:.1f}% (±{np.std(pdrs_c)*100:.1f}%)")
    print(f"  Non-zero PDR episodes: {sum(1 for p in pdrs_c if p > 0)}/{N_EPISODES}")

    # =====================================================================
    # Summary
    # =====================================================================
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"  Test A (select_actions, seed=42): PDR={np.mean(pdrs_a)*100:.1f}%")
    print(f"  Test B (forward+greedy, seed=42):  PDR={np.mean(pdrs_b)*100:.1f}%")
    print(f"  Test C (select_actions, seed=100): PDR={np.mean(pdrs_c)*100:.1f}%")
    print(f"  Parallel runner (from npy):        PDR=~40%")

    if np.mean(pdrs_a) < 0.1 and np.mean(pdrs_b) < 0.1:
        print("\n  CONCLUSION: Single-env evaluation fundamentally broken.")
        print("  The issue is NOT in GAPF's action selection.")
        print("  The issue is in single-env vs multi-env (parallel runner).")
    elif np.mean(pdrs_a) > 0.2 and np.mean(pdrs_b) < 0.1:
        print("\n  CONCLUSION: GAPF's manual greedy breaks things.")
        print("  Fix: use mac.select_actions() instead of mac.forward().")
    else:
        print(f"\n  CONCLUSION: Both methods work. Check other factors.")


if __name__ == "__main__":
    main()
