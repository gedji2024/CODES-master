"""
Metrics Collector
=================
Collects, aggregates, and exports per-round metrics
across protocols, seeds, and scenarios.

Key metrics (matching IEEE TGCN / IoT-J reporting standards):
    1. Network Lifetime -- rounds until first/50%/last node death [1]
    2. Packet Delivery Ratio (PDR) -- delivered/generated over time [2]
    3. Average Residual Energy -- energy balance across nodes
    4. Total Carbon Emissions -- cumulative operational gCO2eq [3]
    5. Lifecycle Carbon Intensity (LCI) -- gCO2eq per useful packet [4]
       LCI = (C_embodied + C_operational + C_eol) / packets_delivered
    6. Data Fidelity -- 1 - NMSE (reconstruction quality after CS)
    7. Energy Efficiency -- packets delivered per Joule
    8. Post-Disaster Recovery Time -- rounds to restore 90% pre-disaster PDR

Statistical aggregation across seeds:
    - Mean and standard deviation computed per metric
    - 95% CI via t-distribution: CI = t_{0.975, n-1} * s / sqrt(n)
    - Jain's Fairness Index [5] for energy balance

References
----------
[1] Dietrich, I. & Dressler, F. "On the Lifetime of Wireless Sensor
    Networks." ACM Trans. Sensor Networks, 5(1), Art. 5, 2009.
    DOI: 10.1145/1464420.1464425

[2] Heinzelman, W.B. et al. IEEE Trans. Wireless Comm., 1(4), 2002.
    DOI: 10.1109/TWC.2002.804190  (PDR definition)

[3] ISO 14064-1:2018. "Greenhouse gases -- Part 1: Specification with
    guidance for quantification and reporting of GHG emissions."

[4] ISO 14040:2006. "Environmental management -- Life cycle assessment."

[5] Jain, R., Chiu, D. & Hawe, W. "A Quantitative Measure of Fairness
    and Discrimination for Resource Allocation." DEC-TR-301, 1984.
"""

import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class RoundMetrics:
    """Metrics for a single simulation round."""
    round_num: int = 0
    alive_nodes: int = 0
    num_chs: int = 0
    packets_generated: int = 0
    packets_delivered: int = 0
    energy_consumed: float = 0.0
    carbon_emitted: float = 0.0
    data_fidelity: float = 1.0
    compression_ratio: float = 1.0
    carbon_queue: float = 0.0
    recovery_mode: bool = False


class MetricsCollector:
    """
    Collects and aggregates per-round simulation metrics.

    Tracks cumulative values and computes standard WSN benchmarks.
    """

    def __init__(self, num_nodes: int, initial_energy: float):
        self.num_nodes = num_nodes
        self.initial_energy = initial_energy
        self.round_data: List[Dict] = []

        # Cumulative trackers
        self.total_packets_generated = 0
        self.total_packets_delivered = 0
        self.total_energy_consumed = 0.0
        self.total_carbon_emitted = 0.0

        # Lifetime markers
        self.first_node_death_round = -1
        self.half_nodes_death_round = -1
        self.last_node_death_round = -1
        self._prev_alive = num_nodes

        # Post-disaster recovery
        self._pre_disaster_pdr = None
        self._disaster_round = -1
        self._recovery_round = -1
        self._pdr_window = 10  # rounds for rolling PDR

        # Energy fairness tracking (Jain's index)
        self._energy_snapshots: List = []

    def record_round(self, metrics: Dict) -> None:
        """
        Record metrics from one round.

        Parameters
        ----------
        metrics : Dict
            Round metrics from protocol.steady_phase().
        """
        self.round_data.append(metrics)

        # Accumulate
        self.total_packets_generated += metrics.get('packets_generated', 0)
        self.total_packets_delivered += metrics.get('packets_delivered', 0)
        self.total_energy_consumed += metrics.get('energy_consumed', 0.0)
        self.total_carbon_emitted += metrics.get('carbon_emitted', 0.0)

        # Track per-node energy for Jain's fairness
        node_energies = metrics.get('node_energies', None)
        if node_energies is not None:
            self._energy_snapshots.append(np.array(node_energies))

        # Lifetime tracking
        alive = metrics.get('alive_nodes', 0)
        round_num = metrics.get('round', 0)

        if self._prev_alive == self.num_nodes and alive < self.num_nodes:
            self.first_node_death_round = round_num

        if self._prev_alive > self.num_nodes // 2 >= alive:
            self.half_nodes_death_round = round_num

        if alive == 0 and self._prev_alive > 0:
            self.last_node_death_round = round_num

        self._prev_alive = alive

        # Post-disaster recovery tracking
        if metrics.get('recovery_mode', False) and self._disaster_round < 0:
            self._disaster_round = round_num
            # Compute pre-disaster PDR
            if len(self.round_data) > self._pdr_window:
                recent = self.round_data[-self._pdr_window - 1:-1]
                gen = sum(r.get('packets_generated', 0) for r in recent)
                dlv = sum(r.get('packets_delivered', 0) for r in recent)
                self._pre_disaster_pdr = dlv / gen if gen > 0 else 1.0

        # Check if PDR has recovered to 90% of pre-disaster level
        if (self._disaster_round > 0 and self._recovery_round < 0
                and self._pre_disaster_pdr is not None):
            if len(self.round_data) >= self._pdr_window:
                recent = self.round_data[-self._pdr_window:]
                gen = sum(r.get('packets_generated', 0) for r in recent)
                dlv = sum(r.get('packets_delivered', 0) for r in recent)
                current_pdr = dlv / gen if gen > 0 else 0.0
                if current_pdr >= 0.9 * self._pre_disaster_pdr:
                    self._recovery_round = round_num

    def get_time_series(self, key: str) -> np.ndarray:
        """Extract a specific metric as time series."""
        return np.array([d.get(key, 0) for d in self.round_data])

    def get_pdr_series(self, window: int = 50) -> np.ndarray:
        """
        Compute rolling PDR (Packet Delivery Ratio) over time.

        Parameters
        ----------
        window : int
            Rolling window size in rounds.

        Returns
        -------
        np.ndarray
            PDR values for each round.
        """
        gen = self.get_time_series('packets_generated')
        dlv = self.get_time_series('packets_delivered')
        n = len(gen)
        pdr = np.zeros(n)
        for i in range(n):
            start = max(0, i - window + 1)
            g = gen[start:i + 1].sum()
            d = dlv[start:i + 1].sum()
            pdr[i] = d / g if g > 0 else 0.0
        return pdr

    def compute_summary(self) -> Dict:
        """
        Compute all summary metrics for this experiment run.

        Returns
        -------
        dict
            Complete metrics summary.
        """
        n_rounds = len(self.round_data)
        if n_rounds == 0:
            return {}

        overall_pdr = (self.total_packets_delivered / self.total_packets_generated
                       if self.total_packets_generated > 0 else 0.0)

        energy_efficiency = (self.total_packets_delivered / self.total_energy_consumed
                             if self.total_energy_consumed > 0 else 0.0)

        # Average data fidelity
        fidelity_series = self.get_time_series('data_fidelity')
        valid_fidelity = fidelity_series[fidelity_series > 0]
        avg_fidelity = float(np.mean(valid_fidelity)) if len(valid_fidelity) > 0 else 1.0

        # Alive nodes time series
        alive_series = self.get_time_series('alive_nodes')

        # Operational lifetime (rounds until 50% nodes dead)
        if self.half_nodes_death_round < 0:
            # 50% never died — set to total rounds
            operational_lifetime = n_rounds
        else:
            operational_lifetime = self.half_nodes_death_round

        # Recovery time
        recovery_time = -1
        if self._disaster_round > 0 and self._recovery_round > 0:
            recovery_time = self._recovery_round - self._disaster_round

        return {
            # Lifetime
            'first_death_round': self.first_node_death_round,
            'half_death_round': self.half_nodes_death_round,
            'last_death_round': self.last_node_death_round,
            'operational_lifetime': operational_lifetime,

            # Delivery
            'total_generated': self.total_packets_generated,
            'total_delivered': self.total_packets_delivered,
            'overall_pdr': overall_pdr,

            # Energy
            'total_energy_J': self.total_energy_consumed,
            'energy_efficiency_pkt_per_J': energy_efficiency,

            # Energy breakdown (cumulative over all rounds)
            'energy_intra_J': float(np.sum(
                self.get_time_series('energy_intra'))),
            'energy_inter_J': float(np.sum(
                self.get_time_series('energy_inter'))),
            'energy_control_J': float(np.sum(
                self.get_time_series('energy_control'))),

            # Carbon
            'total_carbon_gCO2': self.total_carbon_emitted,
            'avg_carbon_per_round': (self.total_carbon_emitted / n_rounds
                                     if n_rounds > 0 else 0.0),

            # Fidelity
            'avg_data_fidelity': avg_fidelity,

            # Disaster recovery
            'recovery_time_rounds': recovery_time,

            # Energy fairness (Jain's index)
            'jains_fairness': self.get_final_jains_fairness(),

            # Alive at end
            'final_alive_nodes': int(alive_series[-1]) if len(alive_series) > 0 else 0,
            'num_rounds_run': n_rounds,
        }

    def get_jains_fairness_series(self, sample_every: int = 50) -> np.ndarray:
        """
        Compute Jain's Fairness Index over time for residual energy.

        Jain's index J(x₁,...,xₙ) = (Σxᵢ)² / (n · Σxᵢ²)
        where xᵢ = residual energy of node i.

        J = 1.0 → perfectly fair (all nodes equal)
        J = 1/n → maximally unfair (one node has all energy)

        Reference:
            Jain, R., Chiu, D., & Hawe, W. (1984). "A Quantitative Measure
            of Fairness and Discrimination for Resource Allocation."
            DEC Research Report TR-301.

        Parameters
        ----------
        sample_every : int
            Compute fairness every N rounds to reduce overhead.

        Returns
        -------
        np.ndarray
            Jain's fairness index at sampled rounds.
        """
        if not self._energy_snapshots:
            return np.array([])

        indices = range(0, len(self._energy_snapshots), sample_every)
        fairness = []
        for i in indices:
            energies = self._energy_snapshots[i]
            # Only consider alive nodes (energy > 0)
            alive_energies = energies[energies > 0]
            if len(alive_energies) < 2:
                fairness.append(1.0)
                continue
            sum_x = np.sum(alive_energies)
            sum_x2 = np.sum(alive_energies ** 2)
            n = len(alive_energies)
            j = (sum_x ** 2) / (n * sum_x2) if sum_x2 > 0 else 1.0
            fairness.append(float(j))

        return np.array(fairness)

    def get_final_jains_fairness(self) -> float:
        """
        Compute Jain's Fairness Index at the last recorded round.

        Returns
        -------
        float
            Jain's index in [1/n, 1].
        """
        if not self._energy_snapshots:
            return 1.0
        energies = self._energy_snapshots[-1]
        alive_energies = energies[energies > 0]
        if len(alive_energies) < 2:
            return 1.0
        sum_x = np.sum(alive_energies)
        sum_x2 = np.sum(alive_energies ** 2)
        n = len(alive_energies)
        return float((sum_x ** 2) / (n * sum_x2)) if sum_x2 > 0 else 1.0

    def get_energy_variance_series(self, sample_every: int = 50) -> np.ndarray:
        """
        Compute coefficient of variation (CV) of residual energy over time.

        CV = std / mean — measures energy imbalance.
        Lower CV = more balanced energy consumption.

        Returns
        -------
        np.ndarray
            CV values at sampled rounds.
        """
        if not self._energy_snapshots:
            return np.array([])

        indices = range(0, len(self._energy_snapshots), sample_every)
        cvs = []
        for i in indices:
            energies = self._energy_snapshots[i]
            alive_energies = energies[energies > 0]
            if len(alive_energies) < 2:
                cvs.append(0.0)
                continue
            mean_e = np.mean(alive_energies)
            std_e = np.std(alive_energies)
            cvs.append(float(std_e / mean_e) if mean_e > 0 else 0.0)

        return np.array(cvs)

    def get_lci(self, embodied_carbon_total: float,
                eol_carbon_total: float) -> float:
        """
        Compute Lifecycle Carbon Intensity (LCI).

        LCI = (C_embodied + C_operational + C_eol) / packets_delivered

        Parameters
        ----------
        embodied_carbon_total : float
            Total embodied carbon of all nodes (gCO2eq).
        eol_carbon_total : float
            Total end-of-life carbon (gCO2eq).

        Returns
        -------
        float
            LCI in gCO2eq per useful packet.
        """
        if self.total_packets_delivered == 0:
            return float('inf')
        total = embodied_carbon_total + self.total_carbon_emitted + eol_carbon_total
        return total / self.total_packets_delivered
