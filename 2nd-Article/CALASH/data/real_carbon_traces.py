"""
Real Carbon Intensity Trace Loader
====================================
Loads real hourly carbon intensity data from the UK National Grid ESO
Carbon Intensity API for genuine carbon-aware simulation.

Dataset provenance:
    Name:     UK National Grid Carbon Intensity
    Source:   National Grid ESO, in partnership with Environmental
              Defense Fund Europe, University of Oxford, and WWF
    API:      https://api.carbonintensity.org.uk/
    Docs:     https://carbon-intensity.github.io/api-definitions/
    Format:   JSON (converted to CSV/NPZ by fetch_carbon_intensity.py)
    Coverage: Hourly carbon intensity for Great Britain, 2023 full year
    Values:   8,760 hourly gCO2/kWh (actual generation mix, not forecast)
    Mean:     ~152 gCO2/kWh (2023, reflecting UK's growing wind share)
    Range:    ~30 gCO2/kWh (windy nights) to ~400 gCO2/kWh (gas peaker peaks)
    Licence:  CC BY 4.0 (free, no API key required)
    Parsed:   data/real_traces/fetch_carbon_intensity.py ->
              uk_carbon_intensity_2023.csv (203 KB)
              uk_carbon_intensity_2023.npz (16 KB)

Citation:
    UK National Grid ESO. "Carbon Intensity API." 2023.
    https://carbonintensity.org.uk/

    Sheridan, M. & Jenkins, N. "Methodology for Determining the Time-
    Varying Grid Carbon Intensity of Electric Vehicle Charging."
    IEEE Trans. Smart Grid, 2020. (Underlying methodology.)

Why this dataset:
    - Free, public, high-quality hourly CI data (no paid API key needed)
    - Full year (2023) captures seasonal variation
    - Real generation-mix-weighted intensity (not just average)
    - Ideal for validating carbon-aware scheduling algorithms
    - Demonstrates CALASH's carbon awareness with real grid data

This module provides:
    - RealCarbonTraceLoader: load real hourly CI data
    - get_ci(): get CI for a given simulation round
    - get_trace(): get full CI trace for all rounds
"""

import os
import numpy as np


_UK_NPZ = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'real_traces', 'uk_carbon_intensity_2023.npz'
)

_UK_CSV = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'real_traces', 'uk_carbon_intensity_2023.csv'
)


class RealCarbonTraceLoader:
    """
    Load real hourly carbon intensity traces for simulation.

    Maps simulation rounds to hourly CI values from the real trace.
    Assumes each simulation round ≈ 1 minute (configurable).

    Parameters
    ----------
    rounds_per_hour : int
        Number of simulation rounds per real-world hour.
        Default: 60 (1 round = 1 minute).
    """

    def __init__(self, rounds_per_hour: int = 60):
        self.rounds_per_hour = rounds_per_hour
        self._loaded = False
        self._ci_hourly = None
        self._metadata = {}

    def _load(self):
        """Lazy-load the NPZ or CSV file."""
        if self._loaded:
            return

        if os.path.exists(_UK_NPZ):
            npz = np.load(_UK_NPZ, allow_pickle=True)
            self._ci_hourly = npz['ci_hourly']
            self._metadata = {
                'region': str(npz.get('region', 'UK')),
                'year': int(npz.get('year', 2023)),
                'source': str(npz.get('source',
                                      'UK National Grid Carbon Intensity API')),
                'n_hours': len(self._ci_hourly),
            }
        elif os.path.exists(_UK_CSV):
            # Fallback: parse CSV
            ci_values = []
            with open(_UK_CSV, 'r') as f:
                next(f)  # skip header
                for line in f:
                    parts = line.strip().split(',')
                    if len(parts) >= 2:
                        ci_values.append(float(parts[1]))
            self._ci_hourly = np.array(ci_values)
            self._metadata = {
                'region': 'UK',
                'year': 2023,
                'source': 'UK National Grid Carbon Intensity API (CSV)',
                'n_hours': len(self._ci_hourly),
            }
        else:
            raise FileNotFoundError(
                f"Real CI data not found. Run: "
                f"python data/real_traces/fetch_carbon_intensity.py"
            )

        self._loaded = True

    @property
    def available(self) -> bool:
        """Check if the real CI data file exists."""
        return os.path.exists(_UK_NPZ) or os.path.exists(_UK_CSV)

    def get_ci(self, round_num: int) -> float:
        """
        Get carbon intensity for a simulation round.

        Parameters
        ----------
        round_num : int
            Current simulation round (1-indexed).

        Returns
        -------
        float
            Carbon intensity in gCO₂/kWh.
        """
        self._load()

        # Map round to hour index (cyclically)
        hour_idx = ((round_num - 1) // self.rounds_per_hour) % len(self._ci_hourly)
        return float(self._ci_hourly[hour_idx])

    def get_trace(self, n_rounds: int) -> np.ndarray:
        """
        Get a full CI trace for all simulation rounds.

        Parameters
        ----------
        n_rounds : int
            Number of simulation rounds.

        Returns
        -------
        np.ndarray
            CI values for each round, shape (n_rounds,).
        """
        self._load()
        ci = np.empty(n_rounds)
        for r in range(n_rounds):
            hour_idx = (r // self.rounds_per_hour) % len(self._ci_hourly)
            ci[r] = self._ci_hourly[hour_idx]
        return ci

    def statistics(self) -> dict:
        """Return summary statistics of the real trace."""
        self._load()
        return {
            **self._metadata,
            'mean': float(np.mean(self._ci_hourly)),
            'std': float(np.std(self._ci_hourly)),
            'min': float(np.min(self._ci_hourly)),
            'max': float(np.max(self._ci_hourly)),
            'median': float(np.median(self._ci_hourly)),
        }


def is_real_ci_available() -> bool:
    """Check if real CI data exists."""
    return os.path.exists(_UK_NPZ) or os.path.exists(_UK_CSV)
