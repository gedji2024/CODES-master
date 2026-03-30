#!/usr/bin/env python3
"""
generate_figures.py — Generate publication-quality figures for CASTER-ZT paper.
Reads campaign_output_v2 data and produces PDF/PNG figures.
"""
import json
import os
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# Style
plt.rcParams.update({
    'font.size': 11,
    'font.family': 'serif',
    'axes.labelsize': 12,
    'axes.titlesize': 13,
    'legend.fontsize': 9,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'axes.grid': True,
    'grid.alpha': 0.3,
})

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "campaign_output_v2")
FIG_DIR = os.path.join(BASE, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

# Load data
with open(os.path.join(DATA_DIR, "all_results.json")) as f:
    all_results = json.load(f)

with open(os.path.join(DATA_DIR, "aggregated_tables.json")) as f:
    agg = json.load(f)


def get_runs(method, attack, severity, n_cells=12):
    return [r for r in all_results
            if r["method"] == method
            and r["attack_type"] == attack
            and r["severity"] == severity
            and r["n_cells"] == n_cells]


# ========================================================================
# Figure 1: Bar chart — Rogue Detection Rate comparison
# ========================================================================
def fig_rogue_detection_comparison():
    methods = ["CASTER_ZT", "IF_TRUST", "SHIELD_BINARY", "AGENTIC_AUTO",
               "CPO_SOFT", "TRUST_IMPLICIT"]
    labels = ["CASTER-ZT", "IF-Trust", "Shield-Binary", "Agentic-Auto",
              "CPO-Soft", "Trust-Implicit"]
    attacks = [("IDENTITY_CREDENTIAL_ABUSE", "HIGH"),
               ("COMBINED", "HIGH")]
    attack_labels = ["Identity Abuse", "Combined"]
    colors = ["#2196F3", "#FF9800"]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(methods))
    width = 0.35

    for i, (atk, sev) in enumerate(attacks):
        means = []
        stds = []
        for m in methods:
            key = f"{m}_{atk}_{sev}"
            d = agg.get(key, {})
            means.append(d.get("rogue_detect_mean", 0) * 100)
            stds.append(d.get("rogue_detect_std", 0) * 100)
        bars = ax.bar(x + i * width - width / 2, means, width,
                      yerr=stds, label=attack_labels[i],
                      color=colors[i], capsize=3, edgecolor='black',
                      linewidth=0.5)

    ax.set_ylabel("Rogue Detection Rate (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha='right')
    ax.set_ylim(0, 110)
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "fig_rogue_detection.pdf"))
    plt.savefig(os.path.join(FIG_DIR, "fig_rogue_detection.png"))
    plt.close()
    print("  [OK] fig_rogue_detection")


# ========================================================================
# Figure 2: Grouped bar — Security vs. False Positive tradeoff
# ========================================================================
def fig_security_tradeoff():
    methods = ["CASTER_ZT", "IF_TRUST", "SHIELD_BINARY", "AGENTIC_AUTO",
               "CPO_SOFT"]
    labels = ["CASTER-ZT", "IF-Trust", "Shield-Bin.", "Agentic-Auto",
              "CPO-Soft"]

    atk, sev = "IDENTITY_CREDENTIAL_ABUSE", "HIGH"
    rogue_det = []
    false_blk = []
    for m in methods:
        key = f"{m}_{atk}_{sev}"
        d = agg.get(key, {})
        rogue_det.append(d.get("rogue_detect_mean", 0) * 100)
        false_blk.append(d.get("false_block_mean", 0) * 100)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    x = np.arange(len(methods))
    w = 0.35
    ax.bar(x - w/2, rogue_det, w, label="Rogue Detection (%)",
           color="#4CAF50", edgecolor='black', linewidth=0.5)
    ax.bar(x + w/2, false_blk, w, label="False Block (%)",
           color="#F44336", edgecolor='black', linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha='right')
    ax.set_ylabel("Rate (%)")
    ax.set_ylim(0, 110)
    ax.legend(loc='upper right')
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "fig_security_tradeoff.pdf"))
    plt.savefig(os.path.join(FIG_DIR, "fig_security_tradeoff.png"))
    plt.close()
    print("  [OK] fig_security_tradeoff")


# ========================================================================
# Figure 3: Recovery quality (omega_rec) comparison
# ========================================================================
def fig_recovery_quality():
    methods = ["CASTER_ZT", "IF_TRUST", "SHIELD_BINARY", "AGENTIC_AUTO",
               "CPO_SOFT", "TRUST_IMPLICIT"]
    labels = ["CASTER-ZT", "IF-Trust", "Shield-Bin.", "Agentic-Auto",
              "CPO-Soft", "Trust-Impl."]

    attacks = [("IDENTITY_CREDENTIAL_ABUSE", "HIGH"),
               ("COMBINED", "HIGH"),
               ("CLEAN", "NONE")]
    atk_labels = ["Identity Abuse", "Combined", "Clean"]
    colors = ["#2196F3", "#FF9800", "#4CAF50"]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(methods))
    n = len(attacks)
    w = 0.25

    for i, (atk, sev) in enumerate(attacks):
        means = []
        stds = []
        for m in methods:
            key = f"{m}_{atk}_{sev}"
            d = agg.get(key, {})
            means.append(d.get("omega_mean", 0))
            stds.append(d.get("omega_std", 0))
        ax.bar(x + (i - n/2 + 0.5) * w, means, w, yerr=stds,
               label=atk_labels[i], color=colors[i], capsize=2,
               edgecolor='black', linewidth=0.5)

    ax.set_ylabel(r"Recovery Quality ($\omega_{rec}$)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha='right')
    ax.set_ylim(0, 1.1)
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "fig_recovery_quality.pdf"))
    plt.savefig(os.path.join(FIG_DIR, "fig_recovery_quality.png"))
    plt.close()
    print("  [OK] fig_recovery_quality")


# ========================================================================
# Figure 4: Ablation study
# ========================================================================
def fig_ablation():
    methods = ["CASTER_ZT", "ABLATION_NO_AUTHZ", "ABLATION_NO_TRUST",
               "ABLATION_NO_RISK"]
    labels = ["Full CASTER-ZT", "−Authorization", "−Trust", "−Risk"]
    metrics_keys = ["rogue_detect_mean", "omega_mean"]
    metric_labels = ["Rogue Detection Rate", r"Recovery $\omega_{rec}$"]
    colors = ["#4CAF50", "#F44336"]

    atk, sev = "IDENTITY_CREDENTIAL_ABUSE", "HIGH"

    fig, ax = plt.subplots(figsize=(7, 4.5))
    x = np.arange(len(methods))
    w = 0.35

    for i, (mk, ml) in enumerate(zip(metrics_keys, metric_labels)):
        vals = []
        for m in methods:
            key = f"{m}_{atk}_{sev}"
            d = agg.get(key, {})
            vals.append(d.get(mk, 0) if "detect" in mk else d.get(mk, 0))
        ax.bar(x + (i - 0.5) * w, vals, w, label=ml,
               color=colors[i], edgecolor='black', linewidth=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha='right')
    ax.set_ylabel("Score")
    ax.set_ylim(0, 1.15)
    ax.legend(loc='upper right')
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "fig_ablation.pdf"))
    plt.savefig(os.path.join(FIG_DIR, "fig_ablation.png"))
    plt.close()
    print("  [OK] fig_ablation")


# ========================================================================
# Figure 5: Multi-scale performance
# ========================================================================
def fig_multiscale():
    scales = [12, 36, 100]

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))

    # (a) Rogue detection by scale
    dets = []
    for nc in scales:
        runs = get_runs("CASTER_ZT", "IDENTITY_CREDENTIAL_ABUSE", "HIGH", nc)
        dets.append(np.mean([r["rogue_detection_rate"] for r in runs]) * 100
                    if runs else 0)
    axes[0].bar([str(s) for s in scales], dets, color="#2196F3",
                edgecolor='black', linewidth=0.5)
    axes[0].set_ylabel("Rogue Detection (%)")
    axes[0].set_xlabel("Network Size (cells)")
    axes[0].set_ylim(0, 110)
    axes[0].set_title("(a) Detection vs. Scale")

    # (b) Latency by scale
    lats = []
    lat_stds = []
    for nc in scales:
        runs = get_runs("CASTER_ZT", "IDENTITY_CREDENTIAL_ABUSE", "HIGH", nc)
        if runs:
            lats.append(np.mean([r["latency_ms_per_tick"] for r in runs]))
            lat_stds.append(np.std([r["latency_ms_per_tick"] for r in runs]))
        else:
            lats.append(0)
            lat_stds.append(0)
    axes[1].bar([str(s) for s in scales], lats, yerr=lat_stds,
                color="#FF9800", edgecolor='black', linewidth=0.5, capsize=3)
    axes[1].set_ylabel("Latency (ms/tick)")
    axes[1].set_xlabel("Network Size (cells)")
    axes[1].set_title("(b) Latency vs. Scale")

    # (c) omega_rec by scale
    omegas = []
    om_stds = []
    for nc in scales:
        runs = get_runs("CASTER_ZT", "IDENTITY_CREDENTIAL_ABUSE", "HIGH", nc)
        if runs:
            omegas.append(np.mean([r["omega_rec"] for r in runs]))
            om_stds.append(np.std([r["omega_rec"] for r in runs]))
        else:
            omegas.append(0)
            om_stds.append(0)
    axes[2].bar([str(s) for s in scales], omegas, yerr=om_stds,
                color="#4CAF50", edgecolor='black', linewidth=0.5, capsize=3)
    axes[2].set_ylabel(r"$\omega_{rec}$")
    axes[2].set_xlabel("Network Size (cells)")
    axes[2].set_ylim(0, 1.1)
    axes[2].set_title(r"(c) Recovery $\omega_{rec}$ vs. Scale")

    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "fig_multiscale.pdf"))
    plt.savefig(os.path.join(FIG_DIR, "fig_multiscale.png"))
    plt.close()
    print("  [OK] fig_multiscale")


# ========================================================================
# Figure 6: Threshold sensitivity (gamma_1 sweep)
# ========================================================================
def fig_threshold_sweep():
    sweep_path = os.path.join(DATA_DIR, "threshold_sweep.json")
    if not os.path.exists(sweep_path):
        print("  [SKIP] threshold_sweep (no data)")
        return

    with open(sweep_path) as f:
        sweep = json.load(f)

    gammas = [s["gamma_1"] for s in sweep]
    blocks = [s["block_mean"] for s in sweep]
    detects = [s["rogue_detect_mean"] * 100 for s in sweep]
    false_blks = [s["false_block_mean"] for s in sweep]
    omegas = [s["omega_mean"] for s in sweep]

    fig, ax1 = plt.subplots(figsize=(7, 4.5))
    ax2 = ax1.twinx()

    l1, = ax1.plot(gammas, detects, 'o-', color="#4CAF50", linewidth=2,
                   label="Rogue Detection (%)", markersize=6)
    l2, = ax1.plot(gammas, false_blks, 's-', color="#F44336", linewidth=2,
                   label="False Block (%)", markersize=6)
    l3, = ax2.plot(gammas, omegas, '^-', color="#2196F3", linewidth=2,
                   label=r"$\omega_{rec}$", markersize=6)

    # Mark the default gamma_1=0.30
    ax1.axvline(x=0.30, color='gray', linestyle='--', alpha=0.7, linewidth=1)
    ax1.annotate(r'$\gamma_1=0.30$', xy=(0.30, 95), fontsize=9, color='gray')

    ax1.set_xlabel(r"Shield threshold $\gamma_1$")
    ax1.set_ylabel("Rate (%)")
    ax2.set_ylabel(r"Recovery Quality ($\omega_{rec}$)")
    ax1.set_ylim(-5, 110)
    ax2.set_ylim(0, 1.1)

    lines = [l1, l2, l3]
    ax1.legend(lines, [l.get_label() for l in lines], loc='center right')

    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "fig_threshold_sweep.pdf"))
    plt.savefig(os.path.join(FIG_DIR, "fig_threshold_sweep.png"))
    plt.close()
    print("  [OK] fig_threshold_sweep")


# ========================================================================
# Figure 7: Severity comparison (MEDIUM vs HIGH)
# ========================================================================
def fig_severity_comparison():
    methods = ["CASTER_ZT", "IF_TRUST", "SHIELD_BINARY", "AGENTIC_AUTO"]
    labels = ["CASTER-ZT", "IF-Trust", "Shield-Bin.", "Agentic-Auto"]

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))

    # (a) Identity Abuse
    for sev, color, marker in [("MEDIUM", "#81D4FA", 'o'), ("HIGH", "#1565C0", 's')]:
        vals = []
        for m in methods:
            key = f"{m}_IDENTITY_CREDENTIAL_ABUSE_{sev}"
            d = agg.get(key, {})
            vals.append(d.get("rogue_detect_mean", 0) * 100)
        axes[0].bar(np.arange(len(methods)) + (0 if sev == "MEDIUM" else 0.35) - 0.175,
                    vals, 0.35, label=sev, color=color,
                    edgecolor='black', linewidth=0.5)
    axes[0].set_xticks(np.arange(len(methods)))
    axes[0].set_xticklabels(labels, rotation=15, ha='right')
    axes[0].set_ylabel("Rogue Detection (%)")
    axes[0].set_ylim(0, 110)
    axes[0].legend()
    axes[0].set_title("(a) Identity Credential Abuse")

    # (b) Combined
    for sev, color in [("MEDIUM", "#FFE082"), ("HIGH", "#E65100")]:
        vals = []
        for m in methods:
            key = f"{m}_COMBINED_{sev}"
            d = agg.get(key, {})
            vals.append(d.get("rogue_detect_mean", 0) * 100)
        axes[1].bar(np.arange(len(methods)) + (0 if sev == "MEDIUM" else 0.35) - 0.175,
                    vals, 0.35, label=sev, color=color,
                    edgecolor='black', linewidth=0.5)
    axes[1].set_xticks(np.arange(len(methods)))
    axes[1].set_xticklabels(labels, rotation=15, ha='right')
    axes[1].set_ylabel("Rogue Detection (%)")
    axes[1].set_ylim(0, 110)
    axes[1].legend()
    axes[1].set_title("(b) Combined Attack")

    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "fig_severity_comparison.pdf"))
    plt.savefig(os.path.join(FIG_DIR, "fig_severity_comparison.png"))
    plt.close()
    print("  [OK] fig_severity_comparison")


# ========================================================================
# Figure 8: Radar / spider chart — comprehensive method comparison
# ========================================================================
def fig_radar_comparison():
    from matplotlib.patches import FancyBboxPatch

    methods = ["CASTER_ZT", "IF_TRUST", "SHIELD_BINARY", "AGENTIC_AUTO",
               "CPO_SOFT"]
    labels = ["CASTER-ZT", "IF-Trust", "Shield-Binary", "Agentic-Auto",
              "CPO-Soft"]
    colors = ["#2196F3", "#FF9800", "#4CAF50", "#9C27B0", "#F44336"]

    # Metrics (all normalized to [0,1], higher=better)
    metric_names = ["Rogue\nDetection", "Recovery\n" + r"$\omega_{rec}$",
                    "Low False\nBlock", "Low\nLatency",
                    "Scalability"]
    n_metrics = len(metric_names)

    atk, sev = "IDENTITY_CREDENTIAL_ABUSE", "HIGH"

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    angles = np.linspace(0, 2 * np.pi, n_metrics, endpoint=False).tolist()
    angles += angles[:1]

    for i, m in enumerate(methods):
        key = f"{m}_{atk}_{sev}"
        d = agg.get(key, {})

        det = d.get("rogue_detect_mean", 0)
        omega = d.get("omega_mean", 0)
        low_fb = 1.0 - d.get("false_block_mean", 0)  # Invert: lower FB = better

        # Latency (use 12-cell runs)
        runs = get_runs(m, atk, sev, 12)
        lat = np.mean([r["latency_ms_per_tick"] for r in runs]) if runs else 1.0
        low_lat = max(0, 1.0 - lat / 2.0)  # Normalize

        # Scalability: check 100-cell
        runs_100 = get_runs(m, atk, sev, 100)
        if runs_100:
            scale_det = np.mean([r["rogue_detection_rate"] for r in runs_100])
        else:
            scale_det = det  # Use 12-cell if 100-cell not available
        scalability = scale_det

        values = [det, omega, low_fb, low_lat, scalability]
        values += values[:1]

        ax.plot(angles, values, 'o-', linewidth=2, label=labels[i],
                color=colors[i], markersize=5)
        ax.fill(angles, values, alpha=0.1, color=colors[i])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(metric_names)
    ax.set_ylim(0, 1.1)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(["0.2", "0.4", "0.6", "0.8", "1.0"], size=8)
    ax.legend(loc='upper right', bbox_to_anchor=(1.35, 1.1))
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "fig_radar_comparison.pdf"))
    plt.savefig(os.path.join(FIG_DIR, "fig_radar_comparison.png"))
    plt.close()
    print("  [OK] fig_radar_comparison")


# ========================================================================
# Main
# ========================================================================
if __name__ == "__main__":
    print("Generating figures...")
    fig_rogue_detection_comparison()
    fig_security_tradeoff()
    fig_recovery_quality()
    fig_ablation()
    fig_multiscale()
    fig_threshold_sweep()
    fig_severity_comparison()
    fig_radar_comparison()
    print(f"\nAll figures saved to: {FIG_DIR}")
