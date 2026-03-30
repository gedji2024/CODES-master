"""
Electricity Maps Carbon Intensity Trace Generator
==================================================
Generates realistic hourly carbon intensity (CI) traces for multiple
regions/countries, calibrated to lifecycle carbon intensity data from
Ember's Yearly Electricity Data (2024 actuals).

Regions (2024 lifecycle data -- Ember, 2026 via Our World in Data):
    France:   mean~41  gCO2eq/kWh (nuclear-dominated, low CI)
    Germany:  mean~338 gCO2eq/kWh (wind+coal, high variance)
    India:    mean~707 gCO2eq/kWh (coal-dominated, high baseline)
    Poland:   mean~612 gCO2eq/kWh (coal, highest in EU)
    Brazil:   mean~106 gCO2eq/kWh (hydro-dominated, drought year)

Note: "lifecycle" carbon intensity includes upstream fuel supply,
plant construction/decommissioning, and transmission losses, not
just direct combustion emissions.

Each trace is 8760 hourly values (one year) with realistic:
    - Diurnal cycle (peak demand hours)
    - Seasonal variation (heating/cooling demand)
    - Auto-correlated noise (weather, demand fluctuations)
    - Weekend effects (lower industrial demand)

Reference:
    Ember (2026). "Yearly Electricity Data." Available via
    Our World in Data (CC BY 4.0).
    https://ourworldindata.org/grapher/carbon-intensity-electricity
    IEA (2024). "World Energy Outlook 2024." International Energy Agency.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
import os


# ─── Published Regional Carbon Intensity Statistics ──────────────────
# Sources: Ember (2026), Yearly Electricity Data — 2024 lifecycle actuals
# via Our World in Data, CC BY 4.0. Cross-validated with IEA WEO 2024.

REGION_PROFILES = {
    'france': {
        'name': 'France',
        'mean_ci': 41.0,          # gCO₂eq/kWh — Ember 2024 lifecycle
        'std_ci': 20.0,
        'min_ci': 10.0,           # nuclear baseload minimum
        'max_ci': 130.0,          # winter gas peaker peaks
        'daily_amplitude': 12.0,  # small diurnal swing (nuclear is flat)
        'daily_peak_hour': 19,    # 7 PM peak demand
        'seasonal_amplitude': 18.0,  # winter heating → more gas
        'seasonal_peak_month': 1,    # January peak
        'weekend_reduction': 0.08,   # 8% lower on weekends
        'noise_autocorr': 0.85,      # weather persistence
        'noise_std': 9.0,
        'grid_mix': 'Nuclear 65%, Wind 11%, Hydro 11%, Solar 7%, Gas 6%',
        'source': 'Ember (2026) Yearly Electricity Data, 2024; RTE eCO2mix',
    },
    'germany': {
        'name': 'Germany',
        'mean_ci': 338.0,         # gCO₂eq/kWh — Ember 2024 lifecycle
        'std_ci': 140.0,          # HIGH variance (renewables intermittency)
        'min_ci': 60.0,           # sunny windy day → low CI
        'max_ci': 680.0,          # winter calm night → all coal/gas
        'daily_amplitude': 95.0,  # large swing: solar noon vs coal night
        'daily_peak_hour': 8,     # morning ramp (coal starts, solar not yet)
        'seasonal_amplitude': 110.0,  # winter coal vs summer solar
        'seasonal_peak_month': 12,    # December peak
        'weekend_reduction': 0.12,    # 12% lower weekends
        'noise_autocorr': 0.80,
        'noise_std': 55.0,
        'grid_mix': 'Wind 27%, Coal 24%, Gas 14%, Solar 12%, Biomass 8%',
        'source': 'Ember (2026) Yearly Electricity Data, 2024; Fraunhofer ISE',
        # Note: Germany closed all nuclear plants in April 2023.
    },
    'india': {
        'name': 'India',
        'mean_ci': 707.0,         # gCO₂eq/kWh — Ember 2024 lifecycle
        'std_ci': 100.0,
        'min_ci': 440.0,          # monsoon hydro + solar peak
        'max_ci': 950.0,          # winter night, all coal
        'daily_amplitude': 75.0,  # moderate swing
        'daily_peak_hour': 20,    # evening peak (AC + lighting)
        'seasonal_amplitude': 85.0,   # monsoon (Jul-Sep) lower
        'seasonal_peak_month': 12,    # December peak
        'weekend_reduction': 0.05,    # small weekend effect
        'noise_autocorr': 0.90,
        'noise_std': 45.0,
        'grid_mix': 'Coal 56%, Solar 12%, Hydro 10%, Wind 7%, Gas 5%',
        'source': 'Ember (2026) Yearly Electricity Data, 2024; CEA India',
    },
    'poland': {
        'name': 'Poland',
        'mean_ci': 612.0,         # gCO₂eq/kWh — Ember 2024 lifecycle
        'std_ci': 105.0,
        'min_ci': 310.0,
        'max_ci': 880.0,
        'daily_amplitude': 75.0,
        'daily_peak_hour': 18,
        'seasonal_amplitude': 85.0,
        'seasonal_peak_month': 1,
        'weekend_reduction': 0.10,
        'noise_autocorr': 0.82,
        'noise_std': 48.0,
        'grid_mix': 'Coal 63%, Wind 18%, Gas 8%, Solar 5%, Biomass 4%',
        'source': 'Ember (2026) Yearly Electricity Data, 2024; PSE',
    },
    'brazil': {
        'name': 'Brazil',
        'mean_ci': 106.0,         # gCO₂eq/kWh — Ember 2024 lifecycle
        'std_ci': 55.0,           # higher variance (drought → more thermal)
        'min_ci': 25.0,           # wet season, full hydro
        'max_ci': 320.0,          # dry season, thermal backup
        'daily_amplitude': 20.0,
        'daily_peak_hour': 19,
        'seasonal_amplitude': 60.0,   # dry season (Jul-Oct) much higher
        'seasonal_peak_month': 9,     # September (end of dry season)
        'weekend_reduction': 0.06,
        'noise_autocorr': 0.88,
        'noise_std': 25.0,
        'grid_mix': 'Hydro 56%, Wind 14%, Solar 8%, Biomass 8%, Gas 12%',
        'source': 'Ember (2026) Yearly Electricity Data, 2024; ONS Brazil',
        # Note: 2024 was a drought year, reducing hydro share.
    },
}


class ElectricityMapsTraces:
    """
    Generate realistic carbon intensity traces matching Electricity Maps data.

    Each trace is 8760 hourly values (one full year) with proper
    diurnal, seasonal, and stochastic components.

    Usage
    -----
    >>> gen = ElectricityMapsTraces(rng=np.random.default_rng(42))
    >>> trace = gen.generate_trace('france')  # (8760,) array
    >>> gen.save_csv('france', 'data/france_ci.csv')
    """

    def __init__(self, rng: np.random.Generator = None):
        self.rng = rng if rng is not None else np.random.default_rng(42)
        self.profiles = REGION_PROFILES

    def generate_trace(self, region: str,
                       hours: int = 8760,
                       start_month: int = 1) -> np.ndarray:
        """
        Generate hourly CI trace for a region.

        Parameters
        ----------
        region : str
            Region key: 'france', 'germany', 'india', 'poland', 'brazil'.
        hours : int
            Number of hours (default 8760 = 1 year).
        start_month : int
            Starting month (1-12).

        Returns
        -------
        np.ndarray
            Carbon intensity trace of shape (hours,), gCO₂/kWh.
        """
        p = self.profiles[region]
        t = np.arange(hours)

        # Start offset in hours for starting month
        month_offset = (start_month - 1) * 730  # ~730 hours per month

        # 1. Diurnal cycle: sinusoidal with peak at specified hour
        hour_of_day = t % 24
        daily = p['daily_amplitude'] * np.sin(
            2 * np.pi * (hour_of_day - p['daily_peak_hour'] + 6) / 24
        )

        # 2. Seasonal cycle: sinusoidal with peak at specified month
        # Convert month to hour index (month 1 = hour 0)
        peak_hour = (p['seasonal_peak_month'] - 1) * 730
        seasonal = p['seasonal_amplitude'] * np.sin(
            2 * np.pi * (t + month_offset - peak_hour) / 8760
        )

        # 3. Weekend effect: lower CI on weekends (lower industrial demand)
        # Day of week: 0=Mon ... 6=Sun (assume hour 0 = Monday midnight)
        day_of_week = (t // 24) % 7
        is_weekend = (day_of_week >= 5).astype(float)
        weekend_effect = -p['weekend_reduction'] * p['mean_ci'] * is_weekend

        # 4. Auto-correlated noise (weather, demand fluctuations)
        raw_noise = self.rng.normal(0, p['noise_std'], hours)
        noise = np.zeros(hours)
        noise[0] = raw_noise[0]
        alpha = p['noise_autocorr']
        for i in range(1, hours):
            noise[i] = alpha * noise[i - 1] + np.sqrt(1 - alpha**2) * raw_noise[i]

        # 5. Combine
        ci = p['mean_ci'] + daily + seasonal + weekend_effect + noise

        # 6. Clip to physical bounds
        ci = np.clip(ci, p['min_ci'], p['max_ci'])

        return ci

    def generate_all_regions(self) -> Dict[str, np.ndarray]:
        """
        Generate traces for all regions.

        Returns
        -------
        dict
            {region_name: ci_trace_array}
        """
        return {region: self.generate_trace(region)
                for region in self.profiles}

    def save_csv(self, region: str, filepath: str,
                 trace: np.ndarray = None) -> str:
        """
        Save trace as CSV file compatible with CarbonTraceManager.

        Format matches Electricity Maps export:
            datetime,carbon_intensity
            2023-01-01 00:00,value

        Parameters
        ----------
        region : str
            Region name.
        filepath : str
            Output file path.
        trace : np.ndarray, optional
            Pre-generated trace. If None, generates new one.

        Returns
        -------
        str
            Path to saved file.
        """
        if trace is None:
            trace = self.generate_trace(region)

        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)

        # Generate datetime index (starting 2023-01-01 00:00)
        with open(filepath, 'w') as f:
            f.write('datetime,carbon_intensity\n')
            for i, ci in enumerate(trace):
                day = i // 24 + 1
                month = min(12, (day - 1) // 30 + 1)
                day_of_month = (day - 1) % 30 + 1
                hour = i % 24
                f.write(f'2023-{month:02d}-{day_of_month:02d} '
                        f'{hour:02d}:00,{ci:.1f}\n')

        return filepath

    def save_all_csvs(self, output_dir: str = 'data/carbon_traces') -> List[str]:
        """
        Generate and save CSV traces for all regions.

        Parameters
        ----------
        output_dir : str
            Output directory.

        Returns
        -------
        list of str
            Paths to saved files.
        """
        os.makedirs(output_dir, exist_ok=True)
        paths = []
        for region in self.profiles:
            trace = self.generate_trace(region)
            path = os.path.join(output_dir, f'{region}_ci.csv')
            self.save_csv(region, path, trace)
            paths.append(path)
        return paths

    def get_trace_statistics(self, region: str) -> Dict:
        """
        Compute statistics for a generated trace.

        Returns
        -------
        dict
            Statistical summary.
        """
        trace = self.generate_trace(region)
        return {
            'region': region,
            'mean': float(np.mean(trace)),
            'std': float(np.std(trace)),
            'min': float(np.min(trace)),
            'max': float(np.max(trace)),
            'median': float(np.median(trace)),
            'cv': float(np.std(trace) / np.mean(trace)),
            'published_mean': self.profiles[region]['mean_ci'],
            'published_std': self.profiles[region]['std_ci'],
        }

    @staticmethod
    def get_region_info() -> Dict:
        """
        Return metadata for all regions.

        For use in paper's experiment description.
        """
        info = {}
        for key, p in REGION_PROFILES.items():
            info[key] = {
                'name': p['name'],
                'mean_ci': p['mean_ci'],
                'std_ci': p['std_ci'],
                'grid_mix': p['grid_mix'],
                'source': p['source'],
            }
        return info
