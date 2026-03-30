import argparse
import os
import sys
from typing import Dict


def find_latest_timestep_dir(checkpoint_path: str) -> str:
    """Return the path to the latest numeric timestep subdirectory.

    If checkpoint_path already contains agent.th, it's returned as-is.
    Otherwise, search numeric subdirectories and return the highest.
    """
    if os.path.isfile(os.path.join(checkpoint_path, "agent.th")):
        return checkpoint_path

    if not os.path.isdir(checkpoint_path):
        raise FileNotFoundError(f"Checkpoint path not found: {checkpoint_path}")

    timesteps = []
    for name in os.listdir(checkpoint_path):
        full = os.path.join(checkpoint_path, name)
        if os.path.isdir(full) and name.isdigit():
            timesteps.append(int(name))

    if not timesteps:
        raise FileNotFoundError(
            f"No numeric timestep subdirectories found under: {checkpoint_path}"
        )

    latest = str(max(timesteps))
    latest_dir = os.path.join(checkpoint_path, latest)
    if not os.path.isfile(os.path.join(latest_dir, "agent.th")):
        raise FileNotFoundError(f"agent.th not found in latest checkpoint dir: {latest_dir}")
    return latest_dir


def bytes_to_kb(bytes_value: int, base: int = 1024) -> float:
    """Convert bytes to kilobytes (default base 1024)."""
    return bytes_value / float(base)


def list_sizes(dir_path: str) -> Dict[str, int]:
    """Return a dict of file sizes in bytes for known checkpoint files."""
    known_files = [
        "agent.th",  # always expected
        "mixer.th",  # QMIX/QTRAN mixer; may be absent for some algs
        "opt.th",    # optimizer state (not model params but useful for total)
    ]
    sizes: Dict[str, int] = {}
    for fname in known_files:
        fpath = os.path.join(dir_path, fname)
        if os.path.isfile(fpath):
            sizes[fname] = os.path.getsize(fpath)
    # Also include any other files in the checkpoint folder for an accurate total
    total_bytes = 0
    for name in os.listdir(dir_path):
        fpath = os.path.join(dir_path, name)
        if os.path.isfile(fpath):
            total_bytes += os.path.getsize(fpath)
    sizes["__TOTAL_CHECKPOINT_BYTES__"] = total_bytes
    return sizes


def main():
    parser = argparse.ArgumentParser(description="Report model/checkpoint file sizes (KB) for an EPyMARL run.")
    parser.add_argument(
        "--checkpoint_path",
        required=True,
        help=(
            "Path to the checkpoint root (results/models/<run>/) or a specific "
            "timestep directory (…/<run>/<timestep>/)."
        ),
    )
    parser.add_argument(
        "--base",
        type=int,
        default=1024,
        choices=[1000, 1024],
        help="Unit base for KB conversion: 1024 (KiB) or 1000 (kB). Default 1024.",
    )
    args = parser.parse_args()

    try:
        ts_dir = find_latest_timestep_dir(args.checkpoint_path)
        sizes = list_sizes(ts_dir)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Pretty print
    print(f"Checkpoint directory: {ts_dir}")
    agent_kb = bytes_to_kb(sizes.get("agent.th", 0), args.base)
    mixer_kb = bytes_to_kb(sizes.get("mixer.th", 0), args.base)
    opt_kb = bytes_to_kb(sizes.get("opt.th", 0), args.base)
    total_model_kb = agent_kb + mixer_kb
    total_checkpoint_kb = bytes_to_kb(sizes.get("__TOTAL_CHECKPOINT_BYTES__", 0), args.base)

    print(f"agent.th: {agent_kb:.2f} KB")
    if mixer_kb:
        print(f"mixer.th: {mixer_kb:.2f} KB")
    else:
        print("mixer.th: 0.00 KB (not found)")
    if opt_kb:
        print(f"opt.th: {opt_kb:.2f} KB")
    print(f"MODEL size (agent + mixer): {total_model_kb:.2f} KB")
    print(f"TOTAL checkpoint folder size: {total_checkpoint_kb:.2f} KB")


if __name__ == "__main__":
    main()
