import os
import argparse
import numpy as np

DEFAULT_ALGOS = ["QMIX", "QTRAN", "QPSOFL", "ENSEMBLE_MAX", "TSMixer", "HYBRID", "GAPF"]
DEFAULT_METRICS = [
    # Effectiveness
    "packet_delivery_ratio",
    "network_throughput",
    "average_latency",           # NaN-aware expected
    "total_consumption_energy",
    "std_remaining_energy",
    "energy_efficiency",
    # Feasibility
    "wall_step_time_ms_mean",
    "wall_step_time_ms_p95",
    "wall_step_time_ms_p99",
    "wall_episode_time_ms",
    "peak_memory_mb",
]


def nanstats(arr):
    arr = np.asarray(arr)
    return float(np.nanmean(arr)), float(np.nanstd(arr))


def stats(arr):
    arr = np.asarray(arr)
    return float(arr.mean()), float(arr.std())


def load_metric(base_dir, metric, algo, version, test=False):
    import glob
    suffix = f"_{algo}_{version}.npy"
    if test:
        suffix = f"_{algo}_test_{version}.npy"
    path = os.path.join(base_dir, f"{metric}{suffix}")
    if os.path.exists(path):
        try:
            return np.load(path)
        except Exception as e:
            print(f"Warning: failed to load {path}: {e}")
            return None
    # Fall back to seed-tagged files (e.g. _ALGO_seed42_test_version.npy)
    # Load ALL seeds and concatenate them for cross-seed aggregation.
    if test:
        pattern = os.path.join(base_dir, f"{metric}_{algo}_seed*_test_{version}.npy")
    else:
        pattern = os.path.join(base_dir, f"{metric}_{algo}_seed*_{version}.npy")
    matches = sorted(glob.glob(pattern))
    if not matches:
        return None
    arrays = []
    for m in matches:
        try:
            arrays.append(np.load(m))
        except Exception as e:
            print(f"Warning: failed to load {m}: {e}")
    if not arrays:
        return None
    return np.concatenate(arrays)


def _slice_last_n(arr, last_n):
    if last_n is None:
        return arr
    try:
        last_n = int(last_n)
    except Exception:
        return arr
    if last_n <= 0:
        return arr
    a = np.asarray(arr)
    if a.size == 0:
        return a
    # Assume first dimension is the sample axis (episodes).
    if a.shape[0] <= last_n:
        return a
    return a[-last_n:]


def _count_seed_files(base_dir, metric, algo, version, test=False):
    """Count how many seed files exist for a given metric/algo combination."""
    import glob
    if test:
        pattern = os.path.join(base_dir, f"{metric}_{algo}_seed*_test_{version}.npy")
    else:
        pattern = os.path.join(base_dir, f"{metric}_{algo}_seed*_{version}.npy")
    return len(glob.glob(pattern))


def summarize(base_dir, algos, version, test=False, last_n=None):
    results = {}
    for algo in algos:
        results[algo] = {}
        for metric in DEFAULT_METRICS:
            arr = load_metric(base_dir, metric, algo, version, test=test)
            if arr is None:
                results[algo][metric] = None
                continue
            arr = _slice_last_n(arr, last_n)
            if metric == "average_latency":
                m, s = nanstats(arr)
            else:
                m, s = stats(arr)
            results[algo][metric] = (m, s)

    # Console summary (human-readable)
    print("\n=== Summary ===")
    print(f"Base dir: {base_dir}")
    print(f"Version:  {version}")
    print(f"Split:    {'test' if test else 'train'}\n")
    for algo in algos:
        # Show seed count from first available metric
        n_seeds = 0
        for metric in DEFAULT_METRICS:
            n = _count_seed_files(base_dir, metric, algo, version, test=test)
            if n > 0:
                n_seeds = n
                break
        seed_info = f" ({n_seeds} seeds aggregated)" if n_seeds > 1 else ""
        print(f"--- {algo}{seed_info} ---")
        for metric in DEFAULT_METRICS:
            val = results[algo].get(metric)
            if val is None:
                print(f"{metric}: (missing)")
            else:
                m, s = val
                print(f"{metric}: mean={m:.4f}, std={s:.4f}")
        print()

    return results


def format_mean_std(val):
    if val is None:
        return "—"
    m, s = val
    return f"{m:.4f} ± {s:.4f}"


def emit_table(results, algos, fmt="md"):
    metrics = DEFAULT_METRICS
    if fmt == "md":
        # Markdown table
        header = "| metric | " + " | ".join(algos) + " |"
        sep = "|" + "---|" * (len(algos) + 1)
        lines = [header, sep]
        for metric in metrics:
            row = [metric]
            for algo in algos:
                row.append(format_mean_std(results.get(algo, {}).get(metric)))
            lines.append("| " + " | ".join(row) + " |")
        return "\n".join(lines)
    elif fmt == "csv":
        lines = ["metric,algo,mean,std"]
        for metric in metrics:
            for algo in algos:
                val = results.get(algo, {}).get(metric)
                if val is None:
                    continue
                m, s = val
                lines.append(f"{metric},{algo},{m:.6f},{s:.6f}")
        return "\n".join(lines)
    elif fmt == "latex":
        # Simple LaTeX tabular
        cols = "l" + "c" * len(algos)
        lines = [f"\\begin{{tabular}}{{{cols}}}", "\\toprule"]
        header = "metric & " + " & ".join(algos) + " \\\\"
        lines.append(header)
        lines.append("\\midrule")
        for metric in metrics:
            cells = [metric]
            for algo in algos:
                cells.append(format_mean_std(results.get(algo, {}).get(metric)))
            lines.append(" {} \\".format(" & ".join(cells)))
        lines.append("\\bottomrule\n\\end{tabular}")
        return "\n".join(lines)
    else:
        raise ValueError("Unsupported format (use md|csv|latex)")


def emit_p95_budget_table(results, algos, budgets_ms, fmt="md", percentile_metric="wall_step_time_ms_p95"):
    # Prepare rows: algo, p95, PASS@B1, PASS@B2, ...
    header_cols = ["algo", percentile_metric] + [f"PASS@{int(b)}ms" for b in budgets_ms]
    # Gather data
    rows = []
    for algo in algos:
        val = results.get(algo, {}).get(percentile_metric)
        if val is None:
            p95 = None
        else:
            p95, _ = val
        passes = []
        for b in budgets_ms:
            if p95 is None:
                passes.append("—")
            else:
                passes.append("PASS" if p95 < b else "FAIL")
        rows.append((algo, p95, passes))

    if fmt == "md":
        header = "| " + " | ".join(header_cols) + " |"
        sep = "|" + "---|" * len(header_cols)
        lines = [header, sep]
        for algo, p95, passes in rows:
            p95_str = "—" if p95 is None else f"{p95:.4f}"
            line = "| " + " | ".join([algo, p95_str] + passes) + " |"
            lines.append(line)
        return "\n".join(lines)
    elif fmt == "csv":
        cols = ["algo", "p95_ms"] + [f"pass_at_{int(b)}ms" for b in budgets_ms]
        lines = [",".join(cols)]
        for algo, p95, passes in rows:
            p95_str = "" if p95 is None else f"{p95:.6f}"
            lines.append(
                ",".join([algo, p95_str] + passes)
            )
        return "\n".join(lines)
    elif fmt == "latex":
        cols = "l" + "c" * (2 + len(budgets_ms) - 1)  # l + c.. for remaining
        lines = [f"\\begin{{tabular}}{{{cols}}}", "\\toprule"]
        header = "algo & p95 (ms) & " + " & ".join([f"PASS@{int(b)}ms" for b in budgets_ms]) + " \\\\"
        lines.append(header)
        lines.append("\\midrule")
        for algo, p95, passes in rows:
            p95_str = "—" if p95 is None else f"{p95:.4f}"
            cells = [algo, p95_str] + passes
            lines.append(" {} \\".format(" & ".join(cells)))
        lines.append("\\bottomrule\n\\end{tabular}")
        return "\n".join(lines)
    else:
        raise ValueError("Unsupported format (use md|csv|latex)")


def _cmp_pass(value: float, op: str, threshold: float) -> bool:
    if value is None:
        return False
    if op in ("<", "lt"):
        return value < threshold
    if op in ("<=", "le"):
        return value <= threshold
    if op in (">", "gt"):
        return value > threshold
    if op in (">=", "ge"):
        return value >= threshold
    raise ValueError(f"Unsupported operator: {op}")


def emit_feasibility_pass_table(results, algos, constraints, fmt="md"):
    """
    constraints: list of tuples (metric_name, op, threshold, label)
      - metric_name must exist in DEFAULT_METRICS (e.g., wall_step_time_ms_p95, peak_memory_mb, model_size_mb, ...)
      - op in {<,<=,>,>=}
      - threshold numeric
      - label optional display name; if None, auto format as metric op threshold
    """
    # Build header
    labels = []
    for metric, op, thr, label in constraints:
        if not label:
            label = f"{metric} {op} {thr}"
        labels.append(label)

    if fmt == "md":
        header = "| algo | " + " | ".join(labels) + " |"
        sep = "|" + "---|" * (len(labels) + 1)
        lines = [header, sep]
        for algo in algos:
            cells = [algo]
            for metric, op, thr, _ in constraints:
                val = results.get(algo, {}).get(metric)
                v = None if val is None else val[0]
                if v is None:
                    cells.append("—")
                else:
                    cells.append("PASS" if _cmp_pass(v, op, thr) else "FAIL")
            lines.append("| " + " | ".join(cells) + " |")
        return "\n".join(lines)
    elif fmt == "csv":
        cols = ["algo"] + labels
        lines = [",".join(cols)]
        for algo in algos:
            row = [algo]
            for metric, op, thr, _ in constraints:
                val = results.get(algo, {}).get(metric)
                v = None if val is None else val[0]
                row.append("" if v is None else ("PASS" if _cmp_pass(v, op, thr) else "FAIL"))
            lines.append(",".join(row))
        return "\n".join(lines)
    elif fmt == "latex":
        cols = "l" + "c" * len(labels)
        lines = [f"\\begin{{tabular}}{{{cols}}}", "\\toprule"]
        lines.append("algo & " + " & ".join(labels) + " \\")
        lines.append("\\midrule")
        for algo in algos:
            cells = [algo]
            for metric, op, thr, _ in constraints:
                val = results.get(algo, {}).get(metric)
                v = None if val is None else val[0]
                cells.append("" if v is None else ("PASS" if _cmp_pass(v, op, thr) else "FAIL"))
            lines.append(" {} \\".format(" & ".join(cells)))
        lines.append("\\bottomrule\n\\end{tabular}")
        return "\n".join(lines)
    else:
        raise ValueError("Unsupported format (use md|csv|latex)")


def main():
    p = argparse.ArgumentParser()
    # Default to epymarl/results/data/ (canonical location for all .npy outputs)
    _default_data_dir = os.path.join(os.path.dirname(__file__), '..', 'epymarl', 'results', 'data')
    p.add_argument("--base-dir", default=os.path.abspath(_default_data_dir))
    p.add_argument("--version", default=None, help="gym_examples.__version__ (if omitted, try to detect)")
    p.add_argument("--algos", nargs="*", default=DEFAULT_ALGOS)
    p.add_argument("--test", action="store_true", help="Summarize test_* npys instead of training")
    p.add_argument("--last-n", type=int, default=None, help="If set, summarize only the last N samples (episodes) from each .npy (useful to align with Hybrid test_data_length)")
    p.add_argument("--format", choices=["md", "csv", "latex"], default=None, help="Optional table output format")
    p.add_argument("--output-file", default=None, help="Optional path to write the table")
    p.add_argument("--budget-ms", type=float, nargs="*", default=None, help="Optional budgets in ms to evaluate PASS/FAIL vs wall_step_time_ms_p95 (e.g., --budget-ms 10 50)")
    p.add_argument("--p95-table", action="store_true", help="Emit a specialized p95 vs budgets table instead of the full metrics table")
    p.add_argument("--use-p99", action="store_true", help="When used with --p95-table/--budget-ms, evaluate budgets against wall_step_time_ms_p99 instead of p95")
    # General feasibility constraints (repeatable)
    p.add_argument("--feas", action="append", default=None,
                   help="Repeatable constraint of form metric:op:value, e.g., peak_memory_mb:<:1024 or model_size_mb:<=:200")
    p.add_argument("--feas-table", action="store_true", help="Emit a generalized feasibility PASS/FAIL table for constraints passed via --feas")
    args = p.parse_args()

    version = args.version
    if version is None:
        # Best-effort detection
        try:
            import gym_examples
            version = gym_examples.__version__
        except Exception:
            version = "unknown"

    results = summarize(args.base_dir, args.algos, version, test=args.test, last_n=args.last_n)

    # If budgets provided, print PASS/FAIL lines for console
    if args.budget_ms:
        budgets = list(args.budget_ms)
        pct_metric = "wall_step_time_ms_p99" if args.use_p99 else "wall_step_time_ms_p95"
        print("p95 PASS/FAIL vs budgets:")
        for algo in args.algos:
            val = results.get(algo, {}).get(pct_metric)
            p95 = None if val is None else val[0]
            if p95 is None:
                status_line = ", ".join([f"@{int(b)}ms: —" for b in budgets])
            else:
                status_line = ", ".join([f"@{int(b)}ms: {'PASS' if p95 < b else 'FAIL'}" for b in budgets])
            print(f"  {algo}: p95={p95 if p95 is not None else '—'} ms | {status_line}")

    if args.format:
        if args.p95_table and args.budget_ms:
            pct_metric = "wall_step_time_ms_p99" if args.use_p99 else "wall_step_time_ms_p95"
            table = emit_p95_budget_table(results, args.algos, list(args.budget_ms), fmt=args.format, percentile_metric=pct_metric)
        elif args.feas_table and args.feas:
            constraints = []
            for item in args.feas:
                try:
                    metric, op, val = item.split(":", 2)
                    constraints.append((metric, op, float(val), None))
                except Exception:
                    raise ValueError(f"Invalid --feas '{item}', expected metric:op:value")
            table = emit_feasibility_pass_table(results, args.algos, constraints, fmt=args.format)
        else:
            table = emit_table(results, args.algos, fmt=args.format)
        if args.output_file:
            out_dir = os.path.dirname(args.output_file)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            with open(args.output_file, "w", encoding="utf-8") as f:
                f.write(table)
            print(f"\nWrote table to {args.output_file}")
        else:
            print("\n" + table)


if __name__ == "__main__":
    main()
