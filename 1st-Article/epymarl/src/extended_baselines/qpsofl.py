"""QPSOFL: Quantum Particle Swarm Optimization with Fuzzy Logic for WSN routing.

A non-RL baseline that selects cluster heads (CHs) via QPSO, then uses a
Mamdani-type Fuzzy Inference System (FIS) to choose relay nodes for multi-hop
data forwarding to the base station.

Algorithm overview (per episode round):
    1. CH Selection (QPSO): find m cluster head positions that minimise a
       combined energy + distance fitness function using Sobol-initialised
       quantum particles with Lévy flight mutations.
    2. Cluster Formation: assign each sensor to its nearest CH.
    3. FIS Relay Selection: for each CH, evaluate candidate neighbours on
       three fuzzy inputs (residual energy, energy deviation, relay distance)
       and select the best relay via centroid defuzzification.
    4. Data Transmission: CMs → CHs → relay/BS, updating energy & latency.

Reference: https://www.nature.com/articles/s41598-024-69360-0
"""

import numpy as np
import os
from pathlib import Path
import gym
import gym_examples
import importlib
import math 
import time
try:
    import torch
except Exception as e:
    raise ImportError(
        "QPSOFL requires 'torch' (used for Sobol initialization via torch.quasirandom.SobolEngine). "
        "Install torch or run this baseline in an environment that includes torch."
    ) from e
try:
    import psutil
except Exception:
    psutil = None

tol = 1e-6  # Tolerance for fitness improvement
alpha = 0.6 # co-efficiency ranging in [0, 1] used to regulate the factors of energy and distance.
w1 = 1.0 # factor in the contraction expansion coefficient
w0 = 0.5 # factor in the contraction expansion coefficient

ERES = ['very_less','less','normal','much','very_much'] # Linguistic variables for residual energy
EDEV = ['very_low','low','normal','high','very_high'] # Linguistic variables for energy deviation
DRY  = ['very_near','near','normal','far','very_far'] # Linguistic variables for relay distance
PROB = ['very_low','low','quite_low','normal','quite_high','high','very_high'] # Linguistic variables for probability

def _src_dir() -> str:
    """Return the epymarl/src directory."""
    return str(Path(__file__).resolve().parent.parent)

# Ensure epymarl/src is on sys.path so we can import utils.paths
import sys as _sys
_sd = _src_dir()
if _sd not in _sys.path:
    _sys.path.insert(0, _sd)

from utils.paths import RESULTS_DATA_DIR
DATA_DIR = RESULTS_DATA_DIR


def _sobol_uniform(n_draws: int, dim: int, seed: int = 42) -> np.ndarray:
    """Generate Sobol quasi-random points in [0, 1) without SciPy.

    Uses PyTorch's SobolEngine (available with torch==1.13.1).
    """
    engine = torch.quasirandom.SobolEngine(dimension=dim, scramble=True, seed=seed)
    return engine.draw(n_draws).cpu().numpy()

def _make_env(**kwargs):
    try:
        return gym.make("WSNRouting-v0", **kwargs)
    except Exception:
        return gym.make("gym_examples:WSNRouting-v0", **kwargs)

# Parse CLI args early so module-level env can use them
import argparse as _argparse
_parser = _argparse.ArgumentParser(add_help=False)
_parser.add_argument("--n-sensors", type=int, required=True,
                     help="Number of sensor agents (passed by pipeline)")
_parser.add_argument("--coverage-radius", type=float, required=True,
                     help="WSN coverage radius in metres (passed by pipeline)")
_parser.add_argument("--seed", type=int, required=True,
                     help="Random seed (passed by pipeline)")
_parser.add_argument("--episodes", type=int, default=None, help="Number of episodes (overrides QPSOFL_EPISODES env var)")
_parser.add_argument("--steps", type=int, default=None, help="Max steps per episode (overrides QPSOFL_STEPS env var)")
_cli_args, _ = _parser.parse_known_args()
# Always pass scenario params to the env — never conditional on defaults
_env_kwargs = {
    "n_sensors": _cli_args.n_sensors,
    "coverage_radius": _cli_args.coverage_radius,
}

try:
    env = _make_env(**_env_kwargs)
except FileNotFoundError:
    # Defensive: ensure directory exists then retry once
    os.makedirs(DATA_DIR, exist_ok=True)
    env = _make_env(**_env_kwargs)
# Unwrap to the base WSNRoutingEnv (avoids Gym's OrderEnforcing wrapper)
raw = getattr(env, "unwrapped", env)
mod = importlib.import_module(raw.__class__.__module__)
E0 = getattr(mod, "initial_energy")  # Initial energy of each sensor node (identical for all sensors)

# Precomputed Lévy constant (beta=1.5) — avoids recomputing gamma every call
_LEVY_BETA = 1.5
_LEVY_DELTA = (math.gamma(1 + _LEVY_BETA) * math.sin(math.pi * _LEVY_BETA / 2) /
               (math.gamma((1 + _LEVY_BETA) / 2) * _LEVY_BETA * 2 ** ((_LEVY_BETA - 1) / 2))) ** (1 / _LEVY_BETA)


def levy_flight_batch(n, rng):
    """Vectorized Lévy flight: return (n,) samples in one numpy call."""
    u = rng.random(n)
    v = rng.random(n)
    return 0.01 * u * _LEVY_DELTA / (np.abs(v).clip(1e-12) ** (1 / _LEVY_BETA))


def repair_indices(indices, n, Eres):
    '''
    Repair the indices to ensure they are valid cluster head indexes.
    - indices: array of shape (m,), the indices to be repaired.
    - n: int, total number of sensor nodes.
    - Eres: array of shape (n,), residual energy of each sensor node.
    
    Returns:
    - repaired_indices: array of shape (m,), the repaired indices.
    '''
    # Coerce to a simple numeric ndarray first (indices may come from different backends)
    idx_arr = np.asarray(indices, dtype=float)
    repaired = np.rint(idx_arr).astype(int)
    repaired[repaired < 0] = 0
    repaired[repaired > (n - 1)] = n - 1
    unique, counts = np.unique(repaired, return_counts=True)
    duplicates = unique[counts > 1]
    for dup in duplicates:
        dup_indices = np.where(repaired == dup)[0]
        for idx in dup_indices[1:]:
            candidates = [i for i in range(n) if i not in repaired]
            if candidates:
                # Prefer nodes with higher residual energy
                candidates.sort(key=lambda x: -Eres[x])
                repaired[idx] = candidates[0]
            else:
                # If no candidates left, just assign a random valid index
                repaired[idx] = np.random.randint(0, n)

    return repaired

def fitness_function(cluster_indexes, m, Eres, sensor_positions, BS_position, R=None, alpha=alpha):
    '''
    Fitness function to evaluate the quality of a set of cluster heads.
    
    Inputs:
    - Eres: array of shape (n,), residual energy of each sensor node.
    - sensor_positions: array of shape (n, 2), positions of each sensor node.
    - BS_position: array of shape (2,), position of the base station.
    - cluster_indexes: array of shape (m,), indexes of the selected cluster heads.
    - m: number of cluster heads.
    - alpha: co-efficiency to balance energy and distance factors.

    Outputs:
    - fitness: float, fitness value of the selected cluster heads.
    '''
    n = Eres.shape[0]
    cluster_indexes = repair_indices(cluster_indexes, n, Eres)
    membership = clusters_formation(cluster_indexes, n, sensor_positions)
    cluster_Eres = Eres[cluster_indexes]  # Residual energy of cluster heads

    s = 0.0
    min_ch_bs = float("inf")
    for i in range(m):
        CH_i_index = cluster_indexes[i]
        sensor_positions_cluster_i = sensor_positions[membership[CH_i_index]]  # Positions of sensors in cluster i
        if sensor_positions_cluster_i.size > 0:
            distances_to_CH_i = np.linalg.norm(sensor_positions_cluster_i - sensor_positions[CH_i_index], axis=1)
            avg_dist = float(np.mean(distances_to_CH_i)) if distances_to_CH_i.size > 0 else 0.0
        else:
            avg_dist = 0.0
        distance_CH_i_to_BS = np.linalg.norm(sensor_positions[CH_i_index] - BS_position)  # Distance from cluster head i to base station
        s += avg_dist + distance_CH_i_to_BS
        if distance_CH_i_to_BS < min_ch_bs:
            min_ch_bs = float(distance_CH_i_to_BS)
    # Soft penalty if no CH is within BS range: penalize how far the closest CH exceeds R
    penalty = 0.0
    if R is not None and np.isfinite(min_ch_bs):
        overflow = max(0.0, min_ch_bs - R)
        # Normalize by R to keep penalty scale comparable across configs
        penalty = overflow / max(R, 1e-9)
    # Optional scale via env var BS_PENALTY_SCALE (default 1.0)
    try:
        penalty_scale = float(os.environ.get("BS_PENALTY_SCALE", "1.0"))
    except Exception:
        penalty_scale = 1.0
    objective = (s / m) + penalty_scale * penalty
    return alpha / np.sum(cluster_Eres) + (1 - alpha) * objective

def ch_selection(m, Itrmax, Np, n, sensor_positions, Eres, BS_position, R, w0=w0, w1=w1):
    '''
    Cluster head selection using QPSOFL algorithm.
    We follow the approach described in algorithm 1 of the reference paper.

    Inputs:
    - n: int, total number of sensor nodes.
    - m: int, number of cluster heads to select.
    - Itrmax: int, maximum number of iterations.
    - Np: int, number of particles in the swarm.

    Outputs:
    - gBest: array of shape (m,), indexes of the selected cluster heads.
    '''

    m = int(m)
    n = int(n)
    Itrmax = int(Itrmax)
    Np = int(Np)

    # Sobol initialization (SciPy-free)
    U = np.asarray(_sobol_uniform(Np, m, seed=_cli_args.seed), dtype=float)
    # Initial particle positions (continuous representation of indices)
    P = U * float(n - 1)
    Pbest = P.copy().astype(float, copy=False)
    # Single RNG reused (avoid per-particle construction overhead)
    rng = np.random.default_rng(_cli_args.seed)
    # Precompute initial fitness values (batch evaluation)
    fitness_P = batch_fitness(P, m=m, Eres=Eres, sensor_positions=sensor_positions, BS_position=BS_position, R=R)
    # Personal best fitness cache
    fitness_Pbest = fitness_P.copy()
    # Global best (avoid repeated fitness_function calls)
    gBest_idx = int(np.argmax(fitness_P))
    gBest = P[gBest_idx].copy()
    gBest_fitness = fitness_P[gBest_idx]
    # Stagnation counters
    stagnation = np.zeros(Np, dtype=int)
    # Early stopping: if gBest hasn't improved for `patience` iterations, stop
    patience = 5
    iters_without_improvement = 0
    # Main loop of QPSOFL
    for itr in range(Itrmax):
        # Sample U away from 0 to avoid log(0)
        U = rng.random((Np, m)).astype(float, copy=False)
        alpha_ce = w0 * (w0 - w1) * ((Itrmax - itr) / Itrmax)
        # Mean of personal best positions (used for all particles this iteration)
        Pbest_bar = np.mean(Pbest, axis=0)

        # ── Vectorized position update ──────────────────────────────
        # Identify stagnated vs active particles
        stag_mask = stagnation >= 2  # (Np,)
        active_mask = ~stag_mask

        # --- Handle stagnated particles (reinitialize) ---
        stag_idx = np.where(stag_mask)[0]
        for i in stag_idx:
            alternate_candidates = np.concatenate((np.arange(i), np.arange(i+1, Np)))
            i0 = rng.choice(alternate_candidates)
            sigma = np.cos(0.5 * math.pi * ((itr / Itrmax) ** 2)) * np.abs(P[i] - P[i0])
            P[i] = rng.normal(loc=P[i], scale=sigma)
            stagnation[i] = 0

        # --- Vectorized update for active particles ---
        act_idx = np.where(active_mask)[0]
        if act_idx.size > 0:
            n_act = act_idx.size
            k = rng.random(n_act)
            rf = rng.random((n_act, m))
            Pit = rf * Pbest[act_idx] + (1 - rf) * gBest  # (n_act, m)
            U_act = np.clip(U[act_idx], 1e-12, 1.0)
            log_term = np.log(1.0 / U_act)  # (n_act, m)
            abs_diff = np.abs(Pbest_bar - P[act_idx])  # (n_act, m)

            # Vectorized levy flights (single numpy call instead of Python loop)
            levy_vals = levy_flight_batch(n_act, rng)  # (n_act,)

            # Branch: k >= 0.5 → lévy, else → standard
            high_k = k >= 0.5
            low_k = ~high_k
            P_new = np.empty((n_act, m), dtype=float)
            if np.any(high_k):
                h_idx = np.where(high_k)[0]
                P_new[h_idx] = levy_vals[h_idx, None] * (P[act_idx[h_idx]] - Pit[h_idx]) + alpha_ce * abs_diff[h_idx] * log_term[h_idx]
            if np.any(low_k):
                l_idx = np.where(low_k)[0]
                P_new[l_idx] = Pit[l_idx] - alpha_ce * abs_diff[l_idx] * log_term[l_idx]
            P[act_idx] = P_new

        # ── Vectorized bounds & NaN recovery ────────────────────────
        finite_mask = np.all(np.isfinite(P), axis=1)
        bad_particles = np.where(~finite_mask)[0]
        for i in bad_particles:
            P[i] = np.asarray(Pbest[i], dtype=float)
            if not np.all(np.isfinite(P[i])):
                P[i] = rng.random(m).astype(float, copy=False) * float(n - 1)
        P = np.clip(P, 0, n - 1)

        # ── Batch fitness evaluation (vectorized across all particles) ──
        fitness_P = batch_fitness(P, m=m, Eres=Eres, sensor_positions=sensor_positions, BS_position=BS_position, R=R)

        # Personal best updates (vectorized)
        improved = fitness_P > (fitness_Pbest + tol)
        Pbest[improved] = P[improved].copy()
        fitness_Pbest[improved] = fitness_P[improved]
        stagnation[improved] = 0
        stagnation[~improved] += 1

        # Global best update
        best_this_iter = int(np.argmax(fitness_P))
        if fitness_P[best_this_iter] > gBest_fitness + tol:
            gBest = P[best_this_iter].copy()
            gBest_fitness = fitness_P[best_this_iter]
            iters_without_improvement = 0
        else:
            iters_without_improvement += 1

        # Early stopping: converged
        if iters_without_improvement >= patience:
            break
    return repair_indices(gBest, n, Eres)

def batch_fitness(P_all, m, Eres, sensor_positions, BS_position, R=None, alpha_val=alpha):
    """Evaluate fitness for ALL particles at once (fully vectorized — no Python loop).

    P_all: (Np, m) continuous particle positions.
    Returns: (Np,) fitness values.
    """
    Np_local = P_all.shape[0]
    n = Eres.shape[0]
    try:
        penalty_scale = float(os.environ.get("BS_PENALTY_SCALE", "1.0"))
    except Exception:
        penalty_scale = 1.0

    # Repair all particles to integer indices
    all_idx = np.rint(np.clip(P_all, 0, n - 1)).astype(int)  # (Np, m)

    # Cluster assignment for all particles at once:
    ch_pos = sensor_positions[all_idx]  # (Np, m, 2)

    # Distance from every sensor to every CH for every particle: (Np, n, m)
    diffs = sensor_positions[None, :, None, :] - ch_pos[:, None, :, :]  # (Np, n, m, 2)
    D = np.linalg.norm(diffs, axis=3)  # (Np, n, m)

    # Closest CH for each sensor in each particle: (Np, n)
    closest_local = np.argmin(D, axis=2)  # (Np, n)

    # Distance from each sensor to its closest CH: (Np, n)
    sensor_to_ch_dist = np.take_along_axis(D, closest_local[:, :, None], axis=2).squeeze(2)

    # ── Fully vectorized per-cluster aggregation (no Python loop) ──
    # One-hot encode cluster assignments: (Np, n, m)
    one_hot = np.zeros((Np_local, n, m), dtype=np.float32)
    np.put_along_axis(one_hot, closest_local[:, :, None], 1.0, axis=2)

    # Weighted sum of distances per cluster: (Np, m)
    cluster_sums = np.einsum('pn,pnm->pm', sensor_to_ch_dist, one_hot)
    # Cluster sizes: (Np, m)
    cluster_counts = one_hot.sum(axis=1)  # (Np, m)
    cluster_counts = np.maximum(cluster_counts, 1.0)  # avoid div by zero
    avg_dists = cluster_sums / cluster_counts  # (Np, m)

    # CH-to-BS distances: (Np, m)
    ch_to_bs = np.linalg.norm(ch_pos - BS_position, axis=2)  # (Np, m)

    # Objective per particle: (Np,)
    objectives = (avg_dists + ch_to_bs).sum(axis=1) / m

    # Penalty per particle: (Np,)
    if R is not None:
        min_ch_bs = ch_to_bs.min(axis=1)  # (Np,)
        overflow = np.maximum(0.0, min_ch_bs - R)
        penalties = overflow / max(R, 1e-9)
    else:
        penalties = np.zeros(Np_local)

    # Residual energy term per particle: (Np,)
    cluster_Eres_sum = np.maximum(Eres[all_idx].sum(axis=1), 1e-12)  # (Np,)

    fitness_vals = alpha_val / cluster_Eres_sum + (1 - alpha_val) * (objectives + penalty_scale * penalties)
    return fitness_vals


def clusters_formation(cluster_indexes, n, sensor_positions):
    '''
    Form clusters based on the selected cluster heads (vectorized).

    Inputs:
    - cluster_indexes: array of shape (m,), indexes of the selected cluster heads.
    - sensor_positions: array of shape (n, 2), positions of each sensor node.
    - n: int, total number of sensor nodes.

    Outputs:
    - clusters: Dictionary mapping each cluster head index to a list of sensor node indexes in its cluster.
    '''
    cluster_indexes = np.asarray(cluster_indexes, dtype=int)
    ch_pos = sensor_positions[cluster_indexes]  # (m, 2)
    # Distance matrix from all sensors to each cluster head: (n, m)
    diffs = sensor_positions[:, None, :] - ch_pos[None, :, :]
    D = np.linalg.norm(diffs, axis=2)
    # For each sensor, find closest CH index (local index 0..m-1)
    closest_local = np.argmin(D, axis=1)
    # Map local CH indices back to global sensor indices
    closest_global = cluster_indexes[closest_local]
    clusters = {int(ch): [] for ch in cluster_indexes}
    # Assign sensors excluding the CHs themselves
    for i in range(n):
        ch = int(closest_global[i])
        if i != ch:
            clusters[ch].append(i)
    return clusters


def residual_energy(cluster_indexes, R, sensor_positions, energy_residual):
    '''
    Calculate the residual energy for candidate relay nodes of each cluster head.
    
    Inputs:
    - cluster_indexes: array of shape (m,), indexes of the selected cluster heads.
    - sensor_positions: array of shape (n, 2), positions of each sensor node.
    - R: float, communication radius.
    - energy_residual: array of shape (n,), residual energy of each sensor node.


    Outputs:
    - Eres: dictionnary of shape (m,): keys are cluster head indexes, values are list of tuples (residual energy, candidate relay nodes).
    '''
    Eres = {}
    CH_positions = sensor_positions[cluster_indexes]
    for idx in cluster_indexes:
        Eres[idx] = []
        CH_neighbors_indicators = np.linalg.norm(CH_positions - sensor_positions[idx], axis=1) <= R
        CH_neighbors_local = np.where(CH_neighbors_indicators)[0]
        CH_neighbors_global = [cluster_indexes[j] for j in CH_neighbors_local]
        Eres_neighbors = energy_residual[CH_neighbors_global]
        for i, neighbor_global in enumerate(CH_neighbors_global):
            if neighbor_global != idx:
                Eres[idx].append((float(Eres_neighbors[i]), int(neighbor_global)))

    return Eres


def energy_deviation(cluster_indexes, sensor_positions, R, energy_residual):
    '''
    Calculate the energy deviation for candidate relay nodes of each cluster head.
    
    Inputs:
    - energy_residual: array of shape (n,), residual energy of each sensor node.
    - cluster_indexes: array of shape (m,), indexes of the selected cluster heads.
    - sensor_positions: array of shape (n, 2), positions of each sensor node.
    - R: float, communication radius.

    Outputs:
    - Edev: dictionnary of shape (m,): keys are cluster head indexes, values are list of tuples (energy deviation, candidate relay nodes).
    '''
    CH_positions = sensor_positions[cluster_indexes]
    Edev = {}
    for idx in cluster_indexes:
        Edev[idx] = []
        CH_neighbors_indicators = np.linalg.norm(CH_positions - sensor_positions[idx], axis=1) <= R
        CH_neighbors_local = np.where(CH_neighbors_indicators)[0]
        for j in CH_neighbors_local:
            neighbor_global = cluster_indexes[j]
            if neighbor_global != idx:
                CH_neighbors_indicators_of_idy = np.linalg.norm(CH_positions - sensor_positions[neighbor_global], axis=1) <= R
                CH_neighbors_local_of_idy = np.where(CH_neighbors_indicators_of_idy)[0]
                CH_neighbors_global_of_idy = [cluster_indexes[k] for k in CH_neighbors_local_of_idy]
                Eres_neighbors_of_idy = energy_residual[CH_neighbors_global_of_idy]
                local_mean = float(np.mean(Eres_neighbors_of_idy)) if Eres_neighbors_of_idy.size > 0 else float(energy_residual[neighbor_global])
                Edev[idx].append((abs(float(energy_residual[neighbor_global]) - local_mean), int(neighbor_global)))

    return Edev


def relay_distance(cluster_indexes, sensor_positions, BS_position, R):
    '''
    Calculate the relay distance for candidate relay nodes of each cluster head.
    
    Inputs:
    - cluster_indexes: array of shape (m,), indexes of the selected cluster heads.
    - sensor_positions: array of shape (n, 2), positions of each sensor node.
    - BS_position: array of shape (2,), position of the base station.
    - R: float, communication radius.

    Outputs:
    - Dry: dictionnary of shape (m,): keys are cluster head indexes, values are list of tuples (relay distance, candidate relay nodes).
    '''
    CH_positions = sensor_positions[cluster_indexes]
    Dry = {}
    for idx in cluster_indexes:
        Dry[idx] = []
        # neighbors within communication radius R
        CH_neighbors_indicators = np.linalg.norm(CH_positions - sensor_positions[idx], axis=1) <= R
        CH_neighbors_local = np.where(CH_neighbors_indicators)[0]
        for j in CH_neighbors_local:
            neighbor_global = cluster_indexes[j]
            if neighbor_global != idx:
                u = (sensor_positions[idx] - BS_position) / np.linalg.norm(sensor_positions[idx] - BS_position)
                nvec = np.array([-u[1], u[0]])  # Perpendicular vector in 2D
                dr = np.abs(np.dot(sensor_positions[neighbor_global] - sensor_positions[idx], nvec))
                dp1 = np.linalg.norm(sensor_positions[neighbor_global] - sensor_positions[idx])**2
                dp2 = 2 * R * np.dot(sensor_positions[neighbor_global] - sensor_positions[idx], u)
                dp3 = R**2
                dp = np.sqrt(dp1 - dp2 + dp3)
                Dry[idx].append((dr + dp, int(neighbor_global)))

    return Dry

def trapmf(x, a, b, c, d):
        '''
        Trapezoidal membership function.
        '''
        if x <= a or x >= d:
            return 0.0
        if a < x < b:
            return (x - a) / (b - a) if b > a else 1.0
        if b <= x <= c:
            return 1.0
        if c < x < d:
            return (d - x) / (d - c)
        return 0.0
        
def trimf(x, a, b, c):
    '''
    Triangular membership function.
    '''
    if x <= a or x >= c:
        return 0.0
    if a < x < b:
        return (x - a) / (b - a)
    return (c - x) / (c - b)

class FIS:
    '''
    Fuzzy Inference System for adapting QPSO parameters.

    Attributes:
    - Eres: Residual energy of each sensor node.
    - Edev: Energy deviation.
    - Dry: Relay distance.

    Methods:
    - fuzzify: accepting the normalized crisp inputs and converting 
them to linguistic variables.
    - fuzzy_rules: obtaining a set of if then rules used for decision making from 
expert experience.
    - infer: reasoning using the fuzzy rules to obtain the fuzzy output.
    - defuzzify: converting the fuzzy output into crisp values Prob.
    '''

    def __init__(self, Eres, Edev, Dry, ERES=ERES, EDEV=EDEV, DRY=DRY, R=None, sensor_positions=None, BS_position=None):
        self.Eres = Eres
        self.Edev = Edev
        self.Dry = Dry  # Keep raw distances; normalize during fuzzification
        self.sensor_positions = sensor_positions
        self.BS_position = BS_position
        self.R = R
        self.RULES = {(er, ed, dr): self.fuzzy_rules(i, j, k) 
                      for (i, er) in enumerate(ERES)
                      for (j, ed) in enumerate(EDEV)
                      for (k, dr) in enumerate(DRY)}

    def fuzzify_residual_energy(self):
        # Fuzzify the residual energy using membership functions
        fuzzified = {}
        for ch in self.Eres:
            fuzzified[ch] = {}
            for eres, relay in self.Eres[ch]:
                fuzzified[ch][relay] = {
                    'very_less': trapmf(eres, 0.00, 0.00, 0.025, 0.25),
                    'less': trimf(eres, 0.10, 0.25, 0.50),
                    'normal': trimf(eres, 0.35, 0.50, 0.75),
                    'much': trimf(eres, 0.625, 0.75, 0.90),
                    'very_much': trapmf(eres, 0.775, 0.975, 1.00, 1.00)
                }
        return fuzzified

    def fuzzify_energy_deviation(self):
        # Fuzzify the energy deviation using membership functions
        fuzzified = {}
        for ch in self.Edev:
            fuzzified[ch] = {}
            for edev, relay in self.Edev[ch]:
                fuzzified[ch][relay] = {
            'very_low': trapmf(edev, 0.00, 0.00, 0.025, 0.25),
            'low': trimf(edev, 0.10, 0.25, 0.50),
            'normal': trimf(edev, 0.35, 0.50, 0.75),
            'high': trimf(edev, 0.625, 0.75, 0.90),
            'very_high': trapmf(edev, 0.775, 0.975, 1.00, 1.00)
        }
        return fuzzified
    
    def fuzzify_relay_distance(self):
        # Fuzzify the relay distance using membership functions
        fuzzified = {}
        for ch in self.Dry:
            fuzzified[ch] = {}
            for dry, relay in self.Dry[ch]:
                denom = (3 * self.R) if (self.R is not None and self.R > 0) else 1.0
                ndry = dry / denom
                fuzzified[ch][relay] = {
                    'very_near': trapmf(ndry, 0.00, 0.00, 0.025, 0.25),
                    'near': trimf(ndry, 0.10, 0.25, 0.50),
                    'normal': trimf(ndry, 0.35, 0.50, 0.75),
                    'far': trimf(ndry, 0.625, 0.75, 0.90),
                    'very_far': trapmf(ndry, 0.775, 0.975, 1.00, 1.00)
                }
        return fuzzified

    def fuzzy_rules(self, i, j, k):
        # Define fuzzy rules based on expert knowledge
        s = i - j - k
        if s == -8 or s == -7:
            return 'very_low'
        elif s == -6 or s == -5:
            return 'low'
        elif s == -4 or s == -3:
            return 'quite_low'
        elif s == -2 or s == -1:
            return 'normal'
        elif s == 0 or s == 1:
            return 'quite_high'
        elif s == 2 or s == 3:
            return 'high'
        else:
            return 'very_high'

    def fuzzify_prob(self, x):
        # Fuzzify the probability using membership functions
        return {
            'very_low': trapmf(x, 0.00, 0.00, 0.02, 0.15),
            'low': trimf(x, 0.08, 0.17, 0.33),
            'quite_low': trimf(x, 0.25, 0.33, 0.50),
            'normal': trimf(x, 0.42, 0.50, 0.67),
            'quite_high': trimf(x, 0.58, 0.67, 0.83),
            'high': trimf(x, 0.75, 0.83, 0.92),
            'very_high': trapmf(x, 0.85, 0.98, 1.00, 1.00)
        }

    def infer_defuzzify(self):
        Edev_fuzz = self.fuzzify_energy_deviation()
        Eres_fuzz = self.fuzzify_residual_energy()
        Dry_fuzz = self.fuzzify_relay_distance()

        x = np.linspace(0, 1, 201)  # Discretize output space
        # Build membership arrays per label
        prob_mfs = {label: np.array([self.fuzzify_prob(xi)[label] for xi in x]) for label in PROB}

        res = {}
        for ch in Edev_fuzz:
            res[ch] = {}
            for relay in Edev_fuzz[ch]:
                final_output = np.zeros_like(x)
                for (er, ed, dr), prob in self.RULES.items():
                    mu_er = Eres_fuzz[ch][relay][er]
                    mu_ed = Edev_fuzz[ch][relay][ed]
                    mu_dr = Dry_fuzz[ch][relay][dr]
                    firing_strength = min(mu_er, mu_ed, mu_dr)
                    if firing_strength > 0:
                        clipped_output = np.minimum(prob_mfs[prob], firing_strength)
                        final_output = np.maximum(final_output, clipped_output)  # Aggregate outputs
                # defuzzification using centroid method
                res[ch][relay] = np.sum(x * final_output) / np.sum(final_output) if np.sum(final_output) > 0 else 0.0
        return res
    
    def find_final_relays(self):
        '''
        Find the final relay nodes for each cluster head based on the defuzzified probabilities.
        
        Outputs:
        - final_relays: Dictionary mapping each cluster head index to its selected relay node index.
        '''
        probs = self.infer_defuzzify()
        final_relays = {}
        for ch, rel_map in probs.items():
            if not rel_map:
                continue
            # If we can compute distances to BS, prefer candidates within BS range; else fall back to prob only
            if self.sensor_positions is not None and self.BS_position is not None and self.R is not None:
                def relay_score(item):
                    relay_idx, prob = item
                    # Distance of candidate relay to BS
                    d_bs = np.linalg.norm(self.sensor_positions[int(relay_idx)] - self.BS_position)
                    within_bs = d_bs <= self.R
                    # Prefer within_bs first, then higher prob, then closer to BS
                    return (1 if within_bs else 0, float(prob), -float(d_bs))
                best_relay = max(rel_map.items(), key=relay_score)[0]
            else:
                best_relay = max(rel_map.items(), key=lambda item: item[1])[0]
            final_relays[ch] = best_relay
        return final_relays 

if __name__ == "__main__":
    m = 15  # Number of cluster heads
    # Maximum number of iterations (allow env override)
    try:
        Itrmax = int(os.environ.get("QPSOFL_ITRMAX", "50"))
    except Exception:
        Itrmax = 50
    # Allow overriding steps and episodes via env vars for easier experimentation
    if _cli_args.steps is not None:
        Nsteps = _cli_args.steps
    else:
        try:
            Nsteps = int(os.environ.get("QPSOFL_STEPS", "100"))
        except Exception:
            Nsteps = 100  # Number of steps maximum per episode (must match time_limit)
    # Number of particles in the swarm (allow env override; power of 2 recommended for Sobol)
    try:
        Np = int(os.environ.get("QPSOFL_NP", "32"))
    except Exception:
        Np = 32
    if _cli_args.episodes is not None:
        Nepisodes = _cli_args.episodes
    else:
        try:
            Nepisodes = int(os.environ.get("QPSOFL_EPISODES", "1000"))
        except Exception:
            Nepisodes = 1000  # Number of episodes
    # Lightweight progress reporting cadence (episodes)
    try:
        PROGRESS_EVERY = int(os.environ.get("PROGRESS_EVERY", "10"))
    except Exception:
        PROGRESS_EVERY = 10
    # Optional profiling to address near real-time measurements
    try:
        PROFILE = bool(int(os.environ.get("QPSOFL_PROFILE", "1")))
    except Exception:
        PROFILE = False

    network_throughputs = []
    energy_efficiencies = []
    packet_delivery_ratios = []
    average_latencies = []
    total_consumption_energies = []
    std_residual_energies = []
    # Minimal feasibility timing (per-episode)
    wall_step_time_ms_mean_list = []
    wall_episode_time_ms_list = []
    wall_step_time_ms_p95_list = []
    wall_step_time_ms_p99_list = []
    peak_memory_mb_list = []

    for episode in range(Nepisodes):
        _ep_start = time.perf_counter()
        _peak_rss = 0
        _proc = psutil.Process(os.getpid()) if psutil else None

        # Per-episode profiling accumulators
        if PROFILE:
            t_ch_select = []
            t_decision = []  # clusters + maps + FIS
            t_tx = []        # transmissions to CHs and to relays/BS
            t_step = []
            try:
                import tracemalloc
                tracemalloc.start()
            except Exception:
                tracemalloc = None

        obs = raw.reset() # ensures remaining_energy exists and is initialized
        Eres = np.array(raw.remaining_energy, dtype=float) # shape: (n_sensors,)
        number_of_packets = np.array(raw.number_of_packets, dtype=int) # shape: (n_sensors,)
        sensor_positions = np.array(raw.sensor_positions, dtype=float) # shape: (n_sensors, 2)
        R = getattr(raw, "coverage_radius")
        n = getattr(raw, "n_sensors")
        base_station_position = getattr(mod, "base_station_position")
        latency_per_hop = getattr(mod, "latency_per_hop")

        network_throughput = None
        energy_efficiency = None
        packet_delivery_ratio = None
        average_latency = None

        packets_delivered = 0
        total_latency = 0
        packet_latency = np.zeros(n)  # Latency for each packet
        total_energy_consumed = 0
        total_packets_sent_by_sensors = 0
        number_of_steps = 0
        # Per-episode operation counters (feasibility proxies)
        op_candidates_total = 0
        op_membership_evals_total = 0
        op_rules_considered_total = 0
        op_distance_evals_total = 0

        for step in range(Nsteps): # We are running rounds inside each episode
            if PROFILE:
                t0 = time.perf_counter()
            number_of_steps += 1
            # CH selection
            if PROFILE:
                t1 = time.perf_counter()
            gBest = ch_selection(m=m, Itrmax=Itrmax, Np=Np, n=n, sensor_positions=sensor_positions, Eres=Eres, BS_position=base_station_position, R=R)
            if PROFILE:
                t_ch_select.append(time.perf_counter() - t1)
            membership = clusters_formation(cluster_indexes=gBest, n=n, sensor_positions=sensor_positions)
            # Use normalized energies (0..1) for the FIS inputs
            if PROFILE:
                t2 = time.perf_counter()
            residual_energy_map = residual_energy(cluster_indexes=gBest, R=R, sensor_positions=sensor_positions, energy_residual=Eres / E0)
            energy_deviation_map = energy_deviation(cluster_indexes=gBest, sensor_positions=sensor_positions, R=R, energy_residual=Eres / E0)
            relay_distance_map = relay_distance(cluster_indexes=gBest, sensor_positions=sensor_positions, BS_position=base_station_position, R=R)
            fis = FIS(Eres=residual_energy_map, Edev=energy_deviation_map, Dry=relay_distance_map, R=R, sensor_positions=sensor_positions, BS_position=base_station_position)
            final_relays = fis.find_final_relays()
            # Operation counts (proxies)
            m_curr = len(gBest)
            candidates = int(sum(len(v) for v in residual_energy_map.values()))
            op_candidates_total += candidates
            op_membership_evals_total += candidates * 15  # 5 MF per input × 3 inputs
            op_rules_considered_total += candidates * 125  # 5×5×5 rules
            op_distance_evals_total += (n - m_curr) * m_curr + m_curr * m_curr + candidates
            if PROFILE:
                t_decision.append(time.perf_counter() - t2)
            # CMs transmit data to CHs, then CHs to their relays (update residual energy and number of packets)
            if PROFILE:
                t3 = time.perf_counter()
            for ch in membership:
                for sensor in membership[ch]:
                    if Eres[sensor] <= 0 or number_of_packets[sensor] <= 0:
                        continue  # Dead node or no packets to send
                    distance = np.linalg.norm(sensor_positions[sensor] - sensor_positions[ch])
                    if distance > R:
                        continue  # Out of communication range
                    trx_power = raw.transmission_energy(number_of_packets[sensor], distance)
                    rx_power = raw.reception_energy(number_of_packets[sensor])
                    if Eres[sensor] < trx_power:
                        continue  # Not enough energy to transmit
                    Eres[sensor] -= trx_power
                    total_energy_consumed += trx_power
                    total_packets_sent_by_sensors += number_of_packets[sensor]
                    if Eres[ch] < rx_power:
                        packet_latency[sensor] = 0 # reset latency if CH cannot receive
                        number_of_packets[sensor] = 0 # packets are lost
                        continue  # Not enough energy to receive
                    Eres[ch] -= rx_power
                    # update metrics
                    total_energy_consumed += rx_power
                    packet_latency[ch] = packet_latency[sensor] + latency_per_hop  # Increment latency by 1 hop
                    packet_latency[sensor] = 0  # reset latency for sensor after transmission
                    # update number of packets
                    number_of_packets[ch] += number_of_packets[sensor]
                    number_of_packets[sensor] = 0  # packets have been sent
            for ch in membership.keys():
                if Eres[ch] <= 0 or number_of_packets[ch] <= 0:
                    continue  # Dead node or no packets to send
                # Try direct transmission to BS first
                dist_bs = np.linalg.norm(sensor_positions[ch] - base_station_position)
                trx_bs = raw.transmission_energy(number_of_packets[ch], dist_bs)
                if dist_bs <= R and Eres[ch] >= trx_bs:
                    Eres[ch] -= trx_bs
                    # metrics for direct BS
                    total_energy_consumed += trx_bs
                    packets_delivered += number_of_packets[ch]
                    total_packets_sent_by_sensors += number_of_packets[ch]
                    total_latency += packet_latency[ch] + latency_per_hop
                    packet_latency[ch] = 0
                    number_of_packets[ch] = 0
                    continue

                # Otherwise try relaying if a candidate exists
                relay = final_relays.get(ch, None)
                if relay is None:
                    continue
                dist = np.linalg.norm(sensor_positions[relay] - sensor_positions[ch])
                if dist > R:
                    continue  # Out of communication range
                trx_power = raw.transmission_energy(number_of_packets[ch], dist)
                rx_power = raw.reception_energy(number_of_packets[ch])
                if Eres[ch] < trx_power:
                    continue  # Not enough energy to transmit                
                # apply energy costs
                Eres[ch] -= trx_power
                total_energy_consumed += trx_power
                total_packets_sent_by_sensors += number_of_packets[ch]

                if Eres[relay] < rx_power:
                    packet_latency[ch] = 0 # reset latency if relay cannot receive
                    number_of_packets[ch] = 0 # packets are lost
                    continue  # Not enough energy to receive
                # apply energy costs
                Eres[relay] -= rx_power
                total_energy_consumed += rx_power
                # latency and packet transfer
                packet_latency[relay] = packet_latency[ch] + latency_per_hop
                packet_latency[ch] = 0
                number_of_packets[relay] += number_of_packets[ch]
                number_of_packets[ch] = 0
            if PROFILE:
                t_tx.append(time.perf_counter() - t3)
                t_step.append(time.perf_counter() - t0)
            # Track peak memory (RSS) with minimal overhead
            if _proc is not None:
                try:
                    _rss = _proc.memory_info().rss
                    if _rss > _peak_rss:
                        _peak_rss = _rss
                except Exception:
                    pass
        # End of episode metrics
        network_throughput = packets_delivered / number_of_steps if number_of_steps > 0 else 0
        energy_efficiency = packets_delivered / total_energy_consumed if total_energy_consumed > 0 else 0
        packet_delivery_ratio = packets_delivered / total_packets_sent_by_sensors if total_packets_sent_by_sensors > 0 else 0
        # Latency semantics: if no packets delivered, allow env-controlled fallback
        # `LATENCY_NO_DELIVERY_VALUE`: "nan" (default) or a numeric value (e.g., "0")
        if packets_delivered > 0:
            average_latency = (total_latency / packets_delivered)
        else:
            _lat_fallback_raw = os.environ.get("LATENCY_NO_DELIVERY_VALUE", "nan").strip().lower()
            if _lat_fallback_raw == "nan":
                average_latency = float('nan')
            else:
                try:
                    average_latency = float(_lat_fallback_raw)
                except Exception:
                    average_latency = float('nan')
        # New metrics: total energy consumption (from initial energy) and std of residual energy at episode end
        total_consumption_energy = float(n * E0 - np.sum(Eres))
        std_residual_energy = float(np.std(Eres))

        network_throughputs.append(network_throughput)
        energy_efficiencies.append(energy_efficiency)
        packet_delivery_ratios.append(packet_delivery_ratio)
        average_latencies.append(average_latency)
        total_consumption_energies.append(total_consumption_energy)
        std_residual_energies.append(std_residual_energy)

        # Minimal feasibility timing per-episode (avoid heavy profile detail)
        _ep_ms = (time.perf_counter() - _ep_start) * 1000.0
        wall_episode_time_ms_list.append(float(_ep_ms))
        if PROFILE and t_step:
            _t_arr = np.asarray(t_step, dtype=float)
            wall_step_time_ms_mean = float(_t_arr.mean() * 1000.0)
            wall_step_time_ms_p95 = float(np.percentile(_t_arr, 95) * 1000.0)
            wall_step_time_ms_p99 = float(np.percentile(_t_arr, 99) * 1000.0)
        else:
            wall_step_time_ms_mean = float(_ep_ms / max(number_of_steps, 1))
            wall_step_time_ms_p95 = wall_step_time_ms_mean
            wall_step_time_ms_p99 = wall_step_time_ms_mean
        wall_step_time_ms_mean_list.append(wall_step_time_ms_mean)
        peak_memory_mb = float((_peak_rss / (1024.0 * 1024.0)) if _peak_rss > 0 else 0.0)
        # Optional: store p95 and peak memory in local lists
        try:
            wall_step_time_ms_p95_list
        except NameError:
            wall_step_time_ms_p95_list = []
            peak_memory_mb_list = []
        wall_step_time_ms_p95_list.append(float(wall_step_time_ms_p95))
        wall_step_time_ms_p99_list.append(float(wall_step_time_ms_p99))
        peak_memory_mb_list.append(peak_memory_mb)

        # Minimal per-episode print only (concise)
        print(
            f"Episode {episode + 1}: Throughput={network_throughput}, EnergyEff={energy_efficiency}, "
            f"PDR={packet_delivery_ratio}, Latency={average_latency}, "
            f"ConsEnergy={total_consumption_energy}, Std(Eres)={std_residual_energy}"
        )

        if PROFILE:
            def stats(xs):
                if not xs:
                    return 0.0, 0.0, 0.0
                import numpy as _np
                a = _np.array(xs, dtype=float)
                return float(a.mean()), float(_np.percentile(a, 90)), float(_np.percentile(a, 95))
            m_ch, p90_ch, p95_ch = stats(t_ch_select)
            m_dec, p90_dec, p95_dec = stats(t_decision)
            m_tx, p90_tx, p95_tx = stats(t_tx)
            m_st, p90_st, p95_st = stats(t_step)
            peak_mem = None
            try:
                if tracemalloc:
                    current, peak = tracemalloc.get_traced_memory()
                    peak_mem = peak / (1024*1024)
                    tracemalloc.stop()
            except Exception:
                pass
            print(
                f"Profile (episode {episode + 1}): "
                f"CHsel mean/p90/p95={m_ch*1000:.2f}/{p90_ch*1000:.2f}/{p95_ch*1000:.2f} ms, "
                f"Decision mean/p90/p95={m_dec*1000:.2f}/{p90_dec*1000:.2f}/{p95_dec*1000:.2f} ms, "
                f"TX mean/p90/p95={m_tx*1000:.2f}/{p90_tx*1000:.2f}/{p95_tx*1000:.2f} ms, "
                f"Step mean/p90/p95={m_st*1000:.2f}/{p90_st*1000:.2f}/{p95_st*1000:.2f} ms" +
                (f", PeakMem={peak_mem:.2f} MB" if peak_mem is not None else "")
            )

        # Periodic running mean/std progress for long runs
        if PROGRESS_EVERY > 0 and ((episode + 1) % PROGRESS_EVERY == 0):
            def mstd(xs):
                m = float(np.mean(xs)) if len(xs) else 0.0
                s = float(np.std(xs, ddof=1)) if len(xs) > 1 else 0.0
                return m, s
            rt = mstd(network_throughputs)
            ree = mstd(energy_efficiencies)
            rpdr = mstd(packet_delivery_ratios)
            # Use NaN-aware stats for latency (episodes with no deliveries)
            _lat_arr = np.array(average_latencies, dtype=float)
            _lat_cnt = int(np.sum(~np.isnan(_lat_arr)))
            rlat = (
                (float(np.nanmean(_lat_arr)) if _lat_cnt > 0 else float('nan')),
                (float(np.nanstd(_lat_arr, ddof=1)) if _lat_cnt > 1 else 0.0)
            )
            rcons = mstd(total_consumption_energies)
            rstdE = mstd(std_residual_energies)
            print(
                f"Progress after {episode + 1} episodes -> "
                f"Throughput(mean±std)={rt[0]:.4f}±{rt[1]:.4f}, "
                f"EnergyEff={ree[0]:.4f}±{ree[1]:.4f}, PDR={rpdr[0]:.4f}±{rpdr[1]:.4f}, "
                f"Latency={rlat[0]:.4f}±{rlat[1]:.4f}, ConsEnergy={rcons[0]:.4f}±{rcons[1]:.4f}, "
                f"Std(Eres)={rstdE[0]:.4f}±{rstdE[1]:.4f}"
            )

    # Overall metrics
    # Report sample standard deviation across episodes (ddof=1)
    overall_throughput = np.mean(network_throughputs), (np.std(network_throughputs, ddof=1) if len(network_throughputs) > 1 else 0.0)
    overall_energy_efficiency = np.mean(energy_efficiencies), (np.std(energy_efficiencies, ddof=1) if len(energy_efficiencies) > 1 else 0.0)
    overall_packet_delivery_ratio = np.mean(packet_delivery_ratios), (np.std(packet_delivery_ratios, ddof=1) if len(packet_delivery_ratios) > 1 else 0.0)
    # NaN-aware overall latency stats (ignore episodes with no deliveries)
    _avg_lat_arr = np.array(average_latencies, dtype=float)
    _avg_lat_cnt = int(np.sum(~np.isnan(_avg_lat_arr)))
    overall_average_latency = (
        (float(np.nanmean(_avg_lat_arr)) if _avg_lat_cnt > 0 else float('nan')),
        (float(np.nanstd(_avg_lat_arr, ddof=1)) if _avg_lat_cnt > 1 else 0.0)
    )
    overall_total_consumption_energy = np.mean(total_consumption_energies), (np.std(total_consumption_energies, ddof=1) if len(total_consumption_energies) > 1 else 0.0)
    overall_std_residual_energy = np.mean(std_residual_energies), (np.std(std_residual_energies, ddof=1) if len(std_residual_energies) > 1 else 0.0)
    print("Overall Performance over all episodes:")
    print(
        f"Throughput={overall_throughput},\n"
        f"Energy Efficiency={overall_energy_efficiency},\n"
        f"PDR={overall_packet_delivery_ratio},\n"
        f"Avg Latency={overall_average_latency},\n"
        f"Total Consumed Energy={overall_total_consumption_energy},\n"
        f"Std(Residual Energy)={overall_std_residual_energy}"
    )

    # Persist minimal reviewer-focused metrics to .npy files
    try:
        algo_name = os.environ.get('ALGO_NAME', 'QPSOFL')
        # Keep algo naming consistent with downstream tools
        algo_name = str(algo_name).upper()
        seed_tag = os.getenv('SEED_TAG', '')  # e.g. "_seed42" for multi-seed runs
        version = getattr(gym_examples, "__version__", "unknown")
        base_back_up_dir = DATA_DIR
        os.makedirs(base_back_up_dir, exist_ok=True)
        metrics = {
            f"network_throughput_{algo_name}": network_throughputs,
            f"energy_efficiency_{algo_name}": energy_efficiencies,
            f"packet_delivery_ratio_{algo_name}": packet_delivery_ratios,
            f"average_latency_{algo_name}": average_latencies,
            f"total_consumption_energy_{algo_name}": total_consumption_energies,
            f"std_remaining_energy_{algo_name}": std_residual_energies,
            # Feasibility timing
            f"wall_step_time_ms_mean_{algo_name}": wall_step_time_ms_mean_list,
            f"wall_episode_time_ms_{algo_name}": wall_episode_time_ms_list,
            f"wall_step_time_ms_p95_{algo_name}": wall_step_time_ms_p95_list,
            f"wall_step_time_ms_p99_{algo_name}": wall_step_time_ms_p99_list,
            f"peak_memory_mb_{algo_name}": peak_memory_mb_list,
        }

        # Write both non-split and "test"-split filenames so tools that assume --test work.
        for metric_name, metric_value in metrics.items():
            arr = np.array(metric_value)
            np.save(os.path.join(base_back_up_dir, f"{metric_name}{seed_tag}_{version}.npy"), arr)
            # Convert <metric>_<ALGO> -> <metric>_<ALGO>_test
            test_name = f"{metric_name}{seed_tag}_test"
            np.save(os.path.join(base_back_up_dir, f"{test_name}_{version}.npy"), arr)
    except Exception as _e:
        print(f"Warning: failed to save .npy metrics: {_e}")