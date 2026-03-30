"""Graph-Attentive Policy Fusion (GAPF) for WSN Routing Algorithm Selection.

Two operating modes:

  CAS (Contextual Algorithm Selection) — episode-level:
    GCN encodes topology → p(QMIX | graph) → select one MAC for entire episode.
    Trained via Bernoulli REINFORCE.

  Fusion — step-level:
    GCN encodes topology → α_t per step → softmax(Q) probability fusion.
    Actions sampled from: α·softmax(Q_qmix) + (1-α)·softmax(Q_qtran).
    Trained via Gaussian-logit REINFORCE on step-level log-probs.

Key design choices:
  - Q-values are normalized to probabilities via softmax before mixing
    (eliminates scale mismatch between QMIX and QTRAN Q-values).
  - Proper REINFORCE with correct log-probabilities.
  - ~1k trainable params; QMIX/QTRAN experts are frozen.

Usage:
    cd epymarl
    python GAPF_hybrid_model.py --mode cas   [--train-episodes 500]
    python GAPF_hybrid_model.py --mode fusion [--train-episodes 500]
"""

import argparse
import glob
import os
import sys
import time
import random

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import Adam
from torch.nn.utils import clip_grad_norm_
from torch.distributions import Categorical, Normal

try:
    import psutil
except ImportError:
    psutil = None

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_script_dir = os.path.dirname(os.path.abspath(__file__))
_src_dir = os.path.join(_script_dir, "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from controllers.basic_controller import BasicMAC
from components.episode_buffer import EpisodeBatch
from components.transforms import OneHot
from envs import REGISTRY as env_REGISTRY
from utils.paths import RESULTS_DATA_DIR, RESULTS_MODELS_DIR

try:
    import gym_examples
    GYM_VERSION = gym_examples.__version__
except Exception:
    GYM_VERSION = "unknown"

RESULTS_DIR = RESULTS_DATA_DIR + os.sep
MODELS_DIR = RESULTS_MODELS_DIR

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Architecture constants (not pipeline-dependent)
GNN_EMBED_DIM = 16
META_HIDDEN = 64
STATE_FEAT_DIM = 4
NODE_FEAT_DIM = 4
LR = 3e-3
ALGO_NAME = "GAPF"
RETURNS_WINDOW = 50  # running-average window size for training progress

# Pipeline-dependent values — set from CLI args in main()
EPISODE_LIMIT = None
COVERAGE_RADIUS = None
MAC_DEVICE = "cpu"  # must match QMIX/QTRAN training device (set in main())


# ---------------------------------------------------------------------------
# GNN Encoder
# ---------------------------------------------------------------------------

class GCNEncoder(nn.Module):
    """2-layer GCN with mean-pool readout."""

    def __init__(self, in_features=NODE_FEAT_DIM, hidden_dim=GNN_EMBED_DIM,
                 out_dim=GNN_EMBED_DIM):
        super().__init__()
        self.W1 = nn.Linear(in_features, hidden_dim, bias=False)
        self.W2 = nn.Linear(hidden_dim, out_dim, bias=False)

    def forward(self, X, A_hat):
        H = F.relu(A_hat @ self.W1(X))
        Z = A_hat @ self.W2(H)
        return Z.mean(dim=0)


# ---------------------------------------------------------------------------
# Meta-Controllers
# ---------------------------------------------------------------------------

class CASController(nn.Module):
    """Episode-level: graph embedding → logit for P(select QMIX)."""

    def __init__(self, embed_dim=GNN_EMBED_DIM, hidden_dim=META_HIDDEN):
        super().__init__()
        self.fc1 = nn.Linear(embed_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, 1)

    def forward(self, z):
        """Returns raw logit (pre-sigmoid)."""
        x = F.relu(self.fc1(z))
        return self.fc2(x).squeeze(-1)


class FusionController(nn.Module):
    """Step-level: (graph_embedding, state_features) → logit for alpha."""

    def __init__(self, embed_dim=GNN_EMBED_DIM, state_dim=STATE_FEAT_DIM,
                 hidden_dim=META_HIDDEN):
        super().__init__()
        self.fc1 = nn.Linear(embed_dim + state_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, 1)

    def forward(self, z, state_features):
        """Returns raw logit (pre-sigmoid)."""
        x = torch.cat([z, state_features], dim=-1)
        x = F.relu(self.fc1(x))
        return self.fc2(x).squeeze(-1)


class GAPFModel(nn.Module):
    """Wraps GCN + mode-specific controller."""

    def __init__(self, mode="cas"):
        super().__init__()
        self.mode = mode
        self.gcn = GCNEncoder()
        if mode == "cas":
            self.controller = CASController()
        else:
            self.controller = FusionController()

    def encode_graph(self, X, A_hat):
        return self.gcn(X, A_hat)

    def get_logit(self, z, state_features=None):
        if self.mode == "cas":
            return self.controller(z)
        else:
            return self.controller(z, state_features)


# ---------------------------------------------------------------------------
# Graph helpers
# ---------------------------------------------------------------------------

def build_adjacency(positions, radius):
    N = positions.shape[0]
    diff = positions[:, None, :] - positions[None, :, :]
    dists = np.linalg.norm(diff, axis=2)
    A = (dists <= radius).astype(np.float32)
    np.fill_diagonal(A, 0.0)
    return A


def normalize_adjacency(A):
    A_tilde = A + np.eye(A.shape[0], dtype=np.float32)
    d = A_tilde.sum(axis=1)
    d_inv_sqrt = 1.0 / np.sqrt(np.maximum(d, 1e-8))
    D_inv_sqrt = np.diag(d_inv_sqrt)
    return (D_inv_sqrt @ A_tilde @ D_inv_sqrt).astype(np.float32)


def build_node_features(positions, A, bs_pos, field_size):
    dist_to_bs = np.linalg.norm(positions - bs_pos, axis=1)
    max_dist = max(dist_to_bs.max(), 1e-8)
    degree = A.sum(axis=1)
    max_degree = max(degree.max(), 1e-8)
    return np.stack([
        positions[:, 0] / field_size,
        positions[:, 1] / field_size,
        dist_to_bs / max_dist,
        degree / max_degree,
    ], axis=1).astype(np.float32)


# ---------------------------------------------------------------------------
# Environment / MAC helpers
# ---------------------------------------------------------------------------

def get_unwrapped_env(env):
    return env.original_env.__dict__['env'].__dict__


def get_state_features(wsn_cache, step):
    """Build state features from cached env internals (avoid repeated dict traversal)."""
    remaining = wsn_cache['remaining_energy']
    n_sensors = len(remaining)
    mean_e = float(remaining.mean())
    std_e = float(remaining.std())
    frac_delivered = float(wsn_cache['packets_delivered']) / max(n_sensors, 1)
    return torch.tensor([mean_e, std_e, frac_delivered, step / float(EPISODE_LIMIT)],
                        dtype=torch.float32)


def extract_episode_metrics(env, wsn_cache=None):
    observations = env.get_obs()
    perf = wsn_cache if wsn_cache is not None else get_unwrapped_env(env)
    return {
        "episode_return": None,
        "std_remaining_energy": float(np.std([o[0] for o in observations])),
        "total_consumption_energy": float(np.sum([o[1] for o in observations])),
        "mean_remaining_energy": float(np.mean([o[0] for o in observations])),
        "network_throughput": float(perf['network_throughput']),
        "energy_efficiency": float(perf['energy_efficiency']),
        "packet_delivery_ratio": float(perf['packet_delivery_ratio']),
        "average_latency": float(perf['average_latency']),
    }


def find_checkpoint(algo_prefix, seed):
    """Find the latest checkpoint for the given algo trained with the given seed."""
    seed_str = f"_seed{seed}_"
    pattern = os.path.join(MODELS_DIR, f"{algo_prefix}_seed*")
    dirs = sorted(glob.glob(pattern))
    if not dirs:
        raise FileNotFoundError(f"No checkpoint matching {pattern}")

    matched = [d for d in dirs if seed_str in os.path.basename(d)]
    if not matched:
        raise FileNotFoundError(
            f"No checkpoint for {algo_prefix} with seed={seed} in {MODELS_DIR}. "
            f"Available: {[os.path.basename(d) for d in dirs]}"
        )
    model_dir = matched[-1]

    steps = []
    for name in os.listdir(model_dir):
        try:
            steps.append(int(name))
        except ValueError:
            continue
    if not steps:
        raise FileNotFoundError(f"No step subdirectories in {model_dir}")
    path = os.path.join(model_dir, str(max(steps)))
    print(f"  {algo_prefix.upper()} checkpoint (seed={seed}): {path}")
    return path


def make_mac_args(n_agents, n_actions, device="cpu"):
    from types import SimpleNamespace as SN
    return SN(
        n_agents=n_agents, n_actions=n_actions, obs_shape=None,
        hidden_dim=64, use_rnn=True, agent="rnn",
        obs_last_action=True, obs_agent_id=True,
        agent_output_type="q", action_selector="epsilon_greedy",
        epsilon_start=0.01, epsilon_finish=0.01, epsilon_anneal_time=1,
        evaluation_epsilon=0.01, mask_before_softmax=True, device=device,
    )


def _safe_actions(actions, avail):
    """Fix invalid action indices (MPS max() bug or all-masked)."""
    invalid = (actions < 0) | (actions >= avail.shape[-1])
    if invalid.any():
        safe_avail = avail.clone().float()
        safe_avail[(safe_avail.sum(dim=-1, keepdim=True) == 0)
                   .expand_as(safe_avail)] = 1.0
        fallback = Categorical(safe_avail).sample().long()
        actions = actions.clone()
        actions[invalid] = fallback[invalid]
    return actions


# ---------------------------------------------------------------------------
# Episode runners
# ---------------------------------------------------------------------------

def _encode_topology(env, gapf_model):
    """GCN-encode the current episode's sensor topology (once per episode)."""
    wsn = get_unwrapped_env(env)
    positions = wsn['sensor_positions']
    radius = wsn.get('coverage_radius', COVERAGE_RADIUS)
    A = build_adjacency(positions, radius=radius)
    A_hat = normalize_adjacency(A)
    # Read BS position and field bounds from the env module (not hardcoded)
    env_mod = type(env.original_env.__dict__['env'])
    import importlib
    wsn_mod = importlib.import_module(env_mod.__module__)
    bs_pos = getattr(wsn_mod, 'base_station_position')
    field_size = float(getattr(wsn_mod, 'upper_bound') - getattr(wsn_mod, 'lower_bound'))
    X = build_node_features(positions, A, bs_pos=bs_pos, field_size=field_size)
    z = gapf_model.encode_graph(
        torch.tensor(X, dtype=torch.float32),
        torch.tensor(A_hat, dtype=torch.float32),
    )
    return z


def run_episode_cas(env, mac_qmix, mac_qtran, gapf_model,
                    scheme, groups, preprocess, training=False):
    """CAS mode: select QMIX or QTRAN for the entire episode."""
    env.reset()
    wsn_cache = get_unwrapped_env(env)  # cache once per episode
    z = _encode_topology(env, gapf_model)

    # Episode-level decision
    logit = gapf_model.get_logit(z)
    p_qmix = torch.sigmoid(logit)

    if training:
        use_qmix = (torch.rand(1).item() < p_qmix.item())
        # Bernoulli log-prob
        if use_qmix:
            log_prob = torch.log(p_qmix.clamp(min=1e-8))
        else:
            log_prob = torch.log((1.0 - p_qmix).clamp(min=1e-8))
    else:
        use_qmix = (p_qmix.item() > 0.5)
        log_prob = None

    mac = mac_qmix if use_qmix else mac_qtran
    mac.init_hidden(batch_size=1)

    batch = EpisodeBatch(scheme, groups, batch_size=1,
                         max_seq_length=EPISODE_LIMIT + 1,
                         preprocess=preprocess, device=MAC_DEVICE)

    episode_return = 0.0
    step_times = []
    terminated = False

    for t in range(EPISODE_LIMIT):
        if terminated:
            break
        t0 = time.perf_counter()

        batch.update({
            "state": [env.get_state()],
            "avail_actions": [env.get_avail_actions()],
            "obs": [env.get_obs()],
        }, ts=t)

        with torch.no_grad():
            q = mac.forward(batch, t)

        avail = batch["avail_actions"][:, t].float()
        q_masked = q.clone()
        q_masked[avail == 0] = -float("inf")
        actions = q_masked.max(dim=2)[1]
        actions = _safe_actions(actions, avail)

        reward, terminated, info = env.step(actions[0])
        episode_return += reward

        batch.update({
            "actions": actions.unsqueeze(-1),
            "reward": [(reward,)],
            "terminated": [(terminated != info.get("episode_limit", False),)],
        }, ts=t)

        step_times.append(time.perf_counter() - t0)

    metrics = extract_episode_metrics(env, wsn_cache)
    metrics["episode_return"] = episode_return
    metrics["selected_algo"] = "QMIX" if use_qmix else "QTRAN"
    metrics["p_qmix"] = p_qmix.item()

    return episode_return, [log_prob] if log_prob is not None else [], metrics, step_times


def run_episode_fusion(env, mac_qmix, mac_qtran, gapf_model,
                       scheme, groups, preprocess, training=False,
                       explore_sigma=0.5):
    """Fusion mode: step-level softmax(Q) probability mixing."""
    env.reset()
    wsn_cache = get_unwrapped_env(env)  # cache once per episode
    z = _encode_topology(env, gapf_model)

    mac_qmix.init_hidden(batch_size=1)
    mac_qtran.init_hidden(batch_size=1)

    batch = EpisodeBatch(scheme, groups, batch_size=1,
                         max_seq_length=EPISODE_LIMIT + 1,
                         preprocess=preprocess, device=MAC_DEVICE)

    episode_return = 0.0
    log_probs = []
    step_times = []
    terminated = False

    for t in range(EPISODE_LIMIT):
        if terminated:
            break
        t0 = time.perf_counter()

        batch.update({
            "state": [env.get_state()],
            "avail_actions": [env.get_avail_actions()],
            "obs": [env.get_obs()],
        }, ts=t)

        avail = batch["avail_actions"][:, t].float()  # (1, n_agents, n_actions)

        # Meta-controller: topology + state → logit → alpha
        sf = get_state_features(wsn_cache, t)
        logit = gapf_model.get_logit(z, sf)

        if training:
            # Sample from Normal(logit, sigma) for exploration
            dist = Normal(logit, explore_sigma)
            sampled_logit = dist.sample()
            log_probs.append(dist.log_prob(sampled_logit))
            alpha = torch.sigmoid(sampled_logit)
        else:
            alpha = torch.sigmoid(logit)

        # Q-values from frozen experts (on MAC_DEVICE, e.g. MPS)
        with torch.no_grad():
            q_qmix = mac_qmix.forward(batch, t)   # (1, n_agents, n_actions)
            q_qtran = mac_qtran.forward(batch, t)

        # Convert Q-values to action probabilities via masked softmax.
        # This normalizes scales — critical for meaningful fusion.
        large_neg = torch.finfo(q_qmix.dtype).min
        q_qmix_m = q_qmix.clone()
        q_qtran_m = q_qtran.clone()
        q_qmix_m[avail == 0] = large_neg
        q_qtran_m[avail == 0] = large_neg

        p_qmix = F.softmax(q_qmix_m, dim=-1)   # (1, n_agents, n_actions)
        p_qtran = F.softmax(q_qtran_m, dim=-1)

        # Zero out unavailable (softmax might assign tiny mass)
        p_qmix = p_qmix * avail
        p_qtran = p_qtran * avail

        # Fuse probabilities (move alpha to MAC device if GAPF runs on CPU)
        alpha = alpha.to(p_qmix.device)
        p_fused = alpha * p_qmix + (1.0 - alpha) * p_qtran
        # Renormalize per agent
        p_sum = p_fused.sum(dim=-1, keepdim=True).clamp(min=1e-8)
        p_fused = p_fused / p_sum

        # Greedy action from fused probabilities
        actions = p_fused.argmax(dim=-1)  # (1, n_agents)
        actions = _safe_actions(actions, avail)

        reward, terminated, info = env.step(actions[0])
        episode_return += reward

        batch.update({
            "actions": actions.unsqueeze(-1),
            "reward": [(reward,)],
            "terminated": [(terminated != info.get("episode_limit", False),)],
        }, ts=t)

        step_times.append(time.perf_counter() - t0)

    metrics = extract_episode_metrics(env, wsn_cache)
    metrics["episode_return"] = episode_return
    metrics["alpha_mean"] = alpha.item() if isinstance(alpha, torch.Tensor) else alpha

    return episode_return, log_probs, metrics, step_times


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train(env, mac_qmix, mac_qtran, gapf_model,
          scheme, groups, preprocess,
          n_episodes=None, lr=LR, mode="cas"):
    """Train GAPF meta-controller via REINFORCE."""
    optimizer = Adam(gapf_model.parameters(), lr=lr)
    baseline = None  # init from first episode
    returns_window = []
    pdr_window = []

    # Accumulate per-episode training metrics for .npy saving
    train_metrics = {
        "mean_returns": [],
        "packet_delivery_ratio": [],
        "total_consumption_energy": [],
        "std_remaining_energy": [],
        "network_throughput": [],
        "energy_efficiency": [],
        "average_latency": [],
    }

    run_fn = run_episode_cas if mode == "cas" else run_episode_fusion

    print(f"\n{'='*60}")
    print(f"GAPF Training ({mode.upper()} mode): {n_episodes} episodes, lr={lr}")
    print(f"{'='*60}")
    t_start = time.perf_counter()

    # Exploration sigma schedule (fusion mode)
    sigma_start = 1.0
    sigma_end = 0.2

    for ep in range(n_episodes):
        # Anneal exploration
        frac = ep / max(n_episodes - 1, 1)
        sigma = sigma_start + (sigma_end - sigma_start) * frac

        if mode == "cas":
            ret, log_probs, metrics, _ = run_fn(
                env, mac_qmix, mac_qtran, gapf_model,
                scheme, groups, preprocess, training=True,
            )
        else:
            ret, log_probs, metrics, _ = run_fn(
                env, mac_qmix, mac_qtran, gapf_model,
                scheme, groups, preprocess, training=True,
                explore_sigma=sigma,
            )

        # REINFORCE update
        if baseline is None:
            baseline = ret
        advantage = ret - baseline
        baseline = 0.95 * baseline + 0.05 * ret

        if log_probs and abs(advantage) > 1e-8:
            # Sum of log-probs × advantage
            total_log_prob = torch.stack(log_probs).sum()
            policy_loss = -advantage * total_log_prob
            optimizer.zero_grad()
            policy_loss.backward()
            clip_grad_norm_(gapf_model.parameters(), 1.0)
            optimizer.step()

        # Record training metrics
        train_metrics["mean_returns"].append(ret)
        for key in train_metrics:
            if key != "mean_returns" and key in metrics:
                train_metrics[key].append(metrics[key])

        returns_window.append(ret)
        pdr_window.append(metrics['packet_delivery_ratio'])
        if len(returns_window) > RETURNS_WINDOW:
            returns_window.pop(0)
            pdr_window.pop(0)

        if (ep + 1) % RETURNS_WINDOW == 0:
            mean_ret = np.mean(returns_window)
            mean_pdr = np.mean(pdr_window) * 100
            elapsed = time.perf_counter() - t_start
            extra = ""
            if mode == "cas":
                extra = f"  p_qmix={metrics.get('p_qmix', 0):.3f}  sel={metrics.get('selected_algo', '?')}"
            else:
                extra = f"  alpha={metrics.get('alpha_mean', 0):.3f}  sigma={sigma:.2f}"
            print(f"  [{ep+1:4d}/{n_episodes}]  "
                  f"ret={ret:7.1f}  mean50={mean_ret:7.1f}  "
                  f"PDR_50={mean_pdr:5.1f}%{extra}  "
                  f"elapsed={elapsed:.0f}s")

    training_time = time.perf_counter() - t_start
    print(f"\nTraining complete in {training_time:.1f}s ({training_time/60:.1f} min)")

    # Save training metrics as .npy files
    os.makedirs(RESULTS_DIR, exist_ok=True)
    seed_tag = os.getenv('SEED_TAG', '')
    version = GYM_VERSION
    print(f"  Saving GAPF training metrics...")
    for metric_name, values in train_metrics.items():
        if values:
            fname = f"{metric_name}_{ALGO_NAME}{seed_tag}_{version}.npy"
            np.save(os.path.join(RESULTS_DIR, fname), np.array(values))
            print(f"    {fname} ({len(values)} episodes)")

    return training_time


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate(env, mac_qmix, mac_qtran, gapf_model,
             scheme, groups, preprocess,
             n_episodes=None, mode="cas"):
    """Evaluate GAPF deterministically."""
    run_fn = run_episode_cas if mode == "cas" else run_episode_fusion

    print(f"\n{'='*60}")
    print(f"GAPF Evaluation ({mode.upper()} mode): {n_episodes} episodes")
    print(f"{'='*60}")

    all_metrics = {
        "mean_returns": [],
        "std_remaining_energy": [],
        "total_consumption_energy": [],
        "network_throughput": [],
        "energy_efficiency": [],
        "packet_delivery_ratio": [],
        "average_latency": [],
        "wall_step_time_ms_mean": [],
        "wall_step_time_ms_p95": [],
        "wall_step_time_ms_p99": [],
        "wall_episode_time_ms": [],
        "peak_memory_mb": [],
    }

    # CAS-specific tracking
    cas_selections = {"QMIX": 0, "QTRAN": 0}

    proc = psutil.Process(os.getpid()) if psutil else None
    t_eval_start = time.perf_counter()

    for ep in range(n_episodes):
        t_ep_start = time.perf_counter()

        ret, _, metrics, step_times = run_fn(
            env, mac_qmix, mac_qtran, gapf_model,
            scheme, groups, preprocess, training=False,
        )

        # Timing
        arr = np.asarray(step_times, dtype=float) * 1000.0
        all_metrics["wall_step_time_ms_mean"].append(float(arr.mean()))
        all_metrics["wall_step_time_ms_p95"].append(float(np.percentile(arr, 95)))
        all_metrics["wall_step_time_ms_p99"].append(float(np.percentile(arr, 99)))
        all_metrics["wall_episode_time_ms"].append(
            float((time.perf_counter() - t_ep_start) * 1000.0))

        # Memory
        peak_rss = 0.0
        if proc:
            try:
                peak_rss = proc.memory_info().rss / (1024 * 1024)
            except Exception:
                pass
        all_metrics["peak_memory_mb"].append(float(peak_rss))

        # Performance
        all_metrics["mean_returns"].append(ret)
        all_metrics["std_remaining_energy"].append(metrics["std_remaining_energy"])
        all_metrics["total_consumption_energy"].append(metrics["total_consumption_energy"])
        all_metrics["network_throughput"].append(metrics["network_throughput"])
        all_metrics["energy_efficiency"].append(metrics["energy_efficiency"])
        all_metrics["packet_delivery_ratio"].append(metrics["packet_delivery_ratio"])
        all_metrics["average_latency"].append(metrics["average_latency"])

        if mode == "cas":
            sel = metrics.get("selected_algo", "?")
            if sel in cas_selections:
                cas_selections[sel] += 1

        if (ep + 1) % 100 == 0:
            elapsed = time.perf_counter() - t_eval_start
            mean_pdr = np.nanmean(all_metrics["packet_delivery_ratio"]) * 100
            extra = ""
            if mode == "cas":
                extra = f"  QMIX={cas_selections['QMIX']} QTRAN={cas_selections['QTRAN']}"
            print(f"  [{ep+1:4d}/{n_episodes}]  PDR={mean_pdr:5.1f}%{extra}  "
                  f"elapsed={elapsed:.0f}s")

    eval_time = time.perf_counter() - t_eval_start

    pdr = np.nanmean(all_metrics["packet_delivery_ratio"]) * 100
    lat = np.nanmean(all_metrics["average_latency"])
    eng = np.nanmean(all_metrics["total_consumption_energy"])
    thr = np.nanmean(all_metrics["network_throughput"])
    ee = np.nanmean(all_metrics["energy_efficiency"])

    print(f"\nEvaluation complete in {eval_time:.1f}s ({eval_time/60:.1f} min)")
    print(f"\n  PDR        = {pdr:.1f}%")
    print(f"  Latency    = {lat:.2f} ms")
    print(f"  Energy     = {eng:.4f} J")
    print(f"  Throughput = {thr:.2f}")
    print(f"  EE         = {ee:.2f}")

    if mode == "cas":
        total = cas_selections["QMIX"] + cas_selections["QTRAN"]
        if total > 0:
            print(f"\n  Algorithm selection: QMIX={cas_selections['QMIX']} "
                  f"({cas_selections['QMIX']/total*100:.0f}%) "
                  f"QTRAN={cas_selections['QTRAN']} "
                  f"({cas_selections['QTRAN']/total*100:.0f}%)")

    return all_metrics


# ---------------------------------------------------------------------------
# Save results
# ---------------------------------------------------------------------------

def save_results(all_metrics, training_time, param_count):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    version = GYM_VERSION
    seed_tag = os.getenv('SEED_TAG', '')  # e.g. "_seed42" for multi-seed runs
    for metric_name, values in all_metrics.items():
        fname = f"{metric_name}_{ALGO_NAME}{seed_tag}_test_{version}.npy"
        path = os.path.join(RESULTS_DIR, fname)
        np.save(path, np.array(values))
        print(f"  Saved {fname} ({len(values)} episodes)")
    np.save(os.path.join(RESULTS_DIR, f"training_time_s_{ALGO_NAME}{seed_tag}_{version}.npy"),
            np.array([training_time]))
    np.save(os.path.join(RESULTS_DIR, f"model_param_count_{ALGO_NAME}{seed_tag}_{version}.npy"),
            np.array([param_count]))
    np.save(os.path.join(RESULTS_DIR, f"model_size_mb_{ALGO_NAME}{seed_tag}_{version}.npy"),
            np.array([param_count * 4 / (1024 * 1024)]))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global EPISODE_LIMIT, COVERAGE_RADIUS

    parser = argparse.ArgumentParser(description="GAPF: Graph-Attentive Policy Fusion")
    parser.add_argument("--mode", type=str, default="cas",
                        choices=["cas", "fusion"],
                        help="cas=episode-level selection, fusion=step-level Q-probability mixing")
    # All pipeline-dependent params — no hardcoded defaults that could silently
    # diverge from QMIX/QTRAN. Values are passed by run_algos.ps1.
    parser.add_argument("--train-episodes", type=int, required=True,
                        help="Number of GAPF meta-controller training episodes")
    parser.add_argument("--eval-episodes", type=int, required=True,
                        help="Number of evaluation episodes (same as test_nepisode)")
    parser.add_argument("--seed", type=int, required=True,
                        help="Random seed (same seed used for QMIX/QTRAN training)")
    parser.add_argument("--time-limit", type=int, required=True,
                        help="Max steps per episode (same as env_args.time_limit)")
    parser.add_argument("--n-sensors", type=int, required=True,
                        help="Number of sensor agents")
    parser.add_argument("--coverage-radius", type=float, required=True,
                        help="WSN coverage radius in metres")
    parser.add_argument("--device", type=str, default="auto",
                        choices=["auto", "cpu", "mps", "cuda"])
    parser.add_argument("--lr", type=float, default=LR)
    args = parser.parse_args()

    # Set module-level variables from pipeline args
    global MAC_DEVICE
    EPISODE_LIMIT = args.time_limit
    COVERAGE_RADIUS = args.coverage_radius

    # Device
    if args.device == "auto":
        if torch.backends.mps.is_available():
            device = "mps"
            os.environ.setdefault("PYTORCH_MPS_HIGH_WATERMARK_RATIO", "0.0")
            os.environ.setdefault("PYTORCH_MPS_LOW_WATERMARK_RATIO", "0.0")
        elif torch.cuda.is_available():
            device = "cuda"
        else:
            device = "cpu"
    else:
        device = args.device
    MAC_DEVICE = device
    print(f"Device: {device}")
    print(f"Mode:   {args.mode.upper()}")
    print(f"Seed:   {args.seed}")
    print(f"Config: time_limit={EPISODE_LIMIT}, n_sensors={args.n_sensors}, "
          f"coverage_radius={COVERAGE_RADIUS}")
    print(f"Episodes: train={args.train_episodes}, eval={args.eval_episodes}")

    # Seeds
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    random.seed(args.seed)

    # Environment
    print(f"\nCreating WSN environment (gym_examples v{GYM_VERSION})...")
    env_kwargs = dict(
        key="gym_examples:WSNRouting-v0",
        time_limit=EPISODE_LIMIT,
        pretrained_wrapper=None,
        seed=args.seed,
        n_sensors=args.n_sensors,
        coverage_radius=args.coverage_radius,
    )
    env = env_REGISTRY["gymma"](**env_kwargs)
    env_info = env.get_env_info()
    n_agents = env_info["n_agents"]
    n_actions = env_info["n_actions"]
    obs_shape = env_info["obs_shape"]
    state_shape = env_info["state_shape"]
    print(f"  n_agents={n_agents}, n_actions={n_actions}, "
          f"obs_shape={obs_shape}, state_shape={state_shape}")

    # Scheme
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
    mac_scheme["actions_onehot"] = {"vshape": (n_actions,), "dtype": torch.float32,
                                    "group": "agents"}

    # Load pre-trained MACs on the SAME device used for QMIX/QTRAN training.
    # RNN hidden states diverge between CPU and MPS due to float32 precision,
    # causing catastrophic action selection failure if device mismatches.
    print(f"\nLoading pre-trained checkpoints for seed={args.seed}...")
    mac_args = make_mac_args(n_agents, n_actions, device=device)

    mac_qmix = BasicMAC(mac_scheme, groups, mac_args)
    mac_qtran = BasicMAC(mac_scheme, groups, mac_args)

    qmix_path = find_checkpoint("qmix", seed=args.seed)
    qtran_path = find_checkpoint("qtran", seed=args.seed)
    mac_qmix.load_models(qmix_path)
    mac_qtran.load_models(qtran_path)
    mac_qmix.agent.to(device)
    mac_qtran.agent.to(device)

    for p in mac_qmix.parameters():
        p.requires_grad_(False)
    for p in mac_qtran.parameters():
        p.requires_grad_(False)
    mac_qmix.agent.eval()
    mac_qtran.agent.eval()
    print(f"  QMIX and QTRAN agents loaded and frozen ({device})")

    # GAPF model
    gapf = GAPFModel(mode=args.mode)
    param_count = sum(p.numel() for p in gapf.parameters())
    print(f"\nGAPF model ({args.mode}): {param_count} parameters (CPU)")

    # Train
    training_time = train(
        env, mac_qmix, mac_qtran, gapf,
        scheme, groups, preprocess,
        n_episodes=args.train_episodes, lr=args.lr,
        mode=args.mode,
    )

    # Evaluate
    gapf.eval()
    with torch.no_grad():
        all_metrics = evaluate(
            env, mac_qmix, mac_qtran, gapf,
            scheme, groups, preprocess,
            n_episodes=args.eval_episodes, mode=args.mode,
        )

    # Save
    print(f"\nSaving results to {RESULTS_DIR}...")
    save_results(all_metrics, training_time, param_count)
    print("\nDone.")


if __name__ == "__main__":
    main()
