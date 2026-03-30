"""Diagnostic: examine Q-values for BS-reachable agents.

Checks whether the QTRAN model assigns higher Q-values to the BS action
(action 70) vs relay actions for agents near the base station.
"""
import os, sys
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

EPISODE_LIMIT = 30
MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "models")


def find_checkpoint(algo_prefix):
    pattern = os.path.join(MODELS_DIR, f"{algo_prefix}_seed*")
    dirs = sorted(glob.glob(pattern))
    model_dir = dirs[-1]
    steps = [int(n) for n in os.listdir(model_dir) if n.isdigit()]
    return os.path.join(model_dir, str(max(steps)))


def main():
    th.manual_seed(42)
    np.random.seed(42)

    # Create env
    env = env_REGISTRY["gymma"](
        key="gym_examples:WSNRouting-v0",
        time_limit=EPISODE_LIMIT,
        pretrained_wrapper=None,
        seed=42,
    )
    info = env.get_env_info()
    n_agents = info["n_agents"]
    n_actions = info["n_actions"]

    print(f"n_agents={n_agents}, n_actions={n_actions}")
    print(f"BS action index = {n_agents} (i.e., action {n_actions-1})")

    # Scheme
    scheme = {
        "state": {"vshape": info["state_shape"]},
        "obs": {"vshape": info["obs_shape"], "group": "agents"},
        "actions": {"vshape": (1,), "group": "agents", "dtype": th.long},
        "avail_actions": {"vshape": (n_actions,), "group": "agents", "dtype": th.int},
        "reward": {"vshape": (1,)},
        "terminated": {"vshape": (1,), "dtype": th.uint8},
    }
    groups = {"agents": n_agents}
    preprocess = {"actions": ("actions_onehot", [OneHot(out_dim=n_actions)])}

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

    # Load QTRAN
    qtran_path = find_checkpoint("qtran")
    print(f"QTRAN checkpoint: {qtran_path}")
    mac = BasicMAC(mac_scheme, groups, args)
    mac.load_models(qtran_path)
    mac.agent.eval()

    # Reset and check initial state
    env.reset()
    mac.init_hidden(batch_size=1)

    batch = EpisodeBatch(scheme, groups, batch_size=1,
                         max_seq_length=EPISODE_LIMIT + 1,
                         preprocess=preprocess, device="cpu")

    # Get env internals
    wsn = env.original_env.__dict__['env'].__dict__
    positions = wsn['sensor_positions']
    distance_to_base = wsn['distance_to_base']

    print(f"\n--- Agent proximity to BS ---")
    bs_reachable = []
    for i in range(n_agents):
        if distance_to_base[i] <= 35.0:
            bs_reachable.append(i)
    print(f"Agents within coverage_radius of BS: {len(bs_reachable)} / {n_agents}")
    print(f"Agent IDs: {bs_reachable[:20]}...")

    # Run first step
    batch.update({
        "state": [env.get_state()],
        "avail_actions": [env.get_avail_actions()],
        "obs": [env.get_obs()],
    }, ts=0)

    with th.no_grad():
        q = mac.forward(batch, 0)  # (1, n_agents, n_actions)

    avail = batch["avail_actions"][:, 0]  # (1, n_agents, n_actions)
    q_np = q.squeeze(0).numpy()  # (n_agents, n_actions)
    avail_np = avail.squeeze(0).numpy()  # (n_agents, n_actions)

    print(f"\n--- Q-values at step 0 ---")
    print(f"Q-value range: [{q_np.min():.4f}, {q_np.max():.4f}]")
    print(f"Q-value mean: {q_np.mean():.4f}")

    # For BS-reachable agents, check if BS action is available and its Q-value
    print(f"\n--- BS-reachable agents: Q-value for BS action (action {n_agents}) ---")
    print(f"{'Agent':>6} {'Dist_BS':>8} {'BS_avail':>9} {'Q_BS':>10} {'Q_max':>10} "
          f"{'Greedy_act':>11} {'N_avail':>8}")
    print("-" * 70)

    for i in bs_reachable[:20]:
        bs_avail = avail_np[i, n_agents]
        q_bs = q_np[i, n_agents]

        # Masked Q-values
        q_masked = q_np[i].copy()
        q_masked[avail_np[i] == 0] = -np.inf
        q_max = q_masked.max()
        greedy_action = q_masked.argmax()
        n_avail = int(avail_np[i].sum())

        print(f"{i:>6d} {distance_to_base[i]:>8.1f} {int(bs_avail):>9d} {q_bs:>10.4f} "
              f"{q_max:>10.4f} {greedy_action:>11d} {n_avail:>8d}")

    # Show a few non-BS-reachable agents too
    print(f"\n--- Non-BS-reachable agents (sample) ---")
    far_agents = [i for i in range(n_agents) if i not in bs_reachable][:10]
    for i in far_agents:
        q_masked = q_np[i].copy()
        q_masked[avail_np[i] == 0] = -np.inf
        q_max = q_masked.max()
        greedy_action = q_masked.argmax()
        n_avail = int(avail_np[i].sum())
        print(f"{i:>6d} {distance_to_base[i]:>8.1f} {'N/A':>9} {q_np[i, n_agents]:>10.4f} "
              f"{q_max:>10.4f} {greedy_action:>11d} {n_avail:>8d}")

    # Check: what's the Q-value distribution across ALL actions for a BS-reachable agent?
    if bs_reachable:
        agent_id = bs_reachable[0]
        print(f"\n--- Full Q-value profile for agent {agent_id} (dist_to_BS={distance_to_base[agent_id]:.1f}m) ---")
        avail_actions = np.where(avail_np[agent_id] == 1)[0]
        print(f"Available actions: {avail_actions.tolist()}")
        for a in avail_actions:
            label = "BS" if a == n_agents else f"relay→{a}"
            print(f"  Action {a:3d} ({label:>10}): Q={q_np[agent_id, a]:.6f}")

    # Run a few more steps to see if BS ever gets picked
    print(f"\n--- Multi-step simulation: greedy actions for BS-reachable agents ---")
    for t in range(5):
        if t > 0:
            batch.update({
                "state": [env.get_state()],
                "avail_actions": [env.get_avail_actions()],
                "obs": [env.get_obs()],
            }, ts=t)

        with th.no_grad():
            q = mac.forward(batch, t)

        avail = batch["avail_actions"][:, t]
        q_np = q.squeeze(0).numpy()
        avail_np = avail.squeeze(0).numpy()

        q_masked = q_np.copy()
        q_masked[avail_np == 0] = -np.inf
        greedy_actions = q_masked.argmax(axis=1)

        bs_picks = sum(1 for i in bs_reachable if greedy_actions[i] == n_agents and avail_np[i, n_agents] == 1)
        total_bs_avail = sum(1 for i in bs_reachable if avail_np[i, n_agents] == 1)

        print(f"  Step {t}: BS-reachable choosing BS = {bs_picks}/{total_bs_avail}, "
              f"all actions range=[{greedy_actions.min()}, {greedy_actions.max()}]")

        # Actually step the env
        actions = th.tensor(greedy_actions).unsqueeze(0)
        reward, terminated, info_step = env.step(actions[0])

        batch.update({
            "actions": actions.unsqueeze(-1),
            "reward": [(reward,)],
            "terminated": [(terminated != info_step.get("episode_limit", False),)],
        }, ts=t)

        pkts = wsn['packets_delivered']
        print(f"         reward={reward:.4f}, pkts_delivered={pkts}")

        if terminated:
            break


if __name__ == "__main__":
    main()
