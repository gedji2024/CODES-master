#!/usr/bin/env python3
"""Benchmark optimized code."""
import warnings
warnings.filterwarnings('ignore')
import time
from config import SimulationConfig
from experiments.runner import run_single_experiment

cfg = SimulationConfig(num_rounds=1000, num_nodes=200)

# Benchmark: 3 seeds for CALASH (has DQN, THz, self-healing)
print("=== CALASH (1000 rounds) ===")
times = []
for seed in [42, 43, 44]:
    t0 = time.perf_counter()
    result = run_single_experiment(cfg, protocol_name='CALASH', seed=seed)
    t1 = time.perf_counter()
    times.append(t1 - t0)
    print(f"  Seed {seed}: {t1-t0:.2f}s  HND={result['half_death_round']}  PDR={result['overall_pdr']:.4f}")

avg = sum(times) / len(times)
print(f"\n  Mean: {avg:.2f}s per 1000 rounds")
print(f"  Estimated 5000 rounds: {avg * 5:.2f}s per run")

# Benchmark: LEACH (baseline, no DQN)
print("\n=== LEACH (1000 rounds) ===")
t0 = time.perf_counter()
result = run_single_experiment(cfg, protocol_name='LEACH', seed=42)
t1 = time.perf_counter()
print(f"  Seed 42: {t1-t0:.2f}s  HND={result['half_death_round']}  PDR={result['overall_pdr']:.4f}")

# Benchmark: full 5000-round CALASH
print("\n=== CALASH (5000 rounds, full run) ===")
cfg5k = SimulationConfig(num_rounds=5000, num_nodes=200)
t0 = time.perf_counter()
result = run_single_experiment(cfg5k, protocol_name='CALASH', seed=42)
t1 = time.perf_counter()
print(f"  5000 rounds: {t1-t0:.2f}s  HND={result['half_death_round']}  PDR={result['overall_pdr']:.4f}  LCI={result['lci']:.2f}")
