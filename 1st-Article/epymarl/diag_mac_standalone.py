"""Diagnostic: load QTRAN MAC standalone and run 10 episodes.
Compare PDR with normal evaluation to find if MAC loading is broken."""

import os, sys, glob, time
import numpy as np
import torch

_script_dir = os.path.dirname(os.path.abspath(__file__))
_src_dir = os.path.join(_script_dir, "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from controllers.basic_controller import BasicMAC
from components.episode_buffer import EpisodeBatch
from components.transforms import OneHot
from envs import REGISTRY as env_REGISTRY
import gym_examples

EPISODE_LIMIT = 30   # Must match training config! run_algos.ps1 uses time_limit=30
SEED = 42
N_EPISODES = 20

torch.manual_seed(SEED)
np.random.seed(SEED)

# Create env
env = env_REGISTRY["gymma"](
    key="gym_examples:WSNRouting-v0",
    time_limit=EPISODE_LIMIT,
    pretrained_wrapper=None,
    seed=SEED,
)
env_info = env.get_env_info()
n_agents = env_info["n_agents"]
n_actions = env_info["n_actions"]
obs_shape = env_info["obs_shape"]
state_shape = env_info["state_shape"]
print(f"n_agents={n_agents}, n_actions={n_actions}, obs={obs_shape}, state={state_shape}")

# Scheme (same as GAPF)
scheme = {
    "state": {"vshape": state_shape},
    "obs": {"vshape": obs_shape, "group": "agents"},
    "actions": {"vshape": (1,), "group": "agents", "dtype": torch.long},
    "avail_actions": {"vshape": (n_actions,), "group": "agents", "dtype": torch.int},
    "reward": {"vshape": (1,)},
    "terminated": {"vshape": (1,), "dtype": torch.uint8},
}
groups = {"agents": n_agents}
preprocess = {"actions": ("actions_onehot", [OneHot(out_dim=n_actions)])}

mac_scheme = dict(scheme)
mac_scheme["actions_onehot"] = {"vshape": (n_actions,), "dtype": torch.float32, "group": "agents"}

# Load QTRAN MAC
from types import SimpleNamespace as SN
mac_args = SN(
    n_agents=n_agents, n_actions=n_actions, obs_shape=None,
    hidden_dim=64, use_rnn=True, agent="rnn",
    obs_last_action=True, obs_agent_id=True,
    agent_output_type="q", action_selector="epsilon_greedy",
    epsilon_start=0.01, epsilon_finish=0.01, epsilon_anneal_time=1,
    evaluation_epsilon=0.01, mask_before_softmax=True, device="cpu",
)

mac = BasicMAC(mac_scheme, groups, mac_args)

# Find QTRAN checkpoint
MODELS_DIR = os.path.join(_script_dir, "results", "models")
pattern = os.path.join(MODELS_DIR, "qtran_seed*")
dirs = sorted(glob.glob(pattern))
model_dir = dirs[-1]
steps = [int(name) for name in os.listdir(model_dir) if name.isdigit()]
ckpt_path = os.path.join(model_dir, str(max(steps)))
print(f"QTRAN checkpoint: {ckpt_path}")

mac.load_models(ckpt_path)
for p in mac.parameters():
    p.requires_grad_(False)
mac.agent.eval()

# Run episodes - TWO METHODS to compare
print("\n=== Method 1: GAPF-style (mac.forward + manual argmax) ===")
for ep in range(N_EPISODES):
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

        with torch.no_grad():
            q = mac.forward(batch, t)  # (1, n_agents, n_actions)

        avail = batch["avail_actions"][:, t].float()
        q_masked = q.clone()
        q_masked[avail == 0] = -float("inf")
        actions = q_masked.max(dim=2)[1]  # (1, n_agents)

        # Check for invalid actions
        invalid = (actions < 0) | (actions >= n_actions)
        if invalid.any():
            print(f"  WARNING: invalid actions at t={t}: {actions[invalid]}")

        reward, terminated, info = env.step(actions[0])
        episode_return += reward

        batch.update({
            "actions": actions.unsqueeze(-1),
            "reward": [(reward,)],
            "terminated": [(terminated != info.get("episode_limit", False),)],
        }, ts=t)

    perf = env.original_env.__dict__['env'].__dict__
    pdr = perf['packet_delivery_ratio']
    print(f"  Ep {ep+1:2d}: return={episode_return:7.1f}  PDR={pdr*100:5.1f}%  "
          f"steps={t+1}  throughput={perf['network_throughput']:.2f}")

print("\n=== Method 2: select_actions (normal pipeline) ===")
for ep in range(N_EPISODES):
    env.reset()
    mac.init_hidden(batch_size=1)
    batch = EpisodeBatch(scheme, groups, batch_size=1,
                         max_seq_length=EPISODE_LIMIT + 1,
                         preprocess=preprocess, device="cpu")

    episode_return = 0.0
    terminated = False
    t_env = ep * EPISODE_LIMIT  # fake t_env

    for t in range(EPISODE_LIMIT):
        if terminated:
            break

        batch.update({
            "state": [env.get_state()],
            "avail_actions": [env.get_avail_actions()],
            "obs": [env.get_obs()],
        }, ts=t)

        actions = mac.select_actions(batch, t_ep=t, t_env=t_env + t, test_mode=True)

        reward, terminated, info = env.step(actions[0])
        episode_return += reward

        batch.update({
            "actions": actions.unsqueeze(-1),
            "reward": [(reward,)],
            "terminated": [(terminated != info.get("episode_limit", False),)],
        }, ts=t)

    perf = env.original_env.__dict__['env'].__dict__
    pdr = perf['packet_delivery_ratio']
    print(f"  Ep {ep+1:2d}: return={episode_return:7.1f}  PDR={pdr*100:5.1f}%  "
          f"steps={t+1}  throughput={perf['network_throughput']:.2f}")

# Also dump Q-value stats for first episode
print("\n=== Q-value analysis (1 episode) ===")
env.reset()
mac.init_hidden(batch_size=1)
batch = EpisodeBatch(scheme, groups, batch_size=1,
                     max_seq_length=EPISODE_LIMIT + 1,
                     preprocess=preprocess, device="cpu")

batch.update({
    "state": [env.get_state()],
    "avail_actions": [env.get_avail_actions()],
    "obs": [env.get_obs()],
}, ts=0)

with torch.no_grad():
    q = mac.forward(batch, 0)

avail = batch["avail_actions"][:, 0].float()
q_valid = q[avail == 1]
print(f"  Q-values shape: {q.shape}")
print(f"  Q-values (valid): min={q_valid.min():.4f}, max={q_valid.max():.4f}, "
      f"mean={q_valid.mean():.4f}, std={q_valid.std():.4f}")
print(f"  Q-values (all agent 0): {q[0, 0, :5].tolist()} ...")
print(f"  Avail (agent 0): {avail[0, 0, :5].tolist()} ...")
print(f"  Selected action (agent 0): {q[0, 0].argmax().item()}")
