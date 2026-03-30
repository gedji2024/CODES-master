"""
LEACH and EE-LEACH Protocol Implementations
============================================
LEACH: Low-Energy Adaptive Clustering Hierarchy (Heinzelman et al., 2000)
    - Probabilistic CH election with epoch-based rotation (Eq. 1 of [1]):
      T(n) = p / (1 - p * (r mod 1/p))  for eligible nodes
    - Two variants: single-hop (original LEACH) and multi-hop (enhanced)
    - Gold-standard baseline used in virtually all WSN clustering papers

EE-LEACH: Energy-Efficient LEACH (Bakaraniya & Mehta, 2013)
    - CH election weighted by residual energy ratio (E_i/E_0)
    - Modified threshold: T(n) = T_LEACH(n) * (E_i / E_0)
    - Extends network lifetime by distributing CH burden to high-energy nodes
    - Represents the class of energy-aware LEACH extensions surveyed in [4]

References
----------
[1] Heinzelman, W.R., Chandrakasan, A.P. & Balakrishnan, H.
    "Energy-Efficient Communication Protocol for Wireless Microsensor
    Networks." Proc. 33rd Hawaii Int. Conf. System Sciences (HICSS),
    2000, pp. 3005-3014. DOI: 10.1109/HICSS.2000.926982

[2] Heinzelman, W.B., Chandrakasan, A.P. & Balakrishnan, H. "An
    Application-Specific Protocol Architecture for Wireless Microsensor
    Networks." IEEE Trans. Wireless Communications, 1(4), pp. 660-670,
    Oct. 2002. DOI: 10.1109/TWC.2002.804190

[3] Bakaraniya, P. & Mehta, S. "K-LEACH: An Improved LEACH Protocol
    for Lifetime Improvement in WSN." Int. J. Engineering Trends and
    Technology (IJETT), 4(5), pp. 1521-1526, 2013.
"""

import numpy as np
from typing import Dict

from protocols.base import BaseProtocol
from models.network import Network, Node
from models.energy import EnergyModel
from models.carbon import CarbonTraceManager
from models.compression import CompressiveSensing


class LEACH(BaseProtocol):
    """
    LEACH protocol with multi-hop inter-cluster routing.

    CH election uses the standard probabilistic threshold:
        T(s_i) = p / (1 - p * (r mod 1/p))   if s_i ∈ G
               = 0                              otherwise

    where p = desired CH percentage, r = current round,
    and G = set of nodes not yet elected in this 1/p cycle.
    """

    def __init__(self, config, energy_model: EnergyModel,
                 carbon_mgr: CarbonTraceManager = None,
                 cs: CompressiveSensing = None,
                 rng: np.random.Generator = None):
        super().__init__(config, energy_model, carbon_mgr, cs)
        self.name = "LEACH"
        self.rng = rng if rng is not None else np.random.default_rng(42)
        # Track which nodes have been CH in the current epoch
        self.epoch_length = int(1.0 / config.ch_percentage)  # rounds per epoch
        self.was_ch_this_epoch = set()

    def setup_phase(self, network: Network, round_num: int) -> None:
        """Probabilistic CH election followed by cluster formation."""
        p = self.config.ch_percentage
        alive = network.alive_nodes()

        if not alive:
            return

        # Reset epoch tracking
        if round_num % self.epoch_length == 0:
            self.was_ch_this_epoch.clear()

        # Eligible nodes: alive and not been CH this epoch
        eligible = [n for n in alive if n.id not in self.was_ch_this_epoch]
        if not eligible:
            # All nodes have been CH — reset epoch
            self.was_ch_this_epoch.clear()
            eligible = alive

        # LEACH threshold
        r_mod = round_num % self.epoch_length
        denom = 1.0 - p * (r_mod % (1.0 / p) if p > 0 else 0)
        if denom <= 0:
            denom = 1e-6
        threshold = p / denom

        # Election
        for node in eligible:
            if self.rng.random() < threshold:
                node.is_ch = True
                node.rounds_as_ch += 1
                node.last_ch_round = round_num
                self.was_ch_this_epoch.add(node.id)

        # Ensure at least one CH
        if not network.cluster_heads() and alive:
            # Force highest-energy node as CH
            best = max(alive, key=lambda n: n.energy)
            best.is_ch = True
            best.rounds_as_ch += 1
            best.last_ch_round = round_num
            self.was_ch_this_epoch.add(best.id)

        # Form clusters
        self.form_clusters(network)

    def steady_phase(self, network: Network, round_num: int) -> Dict:
        """Execute data transmission: members→CH→BS."""
        packet_bits = self.config.packet_size
        total_energy = 0.0

        # Intra-cluster: members → CH
        intra_packets, intra_energy = self.transmit_intra_cluster(
            network, packet_bits
        )
        total_energy += intra_energy

        # Inter-cluster: CH → BS (multi-hop via greedy geographic)
        delivered, inter_energy = self.transmit_inter_cluster(
            network, packet_bits
        )
        total_energy += inter_energy

        # Carbon emissions
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
            'data_fidelity': 1.0,  # No compression in LEACH
            'compression_ratio': 1.0,
        }


class EE_LEACH(LEACH):
    """
    Energy-Efficient LEACH: CH election weighted by residual energy.

    T_EE(s_i) = T_LEACH(s_i) * (E_i(t) / E_0)

    Nodes with more remaining energy are more likely to become CHs,
    distributing the CH burden more evenly and extending network lifetime.

    Reference:
        Bakaraniya, P. & Mehta, S. "K-LEACH: An improved LEACH Protocol
        for Lifetime Improvement in WSN." Int. J. Engineering Trends and
        Technology, 4(5), 2013.
    """

    def __init__(self, config, energy_model: EnergyModel,
                 carbon_mgr: CarbonTraceManager = None,
                 cs: CompressiveSensing = None,
                 rng: np.random.Generator = None):
        super().__init__(config, energy_model, carbon_mgr, cs, rng)
        self.name = "EE-LEACH"

    def setup_phase(self, network: Network, round_num: int) -> None:
        """Energy-weighted CH election."""
        p = self.config.ch_percentage
        alive = network.alive_nodes()

        if not alive:
            return

        # Reset epoch tracking
        if round_num % self.epoch_length == 0:
            self.was_ch_this_epoch.clear()

        eligible = [n for n in alive if n.id not in self.was_ch_this_epoch]
        if not eligible:
            self.was_ch_this_epoch.clear()
            eligible = alive

        # LEACH threshold
        r_mod = round_num % self.epoch_length
        denom = 1.0 - p * (r_mod % (1.0 / p) if p > 0 else 0)
        if denom <= 0:
            denom = 1e-6
        base_threshold = p / denom

        # Energy-weighted threshold
        for node in eligible:
            energy_factor = node.energy_fraction()
            threshold = base_threshold * energy_factor
            if self.rng.random() < threshold:
                node.is_ch = True
                node.rounds_as_ch += 1
                node.last_ch_round = round_num
                self.was_ch_this_epoch.add(node.id)

        # Ensure at least one CH
        if not network.cluster_heads() and alive:
            best = max(alive, key=lambda n: n.energy)
            best.is_ch = True
            best.rounds_as_ch += 1
            best.last_ch_round = round_num
            self.was_ch_this_epoch.add(best.id)

        self.form_clusters(network)


class LEACH_SingleHop(LEACH):
    """
    Original LEACH with single-hop CH→BS routing.

    In the original Heinzelman et al. (2000) paper, CHs transmit
    aggregated data directly to BS in a single hop — no multi-hop
    relay through other CHs.

    This is the faithful original, which suffers from the "far CH"
    problem: CHs far from BS waste excessive energy on long-range TX.
    Included for completeness and fair benchmarking.

    Reference:
        Heinzelman, W.R., Chandrakasan, A. & Balakrishnan, H.
        "Energy-Efficient Communication Protocol for Wireless Microsensor
        Networks." HICSS, 2000.
    """

    def __init__(self, config, energy_model: EnergyModel,
                 carbon_mgr: CarbonTraceManager = None,
                 cs: CompressiveSensing = None,
                 rng: np.random.Generator = None):
        super().__init__(config, energy_model, carbon_mgr, cs, rng)
        self.name = "LEACH-1hop"

    def get_route(self, source_ch: Node, all_chs, bs):
        """Single-hop: always transmit directly to BS."""
        d = source_ch.distance_to(bs)
        return [('BS', d)]