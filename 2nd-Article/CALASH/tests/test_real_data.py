#!/usr/bin/env python3
"""Quick test: real earthquake profile + real Intel Lab + real UK Carbon."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SimulationConfig
from experiments.runner import run_single_experiment

cfg = SimulationConfig(
    num_nodes=30, num_rounds=80, area_width=150, area_height=150,
    signal_source='real_intel_lab',
    carbon_trace_file='real_uk_2023',
    disaster_enabled=True, disaster_round=30, disaster_round_jitter=0.0,
    disaster_event='turkey_syria_2023',
)
r = run_single_experiment(cfg, 'CALASH', seed=42, verbose=False)
print(f'Real earthquake profile: alive={r["final_alive_nodes"]}, PDR={r["overall_pdr"]:.3f}')
print(f'Recovery time: {r.get("recovery_time_rounds", -1)}')
print('Real earthquake profile + real Intel Lab + real UK Carbon: ALL OK')
