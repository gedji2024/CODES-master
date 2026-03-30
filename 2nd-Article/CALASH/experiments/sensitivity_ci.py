"""
CI Sensitivity Experiments
===========================
Carbon intensity sensitivity analysis across different national grids.

Tests CALASH performance under diverse carbon intensity profiles:
    1. France (nuclear-dominant): low CI (~41 gCO2/kWh), low variability
    2. UK (real 2023 data): medium CI (~200 gCO2/kWh), high variability
    3. India (coal-dominant): high CI (~707 gCO2/kWh), moderate variability
    4. Poland (coal-heavy): high CI (~612 gCO2/kWh), moderate variability

This addresses the reviewer concern:
    "Does CALASH's carbon-awareness actually matter?  Would it still
    outperform baselines in a low-carbon grid (France) where CI variation
    is small?  Or in a high-carbon grid (India) where every action is
    carbon-expensive?"

Expected findings:
    - CALASH advantage is LARGEST in medium-variability grids (UK, Germany)
      where carbon-adaptive scheduling has the most leverage
    - In low-CI grids (France): CALASH still wins on lifecycle + routing,
      but carbon savings margin is smaller
    - In high-CI grids (India): CALASH aggressively throttles, giving
      better carbon efficiency but slightly lower PDR (acceptable tradeoff)

References
----------
[1] Ember. "Yearly Electricity Data, 2024." Our World in Data.
    https://ourworldindata.org/grapher/carbon-intensity-electricity
"""

import numpy as np
from typing import Dict, List
from config import SimulationConfig


# Region-specific CI profiles (from Ember 2024 data)
REGION_PROFILES = {
    'france': {
        'name': 'France (Nuclear)',
        'ci_base': 41.0,
        'ci_amplitude_daily': 15.0,
        'ci_amplitude_seasonal': 10.0,
        'ci_noise_std': 8.0,
        'description': 'Low-CI nuclear-dominant grid. Minimal diurnal variation.',
    },
    'uk': {
        'name': 'UK (Mixed, Real 2023)',
        'ci_base': 200.0,
        'ci_amplitude_daily': 80.0,
        'ci_amplitude_seasonal': 40.0,
        'ci_noise_std': 25.0,
        'description': 'Medium-CI mixed grid. High diurnal variation (gas peakers).',
        'trace_file': 'real_uk_2023',
    },
    'germany': {
        'name': 'Germany (Transition)',
        'ci_base': 338.0,
        'ci_amplitude_daily': 100.0,
        'ci_amplitude_seasonal': 50.0,
        'ci_noise_std': 30.0,
        'description': 'Medium-high CI. Coal+wind mix creates high variability.',
    },
    'india': {
        'name': 'India (Coal)',
        'ci_base': 707.0,
        'ci_amplitude_daily': 60.0,
        'ci_amplitude_seasonal': 30.0,
        'ci_noise_std': 20.0,
        'description': 'High-CI coal-dominant grid. Lower relative variation.',
    },
    'poland': {
        'name': 'Poland (Coal)',
        'ci_base': 612.0,
        'ci_amplitude_daily': 70.0,
        'ci_amplitude_seasonal': 35.0,
        'ci_noise_std': 25.0,
        'description': 'High-CI coal-heavy grid. Moderate variation.',
    },
    'brazil': {
        'name': 'Brazil (Hydro)',
        'ci_base': 106.0,
        'ci_amplitude_daily': 30.0,
        'ci_amplitude_seasonal': 40.0,
        'ci_noise_std': 15.0,
        'description': 'Low-CI hydro-dominant. Seasonal variation (dry/wet).',
    },
}


def create_ci_sensitivity_configs(
    regions: List[str] = None,
    base_config: SimulationConfig = None
) -> Dict[str, SimulationConfig]:
    """
    Create simulation configs for CI sensitivity analysis.

    Parameters
    ----------
    regions : list of str
        Region keys to test. Default: all regions.
    base_config : SimulationConfig
        Base config to modify.

    Returns
    -------
    dict
        {region_name: SimulationConfig}
    """
    if regions is None:
        regions = ['france', 'india', 'poland', 'uk']

    if base_config is None:
        base_config = SimulationConfig()

    configs = {}
    for region in regions:
        if region not in REGION_PROFILES:
            continue

        profile = REGION_PROFILES[region]
        overrides = {
            'ci_base': profile['ci_base'],
            'ci_amplitude_daily': profile['ci_amplitude_daily'],
            'ci_amplitude_seasonal': profile['ci_amplitude_seasonal'],
            'ci_noise_std': profile['ci_noise_std'],
        }

        # Use real trace if available
        if 'trace_file' in profile:
            overrides['carbon_trace_file'] = profile['trace_file']
        else:
            overrides['carbon_region'] = region

        configs[profile['name']] = base_config.copy(**overrides)

    return configs


def format_sensitivity_table(results: Dict[str, Dict]) -> str:
    """
    Format CI sensitivity results as a text table.

    Parameters
    ----------
    results : dict
        {region_name: {protocol: {metric: value}}}

    Returns
    -------
    str
        Formatted table.
    """
    lines = []
    lines.append("=" * 80)
    lines.append("CI SENSITIVITY ANALYSIS RESULTS")
    lines.append("=" * 80)

    header = f"{'Region':<25} {'Protocol':<15} {'PDR':<8} {'Carbon':<10} {'Lifetime':<10}"
    lines.append(header)
    lines.append("-" * 80)

    for region, protocols in results.items():
        first = True
        for proto, metrics in protocols.items():
            region_col = region if first else ""
            pdr = metrics.get('pdr', 0)
            carbon = metrics.get('carbon', 0)
            lifetime = metrics.get('lifetime', 0)
            lines.append(
                f"{region_col:<25} {proto:<15} {pdr:<8.4f} {carbon:<10.2f} {lifetime:<10.0f}"
            )
            first = False
        lines.append("-" * 80)

    return "\n".join(lines)
