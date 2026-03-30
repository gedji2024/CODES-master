"""
HEED Protocol Implementation
=============================
Hybrid Energy-Efficient Distributed Clustering (Younis & Fahmy, 2004).

A distributed clustering algorithm that considers both residual energy
and intra-cluster communication cost for CH election.

Key differences from LEACH:
    - CH election is iterative (multiple rounds of competition)
    - Uses both residual energy AND communication cost
    - Does not require global knowledge of network
    - Terminates in O(1) iterations

Reference:
    Younis, O. & Fahmy, S. "HEED: A Hybrid, Energy-Efficient, Distributed
    Clustering Approach for Ad-hoc Sensor Networks." IEEE Trans. Mobile
    Computing, 3(4), 2004. doi:10.1109/TMC.2004.41
"""

import numpy as np
from typing import Dict, List

from protocols.base import BaseProtocol
from models.network import Network, Node
from models.energy import EnergyModel
from models.carbon import CarbonTraceManager
from models.compression import CompressiveSensing


class HEED(BaseProtocol):
    """
    HEED: Hybrid Energy-Efficient Distributed Clustering.

    CH election uses two parameters:
        1. C_prob: based on residual energy (primary)
        2. AMRP: Average Minimum Reachability Power (secondary)

    Iterative probabilistic election terminates in O(1) rounds.
    Uses multi-hop routing to BS (same as other baselines).

    Reference: Younis & Fahmy, IEEE TMC, 2004.
    """

    def __init__(self, config, energy_model: EnergyModel,
                 carbon_mgr: CarbonTraceManager = None,
                 cs: CompressiveSensing = None,
                 rng: np.random.Generator = None):
        super().__init__(config, energy_model, carbon_mgr, cs)
        self.name = "HEED"
        self.rng = rng if rng is not None else np.random.default_rng(42)
        self.c_prob_init = max(config.ch_percentage, 0.05)  # initial CH prob
        self.n_iter = 8  # max HEED iterations (convergence guarantee)

    def setup_phase(self, network: Network, round_num: int) -> None:
        """
        HEED iterative CH election (Younis & Fahmy, IEEE TMC 2004).

        Phase 1: Each node computes CH_prob = C_prob × (E_residual / E_max).
        Phase 2: Iterative competition — in each iteration every
                 non-finalized node decides to become a tentative CH
                 with probability CH_prob.  A tentative CH is promoted
                 to *final* when its cost (AMRP) is lowest among its
                 neighbours.  CH_prob doubles each iteration.
        Phase 3: Uncovered nodes that heard no CH become forced CHs;
                 excess is pruned so #CH ≈ p × N_alive.
        """
        alive = network.alive_nodes()
        if not alive:
            return

        n_alive = len(alive)
        node_map = {n.id: n for n in alive}

        # --- 1. Initial CH probability (energy-weighted) ---
        max_energy = max(n.energy for n in alive)
        ch_prob = {}
        for node in alive:
            e_frac = node.energy / max(max_energy, 1e-10)
            ch_prob[node.id] = max(self.c_prob_init * e_frac, 1e-4)

        # --- AMRP cost: average min-power to reach neighbours ---
        # Lower cost → better CH candidate
        amrp = {}
        for node in alive:
            nbrs = network.alive_neighbors(node.id)
            if nbrs:
                dists = [node.distance_to(nb) for nb in nbrs]
                amrp[node.id] = float(np.mean(dists))
            else:
                amrp[node.id] = float('inf')

        # --- 2. Iterative competition ---
        final_chs = set()
        my_ch = {}  # node_id → CH_id it joins (or self)

        for iteration in range(self.n_iter):
            tentative_chs = set()

            for node in alive:
                if node.id in final_chs:
                    continue

                if self.rng.random() < ch_prob[node.id]:
                    tentative_chs.add(node.id)

                # Double probability for next iteration
                ch_prob[node.id] = min(ch_prob[node.id] * 2, 1.0)

            # Among tentative CHs, finalize those with lowest AMRP
            # in their neighbourhood
            for nid in tentative_chs:
                nbrs = network.alive_neighbors(nid)
                # Check if any neighbour that is also tentative has lower cost
                is_best = True
                for nb in nbrs:
                    if (nb.id in tentative_chs and nb.id != nid
                            and amrp.get(nb.id, float('inf')) < amrp[nid]):
                        is_best = False
                        break
                    # Tie-break by node id (deterministic)
                    if (nb.id in tentative_chs and nb.id != nid
                            and amrp.get(nb.id, float('inf')) == amrp[nid]
                            and nb.id < nid):
                        is_best = False
                        break
                if is_best:
                    final_chs.add(nid)

        # --- 3. Uncovered nodes → forced CH ---
        # Any alive node that has no final CH in range becomes a CH itself
        for node in alive:
            if node.id in final_chs:
                continue
            has_ch = any(
                node.distance_to(node_map[cid]) <= self.config.tx_range
                for cid in final_chs if cid in node_map
            )
            if not has_ch:
                final_chs.add(node.id)

        # --- 4. Prune excess CHs to ≈ p × N_alive ---
        desired = max(1, int(round(self.config.ch_percentage * n_alive)))
        if len(final_chs) > desired * 2:
            # Keep the *desired* CHs with highest energy (original HEED
            # spirit: favour high-energy nodes)
            ch_list = sorted(final_chs,
                             key=lambda cid: node_map[cid].energy,
                             reverse=True)
            final_chs = set(ch_list[:max(desired, 1)])

        # Ensure at least one CH
        if not final_chs:
            best = max(alive, key=lambda n: n.energy)
            final_chs.add(best.id)

        # --- 5. Mark CHs ---
        for node in alive:
            if node.id in final_chs:
                node.is_ch = True
                node.rounds_as_ch += 1
                node.last_ch_round = round_num

        self.form_clusters(network)

    def steady_phase(self, network: Network, round_num: int) -> Dict:
        """Execute data transmission: members→CH→BS via multi-hop."""
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
            'data_fidelity': 1.0,  # No compression in HEED
            'compression_ratio': 1.0,
        }
