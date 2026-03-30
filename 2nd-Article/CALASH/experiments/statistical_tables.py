"""
Statistical Table Formatter for Journal Publication
=====================================================
Generates publication-ready comparison tables with:
    - Mean +/- 95% CI (t-distribution, n-1 degrees of freedom)
    - Bold-best values per metric (automatically detected)
    - Statistical significance markers (Wilcoxon signed-rank test [1])
    - Proper formatting for IEEE / Elsevier journals

Output formats:
    - LaTeX (.tex) -- ready for \\input{} in paper source
    - Markdown (.md) -- for README / quick review
    - CSV (.csv) -- for further processing in Excel/pandas

Table design follows IEEE Transactions formatting guidelines:
    - Caption above table, notes below
    - Horizontal rules only (no vertical lines)
    - Up/down arrows indicate optimization direction per metric

References
----------
[1] Wilcoxon, F. "Individual Comparisons by Ranking Methods."
    Biometrics Bulletin, 1(6), pp. 80-83, 1945. DOI: 10.2307/3001968

[2] IEEE. "Preparation of Papers for IEEE Transactions and Journals."
    IEEE Author Center, 2024.
    https://journals.ieeeauthorcenter.ieee.org/
"""

import os
import json
import numpy as np
from typing import Dict, List, Tuple, Optional


def format_mean_ci(mean: float, ci95: float,
                   decimals: int = 2,
                   bold: bool = False) -> str:
    """Format mean ± CI with optional boldface."""
    if np.isnan(mean):
        return "N/A"
    s = f"{mean:.{decimals}f}$\\pm${ci95:.{decimals}f}"
    if bold:
        s = f"\\textbf{{{s}}}"
    return s


def generate_main_table(results: dict,
                        output_dir: str = 'results',
                        calash_key: str = 'CALASH') -> str:
    """
    Generate the main comparison table (Table I in a typical paper).

    Parameters
    ----------
    results : dict
        {protocol: {metric: {mean, ci95, ...}}}
    output_dir : str
        Output directory.
    calash_key : str
        Key for the proposed method (for significance testing).

    Returns
    -------
    str
        LaTeX table source.
    """
    metrics = [
        ('first_death_round', '1st Death', 0, 'max'),
        ('half_death_round', 'Half Death', 0, 'max'),
        ('overall_pdr', 'PDR', 3, 'max'),
        ('total_carbon_gCO2', 'Carbon (gCO₂)', 4, 'min'),
        ('avg_data_fidelity', 'Fidelity', 3, 'max'),
        ('lci', 'LCI', 2, 'min'),
        ('jains_fairness', "Jain's FI", 3, 'max'),
        ('recovery_time_rounds', 'Recovery', 0, 'min'),
    ]

    protocols = list(results.keys())

    # Find best per metric
    best_proto = {}
    for key, _, _, direction in metrics:
        best_val = None
        best_p = None
        for proto in protocols:
            m = results[proto].get(key, {})
            val = m.get('mean', np.nan)
            if np.isnan(val):
                continue
            if best_val is None:
                best_val = val
                best_p = proto
            elif direction == 'max' and val > best_val:
                best_val = val
                best_p = proto
            elif direction == 'min' and val < best_val:
                best_val = val
                best_p = proto
        best_proto[key] = best_p

    # Significance testing (CALASH vs each baseline)
    significance = {}  # (proto, metric) → symbol
    calash_raw = results.get(calash_key, {}).get('_raw_values', {})
    for proto in protocols:
        if proto == calash_key:
            continue
        proto_raw = results.get(proto, {}).get('_raw_values', {})
        for key, _, _, _ in metrics:
            cal_vals = calash_raw.get(key, [])
            p_vals = proto_raw.get(key, [])
            if len(cal_vals) >= 5 and len(p_vals) >= 5:
                from experiments.parallel_runner import wilcoxon_test
                test = wilcoxon_test(cal_vals, p_vals)
                if test['significant']:
                    significance[(proto, key)] = '$\\dagger$'
                else:
                    significance[(proto, key)] = ''
            else:
                significance[(proto, key)] = ''

    # Build LaTeX
    n_cols = len(metrics) + 1
    col_spec = 'l' + 'r' * len(metrics)

    lines = []
    lines.append('\\begin{table*}[!t]')
    lines.append('\\centering')
    lines.append('\\caption{Performance comparison across all protocols '
                 '(mean $\\pm$ 95\\% CI, 30 seeds). '
                 'Best values are \\textbf{bold}. '
                 '$\\dagger$ indicates $p < 0.05$ vs CALASH '
                 '(Wilcoxon signed-rank test).}')
    lines.append('\\label{tab:main_results}')
    lines.append(f'\\begin{{tabular}}{{{col_spec}}}')
    lines.append('\\toprule')

    # Header
    header = 'Protocol'
    for _, label, _, _ in metrics:
        header += f' & {label}'
    header += ' \\\\'
    lines.append(header)
    lines.append('\\midrule')

    # Data rows
    for proto in protocols:
        row = proto.replace('_', '\\_').replace('-', '\\text{-}')
        for key, _, decimals, direction in metrics:
            m = results[proto].get(key, {})
            mean = m.get('mean', np.nan)
            ci = m.get('ci95', 0)
            is_best = (best_proto.get(key) == proto)
            sig = significance.get((proto, key), '')

            cell = format_mean_ci(mean, ci, decimals, bold=is_best)
            cell += sig
            row += f' & {cell}'

        row += ' \\\\'
        lines.append(row)

        # Separator between baselines and ablations
        if proto in ('Q-Routing',):
            lines.append('\\midrule')

    lines.append('\\bottomrule')
    lines.append('\\end{tabular}')
    lines.append('\\end{table*}')

    latex = '\n'.join(lines)

    # Save
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, 'table_main.tex'), 'w') as f:
        f.write(latex)

    # Also save markdown version
    md = _latex_to_markdown(results, metrics, best_proto)
    with open(os.path.join(output_dir, 'table_main.md'), 'w') as f:
        f.write(md)

    # CSV version
    csv = _to_csv(results, metrics)
    with open(os.path.join(output_dir, 'table_main.csv'), 'w') as f:
        f.write(csv)

    return latex


def _latex_to_markdown(results: dict, metrics: list,
                       best_proto: dict) -> str:
    """Convert to Markdown table."""
    lines = []
    header = '| Protocol |'
    sep = '|----------|'
    for _, label, _, _ in metrics:
        header += f' {label} |'
        sep += '--------:|'
    lines.append(header)
    lines.append(sep)

    for proto in results:
        row = f'| {proto} |'
        for key, _, decimals, _ in metrics:
            m = results[proto].get(key, {})
            mean = m.get('mean', np.nan)
            ci = m.get('ci95', 0)
            is_best = (best_proto.get(key) == proto)
            if np.isnan(mean):
                cell = 'N/A'
            else:
                cell = f'{mean:.{decimals}f}±{ci:.{decimals}f}'
                if is_best:
                    cell = f'**{cell}**'
            row += f' {cell} |'
        lines.append(row)

    return '\n'.join(lines)


def _to_csv(results: dict, metrics: list) -> str:
    """Convert to CSV."""
    lines = []
    header = 'Protocol,' + ','.join(f'{label}_mean,{label}_ci95'
                                    for _, label, _, _ in metrics)
    lines.append(header)

    for proto in results:
        row = proto
        for key, _, decimals, _ in metrics:
            m = results[proto].get(key, {})
            mean = m.get('mean', np.nan)
            ci = m.get('ci95', 0)
            row += f',{mean:.{decimals}f},{ci:.{decimals}f}'
        lines.append(row)

    return '\n'.join(lines)


def generate_scalability_table(results_by_N: dict,
                               output_dir: str = 'results') -> str:
    """Generate scalability comparison table."""
    lines = ['\\begin{table}[!t]', '\\centering',
             '\\caption{Scalability analysis: CALASH half-death round '
             'vs baselines across network sizes.}',
             '\\label{tab:scalability}',
             '\\begin{tabular}{lrrrr}', '\\toprule',
             'Protocol & N=100 & N=200 & N=500 & N=1000 \\\\',
             '\\midrule']

    for proto in ['LEACH', 'EE-LEACH', 'ABC-ACO', 'EERP',
                  'Q-Routing', 'CALASH']:
        row = proto.replace('-', '\\text{-}')
        for N in [100, 200, 500, 1000]:
            data = results_by_N.get(N, {}).get(proto, {})
            agg = data.get('aggregated', data)
            m = agg.get('half_death_round', {})
            mean = m.get('mean', np.nan)
            ci = m.get('ci95', 0)
            if np.isnan(mean):
                row += ' & N/A'
            else:
                row += f' & {mean:.0f}$\\pm${ci:.0f}'
        row += ' \\\\'
        lines.append(row)

    lines += ['\\bottomrule', '\\end{tabular}', '\\end{table}']
    latex = '\n'.join(lines)

    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, 'table_scalability.tex'), 'w') as f:
        f.write(latex)

    return latex
