import argparse
import os
import sys
from typing import Tuple

import torch as th


def find_latest_timestep_dir(checkpoint_path: str) -> str:
    """Return the path to the latest numeric timestep subdirectory.

    If checkpoint_path already points to a directory containing agent.th,
    it will be returned unchanged. Otherwise, it will search numeric
    subdirectories and return the one with the highest number.
    """
    agent_file = os.path.join(checkpoint_path, "agent.th")
    if os.path.isfile(agent_file):
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
    agent_file_latest = os.path.join(latest_dir, "agent.th")
    if not os.path.isfile(agent_file_latest):
        raise FileNotFoundError(
            f"agent.th not found in latest checkpoint dir: {latest_dir}"
        )
    return latest_dir


def count_state_dict_params(state_dict_path: str) -> int:
    """Sum numel() across all tensors in a saved PyTorch state_dict file."""
    sd = th.load(state_dict_path, map_location="cpu")
    if not isinstance(sd, dict):
        raise ValueError(f"File does not contain a state_dict (dict): {state_dict_path}")
    total = 0
    for k, v in sd.items():
        if hasattr(v, "numel"):
            total += int(v.numel())
        else:
            # Some entries could be non-tensors (rare). Ignore.
            pass
    return total


def count_checkpoint_params(dir_path: str) -> Tuple[int, int, int]:
    """Return (agent_params, mixer_params, total_params) from a checkpoint dir.

    Expects files agent.th and optionally mixer.th inside dir_path.
    """
    agent_path = os.path.join(dir_path, "agent.th")
    if not os.path.isfile(agent_path):
        raise FileNotFoundError(f"agent.th not found in: {dir_path}")
    agent_params = count_state_dict_params(agent_path)

    mixer_path = os.path.join(dir_path, "mixer.th")
    mixer_params = count_state_dict_params(mixer_path) if os.path.isfile(mixer_path) else 0

    return agent_params, mixer_params, agent_params + mixer_params


def main():
    parser = argparse.ArgumentParser(description="Count trainable parameters from an EPyMARL QMIX/QTRAN checkpoint.")
    parser.add_argument(
        "--checkpoint_path",
        required=True,
        help=(
            "Path to the checkpoint root (results/models/<run>/) or a specific "
            "timestep directory containing agent.th (…/<run>/<timestep>/)."
        ),
    )
    args = parser.parse_args()

    try:
        ts_dir = find_latest_timestep_dir(args.checkpoint_path)
        agent_params, mixer_params, total_params = count_checkpoint_params(ts_dir)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    print("Checkpoint directory:", ts_dir)
    print("agent.th params:", agent_params)
    if mixer_params > 0:
        print("mixer.th params:", mixer_params)
    else:
        print("mixer.th params: 0 (no mixer.th found)")
    print("TOTAL trainable params:", total_params)


if __name__ == "__main__":
    main()
