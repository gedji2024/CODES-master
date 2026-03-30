#!/usr/bin/env python3
"""
V5 Campaign Runner
==================
Full CALASH V5 campaign with 6G-significant code changes:

Changes from V4:
  1. RIS-assisted sub-6 GHz gain for inter-cluster hops (up to 4 dB)
  2. ISAC passive failure detection (zero heartbeat cost with 6G)
  3. Reduced THz circuit power (50mW → 20mW, modern D-band CMOS)
  4. NoTHz ablation disables ALL 6G (THz + RIS + ISAC + slicing)
  5. Multi-disaster: mainshock + 2 aftershocks at runner level
  6. CI sensitivity: France / UK / Germany / India national grids

Campaign structure:
  (a) Main:          30 seeds × 13 protocols × 5000 rounds
  (b) Scalability:   10 seeds × 13 protocols × 5000 rounds × N∈{100,200,500}
  (c) CI Sensitivity: 10 seeds × 6 protocols × 5000 rounds × 4 regions
"""

import os
import sys
import time
import argparse

# Ensure CALASH root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import SimulationConfig
from experiments.parallel_runner import ParallelRunner


def main():
    parser = argparse.ArgumentParser(description='CALASH V5 Campaign')
    parser.add_argument('--phase', type=str, default='all',
                        choices=['main', 'scalability', 'ci', 'all'],
                        help='Which phase to run')
    parser.add_argument('--seeds', type=int, default=30,
                        help='Seeds for main campaign (default: 30)')
    parser.add_argument('--rounds', type=int, default=5000,
                        help='Simulation rounds (default: 5000)')
    parser.add_argument('--workers', type=int, default=None,
                        help='Parallel workers (default: CPU-1)')
    parser.add_argument('--output', type=str, default='results_v5',
                        help='Output directory')
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    # Base configuration (same as V4 but with aftershocks enabled)
    config = SimulationConfig(
        num_rounds=args.rounds,
        num_seeds=args.seeds,
        num_nodes=200,
        # Real data
        signal_source='real_intel_lab',
        carbon_trace_file='real_uk_2023',
        disaster_enabled=True,
        disaster_round=int(args.rounds * 0.3),
        disaster_event='turkey_syria_2023',
        shakemap_event_id='turkey_syria_2023',
        # Multi-disaster (new in V5)
        aftershock_enabled=True,
        aftershock_count=2,
    )

    runner = ParallelRunner(max_workers=args.workers,
                            output_dir=args.output)

    t_start = time.time()

    # ── Phase 1: Main campaign ──
    if args.phase in ('main', 'all'):
        print("=" * 70)
        print("  PHASE 1: MAIN CAMPAIGN")
        print(f"  {args.seeds} seeds × 13 protocols × {args.rounds} rounds")
        print("=" * 70)
        runner.run_campaign(config, label='main')

    # ── Phase 2: Scalability ──
    if args.phase in ('scalability', 'all'):
        n_sc = min(args.seeds, 10)
        print("\n" + "=" * 70)
        print("  PHASE 2: SCALABILITY")
        print(f"  {n_sc} seeds × N∈{{100,200,500}} × {args.rounds} rounds")
        print("=" * 70)
        runner.run_scalability(
            config,
            node_counts=[100, 200, 500],
            num_seeds=n_sc
        )

    # ── Phase 3: CI Sensitivity ──
    if args.phase in ('ci', 'all'):
        n_ci = min(args.seeds, 10)
        print("\n" + "=" * 70)
        print("  PHASE 3: CI SENSITIVITY")
        print(f"  {n_ci} seeds × 4 regions × {args.rounds} rounds")
        print("=" * 70)
        runner.run_ci_sensitivity(
            config,
            num_seeds=n_ci
        )

    elapsed = time.time() - t_start
    hours = elapsed / 3600
    print(f"\n{'=' * 70}")
    print(f"  V5 CAMPAIGN COMPLETE — {hours:.1f} hours")
    print(f"  Results saved to: {os.path.abspath(args.output)}/")
    print(f"{'=' * 70}")


if __name__ == '__main__':
    main()
