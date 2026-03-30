"""
EERP Protocol Implementation
==============================
Energy-Efficient Routing Protocol for Wireless Sensor Networks.

A representative energy-and-distance-aware clustering baseline that:
    - Elects CHs using a joint residual-energy × distance metric
    - Uses relay nodes for inter-cluster multi-hop routing
    - Balances energy consumption through cost-based CH competition

Key differences from LEACH/HEED:
    - CH election combines energy + distance to BS (not just energy)
    - Relay selection minimises (energy_cost × hop_count) jointly
    - Better-balanced clusters due to distance-weighted join

This is a representative energy-efficiency baseline implementing the
standard energy-distance joint metric found in the WSN routing
literature (e.g., Biswas et al., 2018; Pantazis et al., 2013).
No carbon or disaster awareness.

References
----------
[1] Biswas, S., Das, R. & Chatterjee, P. "Energy-Efficient Connected
    Target Coverage in Multi-Hop Wireless Sensor Networks."
    In: Industry Interactive Innovations in Science, Engineering and
    Technology, Springer, 2018. DOI: 10.1007/978-981-10-3953-9_40

[2] Pantazis, N.A., Nikolidakis, S.A. & Vergados, D.D. "Energy-Efficient
    Routing Protocols in Wireless Sensor Networks: A Survey."
    IEEE Comm. Surveys & Tutorials, 15(2), pp. 551-591, 2013.
    DOI: 10.1109/SURV.2012.062612.00084
"""

import numpy as np
from typing import Dict, List, Tuple

from protocols.base import BaseProtocol
from models.network import Network, Node
from models.energy import EnergyModel
from models.carbon import CarbonTraceManager
from models.compression import CompressiveSensing


class EERP(BaseProtocol):
    """
    EERP: Energy-Efficient Routing Protocol.

    CH election: nodes compute a competition score
        score(i) = alpha * (E_i / E_max) + (1-alpha) * (1 - d_BS_i / d_BS_max)
    and self-elect as CH if score exceeds a threshold.
    The node with the highest score in its neighbourhood wins.

    Relay selection: CHs choose next-hop relay among neighbour CHs
    to minimise a cost function:
        cost(j) = beta * e_tx(d_ij) + (1-beta) * d_jBS / d_BS_max

    This represents 2019 state-of-the-art: energy + distance balanced
    CH election, but NO carbon awareness, no compression, no self-healing.
    """

    def __init__(self, config, energy_model: EnergyModel,
                 carbon_mgr: CarbonTraceManager = None,
                 cs: CompressiveSensing = None,
                 rng: np.random.Generator = None):
        super().__init__(config, energy_model, carbon_mgr, cs)
        self.name = "EERP"
        self.rng = rng if rng is not None else np.random.default_rng(42)
        # EERP parameters
        self.alpha = 0.6       # weight for energy in CH election (paper default)
        self.beta_relay = 0.5  # weight for energy cost in relay selection
        self.epoch_length = int(1.0 / config.ch_percentage)
        self.was_ch_this_epoch = set()

    def setup_phase(self, network: Network, round_num: int) -> None:
        """
        EERP CH election: score = alpha*(E/Emax) + (1-alpha)*(1-d/dmax).

        Neighbourhood competition: only the highest-scoring node among
        its one-hop neighbours becomes CH.
        """
        alive = network.alive_nodes()
        if not alive:
            return

        # Reset epoch
        if round_num % self.epoch_length == 0:
            self.was_ch_this_epoch.clear()

        eligible = [n for n in alive if n.id not in self.was_ch_this_epoch]
        if not eligible:
            self.was_ch_this_epoch.clear()
            eligible = alive

        # Compute competition score for each eligible node
        max_energy = max(n.energy for n in eligible)
        max_dist_bs = max(n.distance_to(network.bs) for n in eligible)
        if max_dist_bs == 0:
            max_dist_bs = 1.0

        scores = {}
        for node in eligible:
            e_ratio = node.energy / max(max_energy, 1e-10)
            d_ratio = 1.0 - node.distance_to(network.bs) / max_dist_bs
            scores[node.id] = self.alpha * e_ratio + (1 - self.alpha) * d_ratio

        # Desired number of CHs
        desired = max(1, int(round(self.config.ch_percentage * len(alive))))

        # Competition radius: smaller than tx_range to allow more CH winners
        # in dense networks. Follows EERP paper's spirit of local competition.
        comp_radius = self.config.tx_range * 0.4

        # Competitive CH election: neighbourhood-best wins
        elected = set()
        for node in eligible:
            # Only compete within competition radius (not full tx_range)
            nbrs = [n for n in network.alive_neighbors(node.id)
                    if node.distance_to(n) <= comp_radius]
            is_best = True
            for nb in nbrs:
                if nb.id in scores and scores.get(nb.id, 0) > scores[node.id]:
                    is_best = False
                    break
                # Tie-break by ID
                if (nb.id in scores
                        and scores.get(nb.id, 0) == scores[node.id]
                        and nb.id < node.id):
                    is_best = False
                    break
            if is_best:
                elected.add(node.id)

        # Limit to 2× desired CH count (soft cap)
        if len(elected) > desired * 2:
            sorted_elected = sorted(elected, key=lambda nid: scores[nid],
                                    reverse=True)
            elected = set(sorted_elected[:desired * 2])

        # Ensure at least one CH
        if not elected:
            best = max(eligible, key=lambda n: scores.get(n.id, 0))
            elected.add(best.id)

        # Mark CHs
        node_map = {n.id: n for n in alive}
        for nid in elected:
            node = node_map[nid]
            node.is_ch = True
            node.rounds_as_ch += 1
            node.last_ch_round = round_num
            self.was_ch_this_epoch.add(nid)

        # Form clusters (distance-weighted join, same as base)
        self.form_clusters(network)

    def get_route(self, source_ch: Node, all_chs: List[Node],
                  bs: Tuple[float, float]) -> List:
        """
        EERP relay selection: minimise cost = beta*e_tx + (1-beta)*d_bs_norm.

        This is the energy-distance joint optimisation from the paper.
        Falls back to direct BS transmission if no good relay exists.
        """
        route = []
        current = source_ch
        visited = {source_ch.id}
        max_hops = 20
        packet_bits = self.config.packet_size

        max_dist_bs = max(
            (ch.distance_to(bs) for ch in all_chs if ch.alive),
            default=1.0
        )
        if max_dist_bs == 0:
            max_dist_bs = 1.0

        for _ in range(max_hops):
            current_dist_bs = current.distance_to(bs)

            # BS reachable directly
            if current_dist_bs <= self.config.tx_range:
                route.append(('BS', current_dist_bs))
                return route

            # Find relay with minimum cost
            best_next = None
            best_cost = float('inf')
            best_dist = 0.0

            for ch in all_chs:
                if ch.id in visited or not ch.alive:
                    continue
                hop_dist = current.distance_to(ch)
                ch_dist_bs = ch.distance_to(bs)

                # Must be in range AND closer to BS (progress guarantee)
                if hop_dist > self.config.tx_range or ch_dist_bs >= current_dist_bs:
                    continue

                # EERP cost function
                e_tx = self.energy.tx_energy(packet_bits, hop_dist)
                d_norm = ch_dist_bs / max_dist_bs
                cost = self.beta_relay * e_tx + (1 - self.beta_relay) * d_norm

                if cost < best_cost:
                    best_cost = cost
                    best_next = ch
                    best_dist = hop_dist

            if best_next is not None:
                route.append((best_next, best_dist))
                visited.add(best_next.id)
                current = best_next
            else:
                # No progress — direct to BS
                route.append(('BS', current_dist_bs))
                return route

        route.append(('BS', current.distance_to(bs)))
        return route

    def steady_phase(self, network: Network, round_num: int) -> Dict:
        """Execute data transmission: members→CH→BS via relay routing."""
        packet_bits = self.config.packet_size
        total_energy = 0.0

        # Intra-cluster: members → CH
        intra_packets, intra_energy = self.transmit_intra_cluster(
            network, packet_bits
        )
        total_energy += intra_energy

        # Inter-cluster: CH → BS (EERP relay routing)
        delivered, inter_energy = self.transmit_inter_cluster(
            network, packet_bits
        )
        total_energy += inter_energy

        # Carbon accounting (tracked but not used for decisions)
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
            'data_fidelity': 1.0,  # No compression in EERP
            'compression_ratio': 1.0,
        }
