#!/usr/bin/env python3
"""
Full Experiment Campaign
========================
Runs all experimental scenarios for the CALASH paper:

    E1: Scalability      — N ∈ {100, 200, 300, 500}
    E2: Disaster Severity — r calibrated via USGS earthquake magnitudes
    E3: Carbon Grid       — Electricity Maps traces (France, Germany, India)
    E4: Lyapunov V        — V ∈ {1, 10, 50, 100, 500, 1000}
    E5: Real Sensor       — Intel Lab dataset (temperature, humidity, light)
    E6: Real Carbon       — 5 Electricity Maps regions
    E7: Energy Fairness   — Jain's index analysis
    E8: Overhead          — wall-clock timing comparison

    Bonus: real_disaster  — USGS earthquakes + NASA FIRMS wildfires

Each with 30 seeds × 6 protocols = 180 runs per config point.

Expected wall time:
    Quick test: ~2 min
    Full E1-E4: ~2-6 hours
    Full E1-E8 + bonus: ~4-10 hours (depending on hardware)

Usage:
    python run_experiments.py --all           # Full campaign (E1-E8)
    python run_experiments.py --quick         # Quick validation
    python run_experiments.py --core          # Original E1-E4 only
    python run_experiments.py --scenario E1   # Single scenario
"""

import argparse
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from experiments.runner import ExperimentRunner
from experiments.scenarios import get_scenario, SCENARIOS
from experiments.visualizations import PaperVisualizer

# Mapping from short names to scenario registry keys
SCENARIO_ALIASES = {
    'E1': 'scalability',
    'E2': 'disaster',
    'E3': 'carbon',
    'E4': 'lyapunov_v',
    'E5': 'real_sensor',
    'E6': 'real_carbon',
    'E7': 'fairness',
    'E8': 'overhead',
}

CORE_SCENARIOS = ['scalability', 'disaster', 'carbon', 'lyapunov_v']
ALL_SCENARIOS = CORE_SCENARIOS + ['real_sensor', 'real_carbon', 'fairness',
                                   'overhead', 'real_disaster']


def run_full_campaign(scenarios: list, quick: bool = False):
    """Run selected experimental scenarios."""
    start_time = time.time()

    if quick:
        scenarios = ['quick']
        protocols = ['LEACH', 'EE-LEACH', 'CALASH']
    else:
        protocols = ['LEACH', 'EE-LEACH', 'Q-Routing',
                     'CALASH', 'CALASH-NoCO2', 'CALASH-NoSH']

    runner = ExperimentRunner(protocols=protocols, output_dir='results')
    plotter = PaperVisualizer(results_dir='results', output_dir='figures')

    all_results = {}

    for scenario_name in scenarios:
        print(f"\n{'#' * 60}")
        print(f"# SCENARIO: {scenario_name.upper()}")
        print(f"{'#' * 60}")

        configs = get_scenario(scenario_name)
        results = runner.run_scenario(scenario_name, configs, verbose=True)

        # Generate scenario-specific figures
        plotter.plot_all(results, scenario_name=scenario_name)

        all_results[scenario_name] = results

    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"CAMPAIGN COMPLETE — {len(scenarios)} scenario(s)")
    print(f"Total wall time: {elapsed / 60:.1f} minutes")
    print(f"Results: results/")
    print(f"Figures: figures/")
    print(f"{'=' * 60}")

    return all_results


def main():
    parser = argparse.ArgumentParser(
        description='CALASH Full Experiment Campaign'
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--all', action='store_true',
                       help='Run full campaign (E1-E8 + real_disaster)')
    group.add_argument('--core', action='store_true',
                       help='Run core experiments only (E1-E4)')
    group.add_argument('--quick', action='store_true',
                       help='Quick validation run')
    group.add_argument('--scenario', type=str,
                       help='Run single scenario (E1-E8, or full name)')

    args = parser.parse_args()

    if args.quick:
        run_full_campaign([], quick=True)
    elif args.core:
        run_full_campaign(CORE_SCENARIOS)
    elif args.all:
        run_full_campaign(ALL_SCENARIOS)
    elif args.scenario:
        # Accept both 'E1' and 'scalability'
        name = SCENARIO_ALIASES.get(args.scenario.upper(), args.scenario)
        if name not in SCENARIOS:
            print(f"Unknown scenario: {args.scenario}")
            print(f"Available: {list(SCENARIO_ALIASES.keys())} "
                  f"or {list(SCENARIOS.keys())}")
            sys.exit(1)
        run_full_campaign([name])


if __name__ == '__main__':
    main()
