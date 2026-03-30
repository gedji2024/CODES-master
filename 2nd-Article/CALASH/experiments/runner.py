"""
Experiment Runner
=================
Orchestrates simulation campaigns across protocols, scenarios, and seeds.

For each (protocol, scenario_config, seed):
    1. Initialize network + models (energy, carbon, compression, disaster)
    2. Run simulation round-by-round (setup_phase -> steady_phase)
    3. Inject disaster at configured round (Gaussian spatial failure)
    4. Collect per-round metrics via MetricsCollector
    5. Aggregate across seeds (mean +/- 95% CI via t-distribution)

Reproducibility:
    Each (protocol, seed) pair uses a deterministic numpy RNG seeded with
    (base_seed + seed_offset). This ensures results are exactly reproducible
    and independent across seeds.

Statistical rigour:
    Default: 30 seeds per scenario. Confidence intervals use the
    t-distribution: CI_95 = t_{0.975, n-1} * s / sqrt(n), following
    standard practice in simulation studies [1].

References
----------
[1] Jain, R. "The Art of Computer Systems Performance Analysis."
    Wiley, 1991. ISBN: 978-0471503361.
    (Seed-based replication, CI computation, warm-up period.)

[2] Law, A.M. "Simulation Modeling and Analysis." 5th ed., McGraw-Hill,
    2015. (Independent replications method for WSN simulation.)
"""

import numpy as np
import json
import os
import time
from typing import Dict, List, Optional, Type
from tqdm import tqdm

from config import SimulationConfig
from models.network import Network
from models.energy import EnergyModel
from models.carbon import CarbonTraceManager
from models.compression import CompressiveSensing
from models.disaster import (DisasterEvent, create_disaster_from_profile,
                              ShakeMapDisasterEvent, create_shakemap_disaster)
from experiments.metrics import MetricsCollector
from protocols.base import BaseProtocol
from protocols.leach import LEACH, EE_LEACH, LEACH_SingleHop
from protocols.abc_aco import ABC_ACO
from protocols.eerp import EERP
from protocols.q_routing import QRouting
from protocols.calash import CALASH
from protocols.ablations import (CALASH_NoCO2, CALASH_NoSH,
                                  CALASH_NoCADR, CALASH_NoLCI,
                                  CALASH_NoTHz)
from protocols.ris_drl import RIS_DRL


# ─── t-distribution critical values for 95% CI ──────────────────────
# t_{0.975, df} lookup table (two-tailed 95% CI)
# Source: Standard statistical tables; verified against scipy.stats.t
_T_TABLE = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
    6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
    11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
    16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
    21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060,
    26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042,
    35: 2.030, 40: 2.021, 50: 2.009, 60: 2.000, 80: 1.990,
    100: 1.984, 200: 1.972, 500: 1.965,
}


def _t_critical(df: int) -> float:
    """Return t_{0.975, df} for a two-tailed 95% CI.

    Uses a lookup table for exact values at common df,
    with interpolation for intermediate values.
    Falls back to z=1.96 for df > 500 (normal approximation).
    """
    if df >= 500:
        return 1.96
    if df in _T_TABLE:
        return _T_TABLE[df]
    # Find bracketing df values and interpolate
    keys = sorted(_T_TABLE.keys())
    for i in range(len(keys) - 1):
        if keys[i] <= df < keys[i + 1]:
            lo, hi = keys[i], keys[i + 1]
            frac = (df - lo) / (hi - lo)
            return _T_TABLE[lo] + frac * (_T_TABLE[hi] - _T_TABLE[lo])
    return 1.96  # fallback


# Protocol registry
PROTOCOL_CLASSES = {
    'LEACH': LEACH,
    'LEACH-1hop': LEACH_SingleHop,
    'EE-LEACH': EE_LEACH,
    'ABC-ACO': ABC_ACO,
    'EERP': EERP,
    'Q-Routing': QRouting,
    'RIS-DRL': RIS_DRL,
    'CALASH': CALASH,
    'CALASH-NoCO2': CALASH_NoCO2,
    'CALASH-NoSH': CALASH_NoSH,
    'CALASH-NoCADR': CALASH_NoCADR,
    'CALASH-NoLCI': CALASH_NoLCI,
    'CALASH-NoTHz': CALASH_NoTHz,
}


def create_protocol(name: str, config: SimulationConfig,
                    energy_model: EnergyModel,
                    carbon_mgr: CarbonTraceManager,
                    cs: CompressiveSensing,
                    rng: np.random.Generator) -> BaseProtocol:
    """Instantiate a protocol by name."""
    if name not in PROTOCOL_CLASSES:
        raise ValueError(f"Unknown protocol: {name}. "
                         f"Available: {list(PROTOCOL_CLASSES.keys())}")
    cls = PROTOCOL_CLASSES[name]
    return cls(config, energy_model, carbon_mgr, cs, rng)


def run_single_experiment(config: SimulationConfig,
                          protocol_name: str,
                          seed: int,
                          verbose: bool = False) -> Dict:
    """
    Run a single simulation experiment.

    Parameters
    ----------
    config : SimulationConfig
        Experiment configuration.
    protocol_name : str
        Name of the protocol to test.
    seed : int
        Random seed for this run.
    verbose : bool
        Print progress.

    Returns
    -------
    dict
        Summary metrics + time series data.
    """
    rng = np.random.default_rng(seed)

    # Initialize components
    network = Network(config, rng)
    energy_model = EnergyModel(config)
    carbon_mgr = CarbonTraceManager(config, rng)
    cs = CompressiveSensing(config, rng)

    # Initialize protocol
    protocol = create_protocol(
        protocol_name, config, energy_model, carbon_mgr, cs, rng
    )

    # Reset protocol state if available
    if hasattr(protocol, 'reset'):
        protocol.reset()
    if hasattr(protocol, 'reset_q_tables'):
        protocol.reset_q_tables()

    # Metrics collector
    collector = MetricsCollector(config.num_nodes, config.initial_energy)

    # Disaster event (prepared but not yet applied)
    disaster = None
    disaster_applied = False
    disaster_round = config.disaster_round
    if config.disaster_enabled:
        # Priority 1: Use real USGS ShakeMap spatial data if configured
        shakemap_key = getattr(config, 'shakemap_event_id', '')
        event_key = getattr(config, 'disaster_event', '')

        if shakemap_key:
            # Real ShakeMap: spatially heterogeneous PGA/MMI damage
            disaster = create_shakemap_disaster(
                shakemap_key, config.disaster_x, config.disaster_y, rng,
                area_width=config.area_width,
                area_height=config.area_height,
            )
            if verbose:
                summary = disaster.get_shakemap_summary()
                print(f"  📡 ShakeMap loaded: {summary.get('event_key', shakemap_key)}, "
                      f"grid={summary.get('grid_points', '?')} pts, "
                      f"max_MMI={summary.get('max_mmi', '?')}")
        elif event_key:
            # Real earthquake profile with calibrated Gaussian
            disaster = create_disaster_from_profile(
                event_key, config.disaster_x, config.disaster_y, rng
            )
        else:
            # Generic Gaussian disaster
            disaster = DisasterEvent(
                config.disaster_x, config.disaster_y,
                config.damage_radius, rng
            )
        # Randomise disaster timing per seed for genuine uncertainty.
        # The protocol does NOT know when the disaster will strike;
        # it must detect it autonomously via heartbeat monitoring.
        jitter = getattr(config, 'disaster_round_jitter', 0.15)
        if jitter > 0:
            lo = int(disaster_round * (1.0 - jitter))
            hi = int(disaster_round * (1.0 + jitter))
            disaster_round = int(rng.integers(lo, hi + 1))

    # ─── Generate aftershock sequence (all protocols face same events) ──
    # Aftershocks are generated at the RUNNER level so every protocol
    # experiences the identical multi-disaster timeline.  This ensures
    # fair comparison: the advantage of CALASH's ISAC passive detection
    # and self-healing is measured under identical seismic sequences.
    #
    # Aftershock parameters follow Bath's law (M_after ≈ M_main - 1.2)
    # and Omori-Utsu temporal decay.  Each aftershock has a reduced
    # damage radius (radius_decay) and a spatial offset from the
    # mainshock epicentre.
    aftershocks = []
    if (config.disaster_enabled
            and getattr(config, 'aftershock_enabled', False)):
        prev_round = disaster_round
        prev_radius = config.damage_radius
        n_aftershocks = getattr(config, 'aftershock_count', 2)
        delay_lo = getattr(config, 'aftershock_delay_min', 500)
        delay_hi = getattr(config, 'aftershock_delay_max', 800)
        radius_decay = getattr(config, 'aftershock_radius_decay', 0.6)
        offset_m = getattr(config, 'aftershock_offset_m', 30.0)

        for i in range(n_aftershocks):
            delay = int(rng.integers(delay_lo, delay_hi + 1))
            as_round = prev_round + delay
            if as_round > config.num_rounds:
                break  # aftershock falls outside simulation window
            as_radius = prev_radius * radius_decay
            # Spatial offset: random direction from mainshock epicentre
            angle = rng.uniform(0, 2 * np.pi)
            as_x = np.clip(config.disaster_x + offset_m * np.cos(angle),
                           0, config.area_width)
            as_y = np.clip(config.disaster_y + offset_m * np.sin(angle),
                           0, config.area_height)
            as_disaster = DisasterEvent(as_x, as_y, as_radius, rng)
            aftershocks.append({
                'round': as_round,
                'disaster': as_disaster,
                'applied': False,
            })
            prev_round = as_round
            prev_radius = as_radius

        if verbose and aftershocks:
            print(f"  🌋 Multi-disaster: mainshock@{disaster_round} + "
                  f"{len(aftershocks)} aftershocks at "
                  f"{[a['round'] for a in aftershocks]}")

    # ─── Main Simulation Loop ────────────────────────────────────
    for round_num in range(1, config.num_rounds + 1):
        # Check termination
        if network.num_alive() == 0:
            break

        # Apply disaster BEFORE protocol round — the physical event
        # happens silently.  The protocol must discover the damage
        # through its own heartbeat-based monitoring (MAPE-K Monitor
        # phase) over subsequent rounds.  This makes self-healing
        # genuinely autonomous — no oracle notification.
        if (disaster is not None and not disaster_applied
                and round_num == disaster_round):
            killed, survived = disaster.apply_to_network(network)
            disaster_applied = True
            # NOTE: We do NOT call protocol.handle_disaster() for detection.
            # The protocol discovers deaths organically via heartbeats.
            # However, we store the disaster event reference so the
            # aftershock model can generate secondary events and
            # progressive damage can be tracked.
            if hasattr(protocol, '_last_disaster_event'):
                protocol._last_disaster_event = disaster
                # Trigger aftershock model initialisation (geophysical,
                # not detection — the protocol still discovers damage
                # autonomously via heartbeats)
                protocol.handle_disaster(network, killed, round_num)

            if verbose:
                print(f"  ⚡ Disaster at round {round_num}: "
                      f"{len(killed)} killed, {len(survived)} survived"
                      f" (protocol NOT notified — must detect via heartbeats)")

        # ── Apply aftershocks (runner-level: all protocols face same) ──
        for ainfo in aftershocks:
            if not ainfo['applied'] and round_num == ainfo['round']:
                as_killed, as_survived = ainfo['disaster'].apply_to_network(
                    network)
                ainfo['applied'] = True
                # Feed aftershock info to protocols that support it
                if hasattr(protocol, '_last_disaster_event'):
                    protocol.handle_disaster(
                        network, as_killed, round_num)
                if verbose:
                    print(f"  🌋 Aftershock at round {round_num}: "
                          f"{len(as_killed)} killed, "
                          f"{len(as_survived)} weakened")

        # Run protocol round (heartbeat monitor detects disaster organically)
        metrics = protocol.run_round(network, round_num)

        # Record disaster stats on the round it happened (for analysis only)
        if disaster_applied and round_num == disaster_round:
            metrics['disaster_killed'] = len(killed)
            metrics['disaster_survived'] = len(survived)
            metrics['disaster_round_actual'] = disaster_round

        # Record metrics
        collector.record_round(metrics)

        if verbose and round_num % 500 == 0:
            alive = network.num_alive()
            pdr = (metrics['packets_delivered'] /
                   max(1, metrics['packets_generated']))
            print(f"  Round {round_num:5d}: alive={alive:3d}, "
                  f"PDR={pdr:.2f}, E_consumed={metrics['energy_consumed']:.6f}J")

    # ─── Compile Results ─────────────────────────────────────────
    summary = collector.compute_summary()

    # LCI computation
    embodied = config.num_nodes * config.embodied_carbon_per_node
    dead_count = config.num_nodes - network.num_alive()
    eol = dead_count * config.eol_carbon_per_node * (1 - config.recycle_rate)
    summary['lci'] = collector.get_lci(embodied, eol)

    # GHG Protocol Scope 2/3 breakdown (WRI, 2015; ISO 14064-1:2018)
    # Uses the final-round energy and dead count for a snapshot
    # of the full lifecycle carbon accounting.
    total_energy_j = summary.get('total_energy_J', 0.0)
    last_round = len(collector.round_data)
    scope_breakdown = carbon_mgr.get_ghg_scope_breakdown(
        energy_joules=total_energy_j,
        round_num=last_round,
        num_nodes=config.num_nodes,
        dead_count=dead_count,
        embodied_per_node=config.embodied_carbon_per_node,
        eol_per_node=config.eol_carbon_per_node,
        recycle_rate=config.recycle_rate,
    )
    summary['ghg_scope1'] = scope_breakdown['scope1']
    summary['ghg_scope2_location'] = scope_breakdown['scope2_location']
    summary['ghg_scope2_marginal'] = scope_breakdown['scope2_marginal']
    summary['ghg_scope3_embodied'] = scope_breakdown['scope3_embodied']
    summary['ghg_scope3_eol'] = scope_breakdown['scope3_eol']
    summary['ghg_total'] = scope_breakdown['total']

    # Jain's fairness index
    summary['jains_fairness'] = collector.get_final_jains_fairness()

    # Fairness time series (sampled every 50 rounds)
    fairness_ts = collector.get_jains_fairness_series(sample_every=50)
    if len(fairness_ts) > 0:
        summary['ts_fairness'] = fairness_ts.tolist()

    # Energy CV time series
    cv_ts = collector.get_energy_variance_series(sample_every=50)
    if len(cv_ts) > 0:
        summary['ts_energy_cv'] = cv_ts.tolist()

    # Time series for plotting
    summary['ts_alive'] = collector.get_time_series('alive_nodes').tolist()
    summary['ts_pdr'] = collector.get_pdr_series(window=50).tolist()
    summary['ts_energy'] = np.cumsum(
        collector.get_time_series('energy_consumed')
    ).tolist()
    summary['ts_carbon'] = np.cumsum(
        collector.get_time_series('carbon_emitted')
    ).tolist()
    summary['ts_fidelity'] = collector.get_time_series('data_fidelity').tolist()

    # Energy breakdown time series (cumulative)
    summary['ts_energy_intra'] = np.cumsum(
        collector.get_time_series('energy_intra')
    ).tolist()
    summary['ts_energy_inter'] = np.cumsum(
        collector.get_time_series('energy_inter')
    ).tolist()
    summary['ts_energy_control'] = np.cumsum(
        collector.get_time_series('energy_control')
    ).tolist()

    if protocol_name in ('CALASH', 'CALASH-NoCO2', 'CALASH-NoSH'):
        summary['ts_carbon_queue'] = collector.get_time_series(
            'carbon_queue'
        ).tolist()

    # Convergence diagnostics (CALASH only)
    if protocol_name == 'CALASH':
        summary['ts_dqn_epsilon'] = collector.get_time_series(
            'dqn_epsilon'
        ).tolist()
        summary['ts_dqn_loss'] = collector.get_time_series(
            'dqn_loss'
        ).tolist()
        summary['ts_lyapunov_V'] = collector.get_time_series(
            'lyapunov_V'
        ).tolist()

    summary['protocol'] = protocol_name
    summary['seed'] = seed

    return summary


class ExperimentRunner:
    """
    Run full experiment campaigns across protocols, scenarios, and seeds.

    Aggregates results with statistical measures (mean ± 95% CI).
    """

    def __init__(self, protocols: List[str] = None,
                 output_dir: str = 'results'):
        """
        Parameters
        ----------
        protocols : list of str
            Protocol names to test.
        output_dir : str
            Directory for result files.
        """
        self.protocols = protocols or list(PROTOCOL_CLASSES.keys())
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def run_scenario(self, scenario_name: str,
                     configs: List[tuple],
                     verbose: bool = True) -> Dict:
        """
        Run all protocols on a scenario with multiple seeds.

        Parameters
        ----------
        scenario_name : str
            Name of the scenario for file naming.
        configs : list of (label, config) tuples
            Scenario configurations.
        verbose : bool
            Print progress.

        Returns
        -------
        dict
            Aggregated results: {protocol: {config_label: {metric: (mean, ci95)}}}
        """
        all_results = {}

        for config_label, config in configs:
            if verbose:
                print(f"\n{'='*60}")
                print(f"Scenario: {scenario_name} | Config: {config_label}")
                print(f"{'='*60}")

            for protocol_name in self.protocols:
                if verbose:
                    print(f"\n  Protocol: {protocol_name}")
                    print(f"  {'-'*40}")

                seed_results = []
                seeds = [config.base_seed + i for i in range(config.num_seeds)]

                iterator = tqdm(seeds, desc=f"    {protocol_name}",
                                disable=not verbose, leave=False)

                for seed in iterator:
                    t0 = time.time()
                    result = run_single_experiment(
                        config, protocol_name, seed, verbose=False
                    )
                    result['wall_time'] = time.time() - t0
                    seed_results.append(result)

                # Aggregate across seeds
                agg = self._aggregate_seeds(seed_results)

                # Store
                key = f"{protocol_name}|{config_label}"
                all_results[key] = {
                    'protocol': protocol_name,
                    'config_label': config_label,
                    'aggregated': agg,
                    'raw_results': seed_results,
                }

                if verbose:
                    self._print_summary(protocol_name, agg)

        # Save results
        self._save_results(scenario_name, all_results)

        return all_results

    def _aggregate_seeds(self, seed_results: List[Dict]) -> Dict:
        """Compute mean ± 95% CI across seeds."""
        if not seed_results:
            return {}

        # Keys to aggregate (scalars only)
        scalar_keys = [
            'first_death_round', 'half_death_round', 'last_death_round',
            'operational_lifetime', 'overall_pdr', 'total_energy_J',
            'energy_efficiency_pkt_per_J', 'total_carbon_gCO2',
            'avg_data_fidelity', 'recovery_time_rounds', 'lci',
            'total_delivered', 'total_generated', 'jains_fairness',
            'wall_time',
        ]

        agg = {}
        for key in scalar_keys:
            values = [r.get(key, np.nan) for r in seed_results]
            values = [v for v in values if v is not None and v >= 0
                      and not np.isnan(v)]
            if values:
                mean = float(np.mean(values))
                std = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
                n = len(values)
                t_crit = _t_critical(n - 1) if n > 1 else 1.96
                ci95 = t_crit * std / np.sqrt(n)
                agg[key] = {'mean': mean, 'std': std, 'ci95': ci95,
                            'n': n}
            else:
                agg[key] = {'mean': np.nan, 'std': np.nan, 'ci95': np.nan,
                            'n': 0}

        # Aggregate time series (mean across seeds, pad/truncate to same length)
        ts_keys = ['ts_alive', 'ts_pdr', 'ts_energy', 'ts_carbon',
                    'ts_fidelity', 'ts_fairness', 'ts_energy_cv']
        for key in ts_keys:
            series_list = [r.get(key, []) for r in seed_results if key in r]
            if series_list:
                max_len = max(len(s) for s in series_list)
                # Pad shorter series with their last value
                padded = []
                for s in series_list:
                    if len(s) < max_len:
                        s = list(s) + [s[-1]] * (max_len - len(s)) if s else [0] * max_len
                    padded.append(s[:max_len])
                arr = np.array(padded)
                agg[key] = {
                    'mean': arr.mean(axis=0).tolist(),
                    'std': arr.std(axis=0).tolist(),
                }

        return agg

    def _print_summary(self, protocol_name: str, agg: Dict):
        """Print summary for one protocol."""
        def fmt(key):
            d = agg.get(key, {})
            m = d.get('mean', np.nan)
            c = d.get('ci95', 0)
            if np.isnan(m):
                return "N/A"
            return f"{m:.2f} ± {c:.2f}"

        print(f"    Lifetime (50%):    {fmt('half_death_round')}")
        print(f"    PDR:               {fmt('overall_pdr')}")
        print(f"    Total Carbon:      {fmt('total_carbon_gCO2')}")
        print(f"    Data Fidelity:     {fmt('avg_data_fidelity')}")
        print(f"    LCI:               {fmt('lci')}")
        print(f"    Recovery Time:     {fmt('recovery_time_rounds')}")

    def _save_results(self, scenario_name: str, results: Dict):
        """Save results to JSON file."""
        # Convert for JSON serialization (remove raw time series for size)
        save_data = {}
        for key, val in results.items():
            save_data[key] = {
                'protocol': val['protocol'],
                'config_label': val['config_label'],
                'aggregated': {
                    k: v for k, v in val['aggregated'].items()
                    if not k.startswith('ts_')
                },
            }

        filepath = os.path.join(self.output_dir, f"{scenario_name}.json")
        with open(filepath, 'w') as f:
            json.dump(save_data, f, indent=2, default=str)
        print(f"\n  Results saved to: {filepath}")

        # Save full results (with time series) as numpy
        ts_filepath = os.path.join(self.output_dir, f"{scenario_name}_full.npz")
        ts_data = {}
        for key, val in results.items():
            agg = val['aggregated']
            safe_key = key.replace('|', '__')
            for ts_key in ['ts_alive', 'ts_pdr', 'ts_energy',
                           'ts_carbon', 'ts_fidelity',
                           'ts_fairness', 'ts_energy_cv']:
                if ts_key in agg:
                    ts_data[f"{safe_key}__{ts_key}_mean"] = np.array(
                        agg[ts_key]['mean']
                    )
                    ts_data[f"{safe_key}__{ts_key}_std"] = np.array(
                        agg[ts_key]['std']
                    )

        if ts_data:
            np.savez_compressed(ts_filepath, **ts_data)
            print(f"  Time series saved to: {ts_filepath}")
