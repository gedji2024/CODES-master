import argparse
import glob
import os
import sys
from typing import Dict, Optional, Tuple


# -------------------- Common helpers --------------------

def bytes_to_kb(nbytes: int, base: int = 1024) -> float:
    return nbytes / float(base)


def find_latest_timestep_dir(checkpoint_path: str) -> str:
    """For EPyMARL runs: return dir containing agent.th (latest timestep if root passed)."""
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
    latest_dir = os.path.join(checkpoint_path, str(max(timesteps)))
    if not os.path.isfile(os.path.join(latest_dir, "agent.th")):
        raise FileNotFoundError(f"agent.th not found in: {latest_dir}")
    return latest_dir


def count_state_dict_params_from_file(path: str) -> int:
    import torch
    sd = torch.load(path, map_location="cpu")
    if not isinstance(sd, dict):
        raise ValueError(f"Not a state_dict (dict): {path}")
    total = 0
    for _, v in sd.items():
        if hasattr(v, "numel"):
            total += int(v.numel())
    return total


def list_dir_file_sizes_bytes(dir_path: str) -> Dict[str, int]:
    sizes: Dict[str, int] = {}
    for fname in os.listdir(dir_path):
        fpath = os.path.join(dir_path, fname)
        if os.path.isfile(fpath):
            sizes[fname] = os.path.getsize(fpath)
    return sizes


# -------------------- TSMixer helpers --------------------

def find_darts_ckpt_by_model_name(model_name: str, models_root: str) -> Optional[str]:
    pattern = os.path.join(models_root, model_name, "**", "checkpoints", "*.ckpt")
    candidates = glob.glob(pattern, recursive=True)
    if not candidates:
        return None
    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return candidates[0]


def count_tsmixer_params(model_name: Optional[str], ckpt_path: Optional[str], models_root: str) -> Tuple[int, str]:
    """Return (param_count, source)
    - Try Darts load_from_checkpoint(model_name) to get trainable params
    - Else, fallback to torch-only count from located ckpt (.ckpt state_dict)
    """
    # Try Darts route first if model_name provided
    if model_name:
        try:
            from darts.models import TSMixerModel  # type: ignore
            model = TSMixerModel.load_from_checkpoint(model_name)
            total = sum(p.numel() for p in model.model.parameters() if p.requires_grad)
            return int(total), "darts"
        except Exception:
            pass
        # Try locating the ckpt under models_root as fallback
        ckpt_auto = find_darts_ckpt_by_model_name(model_name, models_root)
        if ckpt_auto:
            total = count_tsmixer_params_from_ckpt(ckpt_auto)
            return total, ckpt_auto

    # If a direct ckpt path is given, use it
    if ckpt_path and os.path.isfile(ckpt_path):
        total = count_tsmixer_params_from_ckpt(ckpt_path)
        return total, ckpt_path

    raise FileNotFoundError("Could not locate/load TSMixer checkpoint. Provide --model_name or --ckpt_path.")


def count_tsmixer_params_from_ckpt(ckpt_path: str) -> int:
    import torch
    ckpt = torch.load(ckpt_path, map_location="cpu")
    state_dict = ckpt.get("state_dict") if isinstance(ckpt, dict) else None
    if state_dict is None:
        state_dict = ckpt if isinstance(ckpt, dict) else {}
    total = 0
    for _, v in state_dict.items():
        try:
            total += int(v.numel())
        except Exception:
            pass
    return total


def size_of_file(path: str) -> int:
    return os.path.getsize(path)


# -------------------- Main CLI --------------------

def main():
    parser = argparse.ArgumentParser(description="Report model stats (params + sizes) for TSMixer, QMIX, QTRAN.")
    sub = parser.add_subparsers(dest="mode", required=True)

    # TSMixer
    p_tsm = sub.add_parser("tsmixer", help="TSMixerModel stats")
    p_tsm.add_argument("--model_name", help="Darts model_name used when saving (preferred)")
    p_tsm.add_argument("--ckpt_path", help="Direct path to a .ckpt file (fallback)")
    p_tsm.add_argument("--models_root", default=os.path.join(os.getcwd(), ".darts", "models"),
                       help="Root of Darts models (default: ./.darts/models)")
    p_tsm.add_argument("--base", type=int, default=1024, choices=[1000, 1024], help="KB base (1000 or 1024)")

    # EPyMARL (QMIX/QTRAN)
    p_marl = sub.add_parser("epymarl", help="QMIX/QTRAN stats")
    p_marl.add_argument("--checkpoint_path", required=True, help="Run root or specific timestep dir containing agent.th")
    p_marl.add_argument("--base", type=int, default=1024, choices=[1000, 1024], help="KB base (1000 or 1024)")

    args = parser.parse_args()

    if args.mode == "tsmixer":
        # Count params
        total_params, src = count_tsmixer_params(args.model_name, args.ckpt_path, args.models_root)
        # Determine ckpt path for size reporting
        ckpt_path = None
        if src == "darts":
            # Find most recent ckpt to report size
            ckpt_path = find_darts_ckpt_by_model_name(args.model_name, args.models_root)
        else:
            ckpt_path = src  # src holds the path string in fallback
        size_kb = 0.0
        if ckpt_path and os.path.isfile(ckpt_path):
            size_kb = bytes_to_kb(size_of_file(ckpt_path), args.base)
        print("=== TSMixerModel ===")
        if args.model_name:
            print("model_name:", args.model_name)
        if ckpt_path:
            print("checkpoint:", ckpt_path)
        print("trainable_params:", total_params)
        print(f"checkpoint_size: {size_kb:.2f} KB (base {args.base})")
        return

    if args.mode == "epymarl":
        ts_dir = find_latest_timestep_dir(args.checkpoint_path)
        sizes = list_dir_file_sizes_bytes(ts_dir)
        # agent
        agent_path = os.path.join(ts_dir, "agent.th")
        agent_params = count_state_dict_params_from_file(agent_path)
        agent_kb = bytes_to_kb(sizes.get("agent.th", 0), args.base)
        # mixer (optional)
        mixer_params = 0
        mixer_kb = 0.0
        mixer_path = os.path.join(ts_dir, "mixer.th")
        if os.path.isfile(mixer_path):
            mixer_params = count_state_dict_params_from_file(mixer_path)
            mixer_kb = bytes_to_kb(sizes.get("mixer.th", 0), args.base)
        total_params = agent_params + mixer_params
        total_model_kb = agent_kb + mixer_kb
        total_ckpt_kb = bytes_to_kb(sum(sizes.values()), args.base)
        print("=== EPyMARL (QMIX/QTRAN) ===")
        print("checkpoint_dir:", ts_dir)
        print("agent_params:", agent_params)
        print("mixer_params:", mixer_params)
        print("total_params:", total_params)
        print(f"agent.th: {agent_kb:.2f} KB | mixer.th: {mixer_kb:.2f} KB | model: {total_model_kb:.2f} KB | checkpoint_total: {total_ckpt_kb:.2f} KB (base {args.base})")
        return

    print("Unknown mode")
    sys.exit(1)


if __name__ == "__main__":
    main()
