#!/usr/bin/env python3
"""
Publication Figure Generator for CALASH Paper
================================================
Generates the three requested figures from 30-seed campaign results:

    Fig A: Pareto Front  (PDR vs 1/Carbon, 3D dominance overlay)
    Fig B: Ablation Chart (marginal contribution grouped bars)
    Fig C: Convergence Plots (alive-nodes + PDR + carbon sub-plots)

Plus all 14 standard IEEE figures from CALASHPlotter.

Usage:
    python generate_figures.py [--results results/main.json]
                               [--ts results/main_ts.npz]
                               [--outdir figures]
"""

import os
import sys
import json
import argparse
import numpy as np

# Ensure project root is on path
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.patches import FancyArrowPatch
from mpl_toolkits.mplot3d import Axes3D

from analysis.pareto_front import (
    compute_pareto_front_2d,
    compute_pareto_front_3d,
    hypervolume_2d,
)

# ── Inlined from former visualization/ package (removed during cleanup) ──

ABLATION_MAP = {
    'CALASH-NoCO2': 'CARE (Carbon Routing)',
    'CALASH-NoSH': 'SHDR (Self-Healing)',
    'CALASH-NoCADR': 'CADR (Data Reduction)',
    'CALASH-NoLCI': 'LSE (Lifecycle)',
    'CALASH-NoTHz': 'THz/6G Channel',
}


def compute_marginal_contributions(results):
    """Compute marginal contribution of each pillar (ablation deltas)."""
    if 'CALASH' not in results:
        raise ValueError("Full CALASH results required")
    calash = results['CALASH']
    contributions = {}
    metrics = ['pdr', 'lifetime', 'carbon_efficiency', 'data_fidelity']
    for ablation_name, pillar_name in ABLATION_MAP.items():
        if ablation_name not in results:
            continue
        ablated = results[ablation_name]
        contrib = {}
        for metric in metrics:
            if metric in calash and metric in ablated:
                delta = calash[metric] - ablated[metric]
                pct = (delta / max(abs(calash[metric]), 1e-10)) * 100
                contrib[metric] = {
                    'absolute': float(delta),
                    'percentage': float(pct),
                    'calash_value': float(calash[metric]),
                    'ablated_value': float(ablated[metric]),
                }
        contributions[pillar_name] = contrib
    return contributions


# IEEE-compliant rcParams style
STYLE = {
    'figure.figsize': (3.5, 2.8),
    'font.family': 'serif',
    'font.size': 8,
    'axes.labelsize': 9,
    'axes.titlesize': 9,
    'legend.fontsize': 7,
    'xtick.labelsize': 7,
    'ytick.labelsize': 7,
    'lines.linewidth': 1.2,
    'lines.markersize': 4,
    'axes.grid': True,
    'grid.alpha': 0.3,
    'grid.linewidth': 0.5,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.05,
}

COLORS = {
    'LEACH': '#E69F00',
    'EE-LEACH': '#56B4E9',
    'Q-Routing': '#009E73',
    'CALASH': '#D55E00',
    'CALASH-NoCO2': '#CC79A7',
    'CALASH-NoSH': '#0072B2',
}


# ═══════════════════════════════════════════════════════════════════
# Extended color palette for 13 protocols
# ═══════════════════════════════════════════════════════════════════
FULL_COLORS = {
    'LEACH':          '#E69F00',   # orange
    'LEACH-1hop':     '#D4A017',   # dark gold
    'EE-LEACH':       '#56B4E9',   # sky blue
    'ABC-ACO':        '#009E73',   # teal green
    'EERP':           '#F0E442',   # yellow
    'Q-Routing':      '#0072B2',   # deep blue
    'RIS-DRL':        '#CC79A7',   # mauve pink
    'CALASH':         '#D55E00',   # vermillion (ours — stands out)
    'CALASH-NoCO2':   '#999999',   # grey
    'CALASH-NoSH':    '#A0522D',   # sienna
    'CALASH-NoCADR':  '#8B4513',   # saddle brown
    'CALASH-NoLCI':   '#6A5ACD',   # slate blue
    'CALASH-NoTHz':   '#2E8B57',   # sea green
}

FULL_MARKERS = {
    'LEACH':          's',
    'LEACH-1hop':     'P',
    'EE-LEACH':       '^',
    'ABC-ACO':        'D',
    'EERP':           'v',
    'Q-Routing':      'X',
    'RIS-DRL':        'h',
    'CALASH':         'o',
    'CALASH-NoCO2':   '<',
    'CALASH-NoSH':    '>',
    'CALASH-NoCADR':  'd',
    'CALASH-NoLCI':   'p',
    'CALASH-NoTHz':   '*',
}


# ═══════════════════════════════════════════════════════════════════
# Load campaign results
# ═══════════════════════════════════════════════════════════════════

def load_results(json_path: str, npz_path: str) -> dict:
    """
    Load campaign results from JSON (scalars) + NPZ (time-series).

    Returns dict in the format expected by CALASHPlotter:
        {protocol: {'protocol': name, 'aggregated': {...}}}
    """
    with open(json_path) as f:
        scalar_data = json.load(f)

    # Load time-series
    ts_data = {}
    if os.path.exists(npz_path):
        npz = np.load(npz_path, allow_pickle=True)
        for key in npz.files:
            ts_data[key] = npz[key]

    # Build unified results dict
    results = {}
    for proto_name, metrics in scalar_data.items():
        if proto_name.startswith('_'):
            continue  # skip _wilcoxon_tests

        safe = proto_name.replace('-', '_')
        agg = dict(metrics)  # scalar metrics already there

        # Attach time-series
        for ts_key in ['ts_alive', 'ts_pdr', 'ts_energy',
                       'ts_carbon', 'ts_fidelity', 'ts_fairness']:
            mean_key = f"{safe}__{ts_key}_mean"
            std_key = f"{safe}__{ts_key}_std"
            if mean_key in ts_data:
                agg[ts_key] = {
                    'mean': ts_data[mean_key].tolist(),
                    'std': ts_data[std_key].tolist()
                        if std_key in ts_data
                        else np.zeros_like(ts_data[mean_key]).tolist(),
                }

        results[proto_name] = {
            'protocol': proto_name,
            'aggregated': agg,
        }

    return results


# ═══════════════════════════════════════════════════════════════════
# Figure A: Pareto Front (2D + 3D)
# ═══════════════════════════════════════════════════════════════════

def fig_pareto_front(results: dict, outdir: str):
    """
    Generate 2D and 3D Pareto front figures.

    2D: PDR vs 1/Carbon with Pareto front boundary
    3D: PDR vs 1/Carbon vs Lifetime with dominated region shading
    """
    plt.rcParams.update(STYLE)

    names = list(results.keys())
    pdr_vals = []
    carbon_vals = []
    lifetime_vals = []

    for name in names:
        agg = results[name]['aggregated']
        pdr_vals.append(agg.get('overall_pdr', {}).get('mean', 0))
        carbon_vals.append(agg.get('total_carbon_gCO2', {}).get('mean', 1))
        lifetime_vals.append(agg.get('operational_lifetime', {}).get('mean', 0))

    pdr = np.array(pdr_vals)
    carbon = np.array(carbon_vals)
    lifetime = np.array(lifetime_vals)
    inv_carbon = 1.0 / np.maximum(carbon, 1e-10)

    # ──── 2D Pareto (PDR vs Carbon Efficiency) ────
    points_2d = np.column_stack([pdr, inv_carbon])
    pareto_mask = compute_pareto_front_2d(points_2d)

    fig, ax = plt.subplots(figsize=(4.5, 3.5))

    # Plot all protocols
    for i, name in enumerate(names):
        color = FULL_COLORS.get(name, '#666')
        marker = FULL_MARKERS.get(name, 'o')
        ms = 10 if name == 'CALASH' else 7
        zorder = 10 if name == 'CALASH' else 5
        edgecolor = 'black' if pareto_mask[i] else 'none'
        lw = 1.5 if pareto_mask[i] else 0.5

        ax.scatter(pdr[i], inv_carbon[i], c=color, marker=marker,
                   s=ms**2, label=name, zorder=zorder,
                   edgecolors=edgecolor, linewidths=lw)

    # Draw Pareto front boundary
    pareto_idx = np.where(pareto_mask)[0]
    if len(pareto_idx) > 1:
        pareto_pts = points_2d[pareto_idx]
        order = np.argsort(pareto_pts[:, 0])
        ax.plot(pareto_pts[order, 0], pareto_pts[order, 1],
                'r--', linewidth=1.5, alpha=0.7, label='Pareto Front',
                zorder=3)
        # Shade dominated region
        ax.fill_between(
            pareto_pts[order, 0], 0, pareto_pts[order, 1],
            alpha=0.08, color='red', zorder=1
        )

    # Compute hypervolume
    ref = np.array([0.0, 0.0])
    pareto_pts_for_hv = points_2d[pareto_mask]
    hv = hypervolume_2d(pareto_pts_for_hv, ref)

    ax.set_xlabel('Packet Delivery Ratio (PDR)', fontsize=9)
    ax.set_ylabel('Carbon Efficiency (1 / gCO₂eq)', fontsize=9)

    # Smart legend — outside right
    ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left',
              fontsize=6, framealpha=0.9, ncol=1)

    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    path = os.path.join(outdir, 'fig_pareto_2d.pdf')
    fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"  ✓ Saved: {path}")

    # ──── 3D Pareto (PDR × Carbon Eff × Lifetime) ────
    pareto_3d = compute_pareto_front_3d(pdr, inv_carbon, lifetime)

    fig = plt.figure(figsize=(5.5, 4.5))
    ax3 = fig.add_subplot(111, projection='3d')

    for i, name in enumerate(names):
        color = FULL_COLORS.get(name, '#666')
        marker = FULL_MARKERS.get(name, 'o')
        ms = 100 if name == 'CALASH' else 50
        alpha = 1.0 if pareto_3d[i] else 0.5
        edgecolor = 'black' if pareto_3d[i] else 'grey'

        ax3.scatter(pdr[i], inv_carbon[i], lifetime[i],
                    c=color, marker=marker, s=ms, alpha=alpha,
                    edgecolors=edgecolor, linewidths=0.5,
                    label=name, depthshade=True)

    ax3.set_xlabel('PDR', fontsize=8, labelpad=5)
    ax3.set_ylabel('1/Carbon', fontsize=8, labelpad=5)
    ax3.set_zlabel('Lifetime (rounds)', fontsize=8, labelpad=5)
    ax3.legend(bbox_to_anchor=(1.15, 1), loc='upper left',
               fontsize=5.5, framealpha=0.9, ncol=1)
    ax3.view_init(elev=25, azim=135)

    path = os.path.join(outdir, 'fig_pareto_3d.pdf')
    fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"  ✓ Saved: {path}")

    # Print dominance summary
    pareto_names = [names[i] for i in range(len(names)) if pareto_3d[i]]
    print(f"  Pareto-optimal protocols (3D): {pareto_names}")
    print(f"  2D Hypervolume (PDR × 1/Carbon): {hv:.6f}")

    return hv


# ═══════════════════════════════════════════════════════════════════
# Figure B: Ablation Study Bar Chart
# ═══════════════════════════════════════════════════════════════════

def fig_ablation_chart(results: dict, outdir: str):
    """
    Generate grouped bar chart showing marginal contribution of each pillar.

    X-axis: Removed pillar (CARE, SHDR, CADR, LSE, THz/6G)
    Y-axis: Marginal contribution (%) across 4 metrics
    """
    plt.rcParams.update(STYLE)

    # Build flat results for ablation module
    flat = {}
    for name, data in results.items():
        agg = data['aggregated']
        flat[name] = {
            'pdr': agg.get('overall_pdr', {}).get('mean', 0),
            'lifetime': agg.get('operational_lifetime', {}).get('mean', 0),
            'carbon_efficiency': 1.0 / max(
                agg.get('total_carbon_gCO2', {}).get('mean', 1), 1e-10),
            'data_fidelity': agg.get('avg_data_fidelity', {}).get('mean', 0),
        }

    contributions = compute_marginal_contributions(flat)
    if not contributions:
        print("  ⚠ No ablation data — skipping ablation chart")
        return

    pillars = list(contributions.keys())
    metrics = ['pdr', 'lifetime', 'carbon_efficiency', 'data_fidelity']
    metric_labels = {
        'pdr': 'PDR',
        'lifetime': 'Lifetime',
        'carbon_efficiency': 'Carbon Eff.',
        'data_fidelity': 'Data Fidelity',
    }
    colors = ['#2196F3', '#4CAF50', '#FF9800', '#9C27B0']
    hatches = ['', '///', '...', 'xxx']

    n_pillars = len(pillars)
    n_metrics = len(metrics)
    x = np.arange(n_pillars)
    width = 0.19

    fig, ax = plt.subplots(figsize=(5.5, 3.2))

    for i, metric in enumerate(metrics):
        values = []
        for pillar in pillars:
            if metric in contributions[pillar]:
                values.append(contributions[pillar][metric]['percentage'])
            else:
                values.append(0.0)

        bars = ax.bar(x + i * width - width * 1.5, values, width,
                      label=metric_labels[metric], color=colors[i],
                      edgecolor='black', linewidth=0.3,
                      hatch=hatches[i])

        # Value labels
        for bar, val in zip(bars, values):
            if abs(val) > 0.3:
                y = bar.get_height()
                va = 'bottom' if y >= 0 else 'top'
                offset = 0.2 if y >= 0 else -0.2
                ax.text(bar.get_x() + bar.get_width() / 2,
                        y + offset,
                        f'{val:.1f}%', ha='center', va=va,
                        fontsize=5.5, fontweight='bold')

    ax.set_xlabel('Removed Pillar', fontsize=9, fontweight='bold')
    ax.set_ylabel('Marginal Contribution (%)', fontsize=9, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(pillars, rotation=12, ha='right', fontsize=7)
    ax.legend(loc='upper right', fontsize=7, framealpha=0.9)
    ax.axhline(y=0, color='black', linewidth=0.8)
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    path = os.path.join(outdir, 'fig_ablation.pdf')
    fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"  ✓ Saved: {path}")

    # Print summary
    print("  Ablation contributions (%):")
    for pillar in pillars:
        vals = {m: contributions[pillar].get(m, {}).get('percentage', 0)
                for m in metrics}
        print(f"    {pillar:20s} → PDR={vals['pdr']:+.1f}  "
              f"Life={vals['lifetime']:+.1f}  "
              f"Carbon={vals['carbon_efficiency']:+.1f}  "
              f"Fid={vals['data_fidelity']:+.1f}")


# ═══════════════════════════════════════════════════════════════════
# Figure C: Convergence Plots (3-panel)
# ═══════════════════════════════════════════════════════════════════

def fig_convergence(results: dict, outdir: str):
    """
    Generate 3-panel convergence figure:
        Top:    Alive nodes vs round (all 13 protocols)
        Middle: Cumulative PDR over time
        Bottom: Cumulative carbon over time

    With ±σ shading for main protocols.
    """
    plt.rcParams.update(STYLE)

    # Select key protocols for clarity + full CALASH
    key_protocols = [
        'LEACH', 'EE-LEACH', 'ABC-ACO', 'EERP',
        'Q-Routing', 'RIS-DRL', 'CALASH',
    ]
    ablation_protocols = [
        'CALASH-NoCO2', 'CALASH-NoSH', 'CALASH-NoCADR',
        'CALASH-NoLCI', 'CALASH-NoTHz',
    ]

    fig, axes = plt.subplots(3, 1, figsize=(5.5, 7), sharex=True)

    ts_configs = [
        ('ts_alive', 'Alive Nodes', None),
        ('ts_pdr', 'Packet Delivery Ratio', (0, 1.05)),
        ('ts_carbon', 'Cumulative Carbon (gCO₂eq)', None),
    ]

    for ax, (ts_key, ylabel, ylim) in zip(axes, ts_configs):
        # Plot key protocols (solid, thick)
        for proto in key_protocols:
            if proto not in results:
                continue
            agg = results[proto]['aggregated']
            if ts_key not in agg:
                continue

            mean = np.array(agg[ts_key]['mean'])
            std = np.array(agg[ts_key]['std'])
            rounds = np.arange(1, len(mean) + 1)

            color = FULL_COLORS.get(proto, '#666')
            lw = 2.0 if proto == 'CALASH' else 1.0
            ls = '-' if proto == 'CALASH' else '--'
            zorder = 10 if proto == 'CALASH' else 5

            ax.plot(rounds, mean, color=color, linewidth=lw,
                    linestyle=ls, label=proto, zorder=zorder)

            # ±σ shading only for CALASH and selected baselines
            if proto in ('CALASH', 'LEACH', 'Q-Routing', 'RIS-DRL'):
                ax.fill_between(rounds, mean - std, np.maximum(mean + std, 0),
                                alpha=0.12, color=color, zorder=2)

        # Plot ablation protocols (thin, dotted)
        for proto in ablation_protocols:
            if proto not in results:
                continue
            agg = results[proto]['aggregated']
            if ts_key not in agg:
                continue

            mean = np.array(agg[ts_key]['mean'])
            rounds = np.arange(1, len(mean) + 1)
            color = FULL_COLORS.get(proto, '#999')

            ax.plot(rounds, mean, color=color, linewidth=0.7,
                    linestyle=':', alpha=0.6, label=proto, zorder=3)

        ax.set_ylabel(ylabel, fontsize=8)
        if ylim:
            ax.set_ylim(ylim)
        ax.grid(True, alpha=0.3)

    axes[-1].set_xlabel('Round', fontsize=9)

    # Unified legend at bottom
    handles, labels = axes[0].get_legend_handles_labels()
    # Add any extra from other panels not in first
    for ax in axes[1:]:
        h2, l2 = ax.get_legend_handles_labels()
        for h, l in zip(h2, l2):
            if l not in labels:
                handles.append(h)
                labels.append(l)

    fig.legend(handles, labels, loc='lower center',
               ncol=4, fontsize=6, framealpha=0.9,
               bbox_to_anchor=(0.5, -0.02))

    plt.tight_layout(rect=[0, 0.06, 1, 1])
    path = os.path.join(outdir, 'fig_convergence.pdf')
    fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"  ✓ Saved: {path}")


# ═══════════════════════════════════════════════════════════════════
# Figure D: Summary bar chart (all 13 protocols × 4 metrics)
# ═══════════════════════════════════════════════════════════════════

def fig_summary_bars(results: dict, outdir: str):
    """
    4-panel bar chart: Lifetime, PDR, Carbon, Fidelity for all 13 protocols.
    With 95% CI error bars.
    """
    plt.rcParams.update(STYLE)

    metrics = [
        ('operational_lifetime', 'Lifetime (rounds)', None),
        ('overall_pdr', 'PDR', (0, 1.05)),
        ('total_carbon_gCO2', 'Total Carbon (gCO₂eq)', None),
        ('avg_data_fidelity', 'Data Fidelity (1−NMSE)', (0, 1.05)),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(7, 5.5))
    axes = axes.ravel()

    # Order: baselines first, then CALASH, then ablations
    order = [
        'LEACH', 'LEACH-1hop', 'EE-LEACH', 'ABC-ACO', 'EERP',
        'Q-Routing', 'RIS-DRL', 'CALASH',
        'CALASH-NoCO2', 'CALASH-NoSH', 'CALASH-NoCADR',
        'CALASH-NoLCI', 'CALASH-NoTHz',
    ]
    available = [p for p in order if p in results]

    for ax, (mkey, ylabel, ylim) in zip(axes, metrics):
        means = []
        ci95s = []
        colors = []
        for p in available:
            agg = results[p]['aggregated']
            m = agg.get(mkey, {})
            means.append(m.get('mean', 0))
            ci95s.append(m.get('ci95', 0))
            colors.append(FULL_COLORS.get(p, '#666'))

        x = np.arange(len(available))
        ax.bar(x, means, yerr=ci95s, capsize=2, color=colors,
               edgecolor='black', linewidth=0.3)
        ax.set_xticks(x)
        ax.set_xticklabels(available, rotation=45, ha='right', fontsize=5.5)
        ax.set_ylabel(ylabel, fontsize=8)
        if ylim:
            ax.set_ylim(ylim)
        ax.grid(axis='y', alpha=0.3)

        # Highlight CALASH bar
        if 'CALASH' in available:
            idx = available.index('CALASH')
            ax.get_children()[idx].set_edgecolor('red')
            ax.get_children()[idx].set_linewidth(1.5)

    plt.tight_layout()
    path = os.path.join(outdir, 'fig_summary_bars.pdf')
    fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"  ✓ Saved: {path}")


# ═══════════════════════════════════════════════════════════════════
# Figure E: Wilcoxon statistical significance heatmap
# ═══════════════════════════════════════════════════════════════════

def fig_wilcoxon_heatmap(json_path: str, outdir: str):
    """
    Heatmap of Wilcoxon p-values: CALASH vs every other protocol.
    Green = significant (p < 0.05), Red = not significant.
    """
    plt.rcParams.update(STYLE)

    with open(json_path) as f:
        data = json.load(f)

    wilcoxon = data.get('_wilcoxon_tests', {})
    if not wilcoxon:
        print("  ⚠ No Wilcoxon test data — skipping heatmap")
        return

    test_metrics = ['operational_lifetime', 'overall_pdr',
                    'total_carbon_gCO2', 'avg_data_fidelity', 'lci']
    metric_labels = ['Lifetime', 'PDR', 'Carbon', 'Fidelity', 'LCI']

    protocols = sorted(wilcoxon.keys())
    n_proto = len(protocols)
    n_metrics = len(test_metrics)

    pval_matrix = np.ones((n_proto, n_metrics))
    for i, proto_key in enumerate(protocols):
        for j, metric in enumerate(test_metrics):
            if metric in wilcoxon[proto_key]:
                pval_matrix[i, j] = wilcoxon[proto_key][metric].get(
                    'p_value', 1.0)

    fig, ax = plt.subplots(figsize=(5, 3.5))

    # Color map: green for significant, red for not
    from matplotlib.colors import ListedColormap, BoundaryNorm
    cmap = ListedColormap(['#4CAF50', '#FF9800', '#F44336'])
    bounds = [0, 0.01, 0.05, 1.0]
    norm = BoundaryNorm(bounds, cmap.N)

    im = ax.imshow(pval_matrix, cmap=cmap, norm=norm, aspect='auto')

    # Labels
    short_names = [p.replace('CALASH_vs_', '') for p in protocols]
    ax.set_xticks(np.arange(n_metrics))
    ax.set_xticklabels(metric_labels, fontsize=7)
    ax.set_yticks(np.arange(n_proto))
    ax.set_yticklabels(short_names, fontsize=6)

    # Annotate cells
    for i in range(n_proto):
        for j in range(n_metrics):
            p = pval_matrix[i, j]
            txt = f'{p:.3f}' if p >= 0.001 else '<.001'
            color = 'white' if p < 0.05 else 'black'
            ax.text(j, i, txt, ha='center', va='center',
                    fontsize=5.5, color=color, fontweight='bold')

    cbar = fig.colorbar(im, ax=ax, ticks=[0.005, 0.03, 0.5],
                        shrink=0.8)
    cbar.set_ticklabels(['p<0.01', 'p<0.05', 'p≥0.05'])
    cbar.ax.tick_params(labelsize=6)

    plt.tight_layout()
    path = os.path.join(outdir, 'fig_wilcoxon_heatmap.pdf')
    fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"  ✓ Saved: {path}")


# ═══════════════════════════════════════════════════════════════════
# Print LaTeX table (bonus)
# ═══════════════════════════════════════════════════════════════════

def print_latex_table(results: dict):
    """Print a LaTeX-formatted comparison table for the paper."""
    order = [
        'LEACH', 'LEACH-1hop', 'EE-LEACH', 'ABC-ACO', 'EERP',
        'Q-Routing', 'RIS-DRL', 'CALASH',
        'CALASH-NoCO2', 'CALASH-NoSH', 'CALASH-NoCADR',
        'CALASH-NoLCI', 'CALASH-NoTHz',
    ]
    available = [p for p in order if p in results]

    print("\n" + "="*80)
    print("  LaTeX Table: Copy into paper")
    print("="*80)
    print(r"\begin{table}[h]")
    print(r"\centering")
    print(r"\caption{Comparison of 13 protocols (30 seeds, 5000 rounds, 200 nodes)}")
    print(r"\label{tab:main_results}")
    print(r"\scriptsize")
    print(r"\begin{tabular}{lrrrr}")
    print(r"\toprule")
    print(r"Protocol & Lifetime & PDR & Carbon (gCO$_2$) & Fidelity \\")
    print(r"\midrule")

    for p in available:
        agg = results[p]['aggregated']

        def fmt(key, dec=2):
            d = agg.get(key, {})
            m = d.get('mean', float('nan'))
            c = d.get('ci95', 0)
            if np.isnan(m):
                return "N/A"
            return f"{m:.{dec}f}$\\pm${c:.{dec}f}"

        row = f"{p} & {fmt('operational_lifetime', 0)} & " \
              f"{fmt('overall_pdr', 3)} & " \
              f"{fmt('total_carbon_gCO2', 4)} & " \
              f"{fmt('avg_data_fidelity', 3)} \\\\"

        if p == 'CALASH':
            row = r"\textbf{" + row.replace(r"\\", r"} \\")

        print(row)

        if p == 'RIS-DRL':
            print(r"\midrule")

    print(r"\bottomrule")
    print(r"\end{tabular}")
    print(r"\end{table}")


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description='Generate publication figures from CALASH campaign results'
    )
    parser.add_argument('--results', default='results/main.json',
                        help='Path to campaign JSON results')
    parser.add_argument('--ts', default='results/main_ts.npz',
                        help='Path to time-series NPZ file')
    parser.add_argument('--outdir', default='figures',
                        help='Output directory for figures')
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    print(f"\n{'='*60}")
    print(f"  CALASH Publication Figure Generator")
    print(f"  Results: {args.results}")
    print(f"  Output:  {args.outdir}/")
    print(f"{'='*60}\n")

    # Load results
    results = load_results(args.results, args.ts)
    print(f"  Loaded {len(results)} protocols: {list(results.keys())}\n")

    # ── Figure A: Pareto Front ──
    print("▸ Generating Pareto Front figures...")
    hv = fig_pareto_front(results, args.outdir)

    # ── Figure B: Ablation Chart ──
    print("\n▸ Generating Ablation Study chart...")
    fig_ablation_chart(results, args.outdir)

    # ── Figure C: Convergence Plots ──
    print("\n▸ Generating Convergence plots...")
    fig_convergence(results, args.outdir)

    # ── Figure D: Summary Bars ──
    print("\n▸ Generating Summary bar charts...")
    fig_summary_bars(results, args.outdir)

    # ── Figure E: Wilcoxon Heatmap ──
    print("\n▸ Generating Wilcoxon significance heatmap...")
    fig_wilcoxon_heatmap(args.results, args.outdir)

    # ── LaTeX Table ──
    print_latex_table(results)

    print(f"\n{'='*60}")
    print(f"  ✅ All figures saved to {args.outdir}/")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
