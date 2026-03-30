"""
Experiment Scenarios
====================
Defines eight experimental scenarios matching the paper's evaluation:

E1: Scalability — vary number of nodes (100, 200, 300, 500)
E2: Disaster Severity — vary damage radius using USGS earthquake magnitudes
E3: Carbon Grid Variation — real Electricity Maps traces (France, Germany, India)
E4: Lyapunov V Sensitivity — vary V parameter
E5: Real Sensor Signals — Intel Lab dataset (temperature, humidity, light)
E6: Real Carbon Traces — compare regions with Electricity Maps data
E7: Energy Fairness — Jain's index analysis across protocols
E8: Computational Overhead — wall-clock timing comparison

Each scenario returns a list of (name, config) pairs.
"""

from typing import List, Tuple
from config import SimulationConfig, default_config


def scenario_scalability() -> List[Tuple[str, SimulationConfig]]:
    """E1: Vary network size to test scalability."""
    base = default_config()
    sizes = [100, 200, 300, 500]
    return [
        (f"N={n}", base.copy(num_nodes=n))
        for n in sizes
    ]


def scenario_disaster_severity() -> List[Tuple[str, SimulationConfig]]:
    """
    E2: Vary disaster severity using USGS earthquake magnitude mapping.

    Uses empirical magnitude→radius relationship from Worden et al. (2012).
    Each configuration corresponds to a real earthquake severity level.
    """
    base = default_config()

    # USGS-calibrated: magnitude → simulation damage radius
    # Using magnitude_to_simulation_radius() from data/disaster_catalog.py
    from data.disaster_catalog import magnitude_to_simulation_radius
    configs = []
    for mag, label in [(5.5, "M5.5 Moderate"), (6.5, "M6.5 Strong"),
                       (7.5, "M7.5 Major")]:
        r = magnitude_to_simulation_radius(mag, base.area_width)
        configs.append((
            f"{label} (r={r:.0f}m)",
            base.copy(damage_radius=r, disaster_type='earthquake',
                      disaster_event=f'synthetic_M{mag}')
        ))
    return configs


def scenario_carbon_grid() -> List[Tuple[str, SimulationConfig]]:
    """
    E3: Vary carbon intensity using Electricity Maps real regional traces.

    France (nuclear, ~56 gCO₂/kWh) — low-carbon benchmark
    Germany (coal+wind, ~385 gCO₂/kWh) — high-variance mixed grid
    India (coal, ~632 gCO₂/kWh) — high-carbon baseline
    """
    base = default_config()
    configs = [
        ("France (nuclear, ~56g)", base.copy(
            carbon_region='france',
            ci_base=56.0, ci_min=15.0, ci_max=180.0
        )),
        ("Germany (mixed, ~385g)", base.copy(
            carbon_region='germany',
            ci_base=385.0, ci_min=80.0, ci_max=750.0
        )),
        ("India (coal, ~632g)", base.copy(
            carbon_region='india',
            ci_base=632.0, ci_min=400.0, ci_max=900.0
        )),
    ]
    return configs


def scenario_lyapunov_v() -> List[Tuple[str, SimulationConfig]]:
    """E4: Vary Lyapunov V parameter to characterize tradeoff."""
    base = default_config()
    v_values = [1.0, 10.0, 50.0, 100.0, 500.0, 1000.0]
    return [
        (f"V={v}", base.copy(V_lyapunov=v))
        for v in v_values
    ]


def scenario_real_sensor() -> List[Tuple[str, SimulationConfig]]:
    """
    E5: Validate CS fidelity with Intel Lab dataset signals.

    Uses signal vectors matching the statistical properties of the
    Intel Berkeley Research Lab dataset (Madden, 2004):
        54 Mica2Dot sensors, temperature/humidity/light/voltage
        ~2.3 million readings, DCT-domain sparsity ~15-20%

    Tests all four modalities to show CALASH's adaptive compression
    works well on real-world sensor signals, not just synthetic ones.
    """
    base = default_config()
    configs = []
    for modality in ['temperature', 'humidity', 'light']:
        configs.append((
            f"Intel-{modality.capitalize()}",
            base.copy(signal_source='intel_lab',
                      signal_modality=modality)
        ))
    return configs


def scenario_real_carbon() -> List[Tuple[str, SimulationConfig]]:
    """
    E6: Real Electricity Maps carbon traces across 5 regions.

    Demonstrates CALASH's carbon-awareness adapts to diverse grid mixes:
    - Nuclear-dominated (France) — flat, low CI
    - Mixed with high renewables (Germany) — volatile, medium CI
    - Coal-dominated (India) — high baseline, low variance
    - Extreme coal (Poland) — highest in EU
    - Hydro-dominated (Brazil) — seasonal extremes
    """
    base = default_config()
    regions = [
        ('france', 56.0, 15.0, 180.0),
        ('germany', 385.0, 80.0, 750.0),
        ('india', 632.0, 400.0, 900.0),
        ('poland', 668.0, 350.0, 950.0),
        ('brazil', 75.0, 20.0, 250.0),
    ]
    configs = []
    for region, ci_base, ci_min, ci_max in regions:
        configs.append((
            f"EM-{region.capitalize()}",
            base.copy(carbon_region=region,
                      ci_base=ci_base, ci_min=ci_min, ci_max=ci_max)
        ))
    return configs


def scenario_fairness() -> List[Tuple[str, SimulationConfig]]:
    """
    E7: Energy fairness analysis (Jain's index).

    Runs standard config — fairness metrics collected automatically
    via MetricsCollector's Jain's fairness tracking.

    Jain, R., Chiu, D., & Hawe, W. (1984). DEC TR-301.
    """
    base = default_config()
    return [("Standard (N=200)", base)]


def scenario_overhead() -> List[Tuple[str, SimulationConfig]]:
    """
    E8: Computational overhead comparison.

    Wall-clock time per round across protocols.
    Uses smaller config for faster measurement.
    """
    base = default_config()
    return [
        ("Overhead (N=200)", base.copy(num_rounds=1000, num_seeds=10))
    ]


def scenario_real_disaster() -> List[Tuple[str, SimulationConfig]]:
    """
    E2b: Real disaster events from USGS earthquake catalog + NASA FIRMS.

    Each configuration uses damage radius derived from a real event
    via the empirical attenuation relationship of Worden et al. (2012).
    """
    base = default_config()
    from data.disaster_catalog import DisasterCatalog
    catalog = DisasterCatalog(base.area_width, base.area_height)

    configs = []
    # Earthquakes from USGS
    for event_key in ['morocco_2023', 'turkey_syria_2023', 'nepal_2015']:
        params = catalog.get_earthquake_params(event_key)
        configs.append((
            f"EQ-{params['event_name'][:20]}",
            base.copy(
                damage_radius=params['sim_damage_radius_m'],
                disaster_x=params['epicenter_x'],
                disaster_y=params['epicenter_y'],
                disaster_type='earthquake',
                disaster_event=event_key,
            )
        ))
    # Wildfire from NASA FIRMS
    for event_key in ['camp_fire_2018', 'maui_fire_2023']:
        params = catalog.get_wildfire_params(event_key)
        configs.append((
            f"WF-{params['event_name'][:20]}",
            base.copy(
                damage_radius=params['sim_damage_radius_m'],
                disaster_x=params['epicenter_x'],
                disaster_y=params['epicenter_y'],
                disaster_type='wildfire',
                disaster_event=event_key,
            )
        ))
    return configs


def scenario_quick_test() -> List[Tuple[str, SimulationConfig]]:
    """Quick test scenario with small network."""
    return [
        ("Quick", SimulationConfig(
            num_nodes=50,
            num_rounds=500,
            num_seeds=3,
            area_width=200.0,
            area_height=200.0,
            bs_y=250.0,
            disaster_round=250,
            damage_radius=60.0,
        ))
    ]


# Registry of all scenarios
SCENARIOS = {
    # Original E1-E4
    'scalability': scenario_scalability,
    'disaster': scenario_disaster_severity,
    'carbon': scenario_carbon_grid,
    'lyapunov_v': scenario_lyapunov_v,
    # New E5-E8
    'real_sensor': scenario_real_sensor,
    'real_carbon': scenario_real_carbon,
    'fairness': scenario_fairness,
    'overhead': scenario_overhead,
    # Bonus: real disaster events
    'real_disaster': scenario_real_disaster,
    # Utilities
    'quick': scenario_quick_test,
}


def get_scenario(name: str) -> List[Tuple[str, SimulationConfig]]:
    """
    Get scenario configurations by name.

    Parameters
    ----------
    name : str
        Scenario name.

    Returns
    -------
    List of (label, config) tuples.
    """
    if name not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {name}. "
                         f"Available: {list(SCENARIOS.keys())}")
    return SCENARIOS[name]()
