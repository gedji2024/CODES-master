"""
THz/Sub-THz Channel Model for 6G-Integrated WSN
=================================================
Implements the Jornet & Akyildiz (2011) THz propagation model with
molecular absorption, making the framework genuinely 6G-relevant.

The model captures two loss mechanisms unique to THz bands:
    1. Spreading loss:  L_spread(f,d) = (4*pi*f*d/c)^2
    2. Absorption loss: L_abs(f,d) = exp(kappa(f)*d)

where kappa(f) is the molecular absorption coefficient dominated by
water vapour resonance lines in the 0.1-1.0 THz band.

For WSN 6G integration, we model:
    - Sub-THz D2D links (0.1-0.3 THz) for intra-cluster high-rate sensing
    - Conventional sub-6 GHz for inter-cluster long-range routing
    - RIS-assisted link budget improvement for relay nodes

The energy model extends Heinzelman's first-order model with:
    E_Tx_THz(l, d) = l * E_elec + l * P_Tx * T_bit
    where P_Tx is set to overcome THz path loss at distance d.

Operating frequency: 140 GHz (D-band), a candidate for 3GPP Rel-18
FR3 (7.125-71 GHz) and expected 6G sub-THz bands above 100 GHz.

References:
    [1] Jornet, J.M. & Akyildiz, I.F. "Channel Modeling and Capacity
        Analysis for Electromagnetic Wireless Nanonetworks in the
        Terahertz Band." IEEE Trans. Wireless Comm., 10(10), 2011.
    [2] Akyildiz, I.F. et al. "TeraNets: Ultra-broadband Communication
        Networks in the Terahertz Band." IEEE Wireless Comm., 2014.
    [3] Han, C. et al. "Multi-Ray Channel Modeling and Wideband
        Characterization for Wireless Communications in the Terahertz
        Band." IEEE Trans. Wireless Comm., 14(5), 2015.
    [4] Rappaport, T.S. et al. "Wireless Communications and Applications
        Above 100 GHz." IEEE Access, 7, 2019.
    [5] Gordon, I.E. et al. "The HITRAN2020 molecular spectroscopic
        database." JQSRT, 277, 107949, 2022.  (H2O absorption lines)
    [6] 3GPP TR 38.901 v17.0.0 (2022-03). "Study on channel model for
        frequencies from 0.5 to 100 GHz."  (Extended to sub-THz in Rel-18)
    [7] Rec. ITU-R M.2160-0 (2023-11). "IMT-2030 Framework."
    [8] Report ITU-R M.2541-0 (2024-05). "Technical feasibility of
        IMT in bands above 100 GHz."
"""

import numpy as np
from typing import Tuple


# ═══════════════════════════════════════════════════════════════════
# Physical Constants
# ═══════════════════════════════════════════════════════════════════

C_LIGHT = 2.998e8           # speed of light (m/s)
K_BOLTZ = 1.381e-23         # Boltzmann constant (J/K)
PLANCK = 6.626e-34          # Planck constant (J·s)
T_STANDARD = 296.0          # standard temperature (K)
P_STANDARD = 101325.0       # standard pressure (Pa)


# ═══════════════════════════════════════════════════════════════════
# OFDM Waveform Parameters for Sub-THz (140 GHz D-band)
# ═══════════════════════════════════════════════════════════════════
# OFDM is the candidate waveform for sub-THz in 6G (ITU-R M.2541,
# 3GPP Rel-18 FR3 study).  Parameters follow the numerology
# extensions for wide-bandwidth THz channels.
#
# Refs: Rappaport et al. (2019), Akyildiz et al. (2014),
#       Report ITU-R M.2541-0 (2024)
# ═══════════════════════════════════════════════════════════════════

OFDM_PARAMS = {
    'subcarrier_spacing_khz': 480,     # μ=5 numerology (480 kHz SCS)
    'num_subcarriers': 2048,           # Nsc for 10 GHz BW at 480 kHz SCS
    'cp_fraction': 0.07,               # cyclic prefix = 7% of symbol duration
    'symbol_duration_us': 2.08 + 0.146,  # T_sym = 1/Δf + T_cp ≈ 2.23 μs
    'ofdm_efficiency': 0.93,           # after CP + guard overhead
    # PAPR (peak-to-average power ratio) backoff for sub-THz PA
    'papr_backoff_db': 3.0,            # typical OFDM PAPR backoff
}


# ═══════════════════════════════════════════════════════════════════
# Molecular Absorption Model
# ═══════════════════════════════════════════════════════════════════

# Water vapour absorption lines in the 0.1-1.0 THz band
# (Simplified from HITRAN database -- dominant lines only)
# Format: (centre_freq_THz, line_strength_cm^-2, half_width_GHz)
# Source: Jornet & Akyildiz 2011, Table I; cross-checked with
#         HITRAN2020 (Gordon et al., JQSRT 277, 107949, 2022)

_H2O_LINES = [
    (0.557, 1.54e-22, 2.86),    # 557 GHz line
    (0.752, 3.06e-23, 3.21),    # 752 GHz line
    (0.988, 1.03e-22, 2.95),    # 988 GHz line
    (0.183, 2.36e-24, 2.65),    # 183 GHz line (weak but wide)
    (0.325, 8.10e-25, 2.72),    # 325 GHz line (weak)
    (0.380, 4.82e-23, 2.90),    # 380 GHz line (moderate)
    (0.448, 1.12e-24, 2.78),    # 448 GHz line (weak)
]

# ── Absorption coefficient cache (constant for given freq/humidity) ──
_absorption_cache: dict = {}


def molecular_absorption_coefficient(freq_thz: float,
                                     humidity_pct: float = 50.0,
                                     temperature_k: float = T_STANDARD,
                                     pressure_pa: float = P_STANDARD
                                     ) -> float:
    """
    Compute molecular absorption coefficient κ(f) in Neper/m.

    Uses a sum of Lorentzian line shapes from the HITRAN database,
    scaled by water vapour mixing ratio.

    Parameters
    ----------
    freq_thz : float
        Frequency in THz.
    humidity_pct : float
        Relative humidity in percent.
    temperature_k : float
        Ambient temperature in Kelvin.
    pressure_pa : float
        Atmospheric pressure in Pascals.

    Returns
    -------
    float
        Absorption coefficient κ(f) in Neper/m.
    """
    # Water vapour partial pressure (Tetens formula)
    key = (freq_thz, humidity_pct, temperature_k, pressure_pa)
    cached = _absorption_cache.get(key)
    if cached is not None:
        return cached

    t_celsius = temperature_k - 273.15
    p_sat = 610.78 * np.exp(17.269 * t_celsius / (t_celsius + 237.3))
    p_h2o = humidity_pct / 100.0 * p_sat  # Pa

    # Mixing ratio (molecules/m³) via ideal gas law
    n_h2o = p_h2o / (K_BOLTZ * temperature_k)  # molecules/m³

    # Sum of Lorentzian line contributions
    kappa = 0.0
    freq_hz = freq_thz * 1e12

    for f0_thz, strength, hw_ghz in _H2O_LINES:
        f0_hz = f0_thz * 1e12
        hw_hz = hw_ghz * 1e9

        # Pressure-broadened half-width
        alpha_L = hw_hz * (pressure_pa / P_STANDARD) * \
                  np.sqrt(T_STANDARD / temperature_k)

        # Lorentzian line shape (cm⁻¹ → convert to m⁻¹)
        numerator = alpha_L / np.pi
        denominator = (freq_hz - f0_hz)**2 + alpha_L**2
        line_shape = numerator / max(denominator, 1e-30)

        # Contribution: strength (cm⁻²/molecule) × n_h2o (molecules/m³)
        # × line_shape (1/Hz) → convert to Neper/m
        kappa += strength * 1e-4 * n_h2o * line_shape * C_LIGHT

    result = max(kappa, 0.0)
    _absorption_cache[key] = result
    return result


def thz_path_loss_db(freq_thz: float, distance_m: float,
                     humidity_pct: float = 50.0) -> float:
    """
    Total THz path loss in dB.

    L_total(f,d) = L_spread(f,d) + L_abs(f,d)

    Parameters
    ----------
    freq_thz : float
        Carrier frequency in THz.
    distance_m : float
        Link distance in meters.
    humidity_pct : float
        Relative humidity in percent.

    Returns
    -------
    float
        Total path loss in dB.
    """
    if distance_m <= 0:
        return 0.0

    freq_hz = freq_thz * 1e12

    # Free-space spreading loss (Friis)
    l_spread_db = 20 * np.log10(4 * np.pi * distance_m * freq_hz / C_LIGHT)

    # Molecular absorption loss
    kappa = molecular_absorption_coefficient(freq_thz, humidity_pct)
    l_abs_db = 10 * np.log10(np.exp(1)) * kappa * distance_m  # Np → dB

    return l_spread_db + l_abs_db


def thz_capacity_bps(freq_thz: float, bandwidth_ghz: float,
                     distance_m: float, tx_power_dbm: float = 0.0,
                     humidity_pct: float = 50.0) -> float:
    """
    Shannon capacity of a THz link.

    C = B · log₂(1 + SNR)
    SNR = P_Tx / (L_total · N_0 · B)

    Parameters
    ----------
    freq_thz : float
        Centre frequency in THz.
    bandwidth_ghz : float
        Bandwidth in GHz.
    distance_m : float
        Distance in meters.
    tx_power_dbm : float
        Transmit power in dBm.
    humidity_pct : float
        Relative humidity (%).

    Returns
    -------
    float
        Channel capacity in bits per second.
    """
    bandwidth_hz = bandwidth_ghz * 1e9
    tx_power_w = 10 ** ((tx_power_dbm - 30) / 10)

    pl_db = thz_path_loss_db(freq_thz, distance_m, humidity_pct)
    pl_linear = 10 ** (pl_db / 10)

    # Thermal noise
    noise_w = K_BOLTZ * T_STANDARD * bandwidth_hz

    snr = tx_power_w / (pl_linear * noise_w) if pl_linear > 0 else 0
    if snr <= 0:
        return 0.0

    return bandwidth_hz * np.log2(1 + snr)


# ═══════════════════════════════════════════════════════════════════
# RIS-Assisted Link Budget
# ═══════════════════════════════════════════════════════════════════

def ris_gain_db(num_elements: int, freq_thz: float,
                element_spacing_lambda: float = 0.5) -> float:
    """
    LEGACY simplified RIS gain.  Retained for backward compatibility.
    Use ``CascadedRISChannel`` for full cascaded path-loss model.
    """
    if num_elements <= 0:
        return 0.0
    return 20.0 * np.log10(num_elements)


class CascadedRISChannel:
    """
    Cascaded RIS-Assisted Channel Model (Tx → RIS → Rx).

    Implements the full multiplicative fading model from [1] rather
    than the simplified ``20·log₁₀(N)`` gain used previously.

    End-to-end path loss (cascaded):
        PL_total = PL_Tx_RIS · PL_RIS_Rx / G_RIS(N, Δφ)

    where:
        PL_Tx_RIS  = free-space path loss from Tx to RIS panel
        PL_RIS_Rx  = free-space path loss from RIS panel to Rx
        G_RIS      = beamforming gain accounting for:
                     - Number of elements N
                     - Element area A_e = (λ/2)²
                     - Phase alignment error Δφ (hardware impairment)
                     - Array factor with spatial correlation

    Realistic impairments:
        1. **Phase quantization**: Practical RIS use b-bit phase shifters
           (b=1-3), causing quantization loss ~ sinc²(2^{-b}) [2]
        2. **Mutual coupling**: Adjacent elements couple → effective
           gain < N² (modelled via coupling factor η ∈ [0.8, 1.0])
        3. **Cascaded product fading**: The Tx→RIS and RIS→Rx channels
           multiply (not add), creating a double-fading effect that
           reduces the effective SNR gain compared to direct beamforming.

    RIS placement strategy:
        The RIS panel is placed at a configurable position (ris_x, ris_y).
        In disaster WSN, this represents infrastructure-mounted panels
        (building walls, utility poles) that redirect THz beams around
        obstacles and extend coverage post-disaster.

    References
    ----------
    [1] Wu, Q. & Zhang, R. "Intelligent Reflecting Surface Enhanced
        Wireless Network via Joint Active and Passive Beamforming."
        IEEE TWC, 18(8), pp. 4005-4015, 2019.
        DOI: 10.1109/TWC.2019.2918609

    [2] Wu, Q. & Zhang, R. "Beamforming Optimization for Wireless
        Network Aided by Intelligent Reflecting Surface With Discrete
        Phase Shifts." IEEE Trans. Comm., 68(3), pp. 1838-1851, 2020.
        DOI: 10.1109/TCOMM.2019.2958916

    [3] Ozdogan, O., Bjornson, E. & Larsson, E.G. "Intelligent
        Reflecting Surfaces: Physics, Propagation, and Reconfigurable
        Systems." IEEE Wireless Comm. Letters, 9(5), 2020.
        DOI: 10.1109/LWC.2019.2960779

    [4] Di Renzo, M. et al. "Smart Radio Environments Empowered by
        Reconfigurable Intelligent Surfaces: How It Works, State of
        Research, and The Road Ahead." IEEE JSAC, 38(11), 2020.
        DOI: 10.1109/JSAC.2020.3007211

    [5] Zheng, B. & Zhang, R. "Intelligent Reflecting Surface-Enhanced
        OFDM." IEEE Trans. Wireless Comm., 19(6), 2020.
        DOI: 10.1109/TWC.2020.2978439   (RIS with imperfect CSI)

    [6] Xing, Z. et al. "Channel estimation for RIS-aided mmWave MIMO
        with practical beam squint." IEEE TWC, 23(2), 2024.
        DOI: 10.1109/TWC.2023.3291700   (channel estimation error)
    """

    def __init__(self, config):
        """
        Parameters
        ----------
        config : SimulationConfig
            Must have ris_elements, thz_freq_hz, etc.
        """
        self.N = getattr(config, 'ris_elements', 64)
        self.freq_hz = getattr(config, 'thz_freq_hz', 140e9)
        self.freq_thz = self.freq_hz / 1e12
        self.wavelength = C_LIGHT / self.freq_hz

        # Element area: half-wavelength spacing → A_e = (λ/2)²
        self.element_area = (self.wavelength / 2.0) ** 2

        # Phase quantization bits (practical hardware: 1-3 bits)
        self.phase_bits = getattr(config, 'ris_phase_bits', 2)

        # Mutual coupling factor η ∈ [0.8, 1.0]
        # η = 1.0 → no coupling (ideal)
        # η = 0.85 → typical sub-THz RIS with λ/2 spacing [3]
        self.coupling_factor = getattr(config, 'ris_coupling_factor', 0.85)

        # RIS position (default: center-top of deployment area)
        self.ris_x = getattr(config, 'ris_x', config.area_width / 2.0)
        self.ris_y = getattr(config, 'ris_y', config.area_height * 0.8)

        # Precompute phase quantization loss
        # For b-bit phase shifter: loss = sinc²(π / 2^b)
        # b=1: -3.92 dB, b=2: -0.91 dB, b=3: -0.22 dB
        self._quant_loss = np.sinc(1.0 / (2 ** self.phase_bits)) ** 2

        # ─── Channel estimation error model (Xing et al., 2024) ─────
        # Imperfect CSI reduces the effective beamforming gain.
        # With pilot-based estimation, the channel estimate has error
        # variance σ²_e that degrades coherent gain from N² to N²·(1-σ²_e).
        # For N_pilot pilot symbols:
        #   σ²_e ≈ 1 / (N_pilot · SNR_pilot)
        # We model this as a multiplicative CSI quality factor ∈ (0, 1].
        # Practical sub-THz RIS achieves ~0.85-0.95 CSI quality with
        # hierarchical beam training (Zheng & Zhang, 2020).
        self._csi_quality = 0.90  # 90% CSI quality (10% estimation error)

        # ─── Beam misalignment model (sub-THz specific) ─────────────
        # At 140 GHz, beamwidth ∝ λ/(N·d_spacing) ≈ 0.03 rad for N=64.
        # Mechanical vibrations (esp. post-disaster) cause pointing errors.
        # Loss from misalignment (Gaussian beam model):
        #   L_misalign = exp(-2·θ_error² / θ_3dB²)
        # where θ_3dB ≈ λ/(√N · d) is the half-power beamwidth.
        # Default: σ_pointing = 0.5° = 8.7 mrad (typical MEMS mirror)
        self._pointing_error_rad = 0.0087  # 0.5° RMS pointing error
        beamwidth_rad = self.wavelength / (np.sqrt(self.N) * self.wavelength / 2)
        self._beam_misalign_loss = np.exp(
            -2.0 * self._pointing_error_rad ** 2 / max(beamwidth_rad ** 2, 1e-12)
        )

    def _fspl_linear(self, distance_m: float) -> float:
        """Free-space path loss (linear scale), including THz absorption."""
        if distance_m <= 0:
            return 1.0
        pl_db = thz_path_loss_db(self.freq_thz, distance_m)
        return 10 ** (pl_db / 10)

    def cascaded_gain_db(self, d_tx_ris: float, d_ris_rx: float) -> float:
        """
        Compute cascaded RIS path-loss reduction in dB.

        The effective RIS gain compensating the Tx→RIS→Rx path is:

            G_RIS = (N · A_e / (4π))² · η · sinc²(π/2^b) / (PL_tx · PL_rx)

        But since we report it as a gain relative to the direct Tx→Rx link:

            ΔPL = PL_direct / PL_cascaded

        For practical use, we compute the NET path loss of the RIS-assisted
        link and compare it to the direct path.

        Parameters
        ----------
        d_tx_ris : float
            Distance from Tx to RIS panel (meters).
        d_ris_rx : float
            Distance from RIS panel to Rx (meters).

        Returns
        -------
        float
            Effective cascaded gain in dB (positive = beneficial).
        """
        if d_tx_ris <= 0 or d_ris_rx <= 0:
            return 0.0

        # Individual path losses (linear)
        pl_tx_ris = self._fspl_linear(d_tx_ris)
        pl_ris_rx = self._fspl_linear(d_ris_rx)

        # RIS array gain: |sum of element contributions|²
        # With N elements, perfect phase → N² gain
        # With quantization + coupling + CSI error + misalignment:
        #   G = N² · η · sinc²(π/2^b) · (1-σ²_e) · L_misalign
        array_gain = (self.N ** 2
                      * self.coupling_factor
                      * self._quant_loss
                      * self._csi_quality
                      * self._beam_misalign_loss)

        # Each element has aperture A_e, so element gain = 4π·A_e / λ²
        element_gain = 4 * np.pi * self.element_area / (self.wavelength ** 2)

        # Cascaded link: PL_cascaded = PL_tx_ris · PL_ris_rx / (array_gain · element_gain²)
        cascaded_pl = (pl_tx_ris * pl_ris_rx) / max(array_gain * element_gain ** 2, 1e-30)

        # Convert to dB gain (relative to cascaded path loss without RIS)
        # Without RIS, the reflected path has PL_tx_ris · PL_ris_rx with NO array gain
        # So the gain FROM the RIS is just the array + element contribution
        gain_linear = array_gain * element_gain ** 2
        gain_db = 10.0 * np.log10(max(gain_linear, 1e-30))

        return gain_db

    def ris_assisted_path_loss_db(self, tx_x: float, tx_y: float,
                                   rx_x: float, rx_y: float) -> float:
        """
        Compute RIS-assisted end-to-end path loss (dB).

        If the RIS-assisted path has lower loss than the direct path,
        the better (lower PL) option is returned.  This models the
        protocol selecting the best available path.

        Parameters
        ----------
        tx_x, tx_y : float
            Transmitter position.
        rx_x, rx_y : float
            Receiver position.

        Returns
        -------
        float
            Effective path loss in dB (minimum of direct & RIS-assisted).
        """
        # Direct path
        d_direct = np.sqrt((tx_x - rx_x)**2 + (tx_y - rx_y)**2)
        pl_direct = thz_path_loss_db(self.freq_thz, d_direct)

        # RIS-assisted path
        d_tx_ris = np.sqrt((tx_x - self.ris_x)**2 + (tx_y - self.ris_y)**2)
        d_ris_rx = np.sqrt((self.ris_x - rx_x)**2 + (self.ris_y - rx_y)**2)
        pl_ris = (thz_path_loss_db(self.freq_thz, d_tx_ris)
                  + thz_path_loss_db(self.freq_thz, d_ris_rx)
                  - self.cascaded_gain_db(d_tx_ris, d_ris_rx))

        return min(pl_direct, pl_ris)

    def get_diagnostics(self) -> dict:
        """Return RIS configuration diagnostics."""
        return {
            'num_elements': self.N,
            'freq_ghz': self.freq_hz / 1e9,
            'wavelength_mm': self.wavelength * 1e3,
            'element_area_mm2': self.element_area * 1e6,
            'phase_bits': self.phase_bits,
            'quant_loss_db': 10 * np.log10(max(self._quant_loss, 1e-30)),
            'coupling_factor': self.coupling_factor,
            'csi_quality': self._csi_quality,
            'beam_misalign_loss_db': 10 * np.log10(
                max(self._beam_misalign_loss, 1e-30)),
            'pointing_error_deg': np.degrees(self._pointing_error_rad),
            'ideal_gain_db': 20 * np.log10(self.N),
            'practical_gain_db': 10 * np.log10(
                self.N**2 * self.coupling_factor * self._quant_loss
                * self._csi_quality * self._beam_misalign_loss),
            'ris_position': (self.ris_x, self.ris_y),
            'ofdm_params': OFDM_PARAMS,
        }


# ═══════════════════════════════════════════════════════════════════
# 6G-Aware Energy Model Extension
# ═══════════════════════════════════════════════════════════════════

class THz6GEnergyModel:
    """
    Extended energy model for 6G-integrated WSN.

    Adds THz/sub-THz intra-cluster communication on top of the
    standard first-order radio model for inter-cluster routing.

    Architecture:
        - Intra-cluster (member→CH):  Sub-THz D2D (0.14 THz), short range
        - Inter-cluster (CH→CH→BS):   Sub-6 GHz, long range (Heinzelman)
        - Optional RIS assistance for relay links

    The sub-THz intra-cluster link provides:
        - 10-100× higher data rate than sub-6 GHz (wider bandwidth)
        - Lower latency for real-time disaster sensing
        - But higher path loss → only viable at short range (< 30m)
    """

    def __init__(self, config, cascaded_ris: 'CascadedRISChannel' = None):
        # Legacy sub-6 GHz parameters (Heinzelman model)
        self.E_elec = config.E_elec       # 50 nJ/bit
        self.eps_fs = config.eps_fs        # 10 pJ/bit/m²
        self.eps_mp = config.eps_mp        # 0.0013 pJ/bit/m⁴
        self.E_DA = config.E_DA
        self.E_sense = config.E_sense
        self.d0 = config.d0

        # RIS panel position (for inter-cluster gain calculation)
        self._ris_x = getattr(config, 'ris_x', 100.0)
        self._ris_y = getattr(config, 'ris_y', 160.0)

        # Sub-THz parameters for intra-cluster D2D
        self.thz_freq = getattr(config, 'thz_freq_hz', 140e9) / 1e12  # convert Hz to THz
        self.thz_bw = getattr(config, 'thz_bandwidth_hz', 10e9) / 1e9  # convert Hz to GHz
        self.thz_tx_power_dbm = getattr(config, 'thz_tx_power_dbm', 10.0)
        self.thz_max_range = getattr(config, 'thz_max_range_m', 30.0)  # meters
        self.humidity = getattr(config, 'humidity_pct', 50.0)

        # RIS parameters
        self.ris_elements = getattr(config, 'ris_elements', 64)
        self.ris_enabled = getattr(config, 'ris_enabled', True)

        # ─── Cascaded RIS channel model (full CSI + beam misalignment) ───
        # When provided, replaces the legacy 20·log₁₀(N) gain with the
        # full cascaded model including phase quantization, mutual
        # coupling, channel estimation error, and beam misalignment.
        self._cascaded_ris = cascaded_ris

        # ─── OFDM efficiency (applied to effective data rate) ────────
        # Sub-THz OFDM with 480 kHz SCS loses ~7% to CP and ~3 dB to
        # PAPR back-off.  These are first-order physical-layer costs
        # that reduce the usable capacity and increase Tx power.
        self._ofdm_efficiency = OFDM_PARAMS['ofdm_efficiency']  # 0.93
        self._papr_backoff_linear = 10 ** (OFDM_PARAMS['papr_backoff_db'] / 10)

        # Sub-THz circuit power
        self.P_circuit_thz = getattr(config, 'thz_circuit_power_w', 0.05)
        # 50 mW circuit power for THz front-end (ADC + mixer + LNA)

    def tx_energy_thz(self, num_bits: int, distance: float) -> float:
        """
        Compute THz intra-cluster transmission energy.

        E_Tx_THz = ℓ · E_elec + P_Tx_required · T_bit · ℓ + P_circuit · T_bit · ℓ

        where P_Tx is set to achieve target SNR at receiver across distance d.

        Falls back to sub-6 GHz if distance exceeds THz max range.

        Parameters
        ----------
        num_bits : int
            Bits to transmit.
        distance : float
            Distance to receiver (meters).

        Returns
        -------
        float
            Energy in Joules.
        """
        if distance > self.thz_max_range or distance <= 0:
            return self.tx_energy_sub6(num_bits, distance)

        # THz path loss
        pl_db = thz_path_loss_db(self.thz_freq, distance, self.humidity)

        # RIS gain: prefer full cascaded model (CSI + beam misalignment)
        # over legacy 20·log₁₀(N) approximation
        if self.ris_enabled:
            if self._cascaded_ris is not None:
                # Full cascaded model: Tx→RIS→Rx with impairments
                # Assume RIS is roughly equidistant (symmetric placement)
                d_half = distance / 2.0
                pl_db -= self._cascaded_ris.cascaded_gain_db(d_half, d_half)
            else:
                pl_db -= ris_gain_db(self.ris_elements, self.thz_freq)

        pl_linear = 10 ** (pl_db / 10)

        # Required transmit power for target BER (QPSK, BER=1e-6 → SNR≈13.5 dB)
        target_snr = 10 ** (13.5 / 10)
        noise_per_bit = K_BOLTZ * T_STANDARD * (self.thz_bw * 1e9)
        p_tx = target_snr * noise_per_bit * pl_linear

        # PAPR back-off: OFDM sub-THz PA must operate with headroom
        # to handle peak-to-average power ratio (3 dB typical)
        p_tx *= self._papr_backoff_linear

        # Transmission time (based on OFDM-adjusted capacity)
        capacity = thz_capacity_bps(
            self.thz_freq, self.thz_bw, distance,
            10 * np.log10(max(p_tx, 1e-30)) + 30, self.humidity
        )
        if capacity <= 0:
            return self.tx_energy_sub6(num_bits, distance)

        # Apply OFDM efficiency: CP overhead + guard band reduce
        # usable throughput by ~7% (480 kHz SCS, 7% CP fraction)
        effective_capacity = capacity * self._ofdm_efficiency
        t_total = num_bits / effective_capacity  # seconds

        # Energy = electronics + amplifier + circuit
        e_elec = num_bits * self.E_elec
        e_amp = p_tx * t_total
        e_circuit = self.P_circuit_thz * t_total

        return e_elec + e_amp + e_circuit

    def tx_energy_sub6(self, num_bits: int, distance: float) -> float:
        """Standard Heinzelman first-order radio Tx energy."""
        electronics = num_bits * self.E_elec
        if distance < self.d0:
            amplifier = num_bits * self.eps_fs * distance ** 2
        else:
            amplifier = num_bits * self.eps_mp * distance ** 4
        return electronics + amplifier

    def tx_energy(self, num_bits: int, distance: float,
                  use_thz: bool = False) -> float:
        """
        Unified Tx energy interface.

        Parameters
        ----------
        num_bits : int
            Bits to transmit.
        distance : float
            Distance to receiver.
        use_thz : bool
            If True, use THz for short-range intra-cluster.
            If False, use sub-6 GHz.
        """
        if use_thz and distance <= self.thz_max_range:
            return self.tx_energy_thz(num_bits, distance)
        return self.tx_energy_sub6(num_bits, distance)

    def rx_energy(self, num_bits: int) -> float:
        """Reception energy (same for both bands)."""
        return num_bits * self.E_elec

    def da_energy(self, num_bits: int, num_signals: int) -> float:
        """Data aggregation energy."""
        return num_bits * num_signals * self.E_DA

    def sense_energy(self, num_bits: int) -> float:
        """Sensing energy."""
        return num_bits * self.E_sense

    def total_member_cost(self, num_bits: int, dist_to_ch: float,
                          use_thz: bool = False) -> float:
        """Total energy for a member: sense + Tx to CH."""
        return self.sense_energy(num_bits) + \
               self.tx_energy(num_bits, dist_to_ch, use_thz=use_thz)

    def total_ch_cost(self, num_bits: int, num_members: int,
                      dist_to_next: float) -> float:
        """Total CH energy: receive + aggregate + Tx to next hop (sub-6 GHz)."""
        rx_cost = num_members * self.rx_energy(num_bits)
        agg_cost = self.da_energy(num_bits, num_members)
        tx_cost = self.tx_energy_sub6(num_bits, dist_to_next)
        return rx_cost + agg_cost + tx_cost

    def get_link_budget_info(self, distance: float) -> dict:
        """Return link budget diagnostics for a THz link."""
        pl = thz_path_loss_db(self.thz_freq, distance, self.humidity)
        if self.ris_enabled:
            if self._cascaded_ris is not None:
                d_half = distance / 2.0
                ris_g = self._cascaded_ris.cascaded_gain_db(d_half, d_half)
            else:
                ris_g = ris_gain_db(self.ris_elements, self.thz_freq)
        else:
            ris_g = 0.0
        cap = thz_capacity_bps(self.thz_freq, self.thz_bw, distance,
                               self.thz_tx_power_dbm, self.humidity)
        effective_cap = cap * self._ofdm_efficiency
        return {
            'path_loss_db': pl,
            'ris_gain_db': ris_g,
            'effective_pl_db': pl - ris_g,
            'capacity_mbps': cap / 1e6,
            'effective_capacity_mbps': effective_cap / 1e6,
            'ofdm_efficiency': self._ofdm_efficiency,
            'papr_backoff_db': OFDM_PARAMS['papr_backoff_db'],
            'cascaded_ris_active': self._cascaded_ris is not None,
            'thz_viable': distance <= self.thz_max_range,
        }

    # ─── Convenience aliases for CALASH protocol integration ─────

    def intra_cluster_energy(self, num_bits: int, distance: float) -> float:
        """Intra-cluster TX energy using sub-THz D2D (short-range)."""
        return self.tx_energy_thz(num_bits, distance)

    def inter_cluster_energy(self, num_bits: int, distance: float,
                              tx_x: float = None, tx_y: float = None) -> float:
        """Inter-cluster TX energy using sub-6 GHz WITH RIS assistance.

        The 64-element RIS panel at (ris_x, ris_y) reflects sub-6 GHz
        signals toward the BS, reducing path loss for CHs within its
        coverage cone.  Gain decays linearly with distance from the RIS
        to model the limited angular coverage of a planar array.

        RIS gain at sub-6 GHz (3.5 GHz) is lower than at THz due to
        larger wavelength → wider beamwidth → lower directivity.
        Conservative estimate: up to 4 dB for optimally placed CHs,
        0 dB at edge of coverage (80m from RIS).

        Refs: Wu & Zhang (2019), Ozdogan et al. (2020), Bjornson (2020)
        """
        electronics = num_bits * self.E_elec
        if distance < self.d0:
            amplifier = num_bits * self.eps_fs * distance ** 2
        else:
            amplifier = num_bits * self.eps_mp * distance ** 4

        # RIS-assisted sub-6 GHz gain for inter-cluster relay links
        if self.ris_enabled and tx_x is not None and tx_y is not None:
            d_to_ris = np.sqrt((tx_x - self._ris_x)**2 +
                               (tx_y - self._ris_y)**2)
            ris_coverage = 80.0  # meters: effective RIS coverage radius
            if d_to_ris < ris_coverage:
                # Up to 4 dB gain at optimal position, linear decay to 0
                gain_db = 4.0 * (1.0 - d_to_ris / ris_coverage)
                amplifier /= 10 ** (gain_db / 10)

        return electronics + amplifier


# ═══════════════════════════════════════════════════════════════════
# 6G Network Slice Manager
# ═══════════════════════════════════════════════════════════════════

class NetworkSliceManager:
    """
    5G/6G network slicing for heterogeneous WSN traffic.

    Implements three ITU-R IMT-2020 service categories as network
    slices, each with distinct QoS parameters and resource allocation:

        1. **URLLC** (Ultra-Reliable Low-Latency Communication):
           For disaster emergency alerts and self-healing control packets.
           Prioritised scheduling, minimal latency, high reliability.
           - Max latency: 1 ms
           - Reliability: 99.999% (5-nines)
           - Bandwidth: reserved minimum (100 kbps per node)

        2. **mMTC** (massive Machine-Type Communication):
           For regular periodic sensor monitoring (bulk of traffic).
           Best-effort, high density, energy-efficient.
           - Max latency: 10 s (relaxed)
           - Density: up to 10^6 devices/km²
           - Bandwidth: shared pool

        3. **eMBB** (enhanced Mobile Broadband):
           For high-fidelity disaster imagery / uncompressed sensing.
           High throughput using THz D2D links when available.
           - Max latency: 4 ms
           - Bandwidth: up to 10 Gbps (THz)

    The CALASH protocol selects the appropriate slice based on:
        - Traffic type (control → URLLC, data → mMTC or eMBB)
        - Disaster state (recovery → URLLC priority boost)
        - Carbon intensity (high CI → defer mMTC, never defer URLLC)

    Resource allocation follows a proportional fairness model:
        R_slice = R_total × w_slice / Σ w_j
    where weights are dynamically adjusted based on network state.

    References
    ----------
    [1] 3GPP TS 23.501 v17.7.0 (2023). "System architecture for the
        5G System (5GS)." (Network slicing framework.)
    [2] ITU-R M.2083-0 (2015). "IMT Vision — Framework and overall
        objectives of the future development of IMT for 2020 and beyond."
    [3] Foukas, X. et al. "Network Slicing in 5G: Survey and Challenges."
        IEEE Comm. Magazine, 55(5), 2017. DOI: 10.1109/MCOM.2017.1600951
    [4] Afolabi, I. et al. "Network Slicing & Softwarization: A Survey
        on Principles, Enabling Technologies & Solutions." IEEE COMST,
        20(3), 2018. DOI: 10.1109/COMST.2018.2815638
    """

    # Slice type constants
    URLLC = 'urllc'
    MMTC = 'mmtc'
    EMBB = 'embb'

    # Slice QoS profiles (3GPP TS 23.501 compliant)
    SLICE_PROFILES = {
        'urllc': {
            'name': 'URLLC (Disaster Emergency)',
            'max_latency_ms': 1.0,
            'reliability_target': 0.99999,
            'priority': 1,           # highest priority
            'min_bandwidth_kbps': 100,
            'max_retransmissions': 3,
            'preemptive': True,      # can preempt mMTC resources
            'carbon_deferrable': False,  # NEVER defer emergency traffic
        },
        'mmtc': {
            'name': 'mMTC (Regular Monitoring)',
            'max_latency_ms': 10000.0,
            'reliability_target': 0.99,
            'priority': 3,           # lowest priority
            'min_bandwidth_kbps': 1,
            'max_retransmissions': 1,
            'preemptive': False,
            'carbon_deferrable': True,   # CAN defer when CI is high
        },
        'embb': {
            'name': 'eMBB (High-Fidelity Sensing)',
            'max_latency_ms': 4.0,
            'reliability_target': 0.999,
            'priority': 2,           # medium priority
            'min_bandwidth_kbps': 1000,
            'max_retransmissions': 2,
            'preemptive': False,
            'carbon_deferrable': False,
        },
    }

    def __init__(self, config=None):
        """
        Initialize the network slice manager.

        Parameters
        ----------
        config : SimulationConfig, optional
            If provided, uses config parameters for bandwidth allocation.
        """
        # Dynamic resource weights (adjusted per round)
        self._weights = {
            self.URLLC: 0.3,
            self.MMTC: 0.5,
            self.EMBB: 0.2,
        }

        # Slice utilisation tracking (packets per round)
        self._round_packets = {s: 0 for s in [self.URLLC, self.MMTC, self.EMBB]}
        self._total_packets = {s: 0 for s in [self.URLLC, self.MMTC, self.EMBB]}

        # Total available bandwidth (from THz + sub-6 GHz)
        thz_bw = getattr(config, 'thz_bandwidth_hz', 10e9) if config else 10e9
        sub6_bw = 20e6  # 20 MHz sub-6 GHz (typical LTE/NR allocation)
        self._total_bandwidth_hz = thz_bw + sub6_bw

        # Disaster mode flag
        self._disaster_active = False

    def classify_traffic(self, packet_type: str = 'data',
                         is_recovery: bool = False,
                         is_critical: bool = False) -> str:
        """
        Classify a packet into the appropriate network slice.

        Parameters
        ----------
        packet_type : str
            'control' (heartbeat, CH election) or 'data' (sensor readings).
        is_recovery : bool
            Whether the network is in disaster recovery mode.
        is_critical : bool
            Whether the packet contains high-priority data.

        Returns
        -------
        str
            Slice type: 'urllc', 'mmtc', or 'embb'.
        """
        # Control packets during recovery → URLLC (highest priority)
        if packet_type == 'control' and is_recovery:
            return self.URLLC

        # Any packet during recovery flagged as critical → URLLC
        if is_critical and is_recovery:
            return self.URLLC

        # Control packets (heartbeats, beacons) → URLLC
        if packet_type == 'control':
            return self.URLLC

        # High-fidelity data (uncompressed or rho > 0.7) → eMBB
        if is_critical:
            return self.EMBB

        # Regular sensor data → mMTC
        return self.MMTC

    def get_slice_qos(self, slice_type: str) -> dict:
        """Return QoS profile for a given slice."""
        return self.SLICE_PROFILES.get(slice_type, self.SLICE_PROFILES['mmtc'])

    def is_carbon_deferrable(self, slice_type: str) -> bool:
        """Check if traffic on this slice can be deferred for carbon savings."""
        profile = self.get_slice_qos(slice_type)
        return profile.get('carbon_deferrable', True)

    def get_bandwidth_allocation(self, slice_type: str) -> float:
        """
        Get allocated bandwidth for a slice (proportional fairness).

        R_slice = R_total × w_slice / Σ w_j

        During disaster recovery, URLLC weight is boosted 2×.

        Returns
        -------
        float
            Allocated bandwidth in Hz.
        """
        weights = self._weights.copy()
        if self._disaster_active:
            weights[self.URLLC] *= 2.0  # boost emergency bandwidth

        total_weight = sum(weights.values())
        fraction = weights.get(slice_type, 0.1) / total_weight
        return self._total_bandwidth_hz * fraction

    def get_energy_multiplier(self, slice_type: str) -> float:
        """
        Energy cost multiplier for slice-specific transmission.

        URLLC: 1.2× (retransmissions + coding overhead for reliability)
        eMBB:  1.0× (standard transmission)
        mMTC:  0.8× (relaxed reliability → less coding overhead)

        Returns
        -------
        float
            Multiplicative energy factor.
        """
        multipliers = {
            self.URLLC: 1.2,   # reliability overhead
            self.EMBB: 1.0,    # standard
            self.MMTC: 0.8,    # relaxed QoS → save energy
        }
        return multipliers.get(slice_type, 1.0)

    def record_packet(self, slice_type: str, count: int = 1):
        """Record packet transmission on a slice (for utilisation tracking)."""
        self._round_packets[slice_type] = (
            self._round_packets.get(slice_type, 0) + count)
        self._total_packets[slice_type] = (
            self._total_packets.get(slice_type, 0) + count)

    def end_round(self):
        """Reset per-round counters and update weights."""
        # Adaptive weight adjustment based on utilisation
        total = sum(self._round_packets.values()) or 1
        for s in [self.URLLC, self.MMTC, self.EMBB]:
            util = self._round_packets[s] / total
            # Smooth weight update (EMA)
            self._weights[s] = 0.9 * self._weights[s] + 0.1 * max(util, 0.05)

        self._round_packets = {s: 0 for s in [self.URLLC, self.MMTC, self.EMBB]}

    def set_disaster_mode(self, active: bool):
        """Enable/disable disaster recovery mode for slice prioritisation."""
        self._disaster_active = active

    def get_diagnostics(self) -> dict:
        """Return slice manager diagnostics."""
        return {
            'weights': self._weights.copy(),
            'total_packets': self._total_packets.copy(),
            'disaster_active': self._disaster_active,
        }
