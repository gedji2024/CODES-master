#!/usr/bin/env python3
"""
CALASH Quick Demo
=================
Run a quick simulation with all protocols on a small network
to verify everything works and generate initial figures.

Usage:
    python main.py
    python main.py --scenario quick
    python main.py --scenario scalability
"""

import argparse
import sys
import os
import time
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import SimulationConfig, small_config
from experiments.runner import ExperimentRunner, run_single_experiment, _t_critical
from experiments.scenarios import get_scenario
from experiments.visualizations import PaperVisualizer


def run_quick_demo():
    """Run a quick demo with small network to verify the framework."""
    print("=" * 60)
    print("CALASH Framework — Quick Demo")
    print("=" * 60)

    config = SimulationConfig(
        num_nodes=100,
        num_rounds=1000,
        num_seeds=3,
        area_width=200.0,
        area_height=200.0,
        bs_x=100.0,
        bs_y=225.0,            # just outside area (25m above top edge)
        tx_range=150.0,         # generous range for multi-hop
        initial_energy=2.0,     # 2J for longer lifetime
        ch_percentage=0.10,     # 10% CHs for small network
        disaster_enabled=True,
        disaster_round=500,
        disaster_x=100.0,
        disaster_y=100.0,
        damage_radius=60.0,
    )

    protocols = ['LEACH', 'EE-LEACH', 'Q-Routing', 'CALASH',
                 'CALASH-NoCO2', 'CALASH-NoSH']

    print(f"\nNetwork: {config.num_nodes} nodes in "
          f"{config.area_width}×{config.area_height}m")
    print(f"Rounds: {config.num_rounds}, Seeds: {config.num_seeds}")
    print(f"Disaster: round {config.disaster_round}, "
          f"radius {config.damage_radius}m")
    print(f"BS at ({config.bs_x}, {config.bs_y}), tx_range={config.tx_range}m")
    print(f"Protocols: {', '.join(protocols)}")

    all_results = {}
    for protocol in protocols:
        print(f"\n{'─' * 40}")
        print(f"Running: {protocol}")

        seed_results = []
        for seed_idx in range(config.num_seeds):
            seed = config.base_seed + seed_idx
            t0 = time.time()
            result = run_single_experiment(
                config, protocol, seed, verbose=(seed_idx == 0)
            )
            elapsed = time.time() - t0
            seed_results.append(result)
            print(f"  Seed {seed}: lifetime={result['operational_lifetime']}, "
                  f"PDR={result['overall_pdr']:.3f}, "
                  f"carbon={result['total_carbon_gCO2']:.2e}, "
                  f"time={elapsed:.1f}s")

        # Store for aggregation
        key = f"{protocol}|default"
        # Simple aggregation for demo
        agg = _quick_aggregate(seed_results)
        all_results[key] = {
            'protocol': protocol,
            'config_label': 'default',
            'aggregated': agg,
        }

    # Print comparison table
    print("\n" + "=" * 60)
    print("COMPARISON TABLE")
    print("=" * 60)
    print(f"{'Protocol':<15} {'Lifetime':>10} {'PDR':>8} "
          f"{'Carbon':>12} {'Fidelity':>10} {'LCI':>12}")
    print("-" * 67)
    for key, data in all_results.items():
        a = data['aggregated']
        print(f"{data['protocol']:<15} "
              f"{a.get('operational_lifetime', {}).get('mean', 0):>10.0f} "
              f"{a.get('overall_pdr', {}).get('mean', 0):>8.3f} "
              f"{a.get('total_carbon_gCO2', {}).get('mean', 0):>12.2e} "
              f"{a.get('avg_data_fidelity', {}).get('mean', 0):>10.3f} "
              f"{a.get('lci', {}).get('mean', 0):>12.2f}")

    # Generate figures
    print("\nGenerating figures...")
    plotter = PaperVisualizer(results_dir='results', output_dir='figures')
    plotter.generate_all(label='demo')

    print("\n✅ Demo complete!")
    return all_results


def _quick_aggregate(seed_results):
    """Simple aggregation for the demo."""
    scalar_keys = [
        'first_death_round', 'half_death_round', 'last_death_round',
        'operational_lifetime', 'overall_pdr', 'total_energy_J',
        'energy_efficiency_pkt_per_J', 'total_carbon_gCO2',
        'avg_data_fidelity', 'recovery_time_rounds', 'lci',
        'total_delivered', 'total_generated', 'jains_fairness',
    ]

    agg = {}
    for key in scalar_keys:
        values = [r.get(key, np.nan) for r in seed_results]
        values = [v for v in values if v is not None and not np.isnan(v) and v >= 0]
        if values:
            mean = float(np.mean(values))
            std = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
            n = len(values)
            t_crit = _t_critical(n - 1) if n > 1 else 1.96
            ci95 = t_crit * std / np.sqrt(n)
            agg[key] = {'mean': mean, 'std': std, 'ci95': ci95}
        else:
            agg[key] = {'mean': np.nan, 'std': 0, 'ci95': 0}

    # Time series
    ts_keys = ['ts_alive', 'ts_pdr', 'ts_energy', 'ts_carbon', 'ts_fidelity']
    for key in ts_keys:
        series_list = [r.get(key, []) for r in seed_results if key in r]
        if series_list:
            max_len = max(len(s) for s in series_list)
            padded = []
            for s in series_list:
                if len(s) < max_len:
                    s = list(s) + [s[-1]] * (max_len - len(s)) if s else [0] * max_len
                padded.append(s[:max_len])
            arr = np.array(padded)
            agg[key] = {
                'mean': arr.mean(axis=0).tolist(),
                'std': arr.std(axis=0).tolist(),
            }

    return agg


def run_scenario_experiment(scenario_name: str):
    """Run a full scenario experiment."""
    print(f"\n{'=' * 60}")
    print(f"Running Scenario: {scenario_name}")
    print(f"{'=' * 60}")

    configs = get_scenario(scenario_name)
    runner = ExperimentRunner(
        protocols=['LEACH', 'EE-LEACH', 'Q-Routing', 'CALASH',
                   'CALASH-NoCO2', 'CALASH-NoSH'],
        output_dir='results'
    )

    results = runner.run_scenario(scenario_name, configs, verbose=True)

    # Generate figures
    plotter = PaperVisualizer(results_dir='results', output_dir='figures')
    plotter.generate_all(label=scenario_name)

    return results


def main():
    parser = argparse.ArgumentParser(
        description='CALASH Framework Simulation'
    )
    parser.add_argument('--scenario', type=str, default='quick',
                        choices=['quick', 'scalability', 'disaster',
                                 'carbon', 'lyapunov_v',
                                 'real_sensor', 'real_carbon',
                                 'fairness', 'overhead',
                                 'real_disaster', 'demo'],
                        help='Experiment scenario to run')
    parser.add_argument('--verbose', action='store_true', default=True)

    args = parser.parse_args()

    if args.scenario == 'demo':
        run_quick_demo()
    else:
        run_scenario_experiment(args.scenario)


if __name__ == '__main__':
    main()
