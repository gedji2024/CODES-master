"""
CALASH Ablation Variants
=========================
Per-component ablation baselines to isolate the contribution of each
CALASH pillar. Proper single-factor ablation is essential for causal
attribution in systems with multiple interacting components [1].

Each variant removes exactly ONE pillar while keeping all others intact.
This design ensures that any measured performance delta is attributable
to the removed component alone.

B4: CALASH-NoCO2
    - Removes carbon awareness ONLY (beta=0, greedy routing, fixed rho)
    - Keeps: CADR structure, self-healing, lifecycle
    - Purpose: Proves carbon-awareness is the key differentiator

B5: CALASH-NoSH
    - Removes self-healing ONLY (no heartbeat, no emergency re-clustering)
    - Keeps: carbon-aware CH election, Lyapunov routing, CADR, lifecycle
    - Purpose: Proves self-healing is essential for disaster resilience

B6: CALASH-NoCADR
    - Removes compressive sensing ONLY (rho = 1.0 always, full transmission)
    - Keeps: carbon-aware CH, Lyapunov routing, self-healing, lifecycle
    - Purpose: Proves data reduction saves carbon (fewer bits -> less energy)

B7: CALASH-NoLCI
    - Removes lifecycle integration ONLY (no embodied/EOL carbon in routing)
    - Keeps: carbon-aware CH, Lyapunov routing, CADR, self-healing
    - Purpose: Proves lifecycle-awareness extends network lifetime

References
----------
[1] Lipton, Z.C. & Steinhardt, J. "Troubling Trends in Machine Learning
    Scholarship." Queue, ACM, 17(1), 2019. DOI: 10.1145/3317287.3328534
    (Best practices for ablation studies in ML/systems research.)

[2] Meyes, R. et al. "Ablation Studies in Artificial Neural Networks."
    arXiv:1901.08644, 2019. (Formalises single-factor ablation design.)
"""

import numpy as np
from typing import Dict, List

from protocols.calash import CALASH
from models.network import Network, Node
from models.energy import EnergyModel
from models.carbon import CarbonTraceManager
from models.compression import CompressiveSensing


class CALASH_NoCO2(CALASH):
    """
    CALASH without carbon awareness (ablation baseline B4).

    Single-factor ablation: ONLY removes carbon-related decision logic.
    ALL other features (THz, ISAC, semantic, lifecycle, self-healing) kept.

    Changes from full CALASH:
    - CH election: energy-weighted only (no carbon modulation, β=0)
    - Routing: greedy geographic (no Lyapunov carbon queue, no DQN carbon reward)
    - Compression: fixed ρ = (ρ_min + ρ_max) / 2 (no carbon adaptation)
    - Carbon throttle: disabled (no carbon-driven deferral)
    - THz/ISAC/semantic/lifecycle/self-healing: KEPT (same as full CALASH)
    """

    def __init__(self, config, energy_model: EnergyModel,
                 carbon_mgr: CarbonTraceManager = None,
                 cs: CompressiveSensing = None,
                 rng: np.random.Generator = None):
        super().__init__(config, energy_model, carbon_mgr, cs, rng)
        self.name = "CALASH-NoCO2"
        # Disable carbon modulation in CH election
        self.beta = 0.0
        # Fixed compression ratio (midpoint)
        self.fixed_rho = (config.rho_min + config.rho_max) / 2.0
        # Disable carbon throttle
        self._throttle_enabled = False
        # Disable fidelity feedback (it's driven by CI-adaptive rho)
        self._fidelity_feedback = False
        # Disable DQN (carbon-unaware routing)
        self._dqn_enabled = False

    def get_route(self, source_ch: Node, all_chs: List[Node],
                  bs: tuple, network=None) -> List:
        """Use greedy geographic routing instead of Lyapunov/DQN."""
        return self.greedy_multihop_route(source_ch, all_chs, bs)

    def compress_and_transmit_intra(self, network: Network,
                                    round_num: int):
        """Fixed compression ratio but KEEP THz energy model (single-factor)."""
        if self.cs is None:
            packets, energy = self.transmit_intra_cluster(
                network, self.config.packet_size
            )
            return packets, energy, 0.0, 1.0

        rho = self.fixed_rho
        compressed_bits = self.cs.compressed_packet_bits(rho)

        total_energy = 0.0
        packets = 0
        nmses = []

        # Lookup fidelity once per round
        round_nmse = self.cs.lookup_nmse(rho)
        max_members = getattr(self.config, 'max_members_per_ch', 30)

        for ch in network.cluster_heads():
            members = network.cluster_members(ch.id)
            members_sorted = sorted(members, key=lambda m: m.distance_to(ch))
            served = 0
            for member in members_sorted:
                if served >= max_members:
                    break
                d = member.distance_to(ch)
                e_sense = self.energy.sense_energy(self.config.packet_size)

                # KEEP THz energy model (single-factor: only remove carbon)
                if (self.thz_energy is not None
                        and d <= self.config.thz_max_range_m):
                    e_tx = self.thz_energy.intra_cluster_energy(
                        compressed_bits, d
                    )
                else:
                    e_tx = self.energy.tx_energy(compressed_bits, d)
                e_member = e_sense + e_tx

                # KEEP 6G slice-aware energy
                if self.slice_mgr is not None:
                    data_slice = self.slice_mgr.classify_traffic(
                        'data', is_recovery=self.recovery_mode, is_critical=False)
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
        return packets, total_energy, avg_nmse, rho

    def steady_phase(self, network: Network, round_num: int) -> Dict:
        """Execute without carbon queue updates but WITH all other features."""
        self._current_round = round_num
        total_energy = 0.0

        # Self-healing tick still runs (KEPT — single-factor)
        hb_energy = self._run_self_healing_tick(network, round_num)
        total_energy += hb_energy

        # 6G slice manager (KEPT)
        if self.slice_mgr is not None:
            self.slice_mgr.set_disaster_mode(self.recovery_mode)

        # Fixed-rho intra-cluster with THz (KEPT)
        intra_packets, intra_energy, avg_nmse, avg_rho = \
            self.compress_and_transmit_intra(network, round_num)
        total_energy += intra_energy

        # Inter-cluster: greedy routing but KEEP THz/ISAC energy model
        if self.thz_energy is not None:
            delivered, inter_energy = self._transmit_inter_thz(
                network, self.config.packet_size
            )
        else:
            delivered, inter_energy = self.transmit_inter_cluster(
                network, self.config.packet_size
            )
        total_energy += inter_energy

        carbon = 0.0
        if self.carbon_mgr:
            carbon = self.carbon_mgr.compute_operational_carbon(
                total_energy, round_num
            )
        # No carbon queue update (carbon-unaware)

        self.check_recovery_complete(network, round_num)

        # End-of-round slice bookkeeping (KEPT)
        if self.slice_mgr is not None:
            self.slice_mgr.end_round()

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
            'carbon_queue': 0.0,
            'recovery_mode': self.recovery_mode,
            'deferred_packets': 0,
            'dqn_ratio': 0.0,
        }


class CALASH_NoSH(CALASH):
    """
    CALASH without self-healing (ablation baseline B5).

    Changes from full CALASH:
    - No disaster detection or recovery mode
    - No emergency CH re-election
    - No healer engine (completely disabled)
    - Keeps: carbon-aware CH election, Lyapunov routing, CADR, lifecycle

    After disaster, the protocol continues with standard operation,
    demonstrating the cost of not having self-healing.
    """

    def __init__(self, config, energy_model: EnergyModel,
                 carbon_mgr: CarbonTraceManager = None,
                 cs: CompressiveSensing = None,
                 rng: np.random.Generator = None):
        super().__init__(config, energy_model, carbon_mgr, cs, rng)
        self.name = "CALASH-NoSH"
        # Completely disable self-healing engine
        self.healer = None

    def handle_disaster(self, network: Network, killed_ids: List[int],
                        round_num: int) -> None:
        """Do nothing — no self-healing."""
        pass  # Intentionally empty

    def check_recovery_complete(self, network: Network,
                                round_num: int) -> bool:
        """Always returns True — no recovery mode."""
        return True


class CALASH_NoCADR(CALASH):
    """
    CALASH without compressive sensing (ablation B6).

    Changes from full CALASH:
    - Compression ratio always 1.0 (no compression, full packets)
    - Keeps: carbon-aware CH election, Lyapunov routing, self-healing, lifecycle

    This isolates the contribution of carbon-aware data reduction.
    """

    def __init__(self, config, energy_model: EnergyModel,
                 carbon_mgr: CarbonTraceManager = None,
                 cs: CompressiveSensing = None,
                 rng: np.random.Generator = None):
        super().__init__(config, energy_model, carbon_mgr, cs, rng)
        self.name = "CALASH-NoCADR"

    def compress_and_transmit_intra(self, network: Network,
                                    round_num: int):
        """No compression — transmit full packets."""
        packets, energy = self.transmit_intra_cluster(
            network, self.config.packet_size
        )
        return packets, energy, 0.0, 1.0


class CALASH_NoLCI(CALASH):
    """
    CALASH without lifecycle integration (ablation B7).

    Changes from full CALASH:
    - Lyapunov routing ignores lifecycle penalty (no EOL cost in routing)
    - LCI metric still computed for reporting, but does NOT influence decisions
    - Keeps: carbon-aware CH election, CADR, Lyapunov routing (no lifecycle
      term), self-healing

    This isolates the contribution of lifecycle-aware routing.
    """

    def __init__(self, config, energy_model: EnergyModel,
                 carbon_mgr: CarbonTraceManager = None,
                 cs: CompressiveSensing = None,
                 rng: np.random.Generator = None):
        # Temporarily disable lifecycle for this variant
        config_copy = config.copy(lifecycle_in_routing=False)
        super().__init__(config_copy, energy_model, carbon_mgr, cs, rng)
        self.name = "CALASH-NoLCI"
        # Ensure the router has lifecycle disabled
        self.router.lifecycle_enabled = False


class CALASH_NoTHz(CALASH):
    """
    CALASH without 6G features (ablation B8).

    Disables the ENTIRE 6G communication stack:
    - THz/sub-THz intra-cluster energy model → uses standard radio
    - RIS-assisted inter-cluster gain → uses standard Heinzelman model
    - ISAC passive failure detection → falls back to active heartbeats
    - Network slicing → single best-effort traffic class

    Keeps: carbon-aware CH election, Lyapunov routing, CADR, self-healing
    (with classical heartbeats), lifecycle integration.

    This isolates the FULL contribution of the 6G communication layer.
    The ablation removes all 6G-specific features simultaneously, so the
    measured gap represents the aggregate value of 6G integration.
    """

    def __init__(self, config, energy_model: EnergyModel,
                 carbon_mgr: CarbonTraceManager = None,
                 cs: CompressiveSensing = None,
                 rng: np.random.Generator = None):
        config_copy = config.copy(
            thz_enabled=False,
            ris_enabled=False,
            isac_enabled=False,
            slicing_enabled=False,
        )
        super().__init__(config_copy, energy_model, carbon_mgr, cs, rng)
        self.name = "CALASH-NoTHz"
        # Explicitly disable all 6G features
        self._thz_enabled = False
        self._isac_enabled = False
        self.thz_energy = None
        self.isac = None
        self.slice_mgr = None
