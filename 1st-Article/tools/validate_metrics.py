import os
import numpy as np
import math
from typing import Dict, List, Tuple

# Canonical location: epymarl/results/data/
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'epymarl', 'results', 'data'))

# Define metric groups expected per algorithm
# HYBRID corresponds to the selector pipeline (TSMixer_hybrid_model), TSMixer corresponds to inference-only feasibility.
ALGORITHMS = ["QMIX", "QTRAN", "QPSOFL", "ENSEMBLE_MAX", "HYBRID", "GAPF"]
# Base metric stems (without algo suffix and version) for performance
PERF_METRICS = [
    "network_throughput",
    "energy_efficiency",
    "packet_delivery_ratio",
    "average_latency",
    "returns",
    "total_consumption_energy",
    "std_remaining_energy"
]

# Some stacks write mean episodic returns as `mean_returns` instead of `returns`.
METRIC_ALIASES = {
    "returns": {"returns", "mean_returns"},
}

# Some algorithms/baselines do not produce an RL episodic return metric.
OPTIONAL_PERF_METRICS_BY_ALGO = {
    "QPSOFL": {"returns"},
    "HYBRID": {"returns"},
}
# Feasibility metrics
FEAS_METRICS = [
    "wall_step_time_ms_mean",
    "wall_step_time_ms_p95",
    "wall_step_time_ms_p99",
    "wall_episode_time_ms",
    "peak_memory_mb",
    "training_time_s",
    "model_param_count",
    "model_size_mb"
]

def list_npy_files() -> List[str]:
    if not os.path.isdir(DATA_DIR):
        return []
    return [f for f in os.listdir(DATA_DIR) if f.endswith(".npy")]

def parse_metric_file(filename: str) -> Tuple[str, str, str]:
    """
    Supported patterns:
      - <metric>_<ALGO>_<version>.npy
      - <metric>_<ALGO>_test_<version>.npy
      - <metric>_<ALGO>_seed<N>_<version>.npy
      - <metric>_<ALGO>_seed<N>_test_<version>.npy

    Uses known ALGORITHMS list to correctly match algo names that contain
    underscores (e.g. ENSEMBLE_MAX).
    """
    import re
    base = filename[:-4]  # strip .npy
    # Strip seed tag if present (e.g. _seed42)
    base = re.sub(r'_seed\d+', '', base)
    # Strip trailing _test if present
    is_test = base.endswith('_test')  # not used here but noted
    # Extract version (last _-separated token, looks like digits and dots)
    parts = base.split('_')
    if len(parts) < 3:
        return base, "", ""
    version = parts[-1]
    # Remove version from base
    rest = '_'.join(parts[:-1])
    # Remove trailing _test if present
    if rest.endswith('_test'):
        rest = rest[:-5]  # len('_test') == 5
    # Match against known algo names (longest first to handle ENSEMBLE_MAX before MAX)
    sorted_algos = sorted(ALGORITHMS, key=len, reverse=True)
    for algo in sorted_algos:
        suffix = f"_{algo}"
        if rest.endswith(suffix):
            metric = rest[:-len(suffix)]
            return metric, algo, version
    # Fallback: treat last token as algo
    fallback_parts = rest.split('_')
    algo = fallback_parts[-1]
    metric = '_'.join(fallback_parts[:-1])
    return metric, algo, version

def load_array(path: str) -> np.ndarray:
    try:
        return np.load(path)
    except Exception as e:
        print(f"ERROR loading {path}: {e}")
        return np.array([])

def summarize(arr: np.ndarray) -> Dict[str, float]:
    if arr.size == 0:
        return {"count": 0, "mean": math.nan, "std": math.nan}
    # Latency arrays may contain NaN; use nan-aware stats
    if np.isnan(arr).any():
        mean = float(np.nanmean(arr))
        std = float(np.nanstd(arr, ddof=1)) if arr.size > 1 else 0.0
    else:
        mean = float(np.mean(arr))
        std = float(np.std(arr, ddof=1)) if arr.size > 1 else 0.0
    return {"count": int(arr.size), "mean": mean, "std": std}

def validate_expected(files: List[str]):
    present = {}
    for fn in files:
        metric, algo, version = parse_metric_file(fn)
        present.setdefault(algo, {}).setdefault(metric, []).append(fn)

    def _has_metric(algo: str, metric: str) -> bool:
        if algo not in present:
            return False
        names = METRIC_ALIASES.get(metric)
        if not names:
            return metric in present[algo]
        return any(m in present[algo] for m in names)

    # Report missing performance metrics per algorithm (excluding TSMixer-specific feasibility-only metrics)
    print("\n=== Performance Metrics Presence ===")
    for algo in ALGORITHMS:
        missing = []
        optional = OPTIONAL_PERF_METRICS_BY_ALGO.get(algo, set())
        for m in PERF_METRICS:
            if m in optional:
                continue
            if not _has_metric(algo, m):
                # Hybrid may not have returns if not computed; still flag for completeness
                missing.append(m)
        status = "OK" if not missing else f"MISSING: {', '.join(missing)}"
        print(f"{algo}: {status}")

    print("\n=== Feasibility Metrics Presence (TSMixer / GAPF / model) ===")
    for model_name in ["TSMixer", "GAPF"]:
        feas_missing = []
        for m in FEAS_METRICS:
            if model_name not in present or m not in present[model_name]:
                feas_missing.append(m)
        print(f"{model_name}: " + ("OK" if not feas_missing else f"MISSING: {', '.join(feas_missing)}"))

    # Detailed summaries
    print("\n=== Detailed Summaries (mean±std, count) ===")
    for algo, metrics_map in sorted(present.items()):
        print(f"\nAlgorithm: {algo}")
        for metric, files_for_metric in sorted(metrics_map.items()):
            # Load and concatenate if multiple files (different splits/episodes)
            arrays = [load_array(os.path.join(DATA_DIR, f)) for f in files_for_metric]
            if arrays:
                cat = np.concatenate(arrays) if len(arrays) > 1 else arrays[0]
            else:
                cat = np.array([])
            summary = summarize(cat)
            mean = summary["mean"]
            std = summary["std"]
            print(f"  {metric}: count={summary['count']}, mean={mean:.6f} std={std:.6f}")

if __name__ == "__main__":
    files = list_npy_files()
    if not files:
        print(f"No .npy files found in {DATA_DIR}. Run training/inference first.")
    else:
        validate_expected(files)
