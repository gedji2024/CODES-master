import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend: save to file, no blocking plt.show()
import matplotlib.pyplot as plt
import os
import sys
import glob
import gym_examples
import re
import argparse

# Ensure epymarl/src is on sys.path for shared utilities
_src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)
from utils.paths import RESULTS_DATA_DIR

# Set default font sizes for various elements
plt.rcParams.update({
    'font.size': 18,
    'axes.titlesize': 20,
    'axes.labelsize': 18,
    'xtick.labelsize': 16,
    'ytick.labelsize': 16,
    'legend.fontsize': 18,
    'figure.titlesize': 22
})

# Parse CLI arguments for scenario identification
parser = argparse.ArgumentParser(description="Display and save WSN routing results")
parser.add_argument("--n-sensors", type=int, default=70, help="Number of sensors in scenario")
parser.add_argument("--coverage-radius", type=float, default=35.0, help="Coverage radius in meters")
parser.add_argument("--output-dir", type=str, default=None,
                    help="Directory to save plots (default: <project>/Results_Graphics)")
parser.add_argument("--seeds", type=str, default="",
                    help="Comma-separated seed list for filename traceability")
args = parser.parse_args()

# Build scenario tag for filenames (includes seeds for traceability)
scenario_tag = f"n{args.n_sensors}_r{args.coverage_radius:.0f}"
if args.seeds:
    _seeds_suffix = "seeds_" + args.seeds.replace(",", "_")
    scenario_tag = f"{scenario_tag}_{_seeds_suffix}"

# Determine output directory (absolute path to avoid confusion)
if args.output_dir:
    output_dir = os.path.abspath(args.output_dir)
else:
    # Default: <project_root>/Results_Graphics
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Results_Graphics"))
os.makedirs(output_dir, exist_ok=True)

# Get the version number of gym_examples
version = gym_examples.__version__

# All algorithms to include
ALGORITHMS = ["QMIX", "QTRAN"]  # , "QPSOFL", "GAPF"]
ALGO_COLORS = {"QMIX": "#1f77b4", "QTRAN": "#ff7f0e"}  # , "QPSOFL": "#2ca02c", "GAPF": "#9467bd"}

# Collect all .npy files
all_npy = glob.glob(os.path.join(RESULTS_DATA_DIR, f'*_{version}.npy'))
all_npy += glob.glob(os.path.join(RESULTS_DATA_DIR, f'*_test_{version}.npy'))
all_npy = list(set(all_npy))

algo_pattern = "|".join(ALGORITHMS)


def parse_npy_file(filepath):
    """Extract (metric, algo, seed_or_None, phase) from a filepath.

    phase is 'test' or 'train'.
    """
    basename = os.path.splitext(os.path.basename(filepath))[0]

    # Try seed+test: <metric>_<ALGO>_seed<N>_test_<version>
    m = re.match(
        rf"(.+?)_({algo_pattern})_seed(\d+)_test_{re.escape(version)}$",
        basename
    )
    if m:
        return m.group(1), m.group(2), int(m.group(3)), "test"

    # Try seed+train: <metric>_<ALGO>_seed<N>_<version>  (no _test_)
    m = re.match(
        rf"(.+?)_({algo_pattern})_seed(\d+)_{re.escape(version)}$",
        basename
    )
    if m:
        return m.group(1), m.group(2), int(m.group(3)), "train"

    # Try noseed+test: <metric>_<ALGO>_test_<version>
    m = re.match(
        rf"(.+?)_({algo_pattern})_test_{re.escape(version)}$",
        basename
    )
    if m:
        return m.group(1), m.group(2), None, "test"

    # Try noseed+train: <metric>_<ALGO>_<version>
    m = re.match(
        rf"(.+?)_({algo_pattern})_{re.escape(version)}$",
        basename
    )
    if m:
        return m.group(1), m.group(2), None, "train"

    return None, None, None, None


# Organize files: {phase: {metric: {algo: {seed: filepath}}}}
# For noseed files, seed key is None
data = {"train": {}, "test": {}}
for f in all_npy:
    metric, algo, seed, phase = parse_npy_file(f)
    if metric is None:
        continue
    data[phase].setdefault(metric, {}).setdefault(algo, {})[seed] = f

# Collect all metrics per phase
train_metrics = sorted(data["train"].keys())
test_metrics = sorted(data["test"].keys())


def plot_metric(phase_data, metric_name, phase_label, scenario_tag, output_dir):
    """Plot a single metric for all algorithms. Returns save_path or None."""
    fig, ax = plt.subplots(figsize=(12, 7))
    has_data = False

    for algo in ALGORITHMS:
        if algo not in phase_data.get(metric_name, {}):
            continue
        color = ALGO_COLORS[algo]
        seed_files = phase_data[metric_name][algo]

        # Separate real seeds from noseed (key=None)
        real_seeds = {k: v for k, v in seed_files.items() if k is not None}
        noseed_file = seed_files.get(None)

        if len(real_seeds) >= 2:
            # Multi-seed: mean ± std with shaded band
            arrays = []
            for seed_val in sorted(real_seeds.keys()):
                arr = np.load(real_seeds[seed_val])
                if algo in ("QMIX", "QTRAN") and len(arr) > 2:
                    arr = arr[2:]
                arrays.append(arr)
            min_len = min(len(a) for a in arrays)
            stacked = np.stack([a[:min_len] for a in arrays])
            mean = stacked.mean(axis=0)
            std = stacked.std(axis=0)
            x = np.arange(len(mean))
            ax.plot(x, mean, label=f"{algo} (n={len(arrays)} seeds)", color=color)
            # ax.fill_between(x, mean - std, mean + std, alpha=0.2, color=color)
            has_data = True
        elif len(real_seeds) == 1:
            # Single seed
            seed_val = list(real_seeds.keys())[0]
            arr = np.load(real_seeds[seed_val])
            if algo in ("QMIX", "QTRAN") and len(arr) > 2:
                arr = arr[2:]
            ax.plot(arr, label=algo, color=color)
            has_data = True
        elif noseed_file:
            # Noseed fallback
            arr = np.load(noseed_file)
            if algo in ("QMIX", "QTRAN") and len(arr) > 2:
                arr = arr[2:]
            ax.plot(arr, label=algo, color=color)
            has_data = True

    if not has_data:
        plt.close(fig)
        return None

    pretty_metric = metric_name.replace('_', ' ').title()
    ax.set_title(f"{pretty_metric} ({phase_label})")
    ax.set_xlabel('Episodes')
    ax.set_ylabel(pretty_metric)
    ax.legend()
    fig.tight_layout()

    save_name = f"{metric_name}_{phase_label.lower()}_{scenario_tag}.png"
    save_path = os.path.join(output_dir, save_name)
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return save_path


# Generate training figures
saved_files = []
for metric_name in train_metrics:
    path = plot_metric(data["train"], metric_name, "Train", scenario_tag, output_dir)
    if path:
        saved_files.append(path)

# Generate test figures
for metric_name in test_metrics:
    path = plot_metric(data["test"], metric_name, "Test", scenario_tag, output_dir)
    if path:
        saved_files.append(path)

print(f"\nSaved {len(saved_files)} plots to: {output_dir}")
for f in saved_files:
    print(f"  {os.path.basename(f)}")
