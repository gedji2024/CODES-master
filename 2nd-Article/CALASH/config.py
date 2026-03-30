"""
CALASH Framework Configuration
==============================
Carbon-Aware Lifecycle-Autonomous Self-Healing Framework
for 6G-Integrated Disaster Sensor Networks.

All simulation parameters in one place for reproducibility.
Units: Energy in Joules, Distance in meters, Carbon in gCO2eq.

Default parameter values and their sources:
    - Radio model:     Heinzelman et al. (2000), DOI: 10.1109/HICSS.2000.926982
    - Network:         200 nodes in 200x200m, standard WSN benchmark [ibid.]
    - Carbon:          Ember (2024) lifecycle CI data via Our World in Data
    - Embodied carbon: Pirson & Bol (2021), DOI: 10.1016/j.resconrec.2021.105596
    - E-waste/EOL:     Forti et al. (2024), Global E-waste Monitor, UNU/UNITAR
    - THz channel:     Jornet & Akyildiz (2011), DOI: 10.1109/TWC.2011.081011.100545
    - DQN:             Mnih et al. (2015), DOI: 10.1038/nature14236
    - Lyapunov:        Neely (2010), DOI: 10.2200/S00271ED1V01Y201006CNT007
"""

from dataclasses import dataclass, field
import numpy as np


@dataclass
class SimulationConfig:
    """Master configuration for CALASH simulation experiments."""

    # ─── Network Topology ────────────────────────────────────────────
    area_width: float = 200.0          # meters
    area_height: float = 200.0         # meters
    num_nodes: int = 200               # sensor nodes (excluding BS)
    bs_x: float = 100.0               # base station x-coordinate
    bs_y: float = 250.0               # base station y-coordinate (50m outside area)
    tx_range: float = 100.0           # maximum transmission range (meters)

    # ─── Simulation Control ──────────────────────────────────────────
    num_rounds: int = 5000             # maximum simulation rounds
    num_seeds: int = 30                # independent runs for statistical significance
    base_seed: int = 42                # starting seed for reproducibility

    # ─── First-Order Radio Energy Model (Heinzelman et al., 2000) ────
    E_elec: float = 50e-9             # electronics energy (J/bit)
    eps_fs: float = 10e-12            # free-space amplifier (J/bit/m^2)
    eps_mp: float = 0.0013e-12        # multi-path amplifier (J/bit/m^4)
    E_DA: float = 5e-9               # data aggregation energy (J/bit/signal)
    E_sense: float = 1e-9            # sensing energy (J/bit)
    initial_energy: float = 0.5       # initial energy per node (J)

    # ─── Communication ───────────────────────────────────────────────
    packet_size: int = 4000           # data packet size (bits)
    control_packet_size: int = 200    # control/heartbeat packet size (bits)

    # ─── LEACH Parameters ────────────────────────────────────────────
    ch_percentage: float = 0.05       # desired percentage of cluster heads (p)
    max_members_per_ch: int = 30      # CH TDMA capacity limit (slots per frame)

    # ─── Carbon & Sustainability ─────────────────────────────────────
    carbon_trace_file: str = ""       # path to real CSV data (empty = synthetic)
    carbon_region: str = ""           # Electricity Maps region (france/germany/india/poland/brazil)
    ci_base: float = 200.0            # baseline carbon intensity (gCO2eq/kWh)
    ci_amplitude_daily: float = 80.0  # daily variation amplitude (gCO2eq/kWh)
    ci_amplitude_seasonal: float = 40.0  # seasonal variation amplitude
    ci_noise_std: float = 25.0        # random noise std dev
    ci_min: float = 20.0              # physical minimum CI (gCO2eq/kWh)
    ci_max: float = 600.0             # physical maximum CI (gCO2eq/kWh)
    # Embodied carbon: LCA of IoT sensor node manufacturing.
    # Includes PCB, IC, battery, housing, assembly, and transport.
    # Value: ~10 kgCO2eq per node (conservative upper bound for Mica2-class mote).
    # Refs: Pirson & Bol (2021), JRC Env. Impact IoT, doi:10.1016/j.resconrec.2021.105596
    #        Malmodin & Lunden (2024), "ICT sector electricity & GHG 2020-2030"
    embodied_carbon_per_node: float = 10000.0  # gCO2eq per node
    # End-of-life: e-waste processing, partial material recovery.
    # Ref: Forti et al. (2024) Global E-waste Monitor, UNU/UNITAR.
    eol_carbon_per_node: float = 500.0   # end-of-life disposal carbon per node
    recycle_rate: float = 0.3         # material recovery rate (0-1)

    # Carbon budget: total allowed operational carbon over mission lifetime
    # Set to 0 for unconstrained (baselines). For CALASH, this is the constraint.
    carbon_budget_total: float = 0.0  # gCO2eq (0 = auto-calculate from baseline)

    # ─── CALASH-Specific Parameters ──────────────────────────────────
    V_lyapunov: float = 100.0         # Lyapunov V parameter (delivery-carbon tradeoff)
    beta_carbon_ch: float = 0.3       # carbon modulation factor for CH election [0,1]
    min_ch_fraction: float = 0.05     # minimum fraction of alive nodes as CHs
    healing_detection_rounds: int = 3  # rounds to detect disaster
    healing_restructure_rounds: int = 50  # rounds for emergency restructuring
    disaster_decay_tau: float = 100.0  # disaster flag decay time constant

    # ─── Compressive Sensing (CADR) ──────────────────────────────────
    rho_min: float = 0.3              # min compression ratio (max compression)
    rho_max: float = 0.8              # max compression ratio (min compression)
    signal_dim: int = 100             # signal dimension n
    sparsity: int = 20                # signal sparsity level s (20% — realistic)
    signal_source: str = 'synthetic'  # 'synthetic' or 'intel_lab'
    signal_modality: str = 'temperature'  # Intel Lab modality

    # ─── Disaster Model ──────────────────────────────────────────────
    disaster_enabled: bool = True      # whether disaster event occurs
    disaster_round: int = 2000         # nominal disaster round (centre of jitter window)
    disaster_round_jitter: float = 0.15  # ±15% jitter (per-seed randomisation)
    disaster_x: float = 100.0         # epicenter x (center of 200×200 area)
    disaster_y: float = 100.0         # epicenter y
    damage_radius: float = 60.0       # effective damage radius (meters)
    disaster_type: str = 'generic'    # 'generic', 'earthquake', 'wildfire'
    # Real event key — loads calibrated damage_radius from REAL_DISASTER_PROFILES
    # in models/disaster.py.  Options: 'turkey_syria_2023' (r=80m, severe),
    # 'myanmar_2025' (r=70m, moderate), 'noto_2024' (r=55m, moderate).
    # Empty string = use generic Gaussian with damage_radius above.
    disaster_event: str = ''

    # ShakeMap integration: if set, downloads real USGS ShakeMap grid.xml
    # and uses spatially heterogeneous PGA/MMI data for damage modeling.
    # Use pre-cataloged keys (e.g. 'turkey_syria_2023') or raw USGS event IDs.
    # See data.shakemap_loader.SHAKEMAP_EVENTS for available events.
    # Empty string = disabled (use Gaussian model above).
    shakemap_event_id: str = ''

    # ─── Multi-Disaster / Aftershock Sequence ────────────────────────
    # Models aftershock sequences following Bath's law (largest aftershock
    # ~ M_main - 1.2) and Omori-Utsu temporal decay.  Applied at the
    # RUNNER level so ALL protocols face the same event sequence.
    # Ref: Bath (1965), Omori (1894), Utsu (1961), USGS Earthquake Hazards.
    aftershock_enabled: bool = True       # enable aftershock sequence
    aftershock_count: int = 2             # number of aftershocks after mainshock
    aftershock_delay_min: int = 500       # min rounds between events
    aftershock_delay_max: int = 800       # max rounds between events
    aftershock_radius_decay: float = 0.6  # damage radius multiplier per event
    aftershock_offset_m: float = 30.0     # spatial offset from mainshock (meters)

    # ─── Carbon-Aware Transmission Throttle ──────────────────────────
    # When carbon queue Z(t) is high AND CI is high, throttle member
    # transmissions (defer data to next round).  This gives the Lyapunov
    # carbon budget bound provable teeth: the system can actually
    # *not transmit* when carbon cost is too high.
    carbon_throttle_enabled: bool = True
    carbon_throttle_z_threshold: float = 200.0  # Z(t) above which throttle activates
    carbon_throttle_max_skip: float = 0.10      # max fraction of members that can skip

    # ─── Closed-Loop Fidelity Feedback (CADR) ────────────────────────
    # Track running NMSE and boost compression ratio when fidelity
    # drops below threshold.  Makes CADR genuinely adaptive (closed-loop),
    # not just a static CI-to-rho mapping.
    fidelity_feedback_enabled: bool = True
    fidelity_target_nmse: float = 0.15  # target max NMSE (above → boost rho)
    fidelity_feedback_window: int = 20  # rounds of NMSE history to average

    # ─── Q-Routing Parameters ────────────────────────────────────────
    q_learning_rate: float = 0.1
    q_discount: float = 0.9
    q_epsilon_start: float = 1.0
    q_epsilon_end: float = 0.01
    q_epsilon_decay: float = 0.995

    # ─── DQN Autonomous Routing (CALASH) ─────────────────────────────
    dqn_enabled: bool = True           # use DQN for CALASH routing
    dqn_gamma: float = 0.95            # discount factor
    dqn_lr: float = 1e-3               # learning rate
    dqn_tau: float = 0.005             # soft-update rate
    dqn_batch_size: int = 64
    dqn_buffer_capacity: int = 10_000
    dqn_epsilon_min: float = 0.05
    dqn_epsilon_decay_steps: int = 3000

    # ─── THz / 6G Channel Model ─────────────────────────────────────
    thz_enabled: bool = True           # use THz model for CALASH
    thz_freq_hz: float = 140e9         # sub-THz frequency (140 GHz D-band)
    thz_bandwidth_hz: float = 10e9     # 10 GHz bandwidth
    thz_tx_power_dbm: float = 10.0     # transmit power in dBm
    thz_max_range_m: float = 30.0      # max THz link range (meters)
    thz_circuit_power_w: float = 0.02  # circuit power consumption (20mW, modern D-band)
    humidity_pct: float = 50.0         # relative humidity for absorption
    ris_enabled: bool = True           # RIS-assisted beamforming
    ris_elements: int = 64             # number of RIS elements
    sub6_freq_hz: float = 3.5e9        # sub-6 GHz for inter-cluster

    # ─── 6G Network Slicing (3GPP TS 23.501) ────────────────────────
    # Network slicing provides QoS-differentiated service for different
    # traffic types.  In CALASH, this enables carbon-aware deferral of
    # mMTC traffic while guaranteeing URLLC for disaster emergency.
    slicing_enabled: bool = True       # enable 6G network slicing
    urllc_weight: float = 0.3          # initial URLLC bandwidth weight
    mmtc_weight: float = 0.5           # initial mMTC bandwidth weight
    embb_weight: float = 0.2           # initial eMBB bandwidth weight

    # ─── ISAC: Integrated Sensing and Communication (6G) ─────────────
    # ISAC enables the same THz waveform to serve both data transmission
    # and radar sensing, detecting structural anomalies post-disaster.
    # Ref: Liu et al. (2022), 3GPP TR 22.837, Wei et al. (2024)
    isac_enabled: bool = True          # enable ISAC module
    isac_max_range_m: float = 50.0     # max ISAC sensing range (m)

    # ─── Semantic Communication (6G) ─────────────────────────────────
    # Content-aware compression layer that goes beyond raw CS by
    # evaluating semantic importance of signal features.
    # Ref: Xie et al. (2021), Strinati et al. (2021), 3GPP TR 22.874
    semantic_enabled: bool = True      # enable semantic layer

    # ─── Cascaded RIS Channel Model ──────────────────────────────────
    # Full Tx→RIS→Rx path loss model with phase quantization, mutual
    # coupling, and practical impairments.
    # Ref: Wu & Zhang (2019, 2020), Ozdogan et al. (2020)
    ris_phase_bits: int = 2            # phase quantization bits (1-3)
    ris_coupling_factor: float = 0.85  # mutual coupling factor η
    ris_x: float = 100.0              # RIS panel x position (center)
    ris_y: float = 160.0              # RIS panel y position (near top)

    # ─── CI Gateway Beacon Model (Autonomy) ──────────────────────────
    # Models explicit CI distribution from gateway to edge nodes via
    # periodic beacons, replacing the implicit oracle assumption.
    # Gateway broadcasts CI once per ci_beacon_interval rounds.
    # Nodes use cached CI until next beacon (realistic edge computing).
    ci_beacon_interval: int = 20       # rounds between CI broadcasts
    ci_beacon_energy_j: float = 1e-6   # energy per CI beacon reception

    # ─── Lifecycle Integration (ISO 14040/14044 compliant) ──────────
    lifecycle_in_routing: bool = True   # include lifecycle cost in Lyapunov
    eol_penalty_weight: float = 1.0    # weight for EOL carbon in routing
    # Replacement carbon = embodied + transport (500 gCO2eq transport estimate)
    node_replacement_carbon: float = 10500.0  # gCO2eq per replaced node

    # Dynamic LCA Phase Breakdown (ISO 14040: raw materials → manufacturing
    # → distribution → use → end-of-life).
    # Refs: Pirson & Bol (2021), doi:10.1016/j.resconrec.2021.105596
    #        Noor (2025), Aalto U., "Comprehensive LCA of ICT Equipment"
    #        DT-LCAF (Albelwi, 2026), "Digital Twin Lifecycle Carbon"
    # Phase fractions sum to 1.0; multiply by embodied_carbon_per_node.
    lca_phase_raw_materials: float = 0.35   # mining, refining (Si, Cu, Li)
    lca_phase_manufacturing: float = 0.40   # PCB fab, IC packaging, assembly
    lca_phase_distribution: float = 0.05    # transport to deployment site
    lca_phase_use: float = 0.0              # operational (tracked separately)
    lca_phase_eol: float = 0.20             # disposal, recycling, landfill

    # Battery aging model: capacity fade per charging cycle.
    # Li-ion pouch cells degrade ~20% over 500 full cycles (Bloom et al.,
    # J. Power Sources 2020; Birkl et al., J. Electrochem. Soc. 2017).
    # In WSN context, 1 "cycle" ≈ one deep energy drain to <10%.
    # capacity_fade = 1 - aging_rate * sqrt(equivalent_full_cycles)
    # (square-root law matches SEI growth-limited degradation)
    battery_aging_rate: float = 0.02       # 2% capacity per sqrt(cycle)
    battery_cycle_threshold: float = 0.1   # energy < 10% initial = 1 cycle

    # ─── Derived Constants (computed post-init) ──────────────────────
    d0: float = field(init=False)      # crossover distance (meters)
    J_to_kWh: float = field(init=False, default=1.0 / 3.6e6)  # Joules to kWh

    def __post_init__(self):
        """Compute derived constants."""
        self.d0 = np.sqrt(self.eps_fs / self.eps_mp)
        # Auto-calculate carbon budget if not set
        if self.carbon_budget_total <= 0:
            # Estimate based on full network energy at average CI (×1.5 headroom)
            self.carbon_budget_total = 1.5 * (
                self.num_nodes * self.initial_energy * self.J_to_kWh * self.ci_base
            )

    def copy(self, **overrides):
        """Create a modified copy of this config."""
        import dataclasses
        params = dataclasses.asdict(self)
        params.update(overrides)
        # Remove derived fields
        params.pop('d0', None)
        params.pop('J_to_kWh', None)
        return SimulationConfig(**params)


# ─── Preset Configurations ───────────────────────────────────────────

def default_config() -> SimulationConfig:
    """Standard configuration for paper experiments."""
    return SimulationConfig()


def small_config() -> SimulationConfig:
    """Quick testing configuration."""
    return SimulationConfig(
        num_nodes=50,
        num_rounds=1000,
        num_seeds=5,
    )


def scalability_configs() -> list:
    """Configurations for scalability experiments (E1)."""
    base = default_config()
    return [base.copy(num_nodes=n) for n in [100, 200, 300, 500]]


def disaster_severity_configs() -> list:
    """Configurations for disaster severity experiments (E2)."""
    base = default_config()
    return [base.copy(damage_radius=r) for r in [50.0, 100.0, 150.0]]


def carbon_variation_configs() -> list:
    """Configurations for carbon variation experiments (E3)."""
    base = default_config()
    return [
        base.copy(ci_base=50.0, ci_amplitude_daily=20.0),   # Low-carbon grid
        base.copy(ci_base=200.0, ci_amplitude_daily=80.0),  # Medium (France-like)
        base.copy(ci_base=450.0, ci_amplitude_daily=100.0), # High-carbon grid
    ]
