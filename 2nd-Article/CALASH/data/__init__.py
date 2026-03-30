"""
Real-World Data Generators
==========================
Generate realistic datasets based on published statistics from:

1. Intel Berkeley Research Lab (2004) — sensor readings
2. Electricity Maps — carbon intensity traces by country
3. USGS Earthquake Catalog — seismic disaster parameters
4. NASA FIRMS / MODIS — wildfire disaster parameters

These generators reproduce the statistical properties of real datasets
(distributions, correlations, temporal patterns) for reproducible experiments
without requiring external data downloads.

Citations:
    [1] Madden, S. "Intel Lab Data." MIT CSAIL, 2004.
        http://db.csail.mit.edu/labdata/labdata.html
    [2] Electricity Maps. "Real-time & Historical Carbon Intensity."
        https://app.electricitymaps.com
    [3] USGS Earthquake Hazards Program. https://earthquake.usgs.gov
    [4] NASA FIRMS: Fire Information for Resource Management System.
        https://firms.modaps.eosdis.nasa.gov
    [5] Worden, C.B. & Wald, D.J. (2016). ShakeMap Manual Online.
        USGS. doi:10.5066/F7D21VPQ
"""

from data.intel_lab import IntelLabDataset
from data.electricity_maps import ElectricityMapsTraces
from data.disaster_catalog import DisasterCatalog
from data.shakemap_loader import ShakeMapLoader, ShakeMapGrid, SHAKEMAP_EVENTS

__all__ = [
    'IntelLabDataset',
    'ElectricityMapsTraces',
    'DisasterCatalog',
    'ShakeMapLoader',
    'ShakeMapGrid',
    'SHAKEMAP_EVENTS',
]
