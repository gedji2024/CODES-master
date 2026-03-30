"""Diagnostic 2: Use the EXACT same pipeline as run.py evaluation.
Then also run our standalone loop and compare actions side by side."""

import os, sys, glob, time, copy
import numpy as np
import torch as th

_script_dir = os.path.dirname(os.path.abspath(__file__))
_src_dir = os.path.join(_script_dir, "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from controllers.basic_controller import BasicMAC
from components.episode_buffer import EpisodeBatch, ReplayBuffer
from components.transforms import OneHot
from envs import REGISTRY as env_REGISTRY
from runners.episode_runner import EpisodeRunner
from types import SimpleNamespace as SN
import gym_examples

os.environ["ALGO_NAME"] = "QTRAN_DIAG2"

EPISODE_LIMIT = 30
SEED = 42

# Build args exactly like run.py would
args = SN(
    n_agents=70, n_actions=71, state_shape=350,
    hidden_dim=64, use_rnn=True, agent="rnn",
    obs_last_action=True, obs_agent_id=True,
    agent_output_type="q", action_selector="epsilon_greedy",
    epsilon_start=0.01, epsilon_finish=0.01, epsilon_anneal_time=1,
    evaluation_epsilon=0.01, mask_before_softmax=True,
    # Runner args
    batch_size_run=1, env="gymma",
    env_args={"key": "gym_examples:WSNRouting-v0", "time_limit": EPISODE_LIMIT,
              "pretrained_wrapper": None, "seed": SEED},
    device="cpu", render=False,
    mac="basic_mac",
    # Test args
    test_nepisode=10,
    runner_log_interval=100000,
    buffer_size=100, buffer_cpu_only=True,
    test_greedy=True,
)

# Logger mock
class MockLogger:
    def __init__(self):
        self.console_logger = self
    def info(self, msg): print(msg)
    def log_stat(self, key, value, t): pass
    def print_recent_stats(self): pass

logger = MockLogger()

# Create runner (creates the env internally)
runner = EpisodeRunner(args=args, logger=logger)
env_info = runner.get_env_info()
print(f"env_info: n_agents={env_info['n_agents']}, n_actions={env_info['n_actions']}")

# Scheme (matching run.py)
scheme = {
    "state": {"vshape": env_info["state_shape"]},
    "obs": {"vshape": env_info["obs_shape"], "group": "agents"},
    "actions": {"vshape": (1,), "group": "agents", "dtype": th.long},
    "avail_actions": {"vshape": (env_info["n_actions"],), "group": "agents", "dtype": th.int},
    "reward": {"vshape": (1,)},
    "terminated": {"vshape": (1,), "dtype": th.uint8},
}
groups = {"agents": env_info["n_agents"]}
preprocess = {"actions": ("actions_onehot", [OneHot(out_dim=env_info["n_actions"])])}

# Create ReplayBuffer to get the proper scheme (same as run.py:138-148)
buffer = ReplayBuffer(scheme, groups, args.buffer_size,
                      env_info["episode_limit"] + 1,
                      preprocess=preprocess, device="cpu")

# Create MAC using buffer.scheme (same as run.py:148)
mac = BasicMAC(buffer.scheme, groups, args)

# Load QTRAN checkpoint
MODELS_DIR = os.path.join(_script_dir, "results", "models")
dirs = sorted(glob.glob(os.path.join(MODELS_DIR, "qtran_seed*")))
model_dir = dirs[-1]
steps = [int(name) for name in os.listdir(model_dir) if name.isdigit()]
ckpt_path = os.path.join(model_dir, str(max(steps)))
print(f"QTRAN checkpoint: {ckpt_path}")
mac.load_models(ckpt_path)
for p in mac.parameters():
    p.requires_grad_(False)
mac.agent.eval()

# Setup runner with the MAC
runner.setup(scheme=scheme, groups=groups, preprocess=preprocess, mac=mac)

# Run episodes using the EXACT episode runner pipeline
print("\n=== Using EpisodeRunner.run() (exact pipeline) ===")
for ep in range(10):
    batch = runner.run(test_mode=True)
    perf = runner.env.original_env.__dict__['env'].__dict__
    pdr = perf['packet_delivery_ratio']
    ret = runner.test_returns[-1] if runner.test_returns else 0
    print(f"  Ep {ep+1:2d}: return={ret:7.1f}  PDR={pdr*100:5.1f}%")

mean_pdr = np.mean(runner.episode_packet_delivery_ratio) * 100
print(f"\nMean PDR (EpisodeRunner): {mean_pdr:.1f}%")

# Now run our standalone loop with the SAME env and MAC
print("\n=== Standalone loop (same env, same MAC) ===")
pdrs2 = []
for ep in range(10):
    runner.env.reset()
    mac.init_hidden(batch_size=1)
    new_batch = EpisodeBatch(scheme, groups, batch_size=1,
                             max_seq_length=EPISODE_LIMIT + 1,
                             preprocess=preprocess, device="cpu")
    episode_return = 0.0
    terminated = False
    for t in range(EPISODE_LIMIT):
        if terminated:
            break
        new_batch.update({
            "state": [runner.env.get_state()],
            "avail_actions": [runner.env.get_avail_actions()],
            "obs": [runner.env.get_obs()],
        }, ts=t)

        with th.no_grad():
            q = mac.forward(new_batch, t)
        avail = new_batch["avail_actions"][:, t].float()
        q_masked = q.clone()
        q_masked[avail == 0] = -float("inf")
        actions = q_masked.max(dim=2)[1]

        reward, terminated, info = runner.env.step(actions[0])
        episode_return += reward
        new_batch.update({
            "actions": actions.unsqueeze(-1),
            "reward": [(reward,)],
            "terminated": [(terminated != info.get("episode_limit", False),)],
        }, ts=t)

    perf = runner.env.original_env.__dict__['env'].__dict__
    pdr = perf['packet_delivery_ratio']
    pdrs2.append(pdr)
    print(f"  Ep {ep+1:2d}: return={episode_return:7.1f}  PDR={pdr*100:5.1f}%")

print(f"\nMean PDR (standalone): {np.mean(pdrs2)*100:.1f}%")

# Compare: single episode with action-level comparison
print("\n=== Action comparison (1 episode) ===")
runner.env.reset()
mac.init_hidden(batch_size=1)

# Save hidden states
h_before = mac.hidden_states.clone()

new_batch = EpisodeBatch(scheme, groups, batch_size=1,
                         max_seq_length=EPISODE_LIMIT + 1,
                         preprocess=preprocess, device="cpu")
new_batch.update({
    "state": [runner.env.get_state()],
    "avail_actions": [runner.env.get_avail_actions()],
    "obs": [runner.env.get_obs()],
}, ts=0)

# Method A: mac.select_actions (normal pipeline)
actions_normal = mac.select_actions(new_batch, t_ep=0, t_env=0, test_mode=True)

# Reset hidden state
mac.hidden_states = h_before.clone()

# Method B: mac.forward + manual argmax (GAPF style)
with th.no_grad():
    q = mac.forward(new_batch, 0)
avail = new_batch["avail_actions"][:, 0].float()
q_masked = q.clone()
q_masked[avail == 0] = -float("inf")
actions_manual = q_masked.max(dim=2)[1]

print(f"Actions match: {th.equal(actions_normal, actions_manual)}")
diff_mask = actions_normal != actions_manual
if diff_mask.any():
    n_diff = diff_mask.sum().item()
    print(f"  Differ at {n_diff}/{actions_normal.numel()} positions")
    # Show first 5 diffs
    diff_idx = diff_mask.nonzero(as_tuple=True)[1][:5]
    for i in diff_idx:
        i = i.item()
        print(f"  Agent {i}: normal={actions_normal[0,i].item()} vs manual={actions_manual[0,i].item()}")
        # Show Q-values for this agent
        print(f"    Q: {q[0,i,:5].tolist()}")
        print(f"    avail: {avail[0,i,:5].tolist()}")
else:
    print("  All actions identical!")
