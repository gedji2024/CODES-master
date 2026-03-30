"""
Q-Routing Baseline Protocol
============================
Q-learning based per-node routing, representing reinforcement learning
approaches to WSN routing. Based on the seminal Q-routing paradigm
of Boyan & Littman (1994) adapted for WSN cluster-head routing.

Each cluster head maintains a Q-table indexed by neighbor CH IDs.
Q-values estimate the cost to deliver a packet to BS via each neighbor.

Q-update rule (per packet delivery, standard Q-learning [1]):
    Q_x(y) <- (1-alpha) * Q_x(y) + alpha * [cost(x->y) + gamma * min_z Q_y(z)]

Action selection: epsilon-greedy with exponential decay.
Reward: negative energy cost (minimization objective).
CH election: energy-weighted (same as EE-LEACH) for fair comparison.

Comparison with CALASH DQN:
    - Q-Routing: tabular Q-learning, energy-only reward, no carbon awareness
    - CALASH:    deep Q-network (DQN), multi-objective reward (energy + carbon +
                 lifecycle), Lyapunov constraint, experience replay

References
----------
[1] Watkins, C.J.C.H. & Dayan, P. "Q-Learning." Machine Learning,
    vol. 8, pp. 279-292, 1992. DOI: 10.1007/BF00992698

[2] Boyan, J.A. & Littman, M.L. "Packet Routing in Dynamically Changing
    Networks: A Reinforcement Learning Approach." Advances in Neural
    Information Processing Systems (NeurIPS), 1994.
"""

import numpy as np
from typing import Dict, List, Tuple
from collections import defaultdict

from protocols.base import BaseProtocol
from models.network import Network, Node
from models.energy import EnergyModel
from models.carbon import CarbonTraceManager
from models.compression import CompressiveSensing


class QRouting(BaseProtocol):
    """
    Q-learning routing protocol for WSN cluster heads.

    Uses energy-weighted CH election (like EE-LEACH) combined
    with Q-learning for inter-cluster routing decisions.
    No carbon awareness — purely energy-driven.
    """

    def __init__(self, config, energy_model: EnergyModel,
                 carbon_mgr: CarbonTraceManager = None,
                 cs: CompressiveSensing = None,
                 rng: np.random.Generator = None):
        super().__init__(config, energy_model, carbon_mgr, cs)
        self.name = "Q-Routing"
        self.rng = rng if rng is not None else np.random.default_rng(42)

        # Q-learning parameters
        self.alpha = config.q_learning_rate
        self.gamma = config.q_discount
        self.epsilon = config.q_epsilon_start
        self.epsilon_end = config.q_epsilon_end
        self.epsilon_decay = config.q_epsilon_decay

        # Q-tables: node_id → {neighbor_id: Q-value}
        # Special key 'BS' for direct-to-BS transmission
        self.q_tables: Dict[int, Dict] = defaultdict(
            lambda: defaultdict(lambda: 0.0)
        )

        # CH election tracking (same as EE-LEACH)
        self.epoch_length = int(1.0 / config.ch_percentage)
        self.was_ch_this_epoch = set()

    def reset_q_tables(self):
        """Reset Q-tables for new experiment run."""
        self.q_tables = defaultdict(lambda: defaultdict(lambda: 0.0))
        self.epsilon = self.config.q_epsilon_start
        self.was_ch_this_epoch.clear()

    def setup_phase(self, network: Network, round_num: int) -> None:
        """Energy-weighted CH election (same as EE-LEACH)."""
        p = self.config.ch_percentage
        alive = network.alive_nodes()

        if not alive:
            return

        if round_num % self.epoch_length == 0:
            self.was_ch_this_epoch.clear()

        eligible = [n for n in alive if n.id not in self.was_ch_this_epoch]
        if not eligible:
            self.was_ch_this_epoch.clear()
            eligible = alive

        r_mod = round_num % self.epoch_length
        denom = 1.0 - p * (r_mod % (1.0 / p) if p > 0 else 0)
        if denom <= 0:
            denom = 1e-6
        base_threshold = p / denom

        for node in eligible:
            energy_factor = node.energy_fraction()
            threshold = base_threshold * energy_factor
            if self.rng.random() < threshold:
                node.is_ch = True
                node.rounds_as_ch += 1
                node.last_ch_round = round_num
                self.was_ch_this_epoch.add(node.id)

        if not network.cluster_heads() and alive:
            best = max(alive, key=lambda n: n.energy)
            best.is_ch = True
            best.rounds_as_ch += 1
            best.last_ch_round = round_num
            self.was_ch_this_epoch.add(best.id)

        self.form_clusters(network)

    def select_next_hop_q(self, source: Node, candidate_chs: List[Node],
                          bs: Tuple[float, float]) -> Tuple:
        """
        Select next hop using ε-greedy Q-learning.

        Parameters
        ----------
        source : Node
            Current transmitting CH.
        candidate_chs : List[Node]
            Available next-hop CHs.
        bs : Tuple[float, float]
            Base station coordinates.

        Returns
        -------
        Tuple[target, distance]
            (Node or 'BS', hop_distance)
        """
        q_table = self.q_tables[source.id]
        source_dist_bs = source.distance_to(bs)

        # Build action set: neighboring CHs closer to BS + direct BS
        actions = []
        for ch in candidate_chs:
            if ch.id == source.id or not ch.alive:
                continue
            d = source.distance_to(ch)
            if d <= self.config.tx_range and ch.distance_to(bs) < source_dist_bs:
                actions.append((ch, d))

        # Direct to BS if in range
        if source_dist_bs <= self.config.tx_range:
            actions.append(('BS', source_dist_bs))

        if not actions:
            # No valid actions — must go direct to BS
            return ('BS', source_dist_bs)

        # ε-greedy action selection
        if self.rng.random() < self.epsilon:
            # Explore: random action
            idx = self.rng.integers(0, len(actions))
            return actions[idx]
        else:
            # Exploit: action with lowest Q-value (cost)
            best_action = None
            best_q = float('inf')
            for target, dist in actions:
                key = 'BS' if target == 'BS' else target.id
                q_val = q_table[key]
                if q_val < best_q:
                    best_q = q_val
                    best_action = (target, dist)
            return best_action if best_action else actions[0]

    def update_q_value(self, source_id: int, target, energy_cost: float,
                       next_node_chs: List[Node], bs: Tuple[float, float]):
        """
        Update Q-value after a routing decision.

        Q_x(y) ← (1-α)·Q_x(y) + α·[cost + γ · min_z Q_y(z)]

        Parameters
        ----------
        source_id : int
            ID of the node that made the decision.
        target : Node or str
            The chosen next hop.
        energy_cost : float
            Actual energy cost of the hop (Joules).
        next_node_chs : List[Node]
            Neighbors of target for computing future Q.
        bs : Tuple[float, float]
            Base station coordinates.
        """
        key = 'BS' if target == 'BS' else target.id

        # Cost: energy normalized to make Q-values manageable
        cost = energy_cost * 1e6  # convert to μJ for numerical stability

        # Future value
        if target == 'BS':
            min_future_q = 0.0  # terminal state
        else:
            # min Q-value among target's neighbors
            target_q = self.q_tables[target.id]
            future_qs = []
            target_dist_bs = target.distance_to(bs)

            for ch in next_node_chs:
                if ch.id == target.id or not ch.alive:
                    continue
                d = target.distance_to(ch)
                if d <= self.config.tx_range and ch.distance_to(bs) < target_dist_bs:
                    future_qs.append(target_q[ch.id])

            # Also consider direct to BS
            if target_dist_bs <= self.config.tx_range:
                future_qs.append(target_q['BS'])

            min_future_q = min(future_qs) if future_qs else 0.0

        # Q-update
        old_q = self.q_tables[source_id][key]
        new_q = (1 - self.alpha) * old_q + self.alpha * (cost + self.gamma * min_future_q)
        self.q_tables[source_id][key] = new_q

    def get_route(self, source_ch: Node, all_chs: List[Node],
                  bs: Tuple[float, float]) -> List:
        """
        Compute route from CH to BS using Q-learning decisions.
        Overrides base class greedy routing.
        """
        route = []
        current = source_ch
        visited = {source_ch.id}
        max_hops = 20

        for _ in range(max_hops):
            candidates = [ch for ch in all_chs
                          if ch.id not in visited and ch.alive]

            target, dist = self.select_next_hop_q(current, candidates, bs)

            if target == 'BS':
                # Q-update
                e_tx = self.energy.tx_energy(self.config.packet_size, dist)
                self.update_q_value(current.id, 'BS', e_tx, [], bs)
                route.append(('BS', dist))
                return route
            else:
                # Q-update
                e_tx = self.energy.tx_energy(self.config.packet_size, dist)
                remaining = [ch for ch in all_chs
                             if ch.id not in visited and ch.id != target.id and ch.alive]
                self.update_q_value(current.id, target, e_tx, remaining, bs)

                route.append((target, dist))
                visited.add(target.id)
                current = target

        # Max hops — direct to BS
        d = current.distance_to(bs)
        route.append(('BS', d))
        return route

    def steady_phase(self, network: Network, round_num: int) -> Dict:
        """Execute data transmission with Q-learning routing."""
        packet_bits = self.config.packet_size
        total_energy = 0.0

        # Intra-cluster
        intra_packets, intra_energy = self.transmit_intra_cluster(
            network, packet_bits
        )
        total_energy += intra_energy

        # Inter-cluster with Q-routing
        delivered, inter_energy = self.transmit_inter_cluster(
            network, packet_bits
        )
        total_energy += inter_energy

        # Decay epsilon
        self.epsilon = max(self.epsilon_end,
                           self.epsilon * self.epsilon_decay)

        # Carbon
        carbon = 0.0
        if self.carbon_mgr:
            carbon = self.carbon_mgr.compute_operational_carbon(
                total_energy, round_num
            )

        return {
            'packets_generated': intra_packets,
            'packets_delivered': delivered,
            'energy_consumed': total_energy,
            'energy_intra': intra_energy,
            'energy_inter': inter_energy,
            'carbon_emitted': carbon,
            'data_fidelity': 1.0,
            'compression_ratio': 1.0,
            'q_epsilon': self.epsilon,
        }
