"""
USGS ShakeMap Grid Data Loader
===============================
Downloads, parses, and maps USGS ShakeMap grid.xml data onto the
CALASH sensor-field topology.

ShakeMap provides gridded estimates of ground-motion parameters (PGA,
PGV, MMI, spectral accelerations) computed by the USGS Earthquake
Hazards Program after significant earthquakes worldwide.

Workflow
--------
1. **Download**: Fetch grid.xml for a given USGS event ID via the
   ComCat product API (or load from a cached local file).
2. **Parse**: Extract the grid specification (lat/lon bounds, spacing)
   and the per-cell data columns (MMI, PGA, PGV, PSA03, PSA10, PSA30,
   Vs30) from the XML.
3. **Map**: Project the real-world lat/lon grid onto the simulation
   sensor field (default 200×200 m) by normalizing coordinates into
   the bounding box.  Interpolate grid values at each sensor node
   location using bilinear interpolation.
4. **Convert**: Translate PGA / MMI values into node failure
   probabilities using the Worden et al. (2012) GMICE, and supply
   spatially heterogeneous damage to the DisasterEvent model.

Supported Events (pre-cataloged)
---------------------------------
    turkey_syria_2023   — us6000jllz  (Mw 7.8)
    noto_2024           — us6000m0xl  (Mw 7.5)
    morocco_2023        — us7000kufc  (Mw 6.8)
    nepal_2015          — us20002926  (Mw 7.8)
    haiti_2010          — usp000h60h  (Mw 7.0)

Any other USGS event ID with a ShakeMap product can also be used.

Data Provenance
---------------
    Source:   USGS Earthquake Hazards Program — ShakeMap
    URL:      https://earthquake.usgs.gov/data/shakemap/
    Format:   XML (grid.xml) — see ShakeMap v4 Technical Manual §4.6
    Licence:  Public domain (U.S. Government work, 17 U.S.C. §105)
    Citation: Worden, C.B. & Wald, D.J. (2016). "ShakeMap Manual
              Online." USGS. doi:10.5066/F7D21VPQ

References
----------
    [1] Worden, C.B. et al. (2012). "Probabilistic Relationships
        between Ground-Motion Parameters and Modified Mercalli
        Intensity in California." BSSA 102(1), 204-221.
        doi:10.1785/0120110156

    [2] Wald, D.J. et al. (1999). "Relationships between Peak Ground
        Acceleration, Peak Ground Velocity, and Modified Mercalli
        Intensity in California." Earthquake Spectra, 15(3), 557-564.
        doi:10.1193/1.1586058

    [3] Worden, C.B. & Wald, D.J. (2016). "ShakeMap Manual Online:
        Technical Manual, User's Guide, and Software Guide." USGS.
        doi:10.5066/F7D21VPQ
"""

import os
import io
import json
import logging
import hashlib
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

logger = logging.getLogger(__name__)

# ─── Cache directory for downloaded ShakeMap files ────────────────────
_CACHE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'real_traces', 'shakemap_cache'
)

# ─── Pre-cataloged USGS event IDs ────────────────────────────────────
SHAKEMAP_EVENTS = {
    'turkey_syria_2023': {
        'event_id': 'us6000jllz',
        'magnitude': 7.8,
        'lat': 37.226, 'lon': 37.014,
        'depth_km': 10.0,
        'date': '2023-02-06',
        'description': 'Pazarcik earthquake, Kahramanmaras sequence',
    },
    'noto_2024': {
        'event_id': 'us6000m0xl',
        'magnitude': 7.5,
        'lat': 37.497, 'lon': 136.944,
        'depth_km': 10.0,
        'date': '2024-01-01',
        'description': 'Noto Peninsula Earthquake',
    },
    'morocco_2023': {
        'event_id': 'us7000kufc',
        'magnitude': 6.8,
        'lat': 31.055, 'lon': -8.396,
        'depth_km': 26.0,
        'date': '2023-09-08',
        'description': '2023 Morocco Earthquake',
    },
    'nepal_2015': {
        'event_id': 'us20002926',
        'magnitude': 7.8,
        'lat': 28.147, 'lon': 84.708,
        'depth_km': 8.2,
        'date': '2015-04-25',
        'description': '2015 Nepal (Gorkha) Earthquake',
    },
    'haiti_2010': {
        'event_id': 'usp000h60h',
        'magnitude': 7.0,
        'lat': 18.443, 'lon': -72.571,
        'depth_km': 13.0,
        'date': '2010-01-12',
        'description': '2010 Haiti Earthquake',
    },
    'miyagi_2011': {
        'event_id': 'official20110311054624120_30',
        'magnitude': 9.1,
        'lat': 38.297, 'lon': 142.373,
        'depth_km': 29.0,
        'date': '2011-03-11',
        'description': '2011 Tōhoku Earthquake & Tsunami',
    },
}


# ═══════════════════════════════════════════════════════════════════════
# ShakeMap Grid Data Structures
# ═══════════════════════════════════════════════════════════════════════

class ShakeMapGrid:
    """
    Parsed ShakeMap grid.xml data.

    Attributes
    ----------
    event_id : str
        USGS event identifier.
    magnitude : float
        Earthquake magnitude (Mw).
    lat_epicenter : float
        Epicenter latitude.
    lon_epicenter : float
        Epicenter longitude.
    depth_km : float
        Hypocentral depth in km.
    grid_spec : dict
        Grid specification (nlon, nlat, lon_min, lon_max, lat_min,
        lat_max, nominal_lon_spacing, nominal_lat_spacing).
    field_names : list of str
        Column names in the grid data.
    data : np.ndarray
        2D array of shape (n_points, n_fields), row-major order.
    lons : np.ndarray
        1D longitude values of grid.
    lats : np.ndarray
        1D latitude values of grid.
    """

    def __init__(self):
        self.event_id: str = ''
        self.magnitude: float = 0.0
        self.lat_epicenter: float = 0.0
        self.lon_epicenter: float = 0.0
        self.depth_km: float = 0.0
        self.grid_spec: Dict[str, Any] = {}
        self.field_names: List[str] = []
        self.data: np.ndarray = np.array([])
        self.lons: np.ndarray = np.array([])
        self.lats: np.ndarray = np.array([])

    @property
    def nlon(self) -> int:
        return int(self.grid_spec.get('nlon', 0))

    @property
    def nlat(self) -> int:
        return int(self.grid_spec.get('nlat', 0))

    @property
    def n_points(self) -> int:
        return len(self.data)

    def get_field(self, name: str) -> np.ndarray:
        """Get a single field column by name (e.g., 'MMI', 'PGA')."""
        if name.upper() not in [f.upper() for f in self.field_names]:
            raise ValueError(
                f"Field '{name}' not found.  Available: {self.field_names}")
        idx = [f.upper() for f in self.field_names].index(name.upper())
        return self.data[:, idx]

    def get_2d_field(self, name: str) -> np.ndarray:
        """
        Get a field reshaped as a 2D grid (nlat × nlon).

        The grid.xml data is stored lon-major (lon varies fastest),
        so we reshape accordingly.
        """
        flat = self.get_field(name)
        return flat.reshape(self.nlat, self.nlon)

    def field_at_latlon(self, name: str, lat: float, lon: float) -> float:
        """
        Bilinear interpolation of a field at an arbitrary lat/lon.

        Parameters
        ----------
        name : str
            Field name (e.g., 'PGA', 'MMI').
        lat, lon : float
            Query coordinates.

        Returns
        -------
        float
            Interpolated field value.
        """
        grid2d = self.get_2d_field(name)
        spec = self.grid_spec

        # Fractional grid indices
        fi = (lat - spec['lat_min']) / spec['nominal_lat_spacing']
        fj = (lon - spec['lon_min']) / spec['nominal_lon_spacing']

        # Clamp to valid range
        fi = np.clip(fi, 0, self.nlat - 1.001)
        fj = np.clip(fj, 0, self.nlon - 1.001)

        i0 = int(fi)
        j0 = int(fj)
        i1 = min(i0 + 1, self.nlat - 1)
        j1 = min(j0 + 1, self.nlon - 1)

        di = fi - i0
        dj = fj - j0

        # Bilinear
        val = (grid2d[i0, j0] * (1 - di) * (1 - dj) +
               grid2d[i1, j0] * di * (1 - dj) +
               grid2d[i0, j1] * (1 - di) * dj +
               grid2d[i1, j1] * di * dj)
        return float(val)

    def summary(self) -> Dict:
        """Return a human-readable summary."""
        result = {
            'event_id': self.event_id,
            'magnitude': self.magnitude,
            'epicenter': (self.lat_epicenter, self.lon_epicenter),
            'depth_km': self.depth_km,
            'grid_points': self.n_points,
            'grid_shape': (self.nlat, self.nlon),
            'fields': self.field_names,
        }
        for f in self.field_names:
            col = self.get_field(f)
            result[f'{f}_range'] = (float(np.min(col)), float(np.max(col)))
        return result


# ═══════════════════════════════════════════════════════════════════════
# Download & Parse
# ═══════════════════════════════════════════════════════════════════════

def _download_grid_xml(event_id: str, cache: bool = True) -> str:
    """
    Download grid.xml for a USGS ShakeMap event.

    Uses the USGS GeoJSON Detail Feed to discover the download URL
    for the ShakeMap grid.xml product, then fetches it.

    Parameters
    ----------
    event_id : str
        USGS event ID (e.g., 'us6000jllz').
    cache : bool
        If True, cache the downloaded file locally.

    Returns
    -------
    str
        Path to the downloaded (or cached) grid.xml file.

    Raises
    ------
    RuntimeError
        If the download fails or the event has no ShakeMap.
    """
    import urllib.request
    import urllib.error

    os.makedirs(_CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(_CACHE_DIR, f'{event_id}_grid.xml')

    if cache and os.path.exists(cache_path):
        logger.info("Using cached grid.xml: %s", cache_path)
        return cache_path

    # Step 1: Query the event detail to find ShakeMap grid.xml URL
    detail_url = (
        f"https://earthquake.usgs.gov/fdsnws/event/1/query"
        f"?eventid={event_id}&format=geojson"
    )
    logger.info("Fetching event detail: %s", detail_url)

    try:
        req = urllib.request.Request(detail_url, headers={
            'User-Agent': 'CALASH-Research/1.0 (PhD thesis; '
                          'shakemap-loader; Python/3.x)',
            'Accept': 'application/json',
        })
        with urllib.request.urlopen(req, timeout=60) as resp:
            detail = json.loads(resp.read().decode('utf-8'))
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        raise RuntimeError(
            f"Failed to fetch event detail for {event_id}: {e}") from e

    # Step 2: Extract the ShakeMap grid.xml download URL
    products = detail.get('properties', {}).get('products', {})
    shakemap_list = products.get('shakemap', [])
    if not shakemap_list:
        raise RuntimeError(
            f"Event {event_id} has no ShakeMap product.")

    # Use the preferred (first) ShakeMap product
    sm = shakemap_list[0]
    contents = sm.get('contents', {})

    # Look for grid.xml in the contents
    grid_key = 'download/grid.xml'
    if grid_key not in contents:
        available = [k for k in contents.keys() if 'grid' in k.lower()]
        raise RuntimeError(
            f"No grid.xml found for {event_id}. "
            f"Available grid-related files: {available}")

    grid_url = contents[grid_key]['url']
    grid_size = contents[grid_key].get('length', 'unknown')
    logger.info("Downloading grid.xml (%s bytes): %s", grid_size, grid_url)

    # Step 3: Download the grid.xml
    try:
        req = urllib.request.Request(grid_url, headers={
            'User-Agent': 'CALASH-Research/1.0',
            'Accept': 'application/xml',
        })
        with urllib.request.urlopen(req, timeout=120) as resp:
            xml_data = resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        raise RuntimeError(
            f"Failed to download grid.xml for {event_id}: {e}") from e

    # Cache locally
    if cache:
        with open(cache_path, 'wb') as f:
            f.write(xml_data)
        logger.info("Cached grid.xml to: %s (%d bytes)",
                     cache_path, len(xml_data))

    return cache_path


def parse_grid_xml(xml_path: str) -> ShakeMapGrid:
    """
    Parse a ShakeMap grid.xml file into a ShakeMapGrid object.

    The grid.xml format (ShakeMap v4) contains:
        <shakemap_grid>
            <event ... magnitude="7.8" lat="37.22" lon="37.01" .../>
            <grid_specification
                lon_min="34.0" lon_max="40.0"
                lat_min="34.6" lat_max="40.0"
                nominal_lon_spacing="0.00833"
                nominal_lat_spacing="0.00833"
                nlon="721" nlat="649" />
            <grid_field index="1" name="LON" units="dd" />
            <grid_field index="2" name="LAT" units="dd" />
            <grid_field index="3" name="MMI" units="intensity" />
            <grid_field index="4" name="PGA" units="%g" />
            <grid_field index="5" name="PGV" units="cm/s" />
            <grid_field index="6" name="PSA03" units="%g" />
            <grid_field index="7" name="PSA10" units="%g" />
            <grid_field index="8" name="PSA30" units="%g" />
            <grid_field index="9" name="STDPGA" ... />  (optional)
            ...
            <grid_data>
            LON LAT MMI PGA PGV PSA03 PSA10 PSA30 VS30
            34.0000 34.6000 3.8 0.3251 2.406 ...
            ...
            </grid_data>
        </shakemap_grid>

    Parameters
    ----------
    xml_path : str
        Path to the grid.xml file.

    Returns
    -------
    ShakeMapGrid
        Parsed grid data.
    """
    logger.info("Parsing grid.xml: %s", xml_path)

    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Handle namespace
    ns = ''
    if root.tag.startswith('{'):
        ns = root.tag.split('}')[0] + '}'

    grid = ShakeMapGrid()

    # Parse event element
    event_el = root.find(f'{ns}event')
    if event_el is not None:
        grid.event_id = event_el.get('event_id', '')
        grid.magnitude = float(event_el.get('magnitude', 0))
        grid.lat_epicenter = float(event_el.get('lat', 0))
        grid.lon_epicenter = float(event_el.get('lon', 0))
        grid.depth_km = float(event_el.get('depth', 0))

    # Parse grid specification
    spec_el = root.find(f'{ns}grid_specification')
    if spec_el is not None:
        grid.grid_spec = {
            'lon_min': float(spec_el.get('lon_min', 0)),
            'lon_max': float(spec_el.get('lon_max', 0)),
            'lat_min': float(spec_el.get('lat_min', 0)),
            'lat_max': float(spec_el.get('lat_max', 0)),
            'nominal_lon_spacing': float(
                spec_el.get('nominal_lon_spacing', 0.01)),
            'nominal_lat_spacing': float(
                spec_el.get('nominal_lat_spacing', 0.01)),
            'nlon': int(spec_el.get('nlon', 0)),
            'nlat': int(spec_el.get('nlat', 0)),
        }

    # Parse field definitions
    field_elements = root.findall(f'{ns}grid_field')
    fields_by_index = {}
    for fe in field_elements:
        idx = int(fe.get('index', 0))
        name = fe.get('name', f'FIELD_{idx}')
        fields_by_index[idx] = name
    grid.field_names = [fields_by_index[k]
                        for k in sorted(fields_by_index.keys())]

    # Parse grid data
    data_el = root.find(f'{ns}grid_data')
    if data_el is not None and data_el.text:
        text = data_el.text.strip()
        # Parse space/newline-delimited numeric data
        grid.data = np.loadtxt(io.StringIO(text))

    if grid.data.ndim == 1:
        n_fields = len(grid.field_names)
        grid.data = grid.data.reshape(-1, n_fields)

    # Extract unique lon/lat arrays
    if len(grid.data) > 0 and 'LON' in grid.field_names:
        lon_idx = grid.field_names.index('LON')
        lat_idx = grid.field_names.index('LAT')
        grid.lons = np.unique(grid.data[:, lon_idx])
        grid.lats = np.unique(grid.data[:, lat_idx])

    logger.info("Parsed %d grid points (%d×%d), %d fields",
                grid.n_points, grid.nlat, grid.nlon,
                len(grid.field_names))

    return grid


# ═══════════════════════════════════════════════════════════════════════
# Spatial Mapping: ShakeMap Grid → Sensor Field Topology
# ═══════════════════════════════════════════════════════════════════════

class ShakeMapLoader:
    """
    Map USGS ShakeMap ground-motion data onto the CALASH sensor field.

    The loader projects real-world lat/lon ShakeMap data onto the
    simulation's 2D Cartesian coordinate system (default 200×200 m)
    using a configurable mapping strategy:

    - **epicenter-centered** (default): The epicenter is placed at
      the simulation disaster epicenter (default 100,100).  The
      ShakeMap coverage area maps proportionally to the simulation
      field so that the spatial damage pattern is preserved.

    - **worst-case**: The area with maximum MMI/PGA is centered on
      the sensor field, simulating a deployment directly at the
      earthquake's most-damaged zone.

    Usage
    -----
    >>> loader = ShakeMapLoader(event_key='turkey_syria_2023',
    ...                         area_width=200.0, area_height=200.0)
    >>> loader.download_and_parse()
    >>> node_pga = loader.get_node_values('PGA', node_positions)
    >>> node_mmi = loader.get_node_values('MMI', node_positions)
    >>> fail_probs = loader.failure_probabilities(node_positions)
    >>> loader.to_disaster_event(epicenter_x=100, epicenter_y=100)
    """

    def __init__(self,
                 event_key: str = None,
                 event_id: str = None,
                 area_width: float = 200.0,
                 area_height: float = 200.0,
                 mapping: str = 'epicenter',
                 cache: bool = True):
        """
        Parameters
        ----------
        event_key : str, optional
            Pre-cataloged event key (e.g., 'turkey_syria_2023').
        event_id : str, optional
            Raw USGS event ID (e.g., 'us6000jllz'). Used if
            event_key is not provided.
        area_width, area_height : float
            Simulation area dimensions in meters.
        mapping : str
            Spatial mapping strategy: 'epicenter' or 'worst_case'.
        cache : bool
            Cache downloaded grid.xml files locally.
        """
        if event_key and event_key in SHAKEMAP_EVENTS:
            self.event_key = event_key
            self.event_id = SHAKEMAP_EVENTS[event_key]['event_id']
            self._catalog_info = SHAKEMAP_EVENTS[event_key]
        elif event_id:
            self.event_key = event_id
            self.event_id = event_id
            self._catalog_info = None
        else:
            raise ValueError(
                "Must provide event_key or event_id.  "
                f"Available keys: {list(SHAKEMAP_EVENTS.keys())}")

        self.area_width = area_width
        self.area_height = area_height
        self.mapping = mapping
        self.cache = cache
        self.grid: Optional[ShakeMapGrid] = None
        self._xml_path: Optional[str] = None

    @property
    def is_loaded(self) -> bool:
        return self.grid is not None and self.grid.n_points > 0

    def download_and_parse(self) -> 'ShakeMapLoader':
        """
        Download (or load from cache) and parse the ShakeMap grid.xml.

        Returns self for method chaining.
        """
        self._xml_path = _download_grid_xml(self.event_id, cache=self.cache)
        self.grid = parse_grid_xml(self._xml_path)
        return self

    def load_from_file(self, xml_path: str) -> 'ShakeMapLoader':
        """
        Load and parse a local grid.xml file directly.

        Parameters
        ----------
        xml_path : str
            Path to a grid.xml file.

        Returns self for method chaining.
        """
        self._xml_path = xml_path
        self.grid = parse_grid_xml(xml_path)
        return self

    # ── Coordinate Mapping ────────────────────────────────────────────

    def _latlon_to_sim(self,
                       lat: float, lon: float,
                       epicenter_sim: Tuple[float, float] = (100.0, 100.0)
                       ) -> Tuple[float, float]:
        """
        Map a lat/lon to simulation (x, y) coordinates.

        For 'epicenter' mapping, the earthquake epicenter maps to
        epicenter_sim, and the full ShakeMap bounding box maps
        proportionally to the simulation area.

        For 'worst_case' mapping, the point of maximum MMI maps
        to the center of the simulation area.

        Parameters
        ----------
        lat, lon : float
            Geographic coordinates.
        epicenter_sim : tuple
            (x, y) position of the epicenter in simulation coordinates.

        Returns
        -------
        (x, y) : tuple of float
            Simulation coordinates in meters.
        """
        spec = self.grid.grid_spec

        if self.mapping == 'worst_case':
            # Find the max-MMI location and center on simulation field
            mmi = self.grid.get_field('MMI')
            max_idx = np.argmax(mmi)
            ref_lon = self.grid.data[max_idx,
                                     self.grid.field_names.index('LON')]
            ref_lat = self.grid.data[max_idx,
                                     self.grid.field_names.index('LAT')]
            center_x = self.area_width / 2
            center_y = self.area_height / 2
        else:
            # Epicenter-centered mapping
            ref_lon = self.grid.lon_epicenter
            ref_lat = self.grid.lat_epicenter
            center_x, center_y = epicenter_sim

        # Approximate meters per degree at epicenter latitude
        m_per_deg_lat = 111_320.0  # ≈ 111.32 km
        m_per_deg_lon = 111_320.0 * np.cos(np.radians(ref_lat))

        # Relative offset in meters
        dx_m = (lon - ref_lon) * m_per_deg_lon
        dy_m = (lat - ref_lat) * m_per_deg_lat

        # Scale: the ShakeMap bounding box spans a real-world area
        # (potentially hundreds of km).  We scale so the full bbox
        # maps to the simulation area, preserving the spatial pattern
        # of shaking relative to the epicenter.
        lon_span_m = (spec['lon_max'] - spec['lon_min']) * m_per_deg_lon
        lat_span_m = (spec['lat_max'] - spec['lat_min']) * m_per_deg_lat

        scale_x = self.area_width / max(lon_span_m, 1.0)
        scale_y = self.area_height / max(lat_span_m, 1.0)

        x = center_x + dx_m * scale_x
        y = center_y + dy_m * scale_y

        return (x, y)

    def _sim_to_latlon(self,
                       x: float, y: float,
                       epicenter_sim: Tuple[float, float] = (100.0, 100.0)
                       ) -> Tuple[float, float]:
        """
        Inverse mapping: simulation (x, y) → (lat, lon).
        """
        spec = self.grid.grid_spec

        if self.mapping == 'worst_case':
            mmi = self.grid.get_field('MMI')
            max_idx = np.argmax(mmi)
            ref_lon = self.grid.data[max_idx,
                                     self.grid.field_names.index('LON')]
            ref_lat = self.grid.data[max_idx,
                                     self.grid.field_names.index('LAT')]
            center_x = self.area_width / 2
            center_y = self.area_height / 2
        else:
            ref_lon = self.grid.lon_epicenter
            ref_lat = self.grid.lat_epicenter
            center_x, center_y = epicenter_sim

        m_per_deg_lat = 111_320.0
        m_per_deg_lon = 111_320.0 * np.cos(np.radians(ref_lat))

        lon_span_m = (spec['lon_max'] - spec['lon_min']) * m_per_deg_lon
        lat_span_m = (spec['lat_max'] - spec['lat_min']) * m_per_deg_lat

        scale_x = self.area_width / max(lon_span_m, 1.0)
        scale_y = self.area_height / max(lat_span_m, 1.0)

        dx_m = (x - center_x) / scale_x
        dy_m = (y - center_y) / scale_y

        lon = ref_lon + dx_m / m_per_deg_lon
        lat = ref_lat + dy_m / m_per_deg_lat

        return (lat, lon)

    # ── Node-Level Queries ────────────────────────────────────────────

    def get_node_values(self,
                        field_name: str,
                        node_positions: List[Tuple[float, float]],
                        epicenter_sim: Tuple[float, float] = (100.0, 100.0)
                        ) -> np.ndarray:
        """
        Interpolate a ShakeMap field at each sensor node position.

        Parameters
        ----------
        field_name : str
            Grid field name: 'MMI', 'PGA', 'PGV', 'PSA03', 'PSA10',
            'PSA30', 'VS30', etc.
        node_positions : list of (x, y)
            Sensor node positions in simulation coordinates (meters).
        epicenter_sim : tuple
            (x, y) epicenter location in simulation coordinates.

        Returns
        -------
        np.ndarray
            Array of interpolated values, one per node.
        """
        if not self.is_loaded:
            raise RuntimeError("ShakeMap not loaded. Call "
                               "download_and_parse() first.")

        values = np.zeros(len(node_positions))
        for i, (x, y) in enumerate(node_positions):
            lat, lon = self._sim_to_latlon(x, y, epicenter_sim)
            values[i] = self.grid.field_at_latlon(field_name, lat, lon)
        return values

    def failure_probabilities(self,
                              node_positions: List[Tuple[float, float]],
                              epicenter_sim: Tuple[float, float] = (100.0, 100.0),
                              method: str = 'pga',
                              mmi_threshold: float = 6.0,
                              pga_threshold_g: float = 0.3
                              ) -> np.ndarray:
        """
        Compute per-node failure probabilities from ShakeMap data.

        Two methods are available:

        1. **pga** (default): Use PGA-based fragility curve.
           P_fail = min(1, (PGA_g / pga_threshold)^2)
           Physical basis: sensor electronics fail when PGA exceeds
           the mounting tolerance (~0.3 g for consumer IoT; Younis
           et al. 2014, Computer Networks).

        2. **mmi**: Use MMI-based threshold.
           P_fail = sigmoid((MMI - mmi_threshold) / 0.5)
           Nodes at MMI ≥ VI (Strong shaking) have >50% failure;
           at MMI ≥ VIII (Destructive), ~98% failure.

        Parameters
        ----------
        node_positions : list of (x, y)
            Sensor node positions in simulation coordinates.
        epicenter_sim : tuple
            (x, y) epicenter in simulation coordinates.
        method : str
            'pga' or 'mmi'.
        mmi_threshold : float
            MMI value at which P_fail = 0.5 (for 'mmi' method).
        pga_threshold_g : float
            PGA value (in g) at which P_fail = 1.0 (for 'pga' method).

        Returns
        -------
        np.ndarray
            Failure probabilities in [0, 1], one per node.
        """
        if method == 'pga':
            pga_pctg = self.get_node_values('PGA', node_positions,
                                            epicenter_sim)
            # PGA is in %g in ShakeMap grid.xml → convert to g
            pga_g = pga_pctg / 100.0
            p_fail = np.minimum(1.0, (pga_g / pga_threshold_g) ** 2)
        elif method == 'mmi':
            mmi = self.get_node_values('MMI', node_positions, epicenter_sim)
            # Sigmoid fragility curve centred at mmi_threshold
            p_fail = 1.0 / (1.0 + np.exp(-(mmi - mmi_threshold) / 0.5))
        else:
            raise ValueError(f"Unknown method '{method}'. Use 'pga' or 'mmi'.")

        return p_fail

    def to_disaster_params(self,
                           epicenter_x: float = 100.0,
                           epicenter_y: float = 100.0,
                           node_positions: List[Tuple[float, float]] = None
                           ) -> Dict:
        """
        Convert ShakeMap data to CALASH disaster simulation parameters.

        Computes:
        - Effective Gaussian damage_radius that best fits the
          ShakeMap spatial failure pattern.
        - Per-node failure probabilities (if positions given).
        - Max MMI, PGA, PGV at the epicenter.

        Parameters
        ----------
        epicenter_x, epicenter_y : float
            Epicenter in simulation coordinates.
        node_positions : list of (x, y), optional
            If provided, include per-node failure probabilities.

        Returns
        -------
        dict
            Dictionary with keys: 'damage_radius', 'epicenter_x/y',
            'max_mmi', 'max_pga_g', 'max_pgv_cms', 'event_id',
            'magnitude', and optionally 'node_failure_probs'.
        """
        if not self.is_loaded:
            raise RuntimeError("ShakeMap not loaded.")

        mmi_all = self.grid.get_field('MMI')
        pga_all = self.grid.get_field('PGA')
        pgv_all = self.grid.get_field('PGV')

        # Estimate effective Gaussian damage radius from ShakeMap
        # Fraction of grid points with MMI >= 8 (Destructive)
        frac_mmi8 = float(np.mean(mmi_all >= 8.0))
        # damage_radius such that 2πr² / (W*H) = frac_mmi8
        area = self.area_width * self.area_height
        if frac_mmi8 > 0:
            damage_radius = np.sqrt(frac_mmi8 * area / (2 * np.pi))
        else:
            # Fall back to MMI >= 6 fraction
            frac_mmi6 = float(np.mean(mmi_all >= 6.0))
            damage_radius = np.sqrt(
                max(frac_mmi6, 0.01) * area / (2 * np.pi))

        damage_radius = np.clip(damage_radius, 10.0, 150.0)

        result = {
            'event_id': self.grid.event_id or self.event_id,
            'event_key': self.event_key,
            'magnitude': self.grid.magnitude,
            'depth_km': self.grid.depth_km,
            'epicenter_x': epicenter_x,
            'epicenter_y': epicenter_y,
            'damage_radius': float(damage_radius),
            'max_mmi': float(np.max(mmi_all)),
            'max_pga_pctg': float(np.max(pga_all)),
            'max_pga_g': float(np.max(pga_all) / 100.0),
            'max_pgv_cms': float(np.max(pgv_all)),
            'mean_mmi': float(np.mean(mmi_all)),
            'frac_mmi_ge_6': float(np.mean(mmi_all >= 6.0)),
            'frac_mmi_ge_8': float(np.mean(mmi_all >= 8.0)),
            'grid_points': self.grid.n_points,
            'source': 'USGS ShakeMap grid.xml',
        }

        if node_positions is not None:
            fail_probs = self.failure_probabilities(
                node_positions, (epicenter_x, epicenter_y))
            result['node_failure_probs'] = fail_probs
            result['expected_kill_fraction'] = float(np.mean(fail_probs))

        return result

    def to_disaster_event(self,
                          epicenter_x: float = 100.0,
                          epicenter_y: float = 100.0,
                          rng: np.random.Generator = None):
        """
        Create a DisasterEvent with ShakeMap-calibrated damage radius.

        Parameters
        ----------
        epicenter_x, epicenter_y : float
            Epicenter in simulation coordinates.
        rng : np.random.Generator
            Random number generator.

        Returns
        -------
        DisasterEvent
            Configured with the ShakeMap-derived damage_radius.
        """
        from models.disaster import DisasterEvent

        params = self.to_disaster_params(epicenter_x, epicenter_y)
        return DisasterEvent(
            epicenter_x=epicenter_x,
            epicenter_y=epicenter_y,
            damage_radius=params['damage_radius'],
            rng=rng,
        )

    def apply_to_network(self,
                         network,
                         epicenter_sim: Tuple[float, float] = (100.0, 100.0),
                         method: str = 'pga',
                         rng: np.random.Generator = None
                         ) -> Tuple[List[int], List[int]]:
        """
        Apply ShakeMap-based spatially heterogeneous damage to a network.

        Unlike the Gaussian model (DisasterEvent), this uses the actual
        ShakeMap PGA/MMI spatial pattern to determine per-node failure
        probabilities, giving realistic heterogeneous damage.

        Parameters
        ----------
        network : Network
            The WSN network object.
        epicenter_sim : tuple
            (x, y) epicenter in simulation coordinates.
        method : str
            'pga' or 'mmi' — how to compute failure probabilities.
        rng : np.random.Generator
            Random number generator.

        Returns
        -------
        killed_ids : list of int
            IDs of nodes killed.
        survived_ids : list of int
            IDs of surviving nodes.
        """
        if rng is None:
            rng = np.random.default_rng()

        # Collect alive node positions
        alive_nodes = [n for n in network.nodes if n.alive]
        positions = [(n.x, n.y) for n in alive_nodes]

        # Get per-node failure probabilities from ShakeMap
        fail_probs = self.failure_probabilities(
            positions, epicenter_sim, method=method)

        killed_ids = []
        survived_ids = []

        for node, p_fail in zip(alive_nodes, fail_probs):
            if rng.random() < p_fail:
                node.alive = False
                node.energy = 0.0
                node.is_ch = False
                killed_ids.append(node.id)
            else:
                survived_ids.append(node.id)
                # Partial energy damage for survivors
                if p_fail > 0.1:
                    energy_loss = 0.5 * p_fail
                    node.energy *= (1.0 - energy_loss)

        return killed_ids, survived_ids

    # ── Visualization Helper ──────────────────────────────────────────

    def generate_damage_heatmap(self,
                                field: str = 'MMI',
                                resolution: int = 100,
                                epicenter_sim: Tuple[float, float] = (100.0, 100.0)
                                ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Generate a 2D heatmap of a ShakeMap field over the simulation area.

        Useful for visualization: overlay the ShakeMap intensity on the
        sensor deployment plot.

        Parameters
        ----------
        field : str
            ShakeMap field: 'MMI', 'PGA', 'PGV', etc.
        resolution : int
            Number of grid points per dimension.
        epicenter_sim : tuple
            (x, y) epicenter in simulation coordinates.

        Returns
        -------
        X, Y : np.ndarray
            2D meshgrid arrays (resolution × resolution).
        Z : np.ndarray
            Interpolated field values (resolution × resolution).
        """
        if not self.is_loaded:
            raise RuntimeError("ShakeMap not loaded.")

        x_lin = np.linspace(0, self.area_width, resolution)
        y_lin = np.linspace(0, self.area_height, resolution)
        X, Y = np.meshgrid(x_lin, y_lin)

        Z = np.zeros_like(X)
        for i in range(resolution):
            for j in range(resolution):
                lat, lon = self._sim_to_latlon(
                    X[i, j], Y[i, j], epicenter_sim)
                Z[i, j] = self.grid.field_at_latlon(field, lat, lon)

        return X, Y, Z

    # ── Serialization ─────────────────────────────────────────────────

    def save_parsed(self, out_path: str = None):
        """
        Save parsed ShakeMap data as a compressed .npz file for
        fast future loading (avoids re-parsing the ~30 MB XML).
        """
        if not self.is_loaded:
            raise RuntimeError("No data to save.")
        if out_path is None:
            out_path = os.path.join(
                _CACHE_DIR,
                f'{self.event_id}_grid_parsed.npz')
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        np.savez_compressed(
            out_path,
            data=self.grid.data,
            field_names=np.array(self.grid.field_names),
            event_id=self.grid.event_id,
            magnitude=self.grid.magnitude,
            lat_epicenter=self.grid.lat_epicenter,
            lon_epicenter=self.grid.lon_epicenter,
            depth_km=self.grid.depth_km,
            **{f'gs_{k}': v for k, v in self.grid.grid_spec.items()},
        )
        logger.info("Saved parsed ShakeMap to %s", out_path)

    def load_parsed(self, npz_path: str = None) -> 'ShakeMapLoader':
        """
        Load a previously saved .npz file (much faster than XML).
        """
        if npz_path is None:
            npz_path = os.path.join(
                _CACHE_DIR,
                f'{self.event_id}_grid_parsed.npz')
        if not os.path.exists(npz_path):
            raise FileNotFoundError(f"No parsed cache at {npz_path}")

        npz = np.load(npz_path, allow_pickle=True)
        self.grid = ShakeMapGrid()
        self.grid.data = npz['data']
        self.grid.field_names = list(npz['field_names'])
        self.grid.event_id = str(npz['event_id'])
        self.grid.magnitude = float(npz['magnitude'])
        self.grid.lat_epicenter = float(npz['lat_epicenter'])
        self.grid.lon_epicenter = float(npz['lon_epicenter'])
        self.grid.depth_km = float(npz['depth_km'])

        # Restore grid_spec
        self.grid.grid_spec = {}
        for key in ['lon_min', 'lon_max', 'lat_min', 'lat_max',
                     'nominal_lon_spacing', 'nominal_lat_spacing',
                     'nlon', 'nlat']:
            gs_key = f'gs_{key}'
            if gs_key in npz:
                val = npz[gs_key]
                if key in ('nlon', 'nlat'):
                    self.grid.grid_spec[key] = int(val)
                else:
                    self.grid.grid_spec[key] = float(val)

        # Restore unique lons/lats
        if 'LON' in self.grid.field_names:
            lon_idx = self.grid.field_names.index('LON')
            lat_idx = self.grid.field_names.index('LAT')
            self.grid.lons = np.unique(self.grid.data[:, lon_idx])
            self.grid.lats = np.unique(self.grid.data[:, lat_idx])

        logger.info("Loaded parsed ShakeMap from %s (%d points)",
                     npz_path, self.grid.n_points)
        return self

    # ── String Representation ─────────────────────────────────────────

    def __repr__(self) -> str:
        status = 'loaded' if self.is_loaded else 'not loaded'
        pts = self.grid.n_points if self.is_loaded else 0
        return (f"ShakeMapLoader(event='{self.event_key}', "
                f"status={status}, points={pts})")

    @staticmethod
    def list_events() -> Dict:
        """List all pre-cataloged ShakeMap events."""
        return {k: v['description'] for k, v in SHAKEMAP_EVENTS.items()}

    @staticmethod
    def get_citation() -> str:
        """Return the standard citation for ShakeMap data."""
        return (
            "Worden, C.B. & Wald, D.J. (2016). ShakeMap Manual Online: "
            "Technical Manual, User's Guide, and Software Guide. "
            "USGS. doi:10.5066/F7D21VPQ\n"
            "Data source: USGS Earthquake Hazards Program, "
            "https://earthquake.usgs.gov/data/shakemap/"
        )
