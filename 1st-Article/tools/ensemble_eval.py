"""Ensemble Evaluation: Combine QMIX and QTRAN Q-values at action level.

At each timestep, both QMIX and QTRAN RNN agents produce Q-values for each
agent. The ensemble combines these Q-values (max mode by default) and selects
the action with the highest combined Q-value. This exploits the complementary
strengths of both algorithms without any additional training.

Usage:
    python tools/ensemble_eval.py --n-episodes 500 --seed 42 --mode max
    python tools/ensemble_eval.py --n-sensors 30 --coverage-radius 25.0 --mode max
"""

import argparse
import os
import sys
import time
import numpy as np
import torch as th
import psutil
from pathlib import Path
from types import SimpleNamespace

# Setup paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
EPYMARL_DIR = PROJECT_DIR / "epymarl"
sys.path.insert(0, str(EPYMARL_DIR / "src"))

import gym
import gym_examples
from modules.agents.rnn_agent import RNNAgent


def load_agent(checkpoint_dir, input_shape, args):
    """Load a trained RNN agent from checkpoint."""
    agent = RNNAgent(input_shape, args)
    agent_path = os.path.join(checkpoint_dir, "agent.th")
    agent.load_state_dict(th.load(agent_path, map_location="cpu"))
    agent.eval()
    return agent


def build_obs(raw_obs, n_agents, n_actions, obs_size):
    """Build agent observations with one-hot agent ID and last action.

    Matches BasicMAC's _build_inputs: [obs, last_action_onehot, agent_id_onehot]
    """
    obs_list = []
    for agent_id in range(n_agents):
        o = raw_obs[agent_id]
        # Flatten observation dict
        flat_obs = np.concatenate([np.atleast_1d(v).flatten() for v in o.values()])
        # Pad to obs_size if needed
        if len(flat_obs) < obs_size:
            flat_obs = np.pad(flat_obs, (0, obs_size - len(flat_obs)))
        obs_list.append(flat_obs)
    return np.array(obs_list, dtype=np.float32)


def build_agent_inputs(obs_array, last_actions, n_agents, n_actions, obs_size):
    """Build full agent input: [obs, last_action_onehot, agent_id_onehot]."""
    inputs = []
    for agent_id in range(n_agents):
        obs = obs_array[agent_id]

        # Last action one-hot
        last_act_oh = np.zeros(n_actions, dtype=np.float32)
        if last_actions is not None:
            last_act_oh[last_actions[agent_id]] = 1.0

        # Agent ID one-hot
        agent_id_oh = np.zeros(n_agents, dtype=np.float32)
        agent_id_oh[agent_id] = 1.0

        inp = np.concatenate([obs, last_act_oh, agent_id_oh])
        inputs.append(inp)
    return np.array(inputs, dtype=np.float32)


def get_avail_actions(env, n_agents, n_actions):
    """Get available actions from the environment."""
    unwrapped = env.unwrapped if hasattr(env, 'unwrapped') else env
    if hasattr(unwrapped, 'get_avail_actions'):
        raw = unwrapped.get_avail_actions()
        avail = []
        for aa in raw:
            a = list(aa)
            if len(a) < n_actions:
                a = a + [0] * (n_actions - len(a))
            avail.append(a)
        return np.array(avail, dtype=np.float32)
    return np.ones((n_agents, n_actions), dtype=np.float32)


def run_ensemble_evaluation(qmix_checkpoint, qtran_checkpoint, n_agents, n_actions,
                           n_episodes=500, seed=42, epsilon=0.01, ensemble_mode="max",
                           env_kwargs=None, time_limit=None, device="auto"):
    """Run ensemble evaluation combining QMIX and QTRAN Q-values.

    Args:
        qmix_checkpoint: Path to QMIX checkpoint directory (containing agent.th)
        qtran_checkpoint: Path to QTRAN checkpoint directory
        n_agents: Number of sensor agents
        n_actions: Number of actions (n_agents + 1 for BS)
        n_episodes: Number of test episodes
        seed: Random seed for reproducibility
        epsilon: Evaluation epsilon (for epsilon-greedy)
        ensemble_mode: How to combine Q-values ("mean", "max", "softmax_weight")
        env_kwargs: Extra kwargs to pass to gym.make (e.g., n_sensors, coverage_radius)
        device: Compute device ("auto", "cpu", "mps", "cuda"). Must match training device.
    """
    # Resolve device — must match the device used during QMIX/QTRAN training
    if device == "auto":
        if th.cuda.is_available():
            device = "cuda"
        elif hasattr(th.backends, 'mps') and th.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
    print(f"Ensemble eval device: {device}")

    obs_size = 5    # [energy, consumption, x, y, packets]
    hidden_dim = 64
    input_shape = obs_size + n_actions + n_agents  # obs + last_action + agent_id

    args = SimpleNamespace(
        hidden_dim=hidden_dim,
        use_rnn=True,
        n_actions=n_actions,
        n_agents=n_agents,
    )

    # Load both agents and move to training device
    print(f"Loading QMIX agent from {qmix_checkpoint}")
    qmix_agent = load_agent(qmix_checkpoint, input_shape, args)
    qmix_agent.to(device)
    print(f"Loading QTRAN agent from {qtran_checkpoint}")
    qtran_agent = load_agent(qtran_checkpoint, input_shape, args)
    qtran_agent.to(device)

    # Create environment with scenario parameters
    env_kw = env_kwargs or {}
    env = gym.make("WSNRouting-v0", **env_kw)
    env.seed(seed)

    # Metrics storage
    all_pdr = []
    all_latency = []
    all_energy_eff = []
    all_throughput = []
    all_returns = []
    all_out_of_range = []
    all_relay_count = []
    all_direct_bs_count = []

    all_wall_step_time_ms_mean = []
    all_wall_step_time_ms_p95 = []
    all_wall_step_time_ms_p99 = []
    all_wall_episode_time_ms = []
    all_peak_memory_mb = []
    all_std_remaining_energy = []
    all_total_consumption_energy = []

    # Also track agreement rate
    total_decisions = 0
    agreements = 0

    rng = np.random.RandomState(seed)

    print(f"\nRunning {n_episodes} episodes with ensemble_mode='{ensemble_mode}' "
          f"(n_agents={n_agents}, n_actions={n_actions})...")
    t_start = time.time()

    for ep in range(n_episodes):
        raw_obs = env.reset()

        # Init hidden states on training device
        qmix_hidden = th.zeros(1, n_agents, hidden_dim, device=device)
        qtran_hidden = th.zeros(1, n_agents, hidden_dim, device=device)

        last_actions = None
        episode_return = 0.0
        done = False
        step = 0
        max_steps = time_limit
        step_times = []
        ep_start = time.perf_counter()

        while not done and step < max_steps:
            _t_step = time.perf_counter()
            # Build observations
            obs_array = build_obs(raw_obs, n_agents, n_actions, obs_size)
            agent_inputs = build_agent_inputs(obs_array, last_actions, n_agents, n_actions, obs_size)
            avail = get_avail_actions(env, n_agents, n_actions)

            # Forward both agents on training device
            inputs_t = th.tensor(agent_inputs, dtype=th.float32, device=device).unsqueeze(0)

            with th.no_grad():
                # Batch all agents in a single forward pass (avoid per-agent Python loop)
                flat_in = inputs_t.view(n_agents, -1)           # (n_agents, input_dim)
                flat_hq = qmix_hidden.view(n_agents, -1)       # (n_agents, hidden_dim)
                flat_ht = qtran_hidden.view(n_agents, -1)       # (n_agents, hidden_dim)
                qmix_q, qmix_hidden = qmix_agent(flat_in, flat_hq)   # (n_agents, n_actions), (n_agents, hidden_dim)
                qtran_q, qtran_hidden = qtran_agent(flat_in, flat_ht)
                qmix_q = qmix_q.unsqueeze(0)                   # (1, n_agents, n_actions)
                qtran_q = qtran_q.unsqueeze(0)
                qmix_hidden = qmix_hidden.unsqueeze(0)         # (1, n_agents, hidden_dim)
                qtran_hidden = qtran_hidden.unsqueeze(0)

            # Mask unavailable actions (use -inf for proper masking)
            avail_t = th.tensor(avail, dtype=th.float32, device=device).unsqueeze(0)
            qmix_q[avail_t == 0] = -float("inf")
            qtran_q[avail_t == 0] = -float("inf")

            # Combine Q-values
            if ensemble_mode == "mean":
                combined_q = (qmix_q + qtran_q) / 2.0
            elif ensemble_mode == "max":
                combined_q = th.max(qmix_q, qtran_q)
            elif ensemble_mode == "softmax_weight":
                # Weight by softmax of max Q-value (confidence-weighted)
                qmix_conf = qmix_q.max(dim=-1, keepdim=True)[0]
                qtran_conf = qtran_q.max(dim=-1, keepdim=True)[0]
                weights = th.softmax(th.cat([qmix_conf, qtran_conf], dim=-1), dim=-1)
                combined_q = weights[:, :, 0:1] * qmix_q + weights[:, :, 1:2] * qtran_q
            else:
                combined_q = (qmix_q + qtran_q) / 2.0

            # Greedy action selection with safety check for all-masked agents
            greedy_actions = combined_q.max(dim=2)[1]  # (1, n_agents)
            # MPS max() on all-inf returns -1; CPU returns 0 — both can be invalid
            invalid = (greedy_actions < 0) | (greedy_actions >= n_actions)
            if invalid.any():
                # Fallback: sample from available actions
                from torch.distributions import Categorical
                safe_avail = avail_t.clone()
                no_valid = (safe_avail.sum(dim=2) == 0)
                if no_valid.any():
                    safe_avail[:, :, -1][no_valid] = 1.0  # BS action fallback
                fallback = Categorical(safe_avail).sample().long()
                greedy_actions[invalid] = fallback[invalid]

            actions = greedy_actions.squeeze(0).cpu().numpy()

            # Epsilon-greedy exploration
            for i in range(n_agents):
                if rng.random() < epsilon:
                    valid_actions = np.where(avail[i] > 0)[0]
                    if len(valid_actions) > 0:
                        actions[i] = rng.choice(valid_actions)

            # Track agreement
            qmix_actions = qmix_q.squeeze(0).cpu().numpy().argmax(axis=1)
            qtran_actions = qtran_q.squeeze(0).cpu().numpy().argmax(axis=1)
            agreements += (qmix_actions == qtran_actions).sum()
            total_decisions += n_agents

            # Step environment
            raw_obs, reward, done, info = env.step(actions.tolist())
            if isinstance(done, list):
                done = all(done)
            if isinstance(reward, list):
                reward = sum(reward)
            episode_return += reward
            last_actions = actions
            step += 1
            step_times.append(time.perf_counter() - _t_step)

        # Collect metrics from env
        unwrapped = env.unwrapped if hasattr(env, 'unwrapped') else env
        if hasattr(unwrapped, 'packet_delivery_ratio'):
            all_pdr.append(float(unwrapped.packet_delivery_ratio))
        if hasattr(unwrapped, 'average_latency'):
            all_latency.append(float(unwrapped.average_latency))
        if hasattr(unwrapped, 'energy_efficiency'):
            all_energy_eff.append(float(unwrapped.energy_efficiency))
        if hasattr(unwrapped, 'network_throughput'):
            all_throughput.append(float(unwrapped.network_throughput))
        if hasattr(unwrapped, 'out_of_range_count'):
            all_out_of_range.append(float(unwrapped.out_of_range_count))
        if hasattr(unwrapped, 'relay_delivery_count'):
            all_relay_count.append(float(unwrapped.relay_delivery_count))
        if hasattr(unwrapped, 'direct_to_bs_count'):
            all_direct_bs_count.append(float(unwrapped.direct_to_bs_count))
        if hasattr(unwrapped, 'remaining_energy'):
            all_std_remaining_energy.append(float(np.std(unwrapped.remaining_energy)))
            total_consumed = unwrapped.n_sensors * 1.0 - float(np.sum(unwrapped.remaining_energy))
            all_total_consumption_energy.append(total_consumed)
        all_returns.append(episode_return)

        # Timing/memory metrics
        ep_elapsed_ms = (time.perf_counter() - ep_start) * 1000.0
        all_wall_episode_time_ms.append(ep_elapsed_ms)
        if step_times:
            _arr = np.asarray(step_times, dtype=float) * 1000.0  # to ms
            all_wall_step_time_ms_mean.append(float(_arr.mean()))
            all_wall_step_time_ms_p95.append(float(np.percentile(_arr, 95)))
            all_wall_step_time_ms_p99.append(float(np.percentile(_arr, 99)))
        proc = psutil.Process()
        all_peak_memory_mb.append(proc.memory_info().rss / (1024 * 1024))

        if (ep + 1) % 50 == 0:
            elapsed = time.time() - t_start
            pdr_so_far = np.mean(all_pdr) if all_pdr else 0
            print(f"  Episode {ep+1}/{n_episodes}: PDR={pdr_so_far:.4f}, "
                  f"agreement={agreements/total_decisions*100:.1f}%, "
                  f"elapsed={elapsed:.1f}s")

    env.close()
    elapsed = time.time() - t_start

    # Print results
    print(f"\n{'='*70}")
    print(f"ENSEMBLE EVALUATION RESULTS ({ensemble_mode} mode)")
    print(f"{'='*70}")
    print(f"  Episodes:          {n_episodes}")
    print(f"  Wall time:         {elapsed:.1f}s ({elapsed/n_episodes*1000:.1f}ms/ep)")
    print(f"  Action agreement:  {agreements/total_decisions*100:.1f}%")
    print(f"  PDR:               {np.mean(all_pdr):.4f} +/- {np.std(all_pdr):.4f}")
    if all_latency:
        print(f"  Avg Latency:       {np.nanmean(all_latency):.4f}")
    if all_energy_eff:
        print(f"  Energy Efficiency: {np.mean(all_energy_eff):.4f}")
    if all_throughput:
        print(f"  Throughput:        {np.mean(all_throughput):.4f}")
    print(f"  Mean Return:       {np.mean(all_returns):.4f}")
    if all_out_of_range:
        print(f"  Out of Range:      {np.mean(all_out_of_range):.1f}")
    if all_relay_count:
        print(f"  Relay Deliveries:  {np.mean(all_relay_count):.1f}")
    if all_direct_bs_count:
        print(f"  Direct BS:         {np.mean(all_direct_bs_count):.1f}")

    # Save results
    results_dir = str(EPYMARL_DIR / "results" / "data")
    os.makedirs(results_dir, exist_ok=True)
    algo_name = f"ENSEMBLE_{ensemble_mode.upper()}"
    seed_tag = os.environ.get('SEED_TAG', '')  # e.g. "_seed42" for multi-seed runs
    version = gym_examples.__version__
    for metric_name, values in [
        ("packet_delivery_ratio", all_pdr),
        ("average_latency", all_latency),
        ("energy_efficiency", all_energy_eff),
        ("network_throughput", all_throughput),
        ("mean_returns", all_returns),
        ("std_remaining_energy", all_std_remaining_energy),
        ("total_consumption_energy", all_total_consumption_energy),
        ("out_of_range_count", all_out_of_range),
        ("relay_delivery_count", all_relay_count),
        ("direct_to_bs_count", all_direct_bs_count),
        ("wall_step_time_ms_mean", all_wall_step_time_ms_mean),
        ("wall_step_time_ms_p95", all_wall_step_time_ms_p95),
        ("wall_step_time_ms_p99", all_wall_step_time_ms_p99),
        ("wall_episode_time_ms", all_wall_episode_time_ms),
        ("peak_memory_mb", all_peak_memory_mb),
    ]:
        if values:
            path = os.path.join(results_dir, f"{metric_name}_{algo_name}{seed_tag}_test_{version}.npy")
            np.save(path, np.array(values))

    print(f"\nResults saved with prefix '{algo_name}'")
    return np.mean(all_pdr)


def find_latest_checkpoint(model_dir):
    """Find the checkpoint with highest timestep."""
    subdirs = [d for d in os.listdir(model_dir) if d.isdigit()]
    if not subdirs:
        return model_dir
    latest = max(subdirs, key=int)
    return os.path.join(model_dir, latest)


def main():
    parser = argparse.ArgumentParser(description="Ensemble QMIX+QTRAN Evaluation")
    parser.add_argument("--n-episodes", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--epsilon", type=float, default=0.01)
    parser.add_argument("--mode", type=str, default="max",
                        choices=["mean", "max", "softmax_weight", "all"])
    parser.add_argument("--qmix-model", type=str, default=None)
    parser.add_argument("--qtran-model", type=str, default=None)
    parser.add_argument("--n-sensors", type=int, required=True,
                        help="Number of sensor agents (must match trained models)")
    parser.add_argument("--coverage-radius", type=float, required=True,
                        help="Coverage radius in meters (passed by pipeline)")
    parser.add_argument("--time-limit", type=int, required=True,
                        help="Max steps per episode (same as env_args.time_limit)")
    args = parser.parse_args()

    n_agents = args.n_sensors
    n_actions = n_agents + 1  # 0..(n-1) relay, n = BS

    # Always pass scenario params to the env — never conditional on defaults
    env_kwargs = {
        "n_sensors": args.n_sensors,
        "coverage_radius": args.coverage_radius,
    }

    # Find model directories
    models_dir = str(EPYMARL_DIR / "results" / "models")

    if args.qmix_model:
        qmix_dir = args.qmix_model
    else:
        qmix_dirs = [d for d in os.listdir(models_dir) if d.startswith("qmix_")]
        if not qmix_dirs:
            print("ERROR: No QMIX model found")
            return
        qmix_dir = os.path.join(models_dir, sorted(qmix_dirs)[-1])

    if args.qtran_model:
        qtran_dir = args.qtran_model
    else:
        qtran_dirs = [d for d in os.listdir(models_dir) if d.startswith("qtran_")]
        if not qtran_dirs:
            print("ERROR: No QTRAN model found")
            return
        qtran_dir = os.path.join(models_dir, sorted(qtran_dirs)[-1])

    qmix_ckpt = find_latest_checkpoint(qmix_dir)
    qtran_ckpt = find_latest_checkpoint(qtran_dir)

    print(f"QMIX checkpoint: {qmix_ckpt}")
    print(f"QTRAN checkpoint: {qtran_ckpt}")
    print(f"Scenario: n_sensors={n_agents}, coverage_radius={args.coverage_radius}")

    modes = ["mean", "max", "softmax_weight"] if args.mode == "all" else [args.mode]

    results = {}
    for mode in modes:
        print(f"\n{'#'*70}")
        print(f"# Ensemble mode: {mode}")
        print(f"{'#'*70}")
        pdr = run_ensemble_evaluation(
            qmix_ckpt, qtran_ckpt,
            n_agents=n_agents,
            n_actions=n_actions,
            n_episodes=args.n_episodes,
            seed=args.seed,
            epsilon=args.epsilon,
            ensemble_mode=mode,
            env_kwargs=env_kwargs,
            time_limit=args.time_limit,
        )
        results[mode] = pdr

    if len(results) > 1:
        print(f"\n{'='*70}")
        print("COMPARISON OF ENSEMBLE MODES")
        print(f"{'='*70}")
        for mode, pdr in sorted(results.items(), key=lambda x: -x[1]):
            print(f"  {mode:20s}: PDR = {pdr:.4f}")


if __name__ == "__main__":
    main()
