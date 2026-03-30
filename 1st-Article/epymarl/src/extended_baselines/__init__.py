"""Extended baselines (focused).

Currently exposes only the QPSOFL optimization baseline and the evaluation
pipeline entrypoint. Historical exploratory baselines (metaheuristics,
clustering, etc.) were removed to keep scope tight for the core comparison:
QPSOFL vs QMIX / QTRAN / TSMixer hybrid.
"""

from .qpsofl_baseline import QPSOFLBaseline, get_qpsofl_baseline  # noqa: F401
from .evaluation_pipeline import main as qpsofl_eval_main  # noqa: F401

__all__ = ["QPSOFLBaseline", "get_qpsofl_baseline", "qpsofl_eval_main"]
