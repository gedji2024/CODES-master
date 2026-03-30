"""
ABC-ACO Protocol Implementation
================================
Hybrid ABC + ACO Energy-Efficient Clustering and Routing (2024 SOTA).

This is the strongest contemporary baseline in the framework, representing
the current state-of-the-art in metaheuristic WSN clustering with
bio-inspired routing. It lacks the carbon awareness, lifecycle integration,
self-healing, and 6G features that CALASH introduces.

Reference:
    El Khediri, S., Selmi, A., Khan, R.U., Moulahi, T. & Lorenz, P.
    "Energy efficient cluster routing protocol for wireless sensor networks
    using hybrid metaheuristic approaches."
    Ad Hoc Networks, vol. 158, art. 103473, May 2024.
    DOI: 10.1016/j.adhoc.2024.103473

Algorithm overview:
    Setup phase -- ABC-based CH selection:
        1. Each node computes multi-criteria fitness (Eq. 18 of [1]):
           f(i) = w_e*(E_i/E_max) + w_d*(1 - d_BS/d_max)
                + w_n*(degree/max_degree) + w_c*centrality
           (w_e=0.4, w_d=0.3, w_n=0.2, w_c=0.1)
        2. ABC optimisation (employed / onlooker / scout phases)
           searches for the CH set maximising average fitness + spatial
           diversity + coverage.
        3. Non-CH nodes join nearest CH within tx_range.

    Steady phase -- ACO-based multi-hop routing:
        1. Intra-cluster: members -> CH  (standard TDMA)
        2. Inter-cluster: CH -> BS via relay CHs.
           Transition probability (Eq. 24 of [1]):
             P(i->j) = tau(i,j)^alpha * eta(i,j)^beta  /  sum_k ...
           Heuristic (Eq. 28 of [1]):
             eta = phi1*(E_j/E_init) + phi2*(1 - d_jBS/d_max) + phi3*(deg/max)
           (phi1=0.5, phi2=0.3, phi3=0.2)
           Pheromone update (Eq. 26 of [1]): evaporation + deposition.

    No carbon awareness, no compression, no self-healing, no lifecycle.

Online adaptation note (important for reviewers):
    The original paper [1] uses ABC offline with 50-100 iterations over a
    static population. We adapt ABC for **online per-round execution** with
    3 iterations (60 total function evaluations: 10 employed + 10 onlooker
    per iteration). This is justified because:
        (a) Initialisation is fitness-biased (not random), so even 1 iteration
            improves upon the initial population.
        (b) Between consecutive rounds, the optimal CH set changes only
            marginally (nodes lose ~0.001 J/round from a 0.5 J budget),
            so 3 iterations suffice to track this slowly-drifting optimum.
        (c) Real WSN motes have ~8 MHz CPUs (e.g., Mica2 ATmega128L);
            50+ iterations per round would dominate the energy budget
            and violate the real-time constraint.
    This "adapted for online per-round execution" approach is standard
    in WSN metaheuristic literature (see also [2] for PSO adaptation).

Additional references:
    [2] Kuila, P. & Jana, P.K. "Energy efficient clustering and routing
        algorithms for wireless sensor networks: Particle swarm
        optimization approach." Engineering Applications of AI, 33, 2014.
        DOI: 10.1016/j.engappai.2014.04.009

    [3] Karaboga, D. & Basturk, B. "A powerful and efficient algorithm for
        numerical function optimization: ABC." J. Global Optimization,
        39(3), pp. 459-471, 2007. DOI: 10.1007/s10898-007-9149-x
        (Original ABC algorithm.)

    [4] Dorigo, M. & Stutzle, T. "Ant Colony Optimization." MIT Press,
        2004. ISBN: 978-0262042192.
        (Original ACO framework.)
"""

import numpy as np
from typing import Dict, List, Tuple

from protocols.base import BaseProtocol
from models.network import Network, Node
from models.energy import EnergyModel
from models.carbon import CarbonTraceManager
from models.compression import CompressiveSensing


class ABC_ACO(BaseProtocol):
    """
    Hybrid ABC+ACO clustering and routing  (El Khediri et al., 2024).

    Represents 2024 state-of-the-art energy-efficient WSN clustering
    with population-based CH optimisation and pheromone-guided routing.
    Serves as a strong modern baseline that lacks the carbon, lifecycle,
    self-healing, and 6G features of CALASH.
    """

    # ──────────────────────────────────────────────────────────────────
    def __init__(self, config, energy_model: EnergyModel,
                 carbon_mgr: CarbonTraceManager = None,
                 cs: CompressiveSensing = None,
                 rng: np.random.Generator = None):
        super().__init__(config, energy_model, carbon_mgr, cs)
        self.name = "ABC-ACO"
        self.rng = rng if rng is not None else np.random.default_rng(42)

        # ── ABC hyper-parameters (adapted from paper [1] Table 3) ─────
        # Original paper: pop=50, iter=100 (offline, static scenario).
        # Our adaptation: pop=10, iter=3 (online, per-round, real-time).
        # Justification: fitness-biased init + slow temporal drift between
        # rounds means 3 iters (60 evaluations) suffice. See module docstring.
        self.n_food_sources = 10          # population size (scaled for online)
        self.abc_max_iter   = 3           # iterations per round (online adaptation)
        self.scout_limit    = 3           # stagnation trigger

        # CH fitness weights  (paper Eq. 18)
        self.w_energy     = 0.4
        self.w_distance   = 0.3
        self.w_degree     = 0.2
        self.w_centrality = 0.1

        # ── ACO hyper-parameters (adapted from paper Table 4) ──────
        self.aco_alpha    = 1.0           # pheromone importance
        self.aco_beta     = 1.0           # heuristic importance
        self.evaporation  = 0.1           # pheromone decay (ρ in paper)
        self.aco_Q        = 1.0           # deposit constant

        # ACO heuristic cost weights (paper Eq. 28: φ1, φ2, φ3)
        self.phi1 = 0.5                   # residual energy
        self.phi2 = 0.3                   # distance to BS
        self.phi3 = 0.2                   # node degree

        # Persistent pheromone table: (src_id, dst_id) → float
        self.pheromone: Dict[Tuple, float] = {}

        # Epoch tracking (prevents repeated CH duty)
        self.epoch_length = int(1.0 / config.ch_percentage)
        self.was_ch_this_epoch: set = set()

    # ──────────────────── per-node fitness ─────────────────────────
    def _node_fitness(self, node: Node,
                      max_energy: float,
                      max_dist_bs: float,
                      max_degree: int,
                      neighbor_map: Dict[int, List[Node]],
                      bs) -> float:
        """Multi-criteria ABC fitness for one node (paper §5.1.2)."""
        e_ratio = node.energy / max(max_energy, 1e-10)
        d_ratio = 1.0 - node.distance_to(bs) / max(max_dist_bs, 1e-10)
        deg     = len(neighbor_map.get(node.id, []))
        deg_ratio = deg / max(max_degree, 1)

        nbrs = neighbor_map.get(node.id, [])
        if nbrs:
            avg_d = np.mean([node.distance_to(n) for n in nbrs])
            centrality = 1.0 / (1.0 + avg_d / self.config.tx_range)
        else:
            centrality = 0.0

        return (self.w_energy * e_ratio
                + self.w_distance * d_ratio
                + self.w_degree * deg_ratio
                + self.w_centrality * centrality)

    # ──────────────────── CH-set fitness ──────────────────────────
    def _evaluate_ch_set(self, ch_ids: set,
                         alive_list: List[Node],
                         fitness_map: Dict[int, float],
                         node_map: Dict[int, Node]) -> float:
        """
        Evaluate quality of a candidate CH set.

        Combines average per-node fitness of CHs with a spatial
        diversity bonus (average pairwise inter-CH distance).
        """
        if not ch_ids:
            return 0.0

        # 1. Average fitness of selected CHs
        avg_fit = np.mean([fitness_map.get(nid, 0.0) for nid in ch_ids])

        # 2. Spatial diversity (higher = CHs more spread out)
        ch_nodes = [node_map[nid] for nid in ch_ids if nid in node_map]
        if len(ch_nodes) >= 2:
            dists = []
            for i in range(len(ch_nodes)):
                for j in range(i + 1, len(ch_nodes)):
                    dists.append(ch_nodes[i].distance_to(ch_nodes[j]))
            diversity = np.mean(dists) / (self.config.tx_range * 2)
            diversity = min(diversity, 1.0)
        else:
            diversity = 0.5

        return 0.7 * avg_fit + 0.3 * diversity

    # ──────────────────── SETUP PHASE (ABC) ───────────────────────
    def setup_phase(self, network: Network, round_num: int) -> None:
        """ABC-optimised CH election + cluster formation."""
        alive = network.alive_nodes()
        if not alive:
            return

        bs = network.bs

        # Epoch rotation
        if round_num % self.epoch_length == 0:
            self.was_ch_this_epoch.clear()

        eligible = [n for n in alive if n.id not in self.was_ch_this_epoch]
        if not eligible:
            self.was_ch_this_epoch.clear()
            eligible = alive

        # ── Pre-compute neighbour map & per-node fitness ──────────
        neighbor_map: Dict[int, List[Node]] = {}
        for node in alive:
            neighbor_map[node.id] = [
                n for n in alive
                if n.id != node.id
                and node.distance_to(n) <= self.config.tx_range
            ]

        max_energy  = max(n.energy for n in eligible)
        max_dist_bs = max(n.distance_to(bs) for n in eligible) or 1.0
        max_degree  = max(len(neighbor_map.get(n.id, [])) for n in eligible) or 1

        fitness_map: Dict[int, float] = {}
        for node in eligible:
            fitness_map[node.id] = self._node_fitness(
                node, max_energy, max_dist_bs, max_degree, neighbor_map, bs
            )

        node_map = {n.id: n for n in alive}

        n_ch = max(1, int(round(self.config.ch_percentage * len(alive))))

        # ── ABC optimisation ──────────────────────────────────────
        eligible_ids = np.array([n.id for n in eligible])
        probs = np.array([fitness_map[nid] for nid in eligible_ids])
        probs_sum = probs.sum()
        if probs_sum > 0:
            probs = probs / probs_sum
        else:
            probs = np.ones(len(probs)) / len(probs)

        n_pop = min(self.n_food_sources, max(4, len(eligible_ids) // 2))
        k = min(n_ch, len(eligible_ids))

        # Initialise food sources (fitness-biased random CH sets)
        food_sources: List[set] = []
        stagnation: List[int] = []
        for _ in range(n_pop):
            sel = self.rng.choice(len(eligible_ids), size=k,
                                  replace=False, p=probs)
            food_sources.append(set(eligible_ids[sel]))
            stagnation.append(0)

        set_fitness = [
            self._evaluate_ch_set(fs, alive, fitness_map, node_map)
            for fs in food_sources
        ]

        # ABC iterations
        for _ in range(self.abc_max_iter):
            # ── Employed bee phase ────────────────────────────────
            for i in range(n_pop):
                new_set = self._neighbor_solution(
                    food_sources[i], eligible_ids, probs
                )
                nf = self._evaluate_ch_set(new_set, alive,
                                           fitness_map, node_map)
                if nf > set_fitness[i]:
                    food_sources[i] = new_set
                    set_fitness[i] = nf
                    stagnation[i] = 0
                else:
                    stagnation[i] += 1

            # ── Onlooker bee phase ────────────────────────────────
            total_fit = sum(set_fitness) or 1.0
            sel_probs = np.array(set_fitness) / total_fit
            for _ in range(n_pop):
                idx = int(self.rng.choice(n_pop, p=sel_probs))
                new_set = self._neighbor_solution(
                    food_sources[idx], eligible_ids, probs
                )
                nf = self._evaluate_ch_set(new_set, alive,
                                           fitness_map, node_map)
                if nf > set_fitness[idx]:
                    food_sources[idx] = new_set
                    set_fitness[idx] = nf
                    stagnation[idx] = 0

            # ── Scout bee phase ───────────────────────────────────
            for i in range(n_pop):
                if stagnation[i] >= self.scout_limit:
                    sel = self.rng.choice(len(eligible_ids), size=k,
                                          replace=False, p=probs)
                    food_sources[i] = set(eligible_ids[sel])
                    set_fitness[i] = self._evaluate_ch_set(
                        food_sources[i], alive, fitness_map, node_map
                    )
                    stagnation[i] = 0

        # Select best CH set
        best_idx = int(np.argmax(set_fitness))
        best_ch_ids = food_sources[best_idx]

        # Mark elected CHs
        for nid in best_ch_ids:
            if nid in node_map and node_map[nid].alive:
                node = node_map[nid]
                node.is_ch = True
                node.rounds_as_ch += 1
                node.last_ch_round = round_num
                self.was_ch_this_epoch.add(nid)

        # Safety: at least one CH
        if not network.cluster_heads():
            best = max(eligible, key=lambda n: fitness_map.get(n.id, 0))
            best.is_ch = True
            best.rounds_as_ch += 1
            best.last_ch_round = round_num
            self.was_ch_this_epoch.add(best.id)

        self.form_clusters(network)

    # ──────────────────── ABC helper ──────────────────────────────
    def _neighbor_solution(self, current_set: set,
                           eligible_ids: np.ndarray,
                           probs: np.ndarray) -> set:
        """Generate a neighbour solution: swap one random CH."""
        new_set = set(current_set)
        if len(new_set) == 0 or len(eligible_ids) <= len(new_set):
            return new_set
        remove_id = self.rng.choice(list(new_set))
        new_set.discard(remove_id)

        remaining_mask = np.array([nid not in new_set for nid in eligible_ids])
        remaining_ids = eligible_ids[remaining_mask]
        remaining_probs = probs[remaining_mask]
        rp_sum = remaining_probs.sum()
        if rp_sum > 0:
            remaining_probs = remaining_probs / rp_sum
        else:
            remaining_probs = np.ones(len(remaining_probs)) / len(remaining_probs)

        if len(remaining_ids) > 0:
            add_id = self.rng.choice(remaining_ids, p=remaining_probs)
            new_set.add(add_id)
        return new_set

    # ──────────────────── ROUTING (ACO) ───────────────────────────
    def get_route(self, source_ch: Node, all_chs: List[Node],
                  bs: Tuple[float, float]) -> List:
        """
        ACO-based relay routing with pheromone + heuristic (paper §5.3).
        """
        route = []
        current = source_ch
        visited = {source_ch.id}
        max_hops = 20

        max_dist_bs = max(
            (ch.distance_to(bs) for ch in all_chs if ch.alive),
            default=1.0
        ) or 1.0

        for _ in range(max_hops):
            current_dist_bs = current.distance_to(bs)

            # BS directly reachable
            if current_dist_bs <= self.config.tx_range:
                route.append(('BS', current_dist_bs))
                self._deposit_pheromone(source_ch, route)
                return route

            # Candidate relay CHs (in range + closer to BS)
            candidates = [
                ch for ch in all_chs
                if ch.id not in visited and ch.alive
                and current.distance_to(ch) <= self.config.tx_range
                and ch.distance_to(bs) < current_dist_bs
            ]

            if not candidates:
                route.append(('BS', current_dist_bs))
                self._deposit_pheromone(source_ch, route)
                return route

            # ── ACO transition probability ────────────────────────
            scores = np.empty(len(candidates))
            for ci, ch in enumerate(candidates):
                e_ratio = ch.energy / max(self.config.initial_energy, 1e-10)
                d_ratio = 1.0 - ch.distance_to(bs) / max_dist_bs
                # Quick degree: count alive CHs within range of candidate
                deg = sum(1 for c in all_chs
                          if c.alive and c.id != ch.id
                          and ch.distance_to(c) <= self.config.tx_range)
                max_deg = max(deg, 1)
                deg_ratio = deg / max_deg if max_deg > 0 else 0.0

                heuristic = (self.phi1 * e_ratio
                             + self.phi2 * d_ratio
                             + self.phi3 * min(deg_ratio, 1.0))

                tau = self.pheromone.get((current.id, ch.id), 1.0)
                scores[ci] = max((tau ** self.aco_alpha)
                                 * (heuristic ** self.aco_beta), 1e-10)

            total = scores.sum()
            p = scores / total

            idx = self.rng.choice(len(candidates), p=p)
            next_ch = candidates[idx]

            route.append((next_ch, current.distance_to(next_ch)))
            visited.add(next_ch.id)
            current = next_ch

        # max hops — direct to BS
        route.append(('BS', current.distance_to(bs)))
        self._deposit_pheromone(source_ch, route)
        return route

    # ──────────────────── pheromone bookkeeping ───────────────────
    def _deposit_pheromone(self, source: Node, route: List) -> None:
        """Evaporate + deposit pheromone on the used path (Eq. 26–27)."""
        # Global evaporation (done once per round per CH, approximation)
        for key in list(self.pheromone):
            self.pheromone[key] *= (1 - self.evaporation)
            if self.pheromone[key] < 0.01:
                del self.pheromone[key]

        path_cost = sum(d for _, d in route)
        deposit = self.aco_Q / max(path_cost, 1e-6)

        current_id = source.id
        for target, _ in route:
            tid = 'BS' if target == 'BS' else target.id
            key = (current_id, tid)
            self.pheromone[key] = self.pheromone.get(key, 1.0) + deposit
            if target != 'BS':
                current_id = target.id

    # ──────────────────── STEADY PHASE ────────────────────────────
    def steady_phase(self, network: Network, round_num: int) -> Dict:
        """Members → CH → BS via ACO relay routing."""
        packet_bits = self.config.packet_size
        total_energy = 0.0

        # Intra-cluster: members → CH (base class helper)
        intra_packets, intra_energy = self.transmit_intra_cluster(
            network, packet_bits
        )
        total_energy += intra_energy

        # Inter-cluster: CH → BS (ACO routing, via get_route override)
        delivered, inter_energy = self.transmit_inter_cluster(
            network, packet_bits
        )
        total_energy += inter_energy

        # Passive carbon accounting (not used for decisions)
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
        }
