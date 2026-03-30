"""
Integrated Sensing and Communication (ISAC) Module
====================================================
Joint radar-communication for 6G-integrated disaster sensor networks.

ISAC is a defining IMT-2030/6G capability where the SAME waveform serves
both data communication and environment sensing (radar).  In disaster
WSNs, this enables:

    1. **Structural health sensing**: THz reflections detect rubble,
       building collapse, and ground deformation — complementing
       heartbeat-based failure detection with physical-layer awareness.

    2. **Range-Doppler estimation**: Each CH-to-CH transmission's
       echo provides range/velocity estimates of reflecting objects
       (debris, collapsed structures), enabling damage mapping.

    3. **Spectrum efficiency**: No separate radar waveform needed —
       the sub-THz communication signal doubles as a sensing probe.

The ISAC model computes:
    - Radar cross-section (RCS) of disaster debris
    - Bistatic range estimation from echo delay
    - Structural anomaly detection score per node
    - Additional energy cost for ISAC processing (FFT + CFAR)

ISAC integration with CALASH:
    - During steady_phase, inter-cluster THz transmissions also
      produce echo returns processed by the ISAC module.
    - Anomaly scores feed into the self-healing Monitor phase,
      augmenting heartbeat-based detection with physical-layer
      disaster indicators (faster detection, fewer false alarms).

References
----------
[1] Liu, F. et al. "Integrated Sensing and Communications: Toward
    Dual-Functional Wireless Networks for 6G and Beyond." IEEE JSAC,
    40(6), pp. 1728-1767, 2022. DOI: 10.1109/JSAC.2022.3156632

[2] Zhang, J.A. et al. "An Overview of Signal Processing Techniques
    for Joint Communication and Radar Sensing." IEEE JSAC, 40(6),
    pp. 1596-1631, 2022. DOI: 10.1109/JSAC.2022.3155515

[3] 3GPP TR 22.837 v19.2.0 (2023-09). "Study on Integrated Sensing
    and Communication." (Defines ISAC use cases for 5G-Advanced/6G.)

[4] Wei, Z. et al. "Integrated Sensing and Communication for IoT:
    Synergies with 6G Networks." IEEE IoT Journal, 11(3), 2024.
    DOI: 10.1109/JIOT.2023.3305644
"""

import numpy as np
from typing import Dict, List, Tuple, Optional


# ═══════════════════════════════════════════════════════════════════
# Physical constants
# ═══════════════════════════════════════════════════════════════════
C_LIGHT = 2.998e8       # speed of light (m/s)
K_BOLTZ = 1.381e-23     # Boltzmann constant (J/K)


class ISACModule:
    """
    Integrated Sensing and Communication for 6G disaster WSN.

    Each inter-cluster THz transmission produces radar echo returns
    that are processed to detect structural anomalies (collapsed
    buildings, debris fields, ground deformation).

    The ISAC processing chain:
        1. Transmit OFDM waveform (communication + radar pilot)
        2. Receive echo returns after round-trip propagation
        3. Range-Doppler processing (2D FFT)
        4. CFAR detection on range-Doppler map
        5. Anomaly scoring: compare current echo profile to baseline

    Energy overhead: ISAC adds ~15% to the communication energy
    budget for FFT processing and matched filtering [Liu et al., 2022].
    """

    def __init__(self, config):
        """
        Parameters
        ----------
        config : SimulationConfig
            Must have thz_freq_hz, thz_bandwidth_hz, etc.
        """
        self.freq_hz = getattr(config, 'thz_freq_hz', 140e9)
        self.bandwidth_hz = getattr(config, 'thz_bandwidth_hz', 10e9)
        self.enabled = getattr(config, 'isac_enabled', True)

        # Radar parameters
        # Range resolution: Δr = c / (2·B)
        self.range_resolution = C_LIGHT / (2 * self.bandwidth_hz)
        # Max unambiguous range (limited by PRF ~ round duration)
        self.max_range = getattr(config, 'isac_max_range_m', 50.0)

        # RCS of disaster debris (m²) — typical for rubble/collapsed wall
        # Ref: Skolnik (2008) "Radar Handbook", Table 2.1
        self.rcs_debris = 1.0        # 1 m² (concrete rubble, ~0 dBsm)
        self.rcs_normal = 0.01       # 0.01 m² (background clutter)

        # CFAR detection threshold (Neyman-Pearson, P_fa = 1e-4)
        self.cfar_threshold = 4.0    # ~4σ above noise floor

        # Processing energy: FFT + CFAR per range-Doppler cell
        # Ref: Liu et al. (2022), Table III — ~15% overhead
        self.processing_overhead = 0.15  # fraction of Tx energy

        # Baseline echo profiles (learned during normal operation)
        self._baseline_profiles: Dict[int, np.ndarray] = {}
        self._anomaly_scores: Dict[int, float] = {}
        self._disaster_score_threshold = 0.5

        # Warm-up rounds before ISAC anomaly detection is active
        self._warmup_rounds = 10
        self._current_round = 0

    def initialize(self, network) -> None:
        """Initialize baseline echo profiles for all alive nodes."""
        self._baseline_profiles.clear()
        self._anomaly_scores.clear()
        self._current_round = 0

    def range_resolution_m(self) -> float:
        """Range resolution in meters: Δr = c/(2B)."""
        return self.range_resolution

    def compute_echo_profile(self, tx_node, rx_positions: List[Tuple[float, float]],
                             rng: np.random.Generator,
                             disaster_active: bool = False) -> np.ndarray:
        """
        Simulate radar echo profile from a THz transmission.

        The transmitting node's OFDM waveform reflects off surrounding
        objects (other nodes, structures, debris).  The echo power at
        range bin r is:

            P_echo(r) = P_tx · G² · λ² · σ(r) / ((4π)³ · r⁴)

        where σ(r) is the RCS at range r.

        Parameters
        ----------
        tx_node : Node
            Transmitting node.
        rx_positions : list of (x, y)
            Positions of reflecting objects / other nodes.
        rng : np.random.Generator
            For noise generation.
        disaster_active : bool
            If True, add debris echoes (increased RCS, new reflectors).

        Returns
        -------
        np.ndarray
            Normalized echo power profile (num_range_bins,).
        """
        num_bins = max(1, int(self.max_range / self.range_resolution))
        profile = np.zeros(num_bins, dtype=np.float32)
        wavelength = C_LIGHT / self.freq_hz

        for (rx, ry) in rx_positions:
            d = np.sqrt((tx_node.x - rx) ** 2 + (tx_node.y - ry) ** 2)
            if d < 0.1 or d > self.max_range:
                continue

            bin_idx = min(int(d / self.range_resolution), num_bins - 1)

            # Radar equation (simplified, normalized)
            rcs = self.rcs_normal
            if disaster_active:
                rcs = self.rcs_debris  # increased RCS from rubble

            echo_power = (wavelength ** 2 * rcs) / (d ** 4 + 1e-12)
            profile[bin_idx] += echo_power

        # Add thermal noise
        noise_floor = K_BOLTZ * 300.0 * self.bandwidth_hz
        noise = rng.exponential(noise_floor, num_bins).astype(np.float32)
        profile += noise

        # Normalize
        max_val = profile.max()
        if max_val > 0:
            profile /= max_val

        return profile

    def update_baseline(self, node_id: int, profile: np.ndarray) -> None:
        """
        Update the baseline echo profile for a node (exponential moving average).

        Called during normal operation (pre-disaster) to learn what
        "normal" looks like for each node's radar view.
        """
        alpha = 0.1  # EMA smoothing factor
        if node_id in self._baseline_profiles:
            self._baseline_profiles[node_id] = (
                (1 - alpha) * self._baseline_profiles[node_id]
                + alpha * profile
            )
        else:
            self._baseline_profiles[node_id] = profile.copy()

    def compute_anomaly_score(self, node_id: int,
                              current_profile: np.ndarray) -> float:
        """
        Compute structural anomaly score by comparing current echo
        to baseline profile.

        Score = normalized L2 distance between current and baseline.
        High score → significant change in radar environment → possible
        structural damage / node failure.

        Parameters
        ----------
        node_id : int
            ID of the sensing node.
        current_profile : np.ndarray
            Current echo profile.

        Returns
        -------
        float
            Anomaly score in [0, 1].  > threshold → anomaly detected.
        """
        if node_id not in self._baseline_profiles:
            return 0.0

        baseline = self._baseline_profiles[node_id]
        # Ensure same length
        min_len = min(len(baseline), len(current_profile))
        diff = current_profile[:min_len] - baseline[:min_len]

        # Normalized L2 distance
        norm_baseline = np.linalg.norm(baseline[:min_len]) + 1e-12
        score = np.linalg.norm(diff) / norm_baseline

        # Clip to [0, 1]
        score = min(1.0, score)
        self._anomaly_scores[node_id] = score

        return score

    def detect_structural_anomaly(self, node_id: int) -> bool:
        """Check if node's ISAC anomaly score exceeds detection threshold."""
        return self._anomaly_scores.get(node_id, 0.0) > self._disaster_score_threshold

    def isac_energy_overhead(self, tx_energy: float) -> float:
        """
        Additional energy for ISAC processing (FFT + CFAR).

        Returns
        -------
        float
            Extra energy in Joules (~15% of Tx energy).
        """
        if not self.enabled:
            return 0.0
        return self.processing_overhead * tx_energy

    def process_round(self, network, round_num: int,
                      rng: np.random.Generator,
                      disaster_active: bool = False) -> Dict[int, float]:
        """
        Run ISAC processing for all cluster heads this round.

        Each CH "senses" its environment via radar echo during its
        inter-cluster transmission.  Anomaly scores are updated.

        Parameters
        ----------
        network : Network
            Current network state.
        round_num : int
            Current simulation round.
        rng : np.random.Generator
            For noise generation.
        disaster_active : bool
            Whether disaster damage is currently affecting the area.

        Returns
        -------
        dict
            {node_id: anomaly_score} for all CHs that performed sensing.
        """
        self._current_round = round_num
        if not self.enabled:
            return {}

        scores = {}
        all_positions = [(n.x, n.y) for n in network.alive_nodes()]

        for ch in network.cluster_heads():
            # Compute current echo profile
            profile = self.compute_echo_profile(
                ch, all_positions, rng, disaster_active=disaster_active
            )

            # During warm-up: only update baseline
            if round_num < self._warmup_rounds:
                self.update_baseline(ch.id, profile)
                scores[ch.id] = 0.0
            else:
                # Compute anomaly and selectively update baseline
                score = self.compute_anomaly_score(ch.id, profile)
                scores[ch.id] = score

                # Only update baseline if no anomaly (normal conditions)
                if score < self._disaster_score_threshold * 0.5:
                    self.update_baseline(ch.id, profile)

        return scores

    def get_high_anomaly_nodes(self) -> List[int]:
        """Return node IDs with anomaly score above threshold."""
        return [nid for nid, score in self._anomaly_scores.items()
                if score > self._disaster_score_threshold]

    def get_diagnostics(self) -> dict:
        """Return ISAC diagnostics for logging."""
        scores = list(self._anomaly_scores.values())
        return {
            'isac_enabled': self.enabled,
            'range_resolution_m': self.range_resolution,
            'num_profiled_nodes': len(self._baseline_profiles),
            'mean_anomaly_score': float(np.mean(scores)) if scores else 0.0,
            'max_anomaly_score': float(np.max(scores)) if scores else 0.0,
            'num_anomalies_detected': len(self.get_high_anomaly_nodes()),
        }
