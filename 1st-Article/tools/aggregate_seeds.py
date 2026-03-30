"""Aggregate per-seed .npy results into mean ± std summary files.

Usage:
    python tools/aggregate_seeds.py [--seeds 42,123,456,789]

Reads:  results/data/<metric>_<ALGO>_seed<N>_test_<version>.npy
Writes: results/data/<metric>_<ALGO>_test_<version>.npy       (mean across seeds)
        results/data/<metric>_<ALGO>_std_test_<version>.npy    (std across seeds)
"""
import argparse
import glob
import os
import re
import sys

import numpy as np

# Resolve paths
_here = os.path.dirname(os.path.abspath(__file__))
_epymarl = os.path.join(_here, os.pardir, "epymarl")
sys.path.insert(0, os.path.join(_epymarl, "src"))
from utils.paths import RESULTS_DATA_DIR

import gym_examples


def main():
    parser = argparse.ArgumentParser(description="Aggregate per-seed .npy results")
    parser.add_argument("--seeds", type=str, default="42,123,456,789",
                        help="Comma-separated seed values to aggregate")
    args = parser.parse_args()

    seeds = [int(s.strip()) for s in args.seeds.split(",")]
    version = gym_examples.__version__

    # Find all per-seed test files
    all_files = glob.glob(os.path.join(RESULTS_DATA_DIR, f"*_seed*_test_{version}.npy"))
    if not all_files:
        print("No per-seed test files found. Nothing to aggregate.")
        return

    # Parse files into (metric, algo, seed) tuples
    # Pattern: <metric>_<ALGO>_seed<N>_test_<version>.npy
    pattern = re.compile(
        rf"^(.+?)_(QMIX|QTRAN|QPSOFL|ENSEMBLE_MAX)_seed(\d+)_test_{re.escape(version)}\.npy$"
    )

    # Group: {(metric, algo): {seed: filepath}}
    groups = {}
    for f in all_files:
        basename = os.path.splitext(os.path.basename(f))[0] + ".npy"
        m = pattern.match(os.path.basename(f))
        if m:
            metric, algo, seed = m.group(1), m.group(2), int(m.group(3))
            if seed in seeds:
                groups.setdefault((metric, algo), {})[seed] = f

    aggregated = 0
    for (metric, algo), seed_files in sorted(groups.items()):
        if len(seed_files) < 2:
            continue  # Need at least 2 seeds to aggregate

        arrays = []
        for seed in sorted(seed_files.keys()):
            arr = np.load(seed_files[seed])
            arrays.append(arr)

        # Truncate to minimum length
        min_len = min(len(a) for a in arrays)
        stacked = np.stack([a[:min_len] for a in arrays])

        mean_arr = stacked.mean(axis=0)
        std_arr = stacked.std(axis=0)

        # Save aggregated files (overwrite non-seed versions)
        mean_path = os.path.join(RESULTS_DATA_DIR, f"{metric}_{algo}_test_{version}.npy")
        std_path = os.path.join(RESULTS_DATA_DIR, f"{metric}_{algo}_std_test_{version}.npy")

        np.save(mean_path, mean_arr)
        np.save(std_path, std_arr)
        aggregated += 1

    print(f"Aggregated {aggregated} (metric, algo) pairs from {len(seeds)} seeds")
    print(f"  Seeds used: {seeds}")
    print(f"  Output dir: {RESULTS_DATA_DIR}")


if __name__ == "__main__":
    main()
