"""Diagnostic: trace where NaN Q-values come from."""
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
import torch.nn.functional as F

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

    # Check model weights directly
    qtran_path = find_checkpoint("qtran")
    print(f"QTRAN checkpoint: {qtran_path}")

    state_dict = th.load(f"{qtran_path}/agent.th", map_location="cpu")
    print(f"\n--- Model weight stats ---")
    for name, param in state_dict.items():
        has_nan = th.isnan(param).any().item()
        has_inf = th.isinf(param).any().item()
        print(f"  {name}: shape={list(param.shape)}, "
              f"min={param.min():.6f}, max={param.max():.6f}, "
              f"nan={has_nan}, inf={has_inf}")

    # Create env and MAC
    env = env_REGISTRY["gymma"](
        key="gym_examples:WSNRouting-v0",
        time_limit=EPISODE_LIMIT,
        pretrained_wrapper=None,
        seed=42,
    )
    info = env.get_env_info()
    n_agents = info["n_agents"]
    n_actions = info["n_actions"]

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

    mac = BasicMAC(mac_scheme, groups, args)
    mac.load_models(qtran_path)
    mac.agent.eval()

    # Reset env
    env.reset()
    mac.init_hidden(batch_size=1)

    batch = EpisodeBatch(scheme, groups, batch_size=1,
                         max_seq_length=EPISODE_LIMIT + 1,
                         preprocess=preprocess, device="cpu")

    # Store pre-transition data
    obs = env.get_obs()
    state = env.get_state()
    avail = env.get_avail_actions()

    print(f"\n--- Observation check ---")
    obs_tensor = th.tensor(np.array(obs), dtype=th.float32)
    print(f"  obs shape: {obs_tensor.shape}")
    print(f"  obs range: [{obs_tensor.min():.6f}, {obs_tensor.max():.6f}]")
    print(f"  obs has NaN: {th.isnan(obs_tensor).any().item()}")
    print(f"  obs has Inf: {th.isinf(obs_tensor).any().item()}")
    print(f"  obs sample (agent 0): {obs[0]}")
    print(f"  obs sample (agent 1): {obs[1]}")

    print(f"\n--- State check ---")
    state_tensor = th.tensor(state, dtype=th.float32)
    print(f"  state shape: {state_tensor.shape}")
    print(f"  state has NaN: {th.isnan(state_tensor).any().item()}")

    print(f"\n--- Avail actions check ---")
    avail_tensor = th.tensor(np.array(avail), dtype=th.int32)
    print(f"  avail shape: {avail_tensor.shape}")
    print(f"  avail sum per agent range: [{avail_tensor.sum(dim=1).min()}, {avail_tensor.sum(dim=1).max()}]")

    # Update batch
    batch.update({
        "state": [state],
        "avail_actions": [avail],
        "obs": [obs],
    }, ts=0)

    # Manually trace through BasicMAC.forward
    print(f"\n--- Tracing MAC.forward() ---")
    agent_inputs = mac._build_inputs(batch, 0)
    print(f"  agent_inputs shape: {agent_inputs.shape}")
    print(f"  agent_inputs range: [{agent_inputs.min():.6f}, {agent_inputs.max():.6f}]")
    print(f"  agent_inputs has NaN: {th.isnan(agent_inputs).any().item()}")
    print(f"  agent_inputs has Inf: {th.isinf(agent_inputs).any().item()}")

    # Check obs portion
    obs_portion = agent_inputs[:, :info["obs_shape"]]
    print(f"  obs portion range: [{obs_portion.min():.6f}, {obs_portion.max():.6f}]")
    print(f"  obs portion NaN: {th.isnan(obs_portion).any().item()}")

    # Check last_action portion
    last_action_portion = agent_inputs[:, info["obs_shape"]:info["obs_shape"]+n_actions]
    print(f"  last_action portion (should be zeros at t=0): sum={last_action_portion.sum():.6f}")

    # Check agent_id portion
    agent_id_portion = agent_inputs[:, info["obs_shape"]+n_actions:]
    print(f"  agent_id portion: shape={agent_id_portion.shape}, sum={agent_id_portion.sum():.6f}")

    # Now run through the agent manually
    print(f"\n--- Tracing RNN agent ---")
    h_in = mac.hidden_states
    print(f"  hidden_states shape: {h_in.shape}")
    print(f"  hidden_states range: [{h_in.min():.6f}, {h_in.max():.6f}]")
    print(f"  hidden_states NaN: {th.isnan(h_in).any().item()}")

    with th.no_grad():
        x = F.relu(mac.agent.fc1(agent_inputs))
        print(f"  After fc1+relu: range=[{x.min():.6f}, {x.max():.6f}], NaN={th.isnan(x).any().item()}")

        h_in_reshaped = h_in.reshape(-1, 64)
        h = mac.agent.rnn(x, h_in_reshaped)
        print(f"  After GRU: range=[{h.min():.6f}, {h.max():.6f}], NaN={th.isnan(h).any().item()}")

        q = mac.agent.fc2(h)
        print(f"  After fc2 (Q-values): range=[{q.min():.6f}, {q.max():.6f}], NaN={th.isnan(q).any().item()}")

    # If NaN in inputs, trace which obs values are NaN
    if th.isnan(agent_inputs).any():
        nan_mask = th.isnan(agent_inputs)
        nan_agents = nan_mask.any(dim=1).nonzero().squeeze(-1)
        print(f"\n  Agents with NaN inputs: {nan_agents[:10].tolist()}")
        for a_idx in nan_agents[:3]:
            nan_features = nan_mask[a_idx].nonzero().squeeze(-1)
            print(f"    Agent {a_idx}: NaN at feature indices {nan_features.tolist()}")
            print(f"    Values: {agent_inputs[a_idx, nan_features].tolist()}")


if __name__ == "__main__":
    main()
