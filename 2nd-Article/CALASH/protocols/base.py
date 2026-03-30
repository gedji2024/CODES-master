"""
Base Protocol Interface
=======================
Abstract base class that all routing protocols must implement.
Ensures fair comparison: identical interface, identical energy model,
identical network topology, and identical metric collection.

All protocols follow the LEACH round structure [1]:
    1. setup_phase:  CH election + cluster formation
    2. steady_phase: data collection, aggregation, routing to BS

This guarantees that performance differences between protocols
are attributable solely to their algorithmic design choices,
not to differences in simulation infrastructure.

References
----------
[1] Heinzelman, W.B., Chandrakasan, A.P. & Balakrishnan, H.
    "An Application-Specific Protocol Architecture for Wireless
    Microsensor Networks." IEEE Trans. Wireless Communications,
    vol. 1, no. 4, pp. 660-670, Oct. 2002. DOI: 10.1109/TWC.2002.804190

[2] Dietrich, I. & Dressler, F. "On the Lifetime of Wireless Sensor
    Networks." ACM Trans. Sensor Networks, 5(1), Art. 5, 2009.
    DOI: 10.1145/1464420.1464425
    (Standard lifetime definitions: first death, half-death, last death.)
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional
import numpy as np

from models.network import Network, Node
from models.energy import EnergyModel
from models.carbon import CarbonTraceManager
from models.compression import CompressiveSensing


class BaseProtocol(ABC):
    """
    Abstract base class for WSN routing protocols.

    All protocols follow the same round structure:
    1. setup_phase:  CH election + cluster formation
    2. steady_phase: data collection, compression, routing to BS
    3. Metrics returned per round for fair comparison.
    """

    def __init__(self, config, energy_model: EnergyModel,
                 carbon_mgr: CarbonTraceManager = None,
                 cs: CompressiveSensing = None):
        self.config = config
        self.energy = energy_model
        self.carbon_mgr = carbon_mgr
        self.cs = cs
        self.name = self.__class__.__name__

    @abstractmethod
    def setup_phase(self, network: Network, round_num: int) -> None:
        """
        Perform CH election and cluster formation.

        Must set node.is_ch and node.cluster_head_id for all alive nodes.

        Parameters
        ----------
        network : Network
            Current network state.
        round_num : int
            Current simulation round.
        """
        pass

    @abstractmethod
    def steady_phase(self, network: Network, round_num: int) -> Dict:
        """
        Execute data transmission phase.

        Members → CH → (multi-hop) → BS

        Must deduct energy from all participating nodes.

        Parameters
        ----------
        network : Network
            Current network state.
        round_num : int
            Current simulation round.

        Returns
        -------
        dict
            Round metrics including:
            - 'packets_generated': int
            - 'packets_delivered': int
            - 'energy_consumed': float (total Joules)
            - 'carbon_emitted': float (gCO2eq)
            - 'data_fidelity': float (1.0 - NMSE, or 1.0 if no compression)
            - 'compression_ratio': float (average ρ used)
        """
        pass

    def handle_disaster(self, network: Network, killed_ids: List[int],
                        round_num: int) -> None:
        """
        React to a disaster event. Default: do nothing (no self-healing).

        Subclasses with self-healing override this method.

        Parameters
        ----------
        network : Network
            Network state after disaster.
        killed_ids : List[int]
            IDs of nodes killed by the disaster.
        round_num : int
            Current round.
        """
        pass  # No self-healing by default

    def run_round(self, network: Network, round_num: int) -> Dict:
        """
        Execute one complete round of the protocol.

        Round structure (Heinzelman et al., 2002):
        1. Setup phase  — CH election + cluster formation
        2. Control overhead — CH advertisement, join requests, TDMA schedule
        3. Steady phase  — data transmission

        Parameters
        ----------
        network : Network
            Current network state.
        round_num : int
            Current simulation round.

        Returns
        -------
        dict
            Round metrics.
        """
        # Reset per-round state
        network.reset_round_state()
        network.refresh_alive_mask()

        # Phase 1: Setup (CH election + cluster formation)
        self.setup_phase(network, round_num)

        # Phase 1b: Control overhead energy (realistic setup cost)
        ctrl_energy = self._control_overhead(network)

        # Phase 2: Steady state (data transmission)
        metrics = self.steady_phase(network, round_num)

        # Include control overhead in total
        metrics['energy_consumed'] = metrics.get('energy_consumed', 0.0) + ctrl_energy

        # Energy breakdown for paper's stacked bar chart
        metrics['energy_control'] = ctrl_energy

        # Packets generated = all alive non-CH nodes (true demand)
        # This ensures orphaned members (no CH in range) count as dropped.
        alive_members = [n for n in network.alive_nodes() if not n.is_ch]
        metrics['packets_generated'] = len(alive_members)

        # Add standard metrics
        metrics['round'] = round_num
        metrics['alive_nodes'] = network.num_alive()
        metrics['num_chs'] = len(network.cluster_heads())

        # Per-node energy snapshot for fairness tracking
        metrics['node_energies'] = [n.energy for n in network.nodes]

        return metrics

    def _control_overhead(self, network: Network) -> float:
        """
        Deduct control overhead energy for the setup phase.

        Every clustering protocol incurs these costs per round:
        1. CH advertisement broadcast (1 control packet per CH, tx_range)
        2. Join-request from each member to its CH (1 control packet)
        3. TDMA schedule from each CH to its cluster (1 control packet)

        This is the standard Heinzelman model extended with realistic
        control overhead that penalises protocols with poor clustering.

        Returns
        -------
        float
            Total control energy consumed (Joules).
        """
        ctrl_bits = self.config.control_packet_size
        total_ctrl_energy = 0.0

        # 1. CH advertisement: each CH broadcasts at max range
        for ch in network.cluster_heads():
            e_adv = self.energy.tx_energy(ctrl_bits, self.config.tx_range)
            ch.consume_energy(e_adv)
            total_ctrl_energy += e_adv

        # 2. Member join-request: each member sends to its CH
        for ch in network.cluster_heads():
            members = network.cluster_members(ch.id)
            for member in members:
                d = member.distance_to(ch)
                e_join = self.energy.tx_energy(ctrl_bits, d)
                member.consume_energy(e_join)
                # CH receives join request
                e_rx = self.energy.rx_energy(ctrl_bits)
                ch.consume_energy(e_rx)
                total_ctrl_energy += e_join + e_rx

        # 3. TDMA schedule: each CH broadcasts schedule to members
        for ch in network.cluster_heads():
            members = network.cluster_members(ch.id)
            if members:
                # Broadcast at distance of farthest member
                max_d = max(member.distance_to(ch) for member in members)
                e_sched = self.energy.tx_energy(ctrl_bits, max_d)
                ch.consume_energy(e_sched)
                total_ctrl_energy += e_sched

        return total_ctrl_energy

    # ─── Common Helper Methods ────────────────────────────────────────

    def form_clusters(self, network: Network) -> None:
        """
        Assign each non-CH alive node to its nearest alive CH.

        Uses vectorized distance matrix lookups for speed.
        Nodes with no CH in transmission range remain unassigned
        (cluster_head_id = -1) and cannot transmit data this round.
        This makes CH placement quality directly impact PDR.
        """
        chs = network.cluster_heads()
        if not chs:
            return

        ch_ids = [ch.id for ch in chs]
        tx_range = self.config.tx_range

        for node in network.alive_nodes():
            if node.is_ch:
                node.cluster_head_id = node.id
                continue

            # Find nearest CH within transmission range using matrix lookup
            best_ch = None
            best_dist = float('inf')
            nid = node.id
            for chid in ch_ids:
                d = network._dist_matrix[nid, chid]
                if d <= tx_range and d < best_dist:
                    best_dist = d
                    best_ch = chid

            if best_ch is not None:
                node.cluster_head_id = best_ch
            else:
                # No CH in range — node is orphaned (cannot transmit)
                node.cluster_head_id = -1

        # Build cluster membership cache for fast lookups
        network.build_cluster_cache()

    def greedy_multihop_route(self, source_ch: Node, all_chs: List[Node],
                              bs: Tuple[float, float]) -> List:
        """
        Greedy geographic multi-hop routing from CH to BS via other CHs.

        At each hop, select the CH (or BS) that is closest to BS
        and closer than the current node, within transmission range.

        Parameters
        ----------
        source_ch : Node
            Starting cluster head.
        all_chs : List[Node]
            All alive cluster heads.
        bs : Tuple[float, float]
            Base station coordinates.

        Returns
        -------
        List
            Route as list of (node_or_bs, distance) tuples.
            Last element is always BS.
        """
        route = []
        current = source_ch
        current_dist_bs = current.distance_to(bs)
        visited = {source_ch.id}
        max_hops = 20  # prevent infinite loops

        for _ in range(max_hops):
            # Check if BS is directly reachable
            if current_dist_bs <= self.config.tx_range:
                route.append(('BS', current_dist_bs))
                return route

            # Find next hop: CH closer to BS and within range
            best_next = None
            best_next_dist_bs = current_dist_bs
            best_hop_dist = float('inf')

            for ch in all_chs:
                if ch.id in visited or not ch.alive:
                    continue
                hop_dist = current.distance_to(ch)
                ch_dist_bs = ch.distance_to(bs)

                if (hop_dist <= self.config.tx_range
                        and ch_dist_bs < current_dist_bs):
                    if ch_dist_bs < best_next_dist_bs:
                        best_next = ch
                        best_next_dist_bs = ch_dist_bs
                        best_hop_dist = hop_dist

            if best_next is not None:
                route.append((best_next, current.distance_to(best_next)))
                visited.add(best_next.id)
                current = best_next
                current_dist_bs = best_next_dist_bs
            else:
                # No progress possible — transmit directly to BS (expensive)
                route.append(('BS', current_dist_bs))
                return route

        # Max hops exceeded — direct to BS
        route.append(('BS', current.distance_to(bs)))
        return route

    def transmit_intra_cluster(self, network: Network,
                               packet_bits: int) -> Tuple[int, float]:
        """
        Members transmit data to their cluster heads.

        Enforces a CH capacity limit (max_members_per_ch). Members
        beyond the limit are unserved (packets dropped). This models
        TDMA slot exhaustion and penalises poor cluster balance.

        Parameters
        ----------
        network : Network
            Current network state.
        packet_bits : int
            Bits to transmit per member.

        Returns
        -------
        packets : int
            Number of packets successfully sent.
        energy : float
            Total energy consumed (Joules).
        """
        total_energy = 0.0
        packets = 0
        max_members = getattr(self.config, 'max_members_per_ch', 30)

        for ch in network.cluster_heads():
            members = network.cluster_members(ch.id)
            # Sort by distance (closest first) to model TDMA slot priority
            members_sorted = sorted(members, key=lambda m: m.distance_to(ch))
            served = 0
            for member in members_sorted:
                if served >= max_members:
                    break  # CH capacity exceeded — packet dropped
                d = member.distance_to(ch)
                # Member: sense + transmit
                e_member = self.energy.total_member_cost(packet_bits, d)
                if member.consume_energy(e_member):
                    # CH: receive
                    e_rx = self.energy.rx_energy(packet_bits)
                    ch.consume_energy(e_rx)
                    total_energy += e_member + e_rx
                    packets += 1
                    member.packets_sent += 1
                    ch.packets_received += 1
                    served += 1
                else:
                    total_energy += e_member

        return packets, total_energy

    def transmit_inter_cluster(self, network: Network,
                               packet_bits: int) -> Tuple[int, float]:
        """
        CHs route aggregated data to BS via multi-hop.

        Parameters
        ----------
        network : Network
            Current network state.
        packet_bits : int
            Bits in aggregated packet.

        Returns
        -------
        packets_delivered : int
            Number of *member packets* that reached BS
            (= sum of cluster sizes for successful CH deliveries).
        energy : float
            Total energy consumed (Joules).
        """
        total_energy = 0.0
        delivered_member_packets = 0
        all_chs = network.cluster_heads()

        for ch in list(all_chs):  # copy list since CHs may die during routing
            if not ch.alive:
                continue

            # Use actual received packets (from intra-cluster), not total members
            num_received = ch.packets_received
            if num_received == 0:
                continue

            # Data aggregation at CH
            e_agg = self.energy.da_energy(packet_bits, num_received)
            if not ch.consume_energy(e_agg):
                total_energy += e_agg
                continue
            total_energy += e_agg

            # Route to BS
            route = self.get_route(ch, all_chs, network.bs)

            # Transmit along route
            current_node = ch
            success = True
            for hop_target, hop_dist in route:
                e_tx = self.energy.tx_energy(packet_bits, hop_dist)
                if not current_node.consume_energy(e_tx):
                    total_energy += e_tx
                    success = False
                    break
                total_energy += e_tx

                if hop_target == 'BS':
                    # Reached BS
                    break
                else:
                    # Relay node receives and forwards
                    e_rx = self.energy.rx_energy(packet_bits)
                    if not hop_target.consume_energy(e_rx):
                        total_energy += e_rx
                        success = False
                        break
                    total_energy += e_rx
                    current_node = hop_target

            if success:
                delivered_member_packets += num_received
                ch.packets_sent += 1

        return delivered_member_packets, total_energy

    def get_route(self, source_ch: Node, all_chs: List[Node],
                  bs: Tuple[float, float]) -> List:
        """
        Compute route from CH to BS. Default: greedy geographic.
        Subclasses override for intelligent routing.
        """
        return self.greedy_multihop_route(source_ch, all_chs, bs)
