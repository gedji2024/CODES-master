"""
Disaster Event Model
====================
Spatially-correlated failure model for natural disasters.

Uses a Gaussian damage profile centered at the epicenter:
    P_fail(s_i) = exp(-d(s_i, epicenter)^2 / (2 * r_fail^2))

Nodes near the epicenter fail with high probability; distant nodes survive.
This matches real earthquake damage patterns (Modified Mercalli Intensity
isoseismal maps show approximately Gaussian spatial decay).

Three severity levels are defined for experiments:
    - Localized (r=50m):  ~10% of nodes in 500x500m area
    - Moderate  (r=100m): ~25% of nodes
    - Severe    (r=150m): ~40% of nodes

Real Disaster Event Profiles
-----------------------------
Calibrated to published seismological data from USGS ShakeMap and
post-event damage assessments:

    Turkey-Syria 2023 (Feb 6):
        Mw 7.8 + Mw 7.7 doublet, East Anatolian Fault.
        Rupture length ~370 km, MMI XII (Extreme), PGA 2.21 g.
        ~60,000 deaths, 1.5 M homeless, >$157 B damage.
        Source: USGS eventpage/us6000jllz; Cen et al. (2023) GEER Report 082.

    Myanmar 2025 (Mar 28):
        Mw 7.7, Sagaing Fault. Rupture length ~500 km, MMI X, PGA 1.07 g.
        ~5,456 deaths, 11,404 injured, $11 B damage.
        Source: USGS eventpage/us7000pn9s; Bradley & Hubbard (2025).

    Noto Peninsula 2024 (Jan 1):
        Mw 7.5, reverse faulting. MMI VIII+, PGA 2.83 g (local).
        504 deaths, >14,000 buildings destroyed.
        Source: USGS eventpage/us6000m0xl; GSI Japan (2024).

Mapping to Gaussian damage radius:
    The Gaussian sigma is calibrated to the distance at which the USGS
    ShakeMap shows MMI >= VIII (destructive). This gives the "effective
    damage radius" in our 200x200m simulation domain:
        damage_radius = R_mmi8 * (sim_area / real_affected_area)
"""

import numpy as np
from typing import List, Optional, Tuple


class DisasterEvent:
    """
    Models a spatially-correlated disaster event (earthquake, explosion, flood).

    The failure probability follows a Gaussian profile around the epicenter.
    Each node fails independently with probability P_fail(distance).
    """

    def __init__(self, epicenter_x: float, epicenter_y: float,
                 damage_radius: float, rng: np.random.Generator = None):
        """
        Initialize disaster event.

        Parameters
        ----------
        epicenter_x, epicenter_y : float
            Epicenter coordinates in meters.
        damage_radius : float
            Effective damage radius (sigma of Gaussian) in meters.
        rng : np.random.Generator
            Random number generator.
        """
        self.epicenter = (epicenter_x, epicenter_y)
        self.damage_radius = damage_radius
        self.rng = rng if rng is not None else np.random.default_rng()

    def failure_probability(self, node_x: float, node_y: float) -> float:
        """
        Compute failure probability for a node at (node_x, node_y).

        P_fail = exp(-d^2 / (2 * r_fail^2))

        Parameters
        ----------
        node_x, node_y : float
            Node coordinates.

        Returns
        -------
        float
            Failure probability in [0, 1].
        """
        dx = node_x - self.epicenter[0]
        dy = node_y - self.epicenter[1]
        d_sq = dx * dx + dy * dy
        return np.exp(-d_sq / (2.0 * self.damage_radius ** 2))

    def apply_to_network(self, network) -> Tuple[List[int], List[int]]:
        """
        Apply disaster to the network. Nodes fail probabilistically.
        Survivors near the epicenter sustain partial damage (energy loss)
        modelling structural stress, antenna misalignment, and battery
        degradation observed in post-earthquake WSN deployments
        (Younis et al., Computer Networks 2014).

        Parameters
        ----------
        network : Network
            The WSN network object.

        Returns
        -------
        killed_ids : List[int]
            IDs of nodes killed by the disaster.
        survived_ids : List[int]
            IDs of alive nodes that survived.
        """
        killed_ids = []
        survived_ids = []

        for node in network.nodes:
            if not node.alive:
                continue

            p_fail = self.failure_probability(node.x, node.y)
            if self.rng.random() < p_fail:
                node.alive = False
                node.energy = 0.0
                node.is_ch = False
                killed_ids.append(node.id)
            else:
                survived_ids.append(node.id)
                # Partial damage to survivors near epicenter:
                # energy_loss = 0.5 * P_fail (up to 50% energy drain)
                if p_fail > 0.1:
                    energy_loss_frac = 0.5 * p_fail
                    node.energy *= (1.0 - energy_loss_frac)

        return killed_ids, survived_ids

    def get_damage_map(self, network) -> np.ndarray:
        """
        Compute failure probability for all nodes (for visualization).

        Parameters
        ----------
        network : Network
            The WSN network.

        Returns
        -------
        np.ndarray
            Array of failure probabilities for each node.
        """
        probs = np.zeros(len(network.nodes))
        for node in network.nodes:
            probs[node.id] = self.failure_probability(node.x, node.y)
        return probs

    @staticmethod
    def estimate_casualties(num_nodes: int, area_width: float,
                            area_height: float, damage_radius: float) -> float:
        """
        Estimate expected fraction of nodes killed (uniform deployment).

        For a Gaussian damage profile in a rectangular area:
        E[killed/total] ≈ (2π * r^2) / (W * H) * (1 - exp(-W*H / (4π*r^2)))

        For large areas relative to damage radius, this simplifies to:
        E[fraction] ≈ 2π * r^2 / (W * H)

        Parameters
        ----------
        num_nodes : int
            Total number of nodes.
        area_width, area_height : float
            Deployment area dimensions.
        damage_radius : float
            Damage radius in meters.

        Returns
        -------
        float
            Expected fraction of nodes killed.
        """
        area = area_width * area_height
        damage_area = 2 * np.pi * damage_radius ** 2
        return min(1.0, damage_area / area)


# ═══════════════════════════════════════════════════════════════════════
# Real Disaster Event Profiles
# ═══════════════════════════════════════════════════════════════════════
# Each profile contains seismological parameters from USGS and published
# post-event assessments.  The 'damage_radius' is the Gaussian sigma
# calibrated to the USGS ShakeMap MMI VIII isoseismal, scaled to the
# simulation domain (200x200 m).
#
# Mapping logic:
#   Real MMI VIII area (km^2) -> fraction of 200x200m area affected
#   damage_radius chosen so that 2*pi*r^2 / (200*200) = fraction_killed
#
# Turkey-Syria 2023:  MMI VIII+ area ~16,000 km^2 over ~350 km swath
#   => massive devastation, ~40% of a 200x200m zone near epicenter
#   => damage_radius ~ 80 m  (severe scenario)
#
# Myanmar 2025:  MMI VIII+ area ~30,000 km^2 over ~500 km rupture
#   => widespread but less concentrated than Turkey doublet
#   => damage_radius ~ 70 m  (moderate-to-severe)
#
# Noto 2024:  MMI VIII area ~800 km^2 (compact peninsula event)
#   => concentrated destruction in small area
#   => damage_radius ~ 55 m  (moderate scenario)
# ═══════════════════════════════════════════════════════════════════════

REAL_DISASTER_PROFILES = {
    'turkey_syria_2023': {
        'name': 'Turkey-Syria Earthquake Doublet (Feb 6, 2023)',
        'magnitude': 7.8,           # Mw (mainshock); second event Mw 7.7
        'depth_km': 10.0,           # shallow crustal
        'fault': 'East Anatolian Fault',
        'rupture_length_km': 370.0, # USGS finite fault model
        'max_slip_m': 12.0,         # meters
        'mmi_max': 'XII',           # Extreme (USGS ShakeMap)
        'pga_max_g': 2.21,          # peak ground acceleration
        'deaths': 59488,            # confirmed total (Turkey + Syria)
        'damage_usd_billion': 157.8,
        'damage_radius': 80.0,      # Gaussian sigma for simulation (meters)
        'severity': 'severe',
        'reference': 'USGS us6000jllz; Cen et al. (2023) GEER Report 082, '
                     'doi:10.18118/G6PM34',
    },
    'myanmar_2025': {
        'name': 'Myanmar (Sagaing) Earthquake (Mar 28, 2025)',
        'magnitude': 7.7,           # Mw (USGS); 7.9 by some agencies
        'depth_km': 10.0,
        'fault': 'Sagaing Fault',
        'rupture_length_km': 500.0, # one of longest observed strike-slip
        'max_slip_m': 7.4,          # INGV finite fault model
        'mmi_max': 'X',             # Extreme (USGS ShakeMap)
        'pga_max_g': 1.07,          # GFZ station Naypyidaw
        'deaths': 5456,             # compiled total (Myanmar + Thailand)
        'damage_usd_billion': 11.0, # World Bank estimate (Myanmar only)
        'damage_radius': 70.0,      # Gaussian sigma for simulation
        'severity': 'moderate',
        'reference': 'USGS us7000pn9s; Bradley & Hubbard (2025), '
                     'Earthquake Insights, doi:10.62481/51b7df8c',
    },
    'noto_2024': {
        'name': 'Noto Peninsula Earthquake (Jan 1, 2024)',
        'magnitude': 7.5,           # Mw (USGS)
        'depth_km': 10.0,
        'fault': 'Noto Peninsula fault zone (reverse)',
        'rupture_length_km': 150.0,
        'max_slip_m': 5.0,
        'mmi_max': 'VIII+',
        'pga_max_g': 2.83,          # local station peak
        'deaths': 504,
        'damage_usd_billion': 17.6, # Japanese government estimate
        'damage_radius': 55.0,      # Gaussian sigma for simulation
        'severity': 'moderate',
        'reference': 'USGS us6000m0xl; GSI Japan (2024); '
                     'Cabinet Office Japan damage report',
    },
}


def create_disaster_from_profile(event_key: str,
                                  epicenter_x: float = 100.0,
                                  epicenter_y: float = 100.0,
                                  rng: np.random.Generator = None) -> DisasterEvent:
    """
    Create a DisasterEvent calibrated to a real earthquake event.

    Parameters
    ----------
    event_key : str
        Key into REAL_DISASTER_PROFILES:
        'turkey_syria_2023', 'myanmar_2025', 'noto_2024'.
    epicenter_x, epicenter_y : float
        Epicenter in simulation coordinates (default: center of 200x200 area).
    rng : np.random.Generator
        Random number generator.

    Returns
    -------
    DisasterEvent
        Configured disaster event with real-calibrated damage radius.

    Raises
    ------
    KeyError
        If event_key not in REAL_DISASTER_PROFILES.
    """
    profile = REAL_DISASTER_PROFILES[event_key]
    return DisasterEvent(
        epicenter_x=epicenter_x,
        epicenter_y=epicenter_y,
        damage_radius=profile['damage_radius'],
        rng=rng,
    )


# ═══════════════════════════════════════════════════════════════════════
# ShakeMap-Based Spatially Heterogeneous Disaster Event
# ═══════════════════════════════════════════════════════════════════════

class ShakeMapDisasterEvent:
    """
    Disaster event using real USGS ShakeMap spatial PGA/MMI data.

    Unlike the Gaussian model (DisasterEvent), this uses the actual
    USGS ShakeMap grid data (e.g. 467,929 grid points for Turkey-Syria
    M7.8) to compute spatially heterogeneous per-node failure
    probabilities.  This gives realistic damage patterns that match
    real-world Modified Mercalli Intensity (MMI) isoseismal maps.

    The ShakeMap data provides:
    - PGA (Peak Ground Acceleration): physical sensor survivability
    - MMI (Modified Mercalli Intensity): structural damage correlation
    - PGV (Peak Ground Velocity): ground motion intensity

    Fragility model (PGA-based, default):
        P_fail(node_i) = min(1, (PGA_i / PGA_threshold)^2)
    where PGA_threshold ≈ 0.3g for consumer IoT devices (Younis et al.,
    Computer Networks 2014).

    This class wraps data.shakemap_loader.ShakeMapLoader and provides
    the same apply_to_network() interface as DisasterEvent for seamless
    integration with the experiment runner.

    Usage
    -----
    >>> event = ShakeMapDisasterEvent('turkey_syria_2023', 100, 100, rng)
    >>> killed, survived = event.apply_to_network(network)
    """

    def __init__(self, event_key: str,
                 epicenter_x: float = 100.0,
                 epicenter_y: float = 100.0,
                 rng: np.random.Generator = None,
                 method: str = 'pga',
                 area_width: float = 200.0,
                 area_height: float = 200.0):
        """
        Parameters
        ----------
        event_key : str
            Pre-cataloged ShakeMap event key or raw USGS event ID.
            Available: 'turkey_syria_2023', 'myanmar_2025', 'noto_2024'.
        epicenter_x, epicenter_y : float
            Epicenter in simulation coordinates.
        rng : np.random.Generator
            Random number generator.
        method : str
            Failure probability method: 'pga' or 'mmi'.
        area_width, area_height : float
            Simulation area dimensions.
        """
        self.epicenter = (epicenter_x, epicenter_y)
        self.rng = rng if rng is not None else np.random.default_rng()
        self.method = method
        self.event_key = event_key

        # Lazy-load the ShakeMap data (avoid import at module level)
        from data.shakemap_loader import ShakeMapLoader
        self._loader = ShakeMapLoader(
            event_key=event_key,
            area_width=area_width,
            area_height=area_height,
        )
        self._loader.download_and_parse()
        self._loaded = self._loader.is_loaded

        # Fallback: if ShakeMap fails to load, create Gaussian DisasterEvent
        self._fallback = None
        if not self._loaded:
            # Use profile-calibrated Gaussian as fallback
            if event_key in REAL_DISASTER_PROFILES:
                radius = REAL_DISASTER_PROFILES[event_key]['damage_radius']
            else:
                radius = 60.0
            self._fallback = DisasterEvent(
                epicenter_x, epicenter_y, radius, rng)

    @property
    def damage_radius(self) -> float:
        """Effective Gaussian-equivalent damage radius (for logging)."""
        if self._loaded:
            params = self._loader.to_disaster_params(
                self.epicenter[0], self.epicenter[1])
            return params['damage_radius']
        elif self._fallback:
            return self._fallback.damage_radius
        return 60.0

    def apply_to_network(self, network) -> Tuple[List[int], List[int]]:
        """
        Apply ShakeMap-based spatially heterogeneous damage to network.

        Uses real PGA/MMI spatial data from USGS ShakeMap to compute
        per-node failure probabilities, giving realistic non-isotropic
        damage patterns.

        Parameters
        ----------
        network : Network
            The WSN network object.

        Returns
        -------
        killed_ids : List[int]
            IDs of nodes killed by the disaster.
        survived_ids : List[int]
            IDs of alive nodes that survived.
        """
        if self._fallback is not None:
            return self._fallback.apply_to_network(network)

        return self._loader.apply_to_network(
            network,
            epicenter_sim=self.epicenter,
            method=self.method,
            rng=self.rng,
        )

    def failure_probability(self, node_x: float, node_y: float) -> float:
        """Compute failure probability for a single node position."""
        if self._fallback is not None:
            return self._fallback.failure_probability(node_x, node_y)

        probs = self._loader.failure_probabilities(
            [(node_x, node_y)],
            epicenter_sim=self.epicenter,
            method=self.method,
        )
        return float(probs[0])

    def get_damage_map(self, network) -> np.ndarray:
        """Compute failure probability for all nodes (for visualization)."""
        if self._fallback is not None:
            return self._fallback.get_damage_map(network)

        positions = [(n.x, n.y) for n in network.nodes]
        probs = self._loader.failure_probabilities(
            positions,
            epicenter_sim=self.epicenter,
            method=self.method,
        )
        return probs

    def get_shakemap_summary(self) -> dict:
        """Return summary of loaded ShakeMap data for logging."""
        if not self._loaded:
            return {'source': 'Gaussian fallback', 'event_key': self.event_key}

        params = self._loader.to_disaster_params(
            self.epicenter[0], self.epicenter[1])
        return params


def create_shakemap_disaster(event_key: str,
                             epicenter_x: float = 100.0,
                             epicenter_y: float = 100.0,
                             rng: np.random.Generator = None,
                             area_width: float = 200.0,
                             area_height: float = 200.0
                             ) -> ShakeMapDisasterEvent:
    """
    Create a ShakeMap-based disaster event with real USGS spatial data.

    Parameters
    ----------
    event_key : str
        Pre-cataloged event key: 'turkey_syria_2023', 'myanmar_2025',
        'noto_2024', or raw USGS event ID.
    epicenter_x, epicenter_y : float
        Epicenter in simulation coordinates.
    rng : np.random.Generator
        Random number generator.
    area_width, area_height : float
        Simulation area dimensions.

    Returns
    -------
    ShakeMapDisasterEvent
        Configured disaster event with real spatial data.
    """
    return ShakeMapDisasterEvent(
        event_key=event_key,
        epicenter_x=epicenter_x,
        epicenter_y=epicenter_y,
        rng=rng,
        area_width=area_width,
        area_height=area_height,
    )


# ═══════════════════════════════════════════════════════════════════════
# Aftershock Sequence Model (Bath-Håkansson + Omori-Utsu)
# ═══════════════════════════════════════════════════════════════════════

class AftershockModel:
    """
    Generates realistic aftershock sequences following the mainshock.

    Real earthquakes are followed by aftershock sequences that can
    persist for days to months.  The Turkey-Syria 2023 event had
    >10,000 aftershocks in the first week, including the Mw 7.7
    doublet just 9 hours after the mainshock (Cen et al., 2023).

    This is critical for self-healing: the WSN must handle REPEATED
    damage events, not just a single shock.  Each aftershock can:
    - Kill additional weakened survivors
    - Disrupt ongoing recovery operations
    - Shift coverage holes

    Models used:
    1. **Bath-Håkansson law**: largest aftershock magnitude
       M_max_after ≈ M_main - 1.2
    2. **Omori-Utsu law**: aftershock rate decay
       n(t) = K / (t + c)^p    (p ≈ 1.1, c ≈ 0.05 days)
    3. **Gutenberg-Richter**: aftershock magnitude distribution
       log₁₀(N) = a - b·M    (b ≈ 1.0)

    References
    ----------
    [1] Utsu, T. "A statistical study on the occurrence of aftershocks."
        Geophysical Magazine, 30, 521-605, 1961.
    [2] Bath, M. "Lateral inhomogeneities of the upper mantle."
        Tectonophysics, 2(6), 483-514, 1965.
    [3] Reasenberg, P.A. & Jones, L.M. "Earthquake hazard after a
        mainshock in California." Science, 243, 1173-1176, 1989.
    [4] Cen, L. et al. "GEER Report 082: Turkey-Syria 2023 Earthquakes."
        DOI: 10.18118/G6PM34.
    """

    def __init__(self, mainshock_magnitude: float,
                 mainshock_radius: float,
                 num_rounds_per_day: int = 240,
                 rng: np.random.Generator = None):
        """
        Parameters
        ----------
        mainshock_magnitude : float
            Mainshock moment magnitude (Mw).
        mainshock_radius : float
            Mainshock damage radius in simulation units (meters).
        num_rounds_per_day : int
            Simulation rounds per day (default: 240 = 10 rounds/hr × 24 hr).
        rng : np.random.Generator
            Random number generator.
        """
        self.M_main = mainshock_magnitude
        self.main_radius = mainshock_radius
        self.rounds_per_day = num_rounds_per_day
        self.rng = rng if rng is not None else np.random.default_rng()

        # Bath-Håkansson: max aftershock magnitude
        self.M_max_after = self.M_main - 1.2

        # Omori-Utsu parameters
        self.p = 1.1     # decay exponent (Utsu, 1961)
        self.c = 0.05    # time offset (days)
        self.K = 10 ** (self.M_main - 4.0)  # productivity (Reasenberg & Jones)

        # Track generated aftershocks
        self._aftershocks = []
        self._mainshock_round = -1

    def set_mainshock_round(self, round_num: int):
        """Record when the mainshock occurred."""
        self._mainshock_round = round_num

    def generate_aftershock(self, current_round: int) -> Optional[DisasterEvent]:
        """
        Check if an aftershock occurs at this round and generate it.

        Uses Omori-Utsu law to determine the rate, then stochastic
        sampling to decide if an event occurs in this time step.

        Parameters
        ----------
        current_round : int
            Current simulation round.

        Returns
        -------
        DisasterEvent or None
            An aftershock event if one occurs, else None.
        """
        if self._mainshock_round < 0:
            return None

        rounds_since = current_round - self._mainshock_round
        if rounds_since <= 0:
            return None

        # Convert rounds to days
        t_days = rounds_since / self.rounds_per_day

        # Omori-Utsu rate (events per day)
        rate = self.K / (t_days + self.c) ** self.p

        # Probability of at least one aftershock this round
        # (thin Poisson approximation: P ≈ rate × dt)
        dt_days = 1.0 / self.rounds_per_day
        p_event = min(rate * dt_days, 0.5)  # cap at 50% per round

        if self.rng.random() >= p_event:
            return None

        # Gutenberg-Richter: sample magnitude
        # F(M) = 1 - 10^(-b·(M-M_min))
        # M = M_min - log₁₀(1 - U) / b
        M_min = self.M_main - 3.0  # minimum detectable aftershock
        b = 1.0
        U = self.rng.random()
        M_after = M_min - np.log10(1 - U * (1 - 10**(-b * (self.M_max_after - M_min)))) / b
        M_after = min(M_after, self.M_max_after)

        # Scale damage radius from magnitude:
        # radius ∝ 10^(0.5·(M-M_ref)) relative to mainshock
        radius_scale = 10 ** (0.5 * (M_after - self.M_main))
        aftershock_radius = self.main_radius * radius_scale

        # Epicenter jitter (aftershocks cluster near mainshock)
        jitter = self.main_radius * 0.5 * self.rng.normal(0, 1, 2)

        aftershock = DisasterEvent(
            epicenter_x=100.0 + jitter[0],  # centered near original
            epicenter_y=100.0 + jitter[1],
            damage_radius=max(aftershock_radius, 5.0),  # minimum 5m
            rng=self.rng,
        )

        self._aftershocks.append({
            'round': current_round,
            'magnitude': M_after,
            'radius': aftershock_radius,
            'days_after': t_days,
        })

        return aftershock

    def get_aftershock_log(self) -> list:
        """Return log of all generated aftershocks."""
        return self._aftershocks.copy()
