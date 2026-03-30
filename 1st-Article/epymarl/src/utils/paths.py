"""Canonical save paths for the project.

Every script that reads/writes .npy result files or model checkpoints should
import from here instead of computing paths ad-hoc.  This guarantees a single
source of truth: ``epymarl/results/data/`` and ``epymarl/results/models/``.

Usage::

    from utils.paths import RESULTS_DATA_DIR, RESULTS_MODELS_DIR
"""

import os

# __file__ is at  epymarl/src/utils/paths.py
# Go up two levels to reach  epymarl/
_EPYMARL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))

RESULTS_DATA_DIR = os.path.join(_EPYMARL_ROOT, "results", "data")
RESULTS_MODELS_DIR = os.path.join(_EPYMARL_ROOT, "results", "models")

# Ensure directories exist on import
os.makedirs(RESULTS_DATA_DIR, exist_ok=True)
os.makedirs(RESULTS_MODELS_DIR, exist_ok=True)
