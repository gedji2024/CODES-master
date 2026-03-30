#!/usr/bin/env python3
"""
V5 Supplementary Campaigns + Figure Generation
================================================
Runs:
  Phase 1: Scalability       (10 seeds × {100,200,500} nodes × 13 protocols)
  Phase 2: CI Sensitivity    (10 seeds × 4 regions × 6 protocols)
  Phase 3: Parameter Sweep   (10 seeds × 4 params × 5 values × 4 protocols)
  Phase 4: Real Validation   (10 seeds × synthetic + real × 13 protocols)
  Phase 5: Generate all 8 publication figures from V5 data

Output to results_v5/ and figures/
"""

import os
import sys
import time
import json
import signal

# Ignore SIGINT so ^C from other terminals can't kill us
signal.signal(signal.SIGINT, signal.SIG_IGN)

# Ensure CALASH root is in path
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from config import SimulationConfig
from experiments.parallel_runner import ParallelRunner


def file_exists(output_dir, name):
    """Check if a result JSON already exists (skip re-running)."""
    path = os.path.join(output_dir, f'{name}.json')
    return os.path.exists(path)


def main():
    output_dir = os.path.join(ROOT, 'results_v5')
    fig_dir = os.path.join(ROOT, 'figures')
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(fig_dir, exist_ok=True)

    # Base config matching main V5 campaign
    config = SimulationConfig(
        num_rounds=5000,
        num_seeds=10,
        num_nodes=200,
        signal_source='real_intel_lab',
        carbon_trace_file='real_uk_2023',
        disaster_enabled=True,
        disaster_round=1500,
        disaster_event='turkey_syria_2023',
        shakemap_event_id='turkey_syria_2023',
        aftershock_enabled=True,
        aftershock_count=2,
    )

    runner = ParallelRunner(max_workers=None, output_dir=output_dir)
    t_start = time.time()

    # ── Phase 1: Scalability ────────────────────────────────────
    # Check which N values still need to run
    needed_nodes = [N for N in [100, 200, 500]
                    if not file_exists(output_dir, f'scalability_N{N}')]
    if needed_nodes:
        print("=" * 70)
        print(f"  PHASE 1: SCALABILITY CAMPAIGN  (N={needed_nodes})")
        print(f"  10 seeds × {len(needed_nodes)} sizes × 13 protocols × 5000 rounds")
        print("=" * 70)
        runner.run_scalability(config, node_counts=needed_nodes, num_seeds=10)
    else:
        print("=" * 70)
        print("  PHASE 1: SCALABILITY — SKIPPED (all N=100,200,500 exist)")
        print("=" * 70)

    t_scal = time.time()
    print(f"\n  Scalability done in {t_scal - t_start:.0f}s")

    # ── Phase 2: CI Sensitivity ─────────────────────────────────
    ci_done = all(file_exists(output_dir, f'ci_sensitivity_{r}')
                  for r in ['france', 'uk', 'germany', 'india'])
    if not ci_done:
        print("\n" + "=" * 70)
        print("  PHASE 2: CI SENSITIVITY CAMPAIGN")
        print("  10 seeds × 4 regions × 6 protocols × 5000 rounds")
        print("=" * 70)
        runner.run_ci_sensitivity(config, num_seeds=10)
    else:
        print("\n" + "=" * 70)
        print("  PHASE 2: CI SENSITIVITY — SKIPPED (all regions exist)")
        print("=" * 70)

    t_ci = time.time()
    print(f"\n  CI Sensitivity done in {t_ci - t_scal:.0f}s")

    # ── Phase 3: Parameter Sensitivity Sweep ────────────────────
    print("\n" + "=" * 70)
    print("  PHASE 3: PARAMETER SENSITIVITY SWEEP")
    print("  10 seeds × 4 params × 5 values × 4 protocols × 5000 rounds")
    print("=" * 70)
    runner.run_sensitivity(config, num_seeds=10)

    t_sens = time.time()
    print(f"\n  Parameter Sensitivity done in {t_sens - t_ci:.0f}s")

    # ── Phase 4: Real vs Synthetic Validation ───────────────────
    val_done = (file_exists(output_dir, 'validation_synthetic') and
                file_exists(output_dir, 'validation_real'))
    if not val_done:
        print("\n" + "=" * 70)
        print("  PHASE 4: REAL vs SYNTHETIC VALIDATION")
        print("  10 seeds × 2 modes × 13 protocols × 5000 rounds")
        print("=" * 70)
        runner.run_real_validation(config, num_seeds=10)
    else:
        print("\n" + "=" * 70)
        print("  PHASE 4: VALIDATION — SKIPPED (files exist)")
        print("=" * 70)

    t_val = time.time()
    print(f"\n  Validation done in {t_val - t_sens:.0f}s")

    elapsed = time.time() - t_start
    print(f"\n{'=' * 70}")
    print(f"  ALL SUPPLEMENTARY CAMPAIGNS COMPLETE — {elapsed:.0f}s total")
    print(f"{'=' * 70}")

    # ── Phase 5: Generate all 8 publication figures ─────────────
    print("\n" + "=" * 70)
    print("  PHASE 5: GENERATING PUBLICATION FIGURES")
    print("=" * 70)

    from experiments.visualizations import PaperVisualizer
    viz = PaperVisualizer(results_dir=output_dir, output_dir=fig_dir)
    viz.generate_all(label='main')

    # Also generate the extra figures from generate_figures.py
    from generate_figures import load_results, fig_pareto_front, \
        fig_ablation_chart, fig_convergence, fig_summary_bars, fig_wilcoxon_heatmap
    results_path = os.path.join(output_dir, 'main.json')
    ts_path = os.path.join(output_dir, 'main_ts.npz')
    results = load_results(results_path, ts_path)
    print(f"\n  Loaded {len(results)} protocols for extra figures")

    fig_pareto_front(results, fig_dir)
    fig_ablation_chart(results, fig_dir)
    fig_convergence(results, fig_dir)
    fig_summary_bars(results, fig_dir)
    fig_wilcoxon_heatmap(results_path, fig_dir)

    print(f"\n{'=' * 70}")
    print(f"  ✅ ALL FIGURES SAVED TO {fig_dir}/")
    print(f"{'=' * 70}")

    # ── Phase 6: Extract key numbers for article ────────────────
    print("\n" + "=" * 70)
    print("  PHASE 6: EXTRACTING ARTICLE NUMBERS")
    print("=" * 70)

    # Scalability numbers
    print("\n  SCALABILITY NUMBERS:")
    for N in [100, 200, 500]:
        path = os.path.join(output_dir, f'scalability_N{N}.json')
        if os.path.exists(path):
            with open(path) as f:
                d = json.load(f)
            calash = d.get('CALASH', {})
            leach = d.get('LEACH', {})
            c_lci = calash.get('lci', {}).get('mean', 0)
            c_ci = calash.get('lci', {}).get('ci95', 0)
            l_lci = leach.get('lci', {}).get('mean', 0)
            l_ci = leach.get('lci', {}).get('ci95', 0)
            c_hd = calash.get('half_death_round', {}).get('mean', 0)
            l_hd = leach.get('half_death_round', {}).get('mean', 0)
            pct = (l_lci - c_lci) / l_lci * 100 if l_lci else 0
            print(f"    N={N}: CALASH LCI={c_lci:.2f}±{c_ci:.2f}, "
                  f"LEACH LCI={l_lci:.2f}±{l_ci:.2f} ({pct:.0f}% lower)")
            print(f"           CALASH HD={c_hd:.0f}, LEACH HD={l_hd:.0f}")

    # CI Sensitivity numbers
    print("\n  CI SENSITIVITY NUMBERS:")
    for region in ['france', 'uk', 'germany', 'india']:
        path = os.path.join(output_dir, f'ci_sensitivity_{region}.json')
        if os.path.exists(path):
            with open(path) as f:
                d = json.load(f)
            calash = d.get('CALASH', {})
            leach = d.get('LEACH', {})
            c_lci = calash.get('lci', {}).get('mean', 0)
            l_lci = leach.get('lci', {}).get('mean', 0)
            pct = (l_lci - c_lci) / l_lci * 100 if l_lci else 0
            print(f"    {region.upper():8s}: CALASH LCI={c_lci:.2f}, "
                  f"LEACH LCI={l_lci:.2f} → {pct:.0f}% advantage")


if __name__ == '__main__':
    main()
