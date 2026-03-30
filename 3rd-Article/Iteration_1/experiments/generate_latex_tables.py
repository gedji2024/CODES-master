#!/usr/bin/env python3
"""
generate_latex_tables.py — Generate LaTeX-ready table content from real experiment results.
Outputs tables that can be directly pasted into main.tex.
"""
import json
import numpy as np

with open('campaign_output_v2/aggregated_tables.json') as f:
    agg = json.load(f)

with open('campaign_output_v2/all_results.json') as f:
    all_results = json.load(f)

with open('campaign_output_v2/statistical_tests.json') as f:
    stats_raw = json.load(f)


def get_runs(method, attack, severity, n_cells=12):
    return [r for r in all_results
            if r["method"] == method
            and r["attack_type"] == attack
            and r["severity"] == severity
            and r["n_cells"] == n_cells]


def g(key, metric, default=0):
    """Get aggregated value."""
    return agg.get(key, {}).get(metric, default)


def fmt_pct(mean, std=None):
    """Format percentage."""
    if std is not None and std > 0.05:
        return f"${mean:.1f}\\pm{std:.1f}$"
    return f"${mean:.1f}$"


def fmt_val(mean, std=None):
    """Format decimal value."""
    if std is not None and std > 0.005:
        return f"${mean:.2f}\\pm{std:.2f}$"
    if std is not None and std > 0.0005:
        return f"${mean:.3f}\\pm{std:.3f}$"
    return f"${mean:.3f}$"


def get_p(attack, severity, baseline, metric):
    """Get p-value from statistical tests."""
    key = f"{attack}_{severity}_{baseline}_{metric}"
    d = stats_raw.get(key, {})
    p = d.get("p_value", 1.0)
    if p < 0.001:
        return "${<}0.001$"
    elif p < 0.01:
        return f"${p:.3f}$"
    elif p < 0.05:
        return f"${p:.2f}$"
    else:
        return f"${p:.2f}$"


# ============================================================
# TABLE 5: Main Security Results
# ============================================================
print("=" * 80)
print("TABLE 5: Main Security Results (tab:main_results)")
print("=" * 80)

# Build rows for each method×condition
methods = [
    ("CASTER_ZT", "CASTER-ZT", None),
    ("TRUST_IMPLICIT", "Trust-Implicit", None),
    ("IDENTITY_ONLY", "Identity-Only", None),
    ("TELEMETRY_ONLY", "Telemetry-Only", None),
    ("CPO_SOFT", "CPO-Soft", "achiam2017cpo"),
    ("SHIELD_BINARY", "Shield-Binary", "alshiekh2018shielding"),
    ("AGENTIC_AUTO", "Agentic-Auto", "toward_autonomous_oran_2026"),
    ("IF_TRUST", "IF-Trust", "zahoor2025ifocsvm"),
]

conditions = [
    ("CLEAN", "NONE", "Clean"),
    ("TELEMETRY_POISONING", "HIGH", "Telemetry poisoning"),
    ("IDENTITY_CREDENTIAL_ABUSE", "HIGH", "Identity abuse"),
    ("COMBINED", "HIGH", "Combined"),
]

print("% Format: Method & Condition & Block% & Scope-Red% & Allow% & RogueDet & FalseBlk & omega_rec & p-value")
print()

for m_id, m_label, cite in methods:
    cite_str = f"\\\\cite{{{cite}}}" if cite else ""
    for atk, sev, cond_label in conditions:
        key = f"{m_id}_{atk}_{sev}"
        d = agg.get(key, {})
        if not d:
            continue
        
        blk = fmt_pct(d.get("block_mean", 0), d.get("block_std", 0))
        scope = fmt_pct(d.get("scope_mean", 0), d.get("scope_std", 0))
        allow = fmt_pct(d.get("allow_mean", 0), d.get("allow_std", 0))
        rdet = d.get("rogue_detect_mean", 0)
        fb = d.get("false_block_mean", 0)
        omega = fmt_val(d.get("omega_mean", 0), d.get("omega_std", 0))
        
        # Detection column
        if atk == "CLEAN":
            det_str = "---"
        elif rdet > 0:
            det_str = f"$\\mathbf{{{rdet:.3f}}}$" if rdet >= 0.999 else f"${rdet:.3f}$"
        else:
            det_str = "$0.000$"
        
        # p-value
        if m_id == "CASTER_ZT" or atk == "CLEAN":
            p_str = "---"
        else:
            p_str = get_p(atk, sev, m_id, "rogue_detection_rate")
        
        print(f"  {m_label}{cite_str} & {cond_label} & {blk} & {scope} & {allow} & {det_str} & {omega} & {p_str} \\\\")
    print("  \\midrule")

# ============================================================
# TABLE 6: Cross-Method Comparison (Combined HIGH)
# ============================================================
print()
print("=" * 80)
print("TABLE 6: Cross-Method Security Comparison (tab:cross_method)")
print("=" * 80)

print("% Under Combined HIGH attack")
rows = [
    ("Proposed", "CASTER_ZT", "CASTER-ZT", None),
    ("External", "CPO_SOFT", "CPO-Soft", "achiam2017cpo"),
    ("External", "SHIELD_BINARY", "Shield-Binary", "alshiekh2018shielding"),
    ("External", "AGENTIC_AUTO", "Agentic-Auto", "toward_autonomous_oran_2026"),
    ("External", "IF_TRUST", "IF-Trust", "zahoor2025ifocsvm"),
    ("Ablation", "ABLATION_NO_AUTHZ", "$-$Authorization", None),
    ("Ablation", "ABLATION_NO_TRUST", "$-$Trust assess.", None),
    ("Ablation", "ABLATION_NO_RISK", "$-$Risk assess.", None),
    ("Isolation", "TRUST_IMPLICIT", "Trust-Implicit", None),
    ("Isolation", "IDENTITY_ONLY", "Identity-Only", None),
    ("Isolation", "TELEMETRY_ONLY", "Telemetry-Only", None),
]

atk, sev = "COMBINED", "HIGH"
for cat, m_id, label, cite in rows:
    key = f"{m_id}_{atk}_{sev}"
    d = agg.get(key, {})
    cln = agg.get(f"{m_id}_CLEAN_NONE", {})
    
    blk = fmt_pct(d.get("block_mean", 0), d.get("block_std", 0))
    scope = fmt_pct(d.get("scope_mean", 0), d.get("scope_std", 0))
    total_filt = d.get("block_mean", 0) + d.get("scope_mean", 0)
    det = d.get("rogue_detect_mean", 0)
    fb_clean = cln.get("block_mean", 0)  # false block under clean
    fb_clean_std = cln.get("block_std", 0)
    
    cite_str = f"~\\cite{{{cite}}}" if cite else ""
    print(f"  {cat} & {label}{cite_str} & {blk} & {scope} & ${total_filt:.1f}$ & ${det:.3f}$ & {fmt_pct(fb_clean, fb_clean_std)} \\\\")

# ============================================================
# TABLE 7: Recovery Quality
# ============================================================
print()
print("=" * 80)
print("TABLE 7: Recovery Quality (tab:recovery_quality)")
print("=" * 80)

recovery_rows = [
    ("CASTER_ZT", "CASTER-ZT"),
    ("IF_TRUST", "IF-Trust"),
    ("SHIELD_BINARY", "Shield-Binary"),
    ("CPO_SOFT", "CPO-Soft"),
    ("AGENTIC_AUTO", "Agentic-Auto"),
    ("TRUST_IMPLICIT", "Trust-Implicit"),
    ("ABLATION_NO_TRUST", "$-$Trust assess."),
    ("ABLATION_NO_RISK", "$-$Risk assess."),
    ("ABLATION_NO_AUTHZ", "$-$Authorization"),
]

caster_omega = g("CASTER_ZT_IDENTITY_CREDENTIAL_ABUSE_HIGH", "omega_mean")
for m_id, label in recovery_rows:
    key = f"{m_id}_IDENTITY_CREDENTIAL_ABUSE_HIGH"
    om = g(key, "omega_mean")
    om_std = g(key, "omega_std")
    delta = om - caster_omega
    p_str = get_p("IDENTITY_CREDENTIAL_ABUSE", "HIGH", m_id, "omega_rec") if m_id != "CASTER_ZT" else "---"
    print(f"  {label} & {fmt_val(om, om_std)} & ${delta:+.3f}$ & {p_str} \\\\")

# ============================================================
# TABLE 8: Ablation Study
# ============================================================
print()
print("=" * 80)
print("TABLE 8: Ablation Study (tab:ablation)")
print("=" * 80)

ablation_methods = [
    ("CASTER_ZT", "CASTER-ZT (full)"),
    ("ABLATION_NO_AUTHZ", "$-$Authorization"),
    ("ABLATION_NO_TRUST", "$-$Trust assess."),
    ("ABLATION_NO_RISK", "$-$Risk assess."),
]

for m_id, label in ablation_methods:
    key = f"{m_id}_IDENTITY_CREDENTIAL_ABUSE_HIGH"
    d = agg.get(key, {})
    blk = fmt_pct(d.get("block_mean", 0), d.get("block_std", 0))
    scope = fmt_pct(d.get("scope_mean", 0), d.get("scope_std", 0))
    total = d.get("block_mean", 0) + d.get("scope_mean", 0)
    det = d.get("rogue_detect_mean", 0)
    rblk = d.get("rogue_block_mean", 0)
    om = g(key, "omega_mean")
    print(f"  {label} & {blk} & {scope} & ${total:.1f}$ & ${det:.3f}$ & ${rblk:.3f}$ & ${om:.3f}$ \\\\")

# ============================================================
# TABLE 9: Severity Comparison
# ============================================================
print()
print("=" * 80)
print("TABLE 9: Severity Comparison (tab:severity)")
print("=" * 80)

for atk_label, atk in [("Identity abuse", "IDENTITY_CREDENTIAL_ABUSE"), ("Combined", "COMBINED"), ("Telem. poisoning", "TELEMETRY_POISONING")]:
    for sev in ["MEDIUM", "HIGH"]:
        key = f"CASTER_ZT_{atk}_{sev}"
        d = agg.get(key, {})
        blk = fmt_pct(d.get("block_mean", 0), d.get("block_std", 0))
        det = d.get("rogue_detect_mean", 0)
        scope = fmt_pct(d.get("scope_mean", 0), d.get("scope_std", 0))
        om = g(key, "omega_mean")
        print(f"  {atk_label} & {sev.capitalize()} & {blk} & ${det:.3f}$ & {scope} & ${om:.3f}$ \\\\")

# ============================================================
# TABLE 10: Multi-Scale
# ============================================================
print()
print("=" * 80)
print("TABLE 10: Multi-Scale (tab:multiscale)")
print("=" * 80)

for nc, zones, seeds_label in [(12, 2, "20 seeds"), (36, 4, "10 seeds"), (100, 8, "10 seeds")]:
    runs_c = get_runs("CASTER_ZT", "IDENTITY_CREDENTIAL_ABUSE", "HIGH", nc)
    
    if runs_c:
        c_blk = np.mean([r["block_pct"] for r in runs_c])
        c_blk_std = np.std([r["block_pct"] for r in runs_c])
        c_det = np.mean([r["rogue_detection_rate"] for r in runs_c])
        c_lat = np.mean([r["latency_ms_per_tick"] for r in runs_c])
        c_om = np.mean([r["omega_rec"] for r in runs_c])
        
        # Best external = Shield-Binary
        runs_sb = get_runs("SHIELD_BINARY", "IDENTITY_CREDENTIAL_ABUSE", "HIGH", nc)
        sb_blk = np.mean([r["block_pct"] for r in runs_sb]) if runs_sb else 0
        
        print(f"  {nc}-cell, {zones}-zone & {fmt_pct(c_blk, c_blk_std)} & ${c_det:.3f}$ & ${c_om:.3f}$ & ${c_lat:.2f}$ ms & {fmt_pct(sb_blk)} \\\\")

# ============================================================
# TABLE 11: Threshold Sensitivity
# ============================================================
print()
print("=" * 80)
print("TABLE 11: Threshold Sensitivity (tab:threshold_sensitivity)")
print("=" * 80)

with open('campaign_output_v2/threshold_sweep.json') as f:
    sweep = json.load(f)

for s in sweep:
    gamma = s["gamma_1"]
    blk = s["block_mean"]
    scope = s.get("scope_mean", 0)
    det = s["rogue_detect_mean"]
    fb = s["false_block_mean"]
    om = s["omega_mean"]
    bold = "\\textbf{" if abs(gamma - 0.30) < 0.01 else ""
    bold_end = "}" if bold else ""
    print(f"  {bold}{gamma:.2f}{bold_end} & {bold}{blk:.1f}{bold_end} & {bold}{scope:.1f}{bold_end} & {bold}{det:.3f}{bold_end} & {bold}{fb:.1f}{bold_end} & {bold}{om:.3f}{bold_end} \\\\")

# ============================================================
# TABLE 12: Deployment Profile
# ============================================================
print()
print("=" * 80)
print("TABLE 12: Deployment Profile (tab:deployment)")
print("=" * 80)

# Compute actual metrics from data
czt_clean = get_runs("CASTER_ZT", "CLEAN", "NONE", 12)
czt_attack = get_runs("CASTER_ZT", "IDENTITY_CREDENTIAL_ABUSE", "HIGH", 12)
ti_clean = get_runs("TRUST_IMPLICIT", "CLEAN", "NONE", 12)
ti_attack = get_runs("TRUST_IMPLICIT", "IDENTITY_CREDENTIAL_ABUSE", "HIGH", 12)

czt_lat = np.mean([r["latency_ms_per_tick"] for r in czt_attack]) if czt_attack else 0
ti_lat = np.mean([r["latency_ms_per_tick"] for r in ti_attack]) if ti_attack else 0
czt_om = np.mean([r["omega_rec"] for r in czt_attack]) if czt_attack else 0
ti_om = np.mean([r["omega_rec"] for r in ti_attack]) if ti_attack else 0

print(f"  Decision latency (ms/tick) & $\\approx${czt_lat:.2f} & $\\approx${ti_lat:.2f} \\\\")
print(f"  $\\omega_{{\\mathrm{{rec}}}}$ (identity attack) & {czt_om:.3f} & {ti_om:.3f} \\\\")
print(f"  Audit completeness & 100\\% & 0\\% \\\\")

# ============================================================
# TABLE: Resource Budget (tab:resource_budget) - mostly static
# ============================================================
print()
print("=" * 80)
print("TABLE 13: Resource Budget (tab:resource_budget)")
print("=" * 80)

# Latency values for different scales
for nc in [12, 36, 100]:
    runs = get_runs("CASTER_ZT", "IDENTITY_CREDENTIAL_ABUSE", "HIGH", nc)
    if runs:
        lat = np.mean([r["latency_ms_per_tick"] for r in runs])
        print(f"  {nc}-cell latency: {lat:.2f} ms")

# ============================================================
# INLINE TEXT NUMBERS
# ============================================================
print()
print("=" * 80)
print("KEY INLINE NUMBERS FOR TEXT")
print("=" * 80)

# CASTER-ZT Identity Abuse HIGH
c_ica = agg.get("CASTER_ZT_IDENTITY_CREDENTIAL_ABUSE_HIGH", {})
print(f"CASTER-ZT Block% (ID abuse): {c_ica.get('block_mean',0):.1f}±{c_ica.get('block_std',0):.1f}")
print(f"CASTER-ZT ScopeR% (ID abuse): {c_ica.get('scope_mean',0):.1f}±{c_ica.get('scope_std',0):.1f}")
print(f"CASTER-ZT Allow% (ID abuse): {c_ica.get('allow_mean',0):.1f}±{c_ica.get('allow_std',0):.1f}")
print(f"CASTER-ZT RogueDet (ID abuse): {c_ica.get('rogue_detect_mean',0):.3f}")
print(f"CASTER-ZT RogueBlk (ID abuse): {c_ica.get('rogue_block_mean',0):.3f}")
print(f"CASTER-ZT FalseBlk (ID abuse): {c_ica.get('false_block_mean',0):.3f}")
print(f"CASTER-ZT omega (ID abuse): {c_ica.get('omega_mean',0):.3f}±{c_ica.get('omega_std',0):.3f}")
total_filter = c_ica.get('block_mean',0) + c_ica.get('scope_mean',0)
print(f"CASTER-ZT Total Filter% (ID abuse): {total_filter:.1f}")

# Combined
c_comb = agg.get("CASTER_ZT_COMBINED_HIGH", {})
print(f"\nCASTER-ZT Block% (Combined): {c_comb.get('block_mean',0):.1f}±{c_comb.get('block_std',0):.1f}")
comb_filt = c_comb.get('block_mean',0) + c_comb.get('scope_mean',0)
print(f"CASTER-ZT Total Filter% (Combined): {comb_filt:.1f}")

# IF-Trust comparison
i_ica = agg.get("IF_TRUST_IDENTITY_CREDENTIAL_ABUSE_HIGH", {})
print(f"\nIF-Trust Block% (ID abuse): {i_ica.get('block_mean',0):.1f}")
print(f"IF-Trust ScopeR% (ID abuse): {i_ica.get('scope_mean',0):.1f}")
print(f"IF-Trust RogueBlk (ID abuse): {i_ica.get('rogue_block_mean',0):.3f}")
print(f"IF-Trust omega (ID abuse): {i_ica.get('omega_mean',0):.3f}")
i_comb = agg.get("IF_TRUST_COMBINED_HIGH", {})
i_comb_filt = i_comb.get('block_mean',0) + i_comb.get('scope_mean',0)
print(f"IF-Trust Total Filter% (Combined): {i_comb_filt:.1f}")

# Baselines
for m, label in [("CPO_SOFT","CPO"), ("SHIELD_BINARY","Shield"), ("AGENTIC_AUTO","Agentic")]:
    d = agg.get(f"{m}_IDENTITY_CREDENTIAL_ABUSE_HIGH", {})
    print(f"\n{label} Block% (ID abuse): {d.get('block_mean',0):.1f}±{d.get('block_std',0):.1f}")
    print(f"{label} RogueDet: {d.get('rogue_detect_mean',0):.3f}")
    print(f"{label} FalseBlk: {d.get('false_block_mean',0):.3f}")
    print(f"{label} omega: {d.get('omega_mean',0):.3f}")
    # Clean false block
    cln = agg.get(f"{m}_CLEAN_NONE", {})
    print(f"{label} Clean Block% (FP): {cln.get('block_mean',0):.1f}")

# Multi-scale latency
print("\nMulti-scale latencies:")
for nc in [12, 36, 100]:
    runs = get_runs("CASTER_ZT", "IDENTITY_CREDENTIAL_ABUSE", "HIGH", nc)
    if runs:
        lat = np.mean([r["latency_ms_per_tick"] for r in runs])
        print(f"  {nc}-cell: {lat:.2f} ms")

# Trust-Implicit omega
ti = agg.get("TRUST_IMPLICIT_IDENTITY_CREDENTIAL_ABUSE_HIGH", {})
print(f"\nTrust-Implicit omega (ID abuse): {ti.get('omega_mean',0):.3f}±{ti.get('omega_std',0):.3f}")

# Experiment totals
print(f"\nTotal runs: 2420 (1540 primary + 440×2 multi-scale)")
print(f"Primary: 11 methods × 7 conditions × 20 seeds = 1540")
print(f"36-cell: 11 methods × 4 conditions × 10 seeds = 440")
print(f"100-cell: 11 methods × 4 conditions × 10 seeds = 440")
