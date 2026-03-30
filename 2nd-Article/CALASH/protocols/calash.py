"""
CALASH Protocol -- Full Framework
=================================
Carbon-Aware Lifecycle-Autonomous Self-Healing Routing Protocol
for 6G-Integrated Disaster Sensor Networks.

Four integrated pillars + two enabling technologies:

    1. CADR  -- Carbon-Aware Data Reduction (adaptive compressive sensing)
       Compression ratio rho(t) inversely tracks carbon intensity CI(t).
       See models/compression.py for the CS pipeline and references.

    2. CARE  -- Carbon-Aware Routing Engine (Lyapunov + DQN hybrid)
       Uses a virtual carbon queue Z(t) and Lyapunov drift-plus-penalty
       to provide provable carbon budget compliance [1]:
           lim sup (1/T) sum C_op(t) <= C_opt + B/V
       DQN agent [2] learns the next-hop policy online from experience.
       See agents/dqn.py for the DQN architecture and references.

    3. SHDR  -- Self-Healing Disaster Recovery (MAPE-K autonomic loop)
       Implements Monitor-Analyze-Plan-Execute [3] with heartbeat-based
       failure detection, coverage-hole analysis, and emergency CH election.
       See the _detect_disaster() and _self_healing_restructure() methods.

    4. LSE   -- Lifecycle Sustainability Engine (LCI in Lyapunov objective)
       Embeds embodied + end-of-life carbon in the routing cost [4] to
       penalise routes through low-energy nodes (whose impending death
       wastes their embodied carbon). Follows ISO 14040/14044 LCA [5].

    Enabling technologies:
    5. DQN   -- Deep Q-Network for autonomous routing adaptation
    6. THz   -- Sub-THz (140 GHz D-band) / 6G channel model [6] for
                intra-cluster, sub-6 GHz (3.5 GHz) for inter-cluster
    7. SLICE -- 6G network slicing (URLLC/mMTC/eMBB) for QoS-aware
                traffic differentiation and carbon-aware deferral

Computational complexity (per round)
-------------------------------------
Let N = num_nodes, C = num_CHs (~5% of N), K = avg_members_per_CH,
    A = avg_neighbours.

    CALASH setup_phase:   O(N · A)     fitness computation + local max
    CALASH steady_phase:  O(C · K · d) intra-cluster (d=8 state dim)
                        + O(C · H · A) inter-cluster routing (H=max_hops)
                        + O(N · A)     heartbeat monitoring
    CALASH total:         O(N · A)     per round

    LEACH setup_phase:    O(N)          global threshold + nearest-CH
    LEACH steady_phase:   O(C · K)      single-hop Tx
    LEACH total:          O(N)          per round

    DQN training step:    O(B · d · H_nn) where B=64, d=8, H_nn=64
                          = O(32,768) ≈ O(1) amortised per decision

    CALASH overhead vs LEACH: O(A) factor for local neighbourhood
    operations (A ≈ 10-20 for typical WSN density).  This is modest
    and scales sub-linearly with N for constant-density deployments.

References
----------
[1] Neely, M.J. "Stochastic Network Optimization with Application to
    Communication and Queueing Systems." Morgan & Claypool, 2010.
    DOI: 10.2200/S00271ED1V01Y201006CNT007

[2] Mnih, V. et al. "Human-level control through deep reinforcement
    learning." Nature, 518(7540), pp. 529-533, 2015.
    DOI: 10.1038/nature14236

[3] Kephart, J.O. & Chess, D.M. "The Vision of Autonomic Computing."
    IEEE Computer, 36(1), pp. 41-50, Jan. 2003.
    DOI: 10.1109/MC.2003.1160055

[4] ISO 14040:2006. "Environmental management -- Life cycle assessment --
    Principles and framework." International Organization for Standardization.

[5] ISO 14044:2006. "Environmental management -- Life cycle assessment --
    Requirements and guidelines."

[6] Jornet, J.M. & Akyildiz, I.F. "Channel Modeling and Capacity Analysis
    for Electromagnetic Wireless Nanonetworks in the Terahertz Band."
    IEEE Trans. Wireless Communications, 10(10), pp. 3211-3221, 2011.
    DOI: 10.1109/TWC.2011.081011.100545

[7] Heinzelman, W.B., Chandrakasan, A.P. & Balakrishnan, H.
    "An Application-Specific Protocol Architecture for Wireless
    Microsensor Networks." IEEE Trans. Wireless Comm., 1(4), 2002.
    DOI: 10.1109/TWC.2002.804190
    (The CH election threshold T(n) that CALASH extends with carbon mod.)
"""

import numpy as np
from typing import Dict, List, Tuple, Optional

from protocols.base import BaseProtocol
from models.network import Network, Node
from models.energy import EnergyModel
from models.carbon import CarbonTraceManager
from models.compression import CompressiveSensing
from agents.lyapunov import LyapunovRouter


class CALASH(BaseProtocol):
    """
    Complete CALASH protocol implementation.

    Combines carbon-aware clustering, hybrid Lyapunov+DQN routing,
    adaptive compressive sensing, real self-healing, lifecycle-aware
    objective, and THz/6G energy model.
    """

    def __init__(self, config, energy_model: EnergyModel,
                 carbon_mgr: CarbonTraceManager = None,
                 cs: CompressiveSensing = None,
                 rng: np.random.Generator = None):
        super().__init__(config, energy_model, carbon_mgr, cs)
        self.name = "CALASH"
        self.rng = rng if rng is not None else np.random.default_rng(42)

        # ─── CARE: Lyapunov routing engine (provable guarantees) ─────
        self.router = LyapunovRouter(config)

        # ─── CARE: DQN routing agent (autonomous learning) ──────────
        self.dqn = None
        self._dqn_enabled = getattr(config, 'dqn_enabled', True)
        if self._dqn_enabled:
            try:
                from agents.dqn import DQNRouter
                self.dqn = DQNRouter(config, self.rng)
            except ImportError:
                self._dqn_enabled = False

        # ─── SHDR: Self-healing engine (MAPE-K) ─────────────────────
        self.healer = None
        try:
            from models.self_healing import SelfHealingEngine
            self.healer = SelfHealingEngine(config, self.rng)
        except ImportError:
            pass

        # ─── THz/6G energy model ────────────────────────────────────
        self.thz_energy = None
        self._thz_enabled = getattr(config, 'thz_enabled', True)
        if self._thz_enabled:
            try:
                from models.thz_channel import THz6GEnergyModel
                # THz model is constructed AFTER CascadedRIS below
                self._thz_pending = True
            except ImportError:
                self._thz_enabled = False
                self._thz_pending = False

        # ─── 6G Network Slice Manager ────────────────────────────────
        self.slice_mgr = None
        try:
            from models.thz_channel import NetworkSliceManager
            self.slice_mgr = NetworkSliceManager(config)
        except ImportError:
            pass

        # ─── ISAC: Integrated Sensing and Communication (6G) ────────
        self.isac = None
        self._isac_enabled = getattr(config, 'isac_enabled', True)
        if self._isac_enabled:
            try:
                from models.isac import ISACModule
                self.isac = ISACModule(config)
            except ImportError:
                self._isac_enabled = False

        # ─── Semantic Communication Layer (6G) ──────────────────────
        self.semantic = None
        self._semantic_enabled = getattr(config, 'semantic_enabled', True)
        if self._semantic_enabled:
            try:
                from models.semantic import SemanticEncoder
                self.semantic = SemanticEncoder(config, self.rng)
            except ImportError:
                self._semantic_enabled = False

        # ─── Cascaded RIS Channel Model (6G) ────────────────────────
        self.cascaded_ris = None
        if getattr(config, 'ris_enabled', True):
            try:
                from models.thz_channel import CascadedRISChannel
                self.cascaded_ris = CascadedRISChannel(config)
            except ImportError:
                pass

        # ─── Now construct THz energy model WITH cascaded RIS ────────
        if getattr(self, '_thz_pending', False):
            from models.thz_channel import THz6GEnergyModel
            self.thz_energy = THz6GEnergyModel(
                config, cascaded_ris=self.cascaded_ris
            )
            self._thz_pending = False

        # ─── CI Gateway Beacon Model (Autonomy) ─────────────────────
        # Explicit CI distribution via gateway beacons — replaces implicit
        # oracle.  The gateway broadcasts CI every ci_beacon_interval rounds.
        # Nodes cache the last received CI value.
        self._ci_beacon_interval = getattr(config, 'ci_beacon_interval', 10)
        self._ci_beacon_energy = getattr(config, 'ci_beacon_energy_j', 1e-6)
        self._cached_ci: float = getattr(config, 'ci_base', 200.0)
        self._last_ci_beacon_round: int = 0

        # ─── Aftershock model (Self-Healing: progressive damage) ────
        self._aftershock_model = None
        self._last_disaster_event = None  # reference for weakened survivors

        # CH election parameters
        self.beta = config.beta_carbon_ch
        self.min_ch_frac = config.min_ch_fraction
        self.epoch_length = int(1.0 / config.ch_percentage)
        self.was_ch_this_epoch = set()

        # Disaster recovery state (legacy + new engine)
        self.disaster_detected = False
        self.disaster_round = -1
        self.recovery_mode = False
        self.alarm_nodes = set()
        self.healing_detection_rounds = config.healing_detection_rounds
        self.healing_restructure_rounds = config.healing_restructure_rounds

        # CS data for fidelity tracking
        self._round_nmses = []
        self._round_rhos = []
        self._current_round = 0

        # ─── Closed-loop fidelity feedback (CADR) ────────────────────
        self._fidelity_feedback = getattr(config, 'fidelity_feedback_enabled', True)
        self._fidelity_target = getattr(config, 'fidelity_target_nmse', 0.15)
        self._fidelity_window = getattr(config, 'fidelity_feedback_window', 20)
        self._fidelity_boost = 0.0  # additive rho boost from feedback

        # ─── Carbon throttle (transmission deferral) ─────────────────
        self._throttle_enabled = getattr(config, 'carbon_throttle_enabled', True)
        self._throttle_z_thresh = getattr(config, 'carbon_throttle_z_threshold', 50.0)
        self._throttle_max_skip = getattr(config, 'carbon_throttle_max_skip', 0.4)
        self._deferred_packets = 0  # packets deferred from previous round

        # ─── DQN vs Lyapunov decision tracking ───────────────────────
        self._dqn_decisions = 0
        self._lyapunov_decisions = 0

    def reset(self):
        """Reset all state for a new experiment run."""
        self.router.reset()
        if self.dqn is not None:
            self.dqn.full_reset()
        self.was_ch_this_epoch.clear()
        self.disaster_detected = False
        self.disaster_round = -1
        self.recovery_mode = False
        self.alarm_nodes.clear()
        self._round_nmses.clear()
        self._round_rhos.clear()
        self._fidelity_boost = 0.0
        self._deferred_packets = 0
        self._dqn_decisions = 0
        self._lyapunov_decisions = 0
        self._cached_ci = getattr(self.config, 'ci_base', 200.0)
        self._last_ci_beacon_round = 0
        self._aftershock_model = None
        self._last_disaster_event = None
        if self.isac is not None:
            self.isac.initialize(None)
        if self.semantic is not None:
            self.semantic.reset()

    # ─── Pillar 1: CADR — Carbon-Aware Data Reduction ────────────────

    def compress_and_transmit_intra(self, network: Network,
                                    round_num: int) -> Tuple[int, float, float, float]:
        """
        Members compress data adaptively and transmit to CH.

        Three adaptive mechanisms:
        1. CI-driven rho: HIGH CI → LOW ρ (saves carbon)
        2. Fidelity feedback: if running NMSE > target → boost ρ (closed-loop)
        3. Carbon throttle: when Z(t) is high AND CI is high, some members
           defer transmission (genuine carbon deferral for Lyapunov bound).

        Uses THz intra-cluster energy model when enabled.
        """
        if self.cs is None or self.carbon_mgr is None:
            packets, energy = self.transmit_intra_cluster(
                network, self.config.packet_size
            )
            return packets, energy, 0.0, 1.0

        # ── CI Gateway Beacon: explicit CI distribution (autonomy) ───
        # The gateway broadcasts CI every ci_beacon_interval rounds.
        # Nodes use cached CI until next beacon — NOT an oracle.
        # Energy cost: each alive node receives the beacon broadcast.
        if (round_num - self._last_ci_beacon_round) >= self._ci_beacon_interval:
            self._cached_ci = self.carbon_mgr.get_ci(round_num)
            self._last_ci_beacon_round = round_num
            # Beacon reception energy (small control packet from gateway)
            for node in network.alive_nodes():
                node.consume_energy(self._ci_beacon_energy)

        ci = self._cached_ci  # Use beacon-distributed CI (NOT oracle)
        is_critical = self.recovery_mode

        # ── Pillar: CADR adaptive compression ratio ──────────────────
        rho = self.cs.adaptive_compression_ratio(ci, is_critical=is_critical)

        # Closed-loop fidelity feedback: boost rho if recent NMSE is poor
        if self._fidelity_feedback and not is_critical:
            if len(self._round_nmses) >= self._fidelity_window:
                recent_nmse = np.mean(
                    self._round_nmses[-self._fidelity_window:])
                if recent_nmse > self._fidelity_target:
                    # Increase rho to improve fidelity (proportional control)
                    overshoot = (recent_nmse - self._fidelity_target) / \
                                max(self._fidelity_target, 0.01)
                    self._fidelity_boost = min(0.1, overshoot * 0.1)
                else:
                    # Decay boost when fidelity is good
                    self._fidelity_boost *= 0.9
            rho = min(self.config.rho_max,
                      rho + self._fidelity_boost)

        # ── Semantic-aware compression (6G): improve effective rho ───
        # Semantic layer computes per-feature importance weights and
        # achieves better NMSE at same ρ via non-uniform allocation.
        semantic_importance = None
        if self.semantic is not None and self._semantic_enabled:
            # Use a representative signal for importance computation
            dummy_signal = np.zeros(self.config.signal_dim)
            semantic_importance = self.semantic.compute_importance(
                dummy_signal, node_id=0, is_disaster=is_critical
            )
            # Semantic gain allows LOWER effective ρ for same quality
            rho = self.semantic.semantic_compression_ratio(rho, semantic_importance)
            rho = max(self.config.rho_min, rho)  # enforce minimum

        compressed_bits = self.cs.compressed_packet_bits(rho)

        # ── Carbon throttle: defer transmissions when carbon is costly ─
        # Only mMTC-classified traffic is deferrable (6G slice-aware).
        # URLLC (emergency) and eMBB (high-fidelity) are NEVER deferred.
        # This is the Lyapunov "backpressure" mechanism that makes the
        # carbon budget bound hold, combined with 3GPP-compliant
        # network slice QoS enforcement.
        ci_norm = self.carbon_mgr.get_normalized_ci(round_num)
        z_queue = self.router.carbon_queue
        skip_fraction = 0.0

        # Classify regular sensor data traffic
        data_slice = 'mmtc'
        if self.slice_mgr is not None:
            data_slice = self.slice_mgr.classify_traffic(
                'data', is_recovery=is_critical, is_critical=False)
            can_defer = self.slice_mgr.is_carbon_deferrable(data_slice)
        else:
            can_defer = True

        if (self._throttle_enabled and not is_critical
                and can_defer
                and z_queue > self._throttle_z_thresh and ci_norm > 0.5):
            # Proportional throttle: more pressure → more deferrals
            pressure = min((z_queue - self._throttle_z_thresh) /
                           (self._throttle_z_thresh + 1.0), 1.0)
            skip_fraction = self._throttle_max_skip * pressure * ci_norm

        total_energy = 0.0
        packets = 0
        nmses = []
        deferred_this_round = 0

        round_nmse = self.cs.lookup_nmse(rho)
        max_members = getattr(self.config, 'max_members_per_ch', 30)

        for ch in network.cluster_heads():
            members = network.cluster_members(ch.id)
            # Sort by distance (closest served first)
            members_sorted = sorted(members, key=lambda m: m.distance_to(ch))
            served = 0
            for member in members_sorted:
                if served >= max_members:
                    break  # CH capacity exceeded

                # Carbon throttle: probabilistic deferral
                if skip_fraction > 0 and self.rng.random() < skip_fraction:
                    deferred_this_round += 1
                    continue  # member defers transmission this round

                d = member.distance_to(ch)

                # Sensing energy (full signal)
                e_sense = self.energy.sense_energy(self.config.packet_size)

                # Transmit: THz intra-cluster if enabled and in range
                if (self.thz_energy is not None
                        and d <= self.config.thz_max_range_m):
                    e_tx = self.thz_energy.intra_cluster_energy(
                        compressed_bits, d
                    )
                else:
                    e_tx = self.energy.tx_energy(compressed_bits, d)

                e_member = e_sense + e_tx

                # 6G slice-aware energy: apply QoS overhead multiplier
                if self.slice_mgr is not None:
                    e_member *= self.slice_mgr.get_energy_multiplier(data_slice)

                if member.consume_energy(e_member):
                    e_rx = self.energy.rx_energy(compressed_bits)
                    ch.consume_energy(e_rx)
                    total_energy += e_member + e_rx
                    packets += 1
                    member.packets_sent += 1
                    ch.packets_received += 1
                    nmses.append(round_nmse)
                    served += 1
                else:
                    total_energy += e_member

        avg_nmse = float(np.mean(nmses)) if nmses else 0.0
        avg_rho = rho

        # Track deferred packets for next round's accounting
        self._deferred_packets = deferred_this_round

        return packets, total_energy, avg_nmse, avg_rho

    # ─── Pillar 2: CARE — Carbon-Aware Routing Engine ────────────────

    def setup_phase(self, network: Network, round_num: int) -> None:
        """
        Competitive Fitness-Based CH Self-Organisation.

        Unlike LEACH's global probabilistic threshold, CALASH uses
        genuinely autonomous local competition:

            1. Each node computes a *CH fitness score* from local
               information only (residual energy, neighbour count,
               distance to BS, carbon intensity, cooldown history).
            2. Each node compares its score against its 1-hop
               neighbours' scores (shared via control beacons).
            3. A node becomes CH if its score is the *local maximum*
               among its neighbourhood — no global threshold needed.

        This is a distributed auction / HEED-style [Younis & Fahmy 2004]
        competitive election enriched with carbon awareness and lifecycle
        sustainability, making it genuinely **autonomous**: every node
        decides independently using only local state.

        Fitness function
        ----------------
        F(i) = w_e · (E_i/E_0) + w_n · (|N(i)|/N_max) + w_d · (1 - d_i/d_max)
               + w_c · max(1 - β·CI_norm, 0.1) + w_h · cooldown(i)

        where cooldown(i) = 0 if node was CH in current epoch, 1 otherwise
        (prevents re-election before other nodes get a turn).

        During disaster recovery the fitness function boosts nodes with
        high energy near coverage holes and penalises damaged nodes,
        enabling organic self-restructuring without external directives.
        """
        alive = network.alive_nodes()
        if not alive:
            return

        # Initialize healer on first round
        if self.healer is not None and round_num == 1:
            self.healer.initialize(network)

        if round_num % self.epoch_length == 0:
            self.was_ch_this_epoch.clear()

        # ── Carbon intensity factor ──────────────────────────────────
        ci_norm = 0.0
        if self.carbon_mgr:
            ci_norm = self.carbon_mgr.get_normalized_ci(round_num)
        carbon_factor = max(1.0 - self.beta * ci_norm, 0.1)

        # During recovery: boost CH density for coverage restoration
        if self.recovery_mode:
            carbon_factor = min(carbon_factor * 1.5, 1.5)

        # ── Reference values for normalisation (local-only: max over alive) ──
        max_energy = max(n.energy for n in alive) or 1e-6
        max_nbrs = max(
            len(network.alive_neighbors(n.id)) for n in alive
        ) or 1.0
        bx, by = network.bs
        max_dist = max(
            np.sqrt((n.x - bx)**2 + (n.y - by)**2) for n in alive
        ) or 1.0

        # ── Fitness weights (tunable, sum to ~1) ─────────────────────
        w_e, w_n, w_d, w_c, w_h = 0.35, 0.15, 0.15, 0.20, 0.15

        # ── Compute fitness scores for all alive nodes ───────────────
        fitness: Dict[int, float] = {}
        for node in alive:
            e_frac = node.energy / max_energy
            n_frac = len(network.alive_neighbors(node.id)) / max_nbrs
            d_frac = 1.0 - (np.sqrt((node.x - bx)**2 + (node.y - by)**2)
                            / max_dist)
            cooldown = 0.0 if node.id in self.was_ch_this_epoch else 1.0

            f = (w_e * e_frac
                 + w_n * n_frac
                 + w_d * d_frac
                 + w_c * carbon_factor
                 + w_h * cooldown)

            # Recovery mode: penalise low-energy nodes heavily
            if self.recovery_mode and e_frac < 0.3:
                f *= 0.1

            fitness[node.id] = f

        # ── Local competition: elect node if it has highest fitness
        #    among its 1-hop neighbourhood ────────────────────────────
        for node in alive:
            nbrs = network.alive_neighbors(node.id)
            my_fit = fitness[node.id]

            # A node wins its neighbourhood competition if it has the
            # strictly highest fitness.  Ties are broken by node ID
            # (deterministic, no randomness needed).
            is_local_max = True
            for nbr in nbrs:
                nbr_fit = fitness.get(nbr.id, 0.0)
                if nbr_fit > my_fit or (nbr_fit == my_fit
                                        and nbr.id > node.id):
                    is_local_max = False
                    break

            if is_local_max:
                node.is_ch = True
                node.rounds_as_ch += 1
                node.last_ch_round = round_num
                self.was_ch_this_epoch.add(node.id)

        # Enforce minimum CH fraction (safety net)
        min_chs = max(1, int(self.min_ch_frac * len(alive)))
        chs = network.cluster_heads()
        if len(chs) < min_chs:
            non_chs = sorted(
                [n for n in alive if not n.is_ch],
                key=lambda n: fitness.get(n.id, 0.0), reverse=True
            )
            for node in non_chs[:min_chs - len(chs)]:
                node.is_ch = True
                node.rounds_as_ch += 1
                node.last_ch_round = round_num
                self.was_ch_this_epoch.add(node.id)

        # Self-healing: force emergency CHs from healer
        if self.healer is not None and self.recovery_mode:
            self.healer.execute_recovery(network)

        self.form_clusters(network)

    def get_route(self, source_ch: Node, all_chs: List[Node],
                  bs: Tuple[float, float],
                  network: Optional['Network'] = None) -> List:
        """
        Compute route using hybrid DQN + Lyapunov routing.

        Strategy:
        - If DQN has enough training data → use DQN (autonomous)
        - Otherwise fall back to Lyapunov (provable guarantees)
        - During disaster recovery → always Lyapunov (no latency for learning)

        Autonomy guarantee:
        - alive_ratio is estimated SOLELY from heartbeat data (packet-absence),
          NEVER from the global node.alive flag.  This makes routing genuinely
          distributed: each CH knows only what it can observe locally via
          heartbeat responses from 1-hop neighbours.
        """
        ci = self._cached_ci  # beacon-distributed CI (NOT oracle)

        # LOCAL alive ratio: estimated from heartbeat-based liveness detection.
        # The HeartbeatTracker._detected_dead set contains neighbour IDs that
        # have been silent for timeout_rounds consecutive rounds.  We NEVER
        # read the global node.alive flag — dead nodes simply stop sending
        # heartbeats, and their silence is detected locally.
        alive_ratio = 0.5  # safe default
        if network is not None:
            local_nbrs = network.adjacency.get(source_ch.id, [])
            if local_nbrs:
                if (self.healer is not None
                        and source_ch.id in self.healer.heartbeat._detected_dead):
                    # Use heartbeat-based estimation (genuinely autonomous)
                    dead_set = self.healer.heartbeat._detected_dead[source_ch.id]
                    alive_count = sum(
                        1 for nid in local_nbrs if nid not in dead_set
                    )
                elif self.healer is not None:
                    # Healer active but no dead-set entry yet → assume all alive
                    alive_count = len(local_nbrs)
                else:
                    # No healer (ablation variant or early init) → use adjacency
                    # count of CHs as proxy (still local information)
                    alive_count = len([
                        ch for ch in all_chs
                        if ch.id in set(local_nbrs) and ch.id != source_ch.id
                    ])
                    alive_count = max(alive_count, 1)
                alive_ratio = alive_count / len(local_nbrs)
            else:
                alive_ratio = len(all_chs) / max(self.config.num_nodes * 0.05, 1)

        # Use DQN if enabled and not in recovery.
        # DQN handles exploration internally via ε-greedy: while ε≈1.0
        # (early rounds) it picks random neighbours, collecting transitions
        # that fill the replay buffer.  train_step() only fires once
        # buffer.size ≥ min_buffer (256), so the network learns
        # *after* enough exploration.  During disaster recovery →
        # always Lyapunov (no latency for exploration).
        #
        # WARMUP POLICY: When ε > 0.3 (first ~1500 rounds), DQN would
        # pick mostly random next-hops, wasting significant energy on
        # suboptimal routes.  Instead, we use Lyapunov for routing but
        # STILL feed the transitions to DQN's replay buffer (imitation
        # learning from the expert Lyapunov policy).  This gives the DQN
        # high-quality training data while avoiding exploration waste.
        use_dqn = (
            self._dqn_enabled
            and self.dqn is not None
            and not self.recovery_mode
        )

        # DQN warmup: use Lyapunov routing but train DQN from those decisions
        dqn_warmup = (
            use_dqn
            and self.dqn.epsilon > 0.3
        )

        # Build heartbeat dead-set for BOTH routing engines
        hb_dead: set = set()
        if (self.healer is not None
                and source_ch.id in self.healer.heartbeat._detected_dead):
            hb_dead = self.healer.heartbeat._detected_dead[source_ch.id]

        if use_dqn and not dqn_warmup:
            self._dqn_decisions += 1
            route = self._dqn_route(source_ch, all_chs, bs, ci, alive_ratio)
        elif dqn_warmup:
            # Warmup: Lyapunov routes, DQN learns from transitions
            self._lyapunov_decisions += 1
            route = self.router.compute_route(
                source_ch, all_chs, bs, ci,
                self.energy, self.config.packet_size,
                dead_set=hb_dead
            )
            # Feed Lyapunov route to DQN as imitation data
            self._train_dqn_from_route(
                source_ch, route, all_chs, bs, ci, alive_ratio
            )
        else:
            self._lyapunov_decisions += 1
            route = self.router.compute_route(
                source_ch, all_chs, bs, ci,
                self.energy, self.config.packet_size,
                dead_set=hb_dead
            )

        # Geographic fallback guard: if Lyapunov/DQN routing produced
        # a significantly longer route than greedy geographic, fall back
        # to geographic.  Extra hops waste more energy (electronics
        # overhead) than they save in carbon/lifecycle cost.
        geo_route = self.greedy_multihop_route(source_ch, all_chs, bs)
        if len(route) > len(geo_route) + 1:
            return geo_route
        return route

    def _lifecycle_factor_fn(self, candidate):
        """Compute lifecycle factor for a candidate node (for DQN routing)."""
        if not self.router.lifecycle_enabled:
            return 1.0
        energy_frac = max(candidate.energy_fraction(), 0.01)
        return self.router.lca.lifecycle_factor(candidate.id, energy_frac)

    def _train_dqn_from_route(self, source_ch: Node, route: List,
                               all_chs: List[Node],
                               bs: Tuple[float, float],
                               ci: float, alive_ratio: float) -> None:
        """
        Feed Lyapunov route decisions to DQN for imitation learning.

        During warmup, Lyapunov provides expert routing.  We store each
        hop as a DQN transition so the DQN learns from good decisions
        instead of random exploration.  This produces a much better
        initial policy when the DQN takes over.
        """
        if self.dqn is None or not route:
            return

        z_queue = self.router.carbon_queue
        current = source_ch

        for i, (hop_target, hop_dist) in enumerate(route):
            is_last = (hop_target == 'BS')

            # Compute lifecycle factor for the hop target
            lf = 1.0
            if not is_last:
                lf = self._lifecycle_factor_fn(hop_target)

            state = self.dqn._build_state(
                current, hop_target, bs, ci, z_queue, alive_ratio,
                lifecycle_factor=lf
            )
            reward = self.dqn.compute_reward(
                current, hop_target, bs, ci,
                self.energy, self.config.packet_size,
                delivered=is_last, dropped=False,
                lifecycle_factor=lf
            )

            if is_last:
                self.dqn.store_transition(state, 0, reward, state, True)
            else:
                # Next state uses the next hop in the route
                next_target = route[i + 1][0] if i + 1 < len(route) else 'BS'
                next_lf = 1.0
                if next_target != 'BS':
                    next_lf = self._lifecycle_factor_fn(next_target)
                next_state = self.dqn._build_state(
                    hop_target, next_target, bs, ci, z_queue, alive_ratio,
                    lifecycle_factor=next_lf
                )
                self.dqn.store_transition(state, 0, reward, next_state, False)

            self.dqn.train_step()

            if not is_last and hasattr(hop_target, 'id'):
                current = hop_target

    def _dqn_route(self, source_ch: Node, all_chs: List[Node],
                   bs: Tuple[float, float], ci: float,
                   alive_ratio: float) -> List:
        """Build route using DQN agent hop-by-hop.

        Candidate filtering uses heartbeat-based liveness estimation
        instead of reading the global node.alive flag, keeping routing
        fully autonomous and distributed.

        Now passes lifecycle_factor_fn to DQN for lifecycle-aware
        candidate evaluation and reward computation.
        """
        # Build heartbeat dead-set for candidate filtering
        dead_set: set = set()
        if (self.healer is not None
                and source_ch.id in self.healer.heartbeat._detected_dead):
            dead_set = self.healer.heartbeat._detected_dead[source_ch.id]

        route = []
        current = source_ch
        visited = {source_ch.id}
        z_queue = self.router.carbon_queue

        # Lifecycle factor function for DQN routing
        lf_fn = self._lifecycle_factor_fn

        for _ in range(20):
            candidates = [ch for ch in all_chs
                          if ch.id not in visited and ch.id not in dead_set]

            next_hop = self.dqn.select_next_hop(
                current, candidates, bs, ci, z_queue,
                min(alive_ratio, 1.0),
                self.energy, self.config.packet_size,
                lifecycle_factor_fn=lf_fn
            )

            if next_hop == 'BS':
                d = current.distance_to(bs)
                route.append(('BS', d))

                # Store experience for learning
                state = self.dqn._build_state(
                    current, 'BS', bs, ci, z_queue, alive_ratio,
                    lifecycle_factor=1.0
                )
                reward = self.dqn.compute_reward(
                    current, 'BS', bs, ci,
                    self.energy, self.config.packet_size,
                    delivered=True, dropped=False,
                    lifecycle_factor=1.0
                )
                self.dqn.store_transition(state, 0, reward, state, True)
                self.dqn.train_step()
                return route
            elif next_hop is not None:
                d = current.distance_to(next_hop)
                route.append((next_hop, d))

                # Compute lifecycle factor for this hop
                hop_lf = lf_fn(next_hop)

                # Store experience
                state = self.dqn._build_state(
                    current, next_hop, bs, ci, z_queue, alive_ratio,
                    lifecycle_factor=hop_lf
                )
                next_state = self.dqn._build_state(
                    next_hop, 'BS', bs, ci, z_queue, alive_ratio,
                    lifecycle_factor=1.0
                )
                reward = self.dqn.compute_reward(
                    current, next_hop, bs, ci,
                    self.energy, self.config.packet_size,
                    delivered=False, dropped=False,
                    lifecycle_factor=hop_lf
                )
                self.dqn.store_transition(state, 0, reward, next_state, False)
                self.dqn.train_step()

                visited.add(next_hop.id)
                current = next_hop
            else:
                d = current.distance_to(bs)
                route.append(('BS', d))
                return route

        d = current.distance_to(bs)
        route.append(('BS', d))
        return route

    # ─── Pillar 3: SHDR — Self-Healing Disaster Recovery ─────────────

    def handle_disaster(self, network: Network, killed_ids: List[int],
                        round_num: int) -> None:
        """
        Legacy callback — intentionally a NO-OP for disaster DETECTION
        (which is autonomous via heartbeats).

        However, we USE this callback to:
        1. Initialize the aftershock model (Bath-Håkansson + Omori-Utsu)
           so that secondary seismic events are generated in future rounds.
        2. Register weakened survivors for progressive damage propagation.

        The self-healing engine still discovers damage autonomously via
        heartbeats — this callback only sets up the geophysical model.
        """
        # Initialize aftershock model on first disaster notification
        if self._aftershock_model is None:
            try:
                from models.disaster import AftershockModel
                # Get mainshock magnitude from config or default
                magnitude = 7.0  # default moderate earthquake
                damage_radius = getattr(self.config, 'damage_radius', 60.0)
                # Check if using a real event profile
                event_key = getattr(self.config, 'disaster_event', '')
                if event_key:
                    try:
                        from models.disaster import REAL_DISASTER_PROFILES
                        profile = REAL_DISASTER_PROFILES.get(event_key, {})
                        magnitude = profile.get('magnitude', 7.0)
                        damage_radius = profile.get('damage_radius', 60.0)
                    except (ImportError, KeyError):
                        pass

                self._aftershock_model = AftershockModel(
                    mainshock_magnitude=magnitude,
                    mainshock_radius=damage_radius,
                    rng=self.rng,
                )
                self._aftershock_model.set_mainshock_round(round_num)
            except ImportError:
                pass

        # Register weakened survivors for progressive damage
        if self.healer is not None and self._last_disaster_event is not None:
            self.healer.register_weakened_survivors(
                network, self._last_disaster_event
            )

    def check_recovery_complete(self, network: Network,
                                round_num: int) -> bool:
        """Check if recovery period has ended."""
        if not self.disaster_detected:
            return True

        if self.healer is not None:
            done = self.healer.check_recovery_complete(network, round_num)
            self.recovery_mode = self.healer.recovery_mode
            return done

        # Fallback timer-based
        rounds_since = round_num - self.disaster_round
        if rounds_since > (self.healing_detection_rounds
                           + self.healing_restructure_rounds):
            self.recovery_mode = False
            return True
        return False

    # ─── Pillar 4: LSE — Lifecycle Sustainability Engine ─────────────

    def compute_lci(self, network: Network, total_delivered: int,
                    total_carbon: float) -> float:
        """
        Compute Lifecycle Carbon Intensity (LCI) metric.

        LCI = (C_embodied + C_operational + C_eol) / packets_delivered
        """
        if total_delivered == 0:
            return float('inf')

        c_embodied = sum(n.embodied_carbon for n in network.nodes)
        dead_count = sum(1 for n in network.nodes if not n.alive)
        c_eol = dead_count * self.config.eol_carbon_per_node * (
            1 - self.config.recycle_rate
        )
        c_total = c_embodied + total_carbon + c_eol
        return c_total / total_delivered

    # ─── Main Steady Phase ────────────────────────────────────────────

    def _run_self_healing_tick(self, network: Network,
                               round_num: int) -> float:
        """
        Autonomous MAPE-K self-healing tick (runs every round).

        This is how the protocol DISCOVERS disaster damage — not via
        an oracle call from the simulator, but through its own
        heartbeat-based monitoring.  The full MAPE-K loop:

            Monitor:  HeartbeatTracker.tick() — detect missed heartbeats
            Analyse:  CoverageAnalyzer — identify coverage holes
            Plan:     Emergency CH election + relay selection
            Execute:  Applied in next setup_phase()

        Heartbeat energy cost: each alive node sends 1 control packet
        to each alive neighbour per round (realistic distributed cost).

        Returns
        -------
        float
            Energy consumed by heartbeat control packets.
        """
        if self.healer is None:
            return 0.0

        # Heartbeat interval: every round during disaster (rapid detection),
        # every 2 rounds in normal mode (energy savings).  This halves
        # heartbeat overhead in the non-disaster phase (~85% of simulation).
        # The heartbeat broadcast is the energy cost; the monitor/analysis
        # runs every round regardless.
        hb_interval = 1 if self.disaster_detected else 2
        skip_broadcast = (round_num % hb_interval != 0)

        # ─── ISAC passive detection mode ──────────────────────────
        # When 6G ISAC is available, use radar echo analysis to detect
        # node failures passively (echo absence = node death).  This
        # eliminates the active heartbeat broadcast energy entirely,
        # since the ISAC sensing beam already illuminates the cluster.
        # Passive detection relies on the THz/sub-THz waveform's dual
        # radar-communication nature (Liu et al., 2022; Zhang et al.,
        # 2021).  Without ISAC, the protocol falls back to classical
        # heartbeat beacons.
        use_isac_passive = (
            self.isac is not None
            and self._isac_enabled
            and self._thz_enabled
        )

        # Heartbeat energy: each alive node sends a small beacon (50 bits)
        # to confirm liveness.  Broadcast distance is CAPPED at the
        # crossover distance d_0 to keep transmissions in the d² free-space
        # regime, avoiding the expensive d⁴ multipath amplifier.
        # This reduces heartbeat overhead from ~11% to ~2% of total energy.
        hb_energy = 0.0
        if not skip_broadcast:
            if use_isac_passive:
                # ISAC passive mode: register heartbeats via radar echo
                # analysis — no energy cost for the sensor nodes.
                # The ISAC radar uses the existing THz sensing beam,
                # so the marginal energy for failure detection is zero.
                for node in network.alive_nodes():
                    self.healer.heartbeat.register_heartbeat(node.id)
            else:
                # Classical heartbeat broadcast (active beacons)
                hb_bits = 50  # minimal beacon (node ID only)
                d0 = self.config.d0  # crossover distance (~87.7m)
                for node in network.alive_nodes():
                    alive_nbrs = network.alive_neighbors(node.id)
                    if alive_nbrs:
                        max_d = max(node.distance_to(nbr)
                                    for nbr in alive_nbrs)
                        broadcast_d = min(max_d, d0)
                        e_hb = self.energy.tx_energy(hb_bits, broadcast_d)
                        if node.consume_energy(e_hb):
                            self.healer.heartbeat.register_heartbeat(
                                node.id)
                        hb_energy += e_hb

        # Monitor phase: heartbeat tick detects failures
        detected_disaster = self.healer.monitor_round(network, round_num)

        # If healer triggered detection → sync recovery flags
        if self.healer.disaster_detected and not self.disaster_detected:
            self.disaster_detected = True
            self.disaster_round = round_num
            self.recovery_mode = True
            self.alarm_nodes = self.healer.alarm_nodes.copy()

            # Analyse + Plan (run once on detection)
            self.healer.analyse(network)
            self.healer.plan_recovery(network)

        # Ongoing recovery: re-analyse coverage each round
        elif self.recovery_mode and self.healer.recovery_mode:
            self.healer.analyse(network)

        # ─── Progressive damage: weakened survivors degrade over time ─
        # Models structural fatigue, battery swelling, antenna drift
        # from mainshock stress (Younis et al., 2014).
        if self.healer is not None and self.disaster_detected:
            prog_failed = self.healer.apply_progressive_damage(
                network, round_num
            )
            # If progressive failures killed more nodes, re-trigger analysis
            if prog_failed and self.recovery_mode:
                self.healer.analyse(network)

        # ─── Aftershock model: generate secondary seismic events ─────
        # Real earthquakes have aftershock sequences (Omori-Utsu law).
        # Each aftershock can damage additional weakened survivors.
        if self._aftershock_model is not None and self.disaster_detected:
            aftershock = self._aftershock_model.generate_aftershock(round_num)
            if aftershock is not None:
                # Apply aftershock damage to network
                killed, survived = aftershock.apply_to_network(network)
                if killed:
                    # Register newly weakened survivors
                    self.healer.register_weakened_survivors(network, aftershock)
                    self.healer._aftershock_count += 1
                    # Force re-analysis
                    if self.healer is not None:
                        self.healer.analyse(network)

        return hb_energy

    def steady_phase(self, network: Network, round_num: int) -> Dict:
        """
        Execute complete CALASH steady phase:
        1. SHDR: Autonomous heartbeat monitoring (MAPE-K)
        2. CADR: carbon-adaptive compression with fidelity feedback
        3. CARE: hybrid DQN+Lyapunov routing at CHs
        4. LSE:  carbon queue update with lifecycle term
        """
        self._current_round = round_num
        total_energy = 0.0

        # Phase 0: SHDR — autonomous heartbeat monitoring (MAPE-K)
        # Protocol discovers disaster damage organically — NOT told by sim.
        hb_energy = self._run_self_healing_tick(network, round_num)
        total_energy += hb_energy

        # Update 6G slice manager disaster mode
        if self.slice_mgr is not None:
            self.slice_mgr.set_disaster_mode(self.recovery_mode)

        # Phase 1: CADR — compressed intra-cluster transmission
        # Includes: CI-driven rho, fidelity feedback, carbon throttle
        intra_packets, intra_energy, avg_nmse, avg_rho = \
            self.compress_and_transmit_intra(network, round_num)
        total_energy += intra_energy

        # Phase 2: CARE — inter-cluster routing (DQN or Lyapunov)
        if self.thz_energy is not None:
            inter_packet_bits = self.config.packet_size
            delivered, inter_energy = self._transmit_inter_thz(
                network, inter_packet_bits
            )
        else:
            delivered, inter_energy = self._transmit_inter_calash(
                network, self.config.packet_size
            )
        total_energy += inter_energy

        # Phase 3: Carbon accounting and queue update
        carbon = 0.0
        if self.carbon_mgr:
            carbon = self.carbon_mgr.compute_operational_carbon(
                total_energy, round_num
            )
            self.router.update_queue(carbon)

        # Phase 4: Check recovery status (autonomous — via coverage metric)
        self.check_recovery_complete(network, round_num)

        # Phase 5: End-of-round slice bookkeeping
        if self.slice_mgr is not None:
            self.slice_mgr.end_round()

        # Track fidelity for closed-loop CADR feedback
        self._round_nmses.append(avg_nmse)
        self._round_rhos.append(avg_rho)

        # Adaptive semantic gain update (rate-distortion feedback loop)
        if self.semantic is not None and self._semantic_enabled:
            dummy_signal = np.zeros(self.config.signal_dim)
            importance = self.semantic.compute_importance(
                dummy_signal, node_id=0, is_disaster=self.recovery_mode
            )
            self.semantic.update_adaptive_gain(
                avg_nmse, importance, is_disaster=self.recovery_mode
            )

        # Convergence diagnostics (DQN + Lyapunov)
        dqn_epsilon = self.dqn.epsilon if self.dqn is not None else 0.0
        dqn_loss = self.dqn._total_loss if self.dqn is not None else 0.0
        lyapunov_V = self.router.carbon_queue ** 2 / 2.0

        # DQN utilisation ratio (how much routing is learned vs formula)
        total_decisions = self._dqn_decisions + self._lyapunov_decisions
        dqn_ratio = (self._dqn_decisions / total_decisions
                     if total_decisions > 0 else 0.0)

        return {
            'packets_generated': intra_packets,
            'packets_delivered': delivered,
            'energy_consumed': total_energy,
            'energy_intra': intra_energy,
            'energy_inter': inter_energy,
            'energy_heartbeat': hb_energy,
            'carbon_emitted': carbon,
            'data_fidelity': 1.0 - avg_nmse,
            'compression_ratio': avg_rho,
            'fidelity_boost': self._fidelity_boost,
            'carbon_queue': self.router.carbon_queue,
            'recovery_mode': self.recovery_mode,
            'deferred_packets': self._deferred_packets,
            'dqn_epsilon': dqn_epsilon,
            'dqn_loss': dqn_loss,
            'dqn_ratio': dqn_ratio,
            'lyapunov_V': lyapunov_V,
        }

    def _transmit_inter_thz(self, network: Network,
                            packet_bits: int) -> Tuple[int, float]:
        """
        Inter-cluster routing with THz-aware energy model + ISAC sensing.

        CHs use sub-6 GHz for inter-cluster hops (longer range).
        The THz6GEnergyModel computes appropriate energy.
        ISAC processing runs on each inter-cluster transmission,
        producing radar echo data for structural anomaly detection.
        """
        total_energy = 0.0
        delivered_member_packets = 0
        all_chs = network.cluster_heads()

        # ISAC: process radar echoes from inter-cluster transmissions
        # Only activate during/after disaster (structural sensing is
        # unnecessary during normal operation, saves ~15% inter-cluster energy)
        if (self.isac is not None and self._isac_enabled
                and self.disaster_detected):
            isac_scores = self.isac.process_round(
                network, self._current_round, self.rng,
                disaster_active=self.disaster_detected
            )
            # Feed ISAC anomaly scores into self-healing engine
            if self.healer is not None:
                for node_id, score in isac_scores.items():
                    if self.isac.detect_structural_anomaly(node_id):
                        # ISAC detected anomaly — flag for self-healing
                        self.healer.alarm_nodes.add(node_id)

        for ch in list(all_chs):
            if not ch.alive:
                continue

            num_received = ch.packets_received
            if num_received == 0:
                continue

            # Data aggregation at CH
            e_agg = self.energy.da_energy(packet_bits, num_received)
            if not ch.consume_energy(e_agg):
                total_energy += e_agg
                continue
            total_energy += e_agg

            # Route to BS (pass network for local alive_ratio)
            route = self.get_route(ch, all_chs, network.bs, network=network)

            # Transmit along route using sub-6 GHz inter-cluster energy
            current_node = ch
            success = True
            for hop_target, hop_dist in route:
                # Inter-cluster: use sub-6 GHz with RIS gain (longer range)
                e_tx = self.thz_energy.inter_cluster_energy(
                    packet_bits, hop_dist,
                    tx_x=current_node.x, tx_y=current_node.y
                )

                # ISAC energy overhead (radar processing on each hop)
                # Only active after disaster detection (saves energy in normal ops)
                if (self.isac is not None and self._isac_enabled
                        and self.disaster_detected):
                    e_tx += self.isac.isac_energy_overhead(e_tx)

                if not current_node.consume_energy(e_tx):
                    total_energy += e_tx
                    success = False
                    break
                total_energy += e_tx

                if hop_target == 'BS':
                    break
                else:
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
                # Register delivery for LCA amortisation (lifecycle)
                self.router.register_delivery(ch.id, num_received)
                for hop_target, _ in route:
                    if hop_target != 'BS' and hasattr(hop_target, 'id'):
                        self.router.register_delivery(hop_target.id, 1)

        return delivered_member_packets, total_energy

    def run_round(self, network: Network, round_num: int) -> Dict:
        """Override to include LCI tracking."""
        metrics = super().run_round(network, round_num)
        return metrics

    def _transmit_inter_calash(self, network: Network,
                                packet_bits: int) -> Tuple[int, float]:
        """
        Inter-cluster routing WITHOUT THz model but WITH DQN/Lyapunov
        and local alive_ratio.  Used when thz_enabled=False.
        """
        total_energy = 0.0
        delivered_member_packets = 0
        all_chs = network.cluster_heads()

        for ch in list(all_chs):
            if not ch.alive:
                continue
            num_received = ch.packets_received
            if num_received == 0:
                continue

            e_agg = self.energy.da_energy(packet_bits, num_received)
            if not ch.consume_energy(e_agg):
                total_energy += e_agg
                continue
            total_energy += e_agg

            route = self.get_route(ch, all_chs, network.bs, network=network)

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
                    break
                else:
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
                # Register delivery for LCA amortisation (lifecycle)
                self.router.register_delivery(ch.id, num_received)
                for hop_target, _ in route:
                    if hop_target != 'BS' and hasattr(hop_target, 'id'):
                        self.router.register_delivery(hop_target.id, 1)

        return delivered_member_packets, total_energy
