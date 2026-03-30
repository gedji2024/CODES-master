#!/usr/bin/env python3
"""
ShakeMapLoader — Smoke Test Suite
===================================
Tests the full ShakeMapLoader pipeline:
  1. Offline tests (unit / parsing / mapping) — no network needed
  2. Online test (download from USGS) — optional, skipped without connectivity

Run:
    cd CALASH
    python -m pytest tests/test_shakemap.py -v
    # or directly:
    python tests/test_shakemap.py
"""

import os
import sys
import tempfile
import textwrap
import unittest

import numpy as np

# Ensure CALASH is importable
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.shakemap_loader import (
    ShakeMapLoader, ShakeMapGrid, SHAKEMAP_EVENTS,
    parse_grid_xml,
)


# ─── Minimal grid.xml fixture ────────────────────────────────────────
# A tiny 3×3 synthetic grid.xml that exercises the full parser
# without network access.  MMI values range from 3 to 9.
MINI_GRID_XML = textwrap.dedent("""\
<?xml version="1.0" encoding="UTF-8"?>
<shakemap_grid xmlns="http://earthquake.usgs.gov/eqcenter/shakemap"
               event_id="test001" event_type="ACTUAL"
               shakemap_id="test001" shakemap_version="1"
               code_version="4.0" process_timestamp="2024-01-01T00:00:00Z"
               shakemap_originator="us"
               map_status="RELEASED"
               shakemap_event_type="ACTUAL">
<event event_id="test001" magnitude="7.5" depth="10" lat="37.0" lon="37.0"
       event_timestamp="2024-01-01T00:00:00Z"
       event_network="us" event_description="Synthetic test event"/>
<grid_specification lon_min="36.0" lon_max="38.0"
                    lat_min="36.0" lat_max="38.0"
                    nominal_lon_spacing="1.0"
                    nominal_lat_spacing="1.0"
                    nlon="3" nlat="3"/>
<grid_field index="1" name="LON" units="dd"/>
<grid_field index="2" name="LAT" units="dd"/>
<grid_field index="3" name="MMI" units="intensity"/>
<grid_field index="4" name="PGA" units="%g"/>
<grid_field index="5" name="PGV" units="cm/s"/>
<grid_data>
36.0 36.0 3.0 0.50 0.10
37.0 36.0 4.5 2.00 1.50
38.0 36.0 3.0 0.50 0.10
36.0 37.0 5.5 8.00 6.00
37.0 37.0 9.0 80.00 60.00
38.0 37.0 5.5 8.00 6.00
36.0 38.0 3.0 0.50 0.10
37.0 38.0 4.5 2.00 1.50
38.0 38.0 3.0 0.50 0.10
</grid_data>
</shakemap_grid>
""")


class TestShakeMapGridParsing(unittest.TestCase):
    """Tests for grid.xml parsing (fully offline)."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        cls.xml_path = os.path.join(cls.tmpdir, 'test_grid.xml')
        with open(cls.xml_path, 'w') as f:
            f.write(MINI_GRID_XML)
        cls.grid = parse_grid_xml(cls.xml_path)

    def test_event_metadata(self):
        self.assertEqual(self.grid.event_id, 'test001')
        self.assertAlmostEqual(self.grid.magnitude, 7.5)
        self.assertAlmostEqual(self.grid.lat_epicenter, 37.0)
        self.assertAlmostEqual(self.grid.lon_epicenter, 37.0)
        self.assertAlmostEqual(self.grid.depth_km, 10.0)

    def test_grid_spec(self):
        self.assertEqual(self.grid.nlon, 3)
        self.assertEqual(self.grid.nlat, 3)
        self.assertAlmostEqual(self.grid.grid_spec['lon_min'], 36.0)
        self.assertAlmostEqual(self.grid.grid_spec['lon_max'], 38.0)
        self.assertAlmostEqual(self.grid.grid_spec['lat_min'], 36.0)
        self.assertAlmostEqual(self.grid.grid_spec['lat_max'], 38.0)

    def test_field_names(self):
        self.assertEqual(self.grid.field_names,
                         ['LON', 'LAT', 'MMI', 'PGA', 'PGV'])

    def test_data_shape(self):
        self.assertEqual(self.grid.n_points, 9)
        self.assertEqual(self.grid.data.shape, (9, 5))

    def test_mmi_range(self):
        mmi = self.grid.get_field('MMI')
        self.assertAlmostEqual(mmi.min(), 3.0)
        self.assertAlmostEqual(mmi.max(), 9.0)

    def test_pga_range(self):
        pga = self.grid.get_field('PGA')
        self.assertAlmostEqual(pga.min(), 0.5)
        self.assertAlmostEqual(pga.max(), 80.0)

    def test_2d_reshape(self):
        mmi2d = self.grid.get_2d_field('MMI')
        self.assertEqual(mmi2d.shape, (3, 3))
        # Epicenter is at center → highest value
        self.assertAlmostEqual(mmi2d[1, 1], 9.0)
        # Corners should be lowest
        self.assertAlmostEqual(mmi2d[0, 0], 3.0)

    def test_bilinear_interpolation_at_grid_point(self):
        # Query exactly at the center grid point (37,37)
        val = self.grid.field_at_latlon('MMI', 37.0, 37.0)
        self.assertAlmostEqual(val, 9.0, places=1)

    def test_bilinear_interpolation_between_points(self):
        # Query between center (MMI=9) and corner (MMI=3)
        val = self.grid.field_at_latlon('MMI', 37.0, 37.5)
        # Should be between 5.5 and 9.0
        self.assertGreater(val, 5.0)
        self.assertLess(val, 9.5)

    def test_summary(self):
        s = self.grid.summary()
        self.assertEqual(s['event_id'], 'test001')
        self.assertEqual(s['grid_points'], 9)
        self.assertEqual(s['grid_shape'], (3, 3))
        self.assertIn('MMI_range', s)


class TestShakeMapLoader(unittest.TestCase):
    """Tests for the ShakeMapLoader class (offline)."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        cls.xml_path = os.path.join(cls.tmpdir, 'test_grid.xml')
        with open(cls.xml_path, 'w') as f:
            f.write(MINI_GRID_XML)
        cls.loader = ShakeMapLoader(
            event_id='test001', area_width=200.0, area_height=200.0)
        cls.loader.load_from_file(cls.xml_path)

    def test_is_loaded(self):
        self.assertTrue(self.loader.is_loaded)

    def test_repr(self):
        r = repr(self.loader)
        self.assertIn('test001', r)
        self.assertIn('loaded', r)

    def test_node_mmi_values(self):
        """Nodes near center should have higher MMI than edges."""
        center = [(100.0, 100.0)]
        edge = [(0.0, 0.0)]
        mmi_center = self.loader.get_node_values('MMI', center)
        mmi_edge = self.loader.get_node_values('MMI', edge)
        self.assertGreater(mmi_center[0], mmi_edge[0])

    def test_failure_probabilities_pga(self):
        positions = [(100.0, 100.0), (0.0, 0.0)]
        probs = self.loader.failure_probabilities(
            positions, method='pga')
        self.assertEqual(len(probs), 2)
        # Center (high PGA) should have higher failure prob
        self.assertGreater(probs[0], probs[1])
        # All probabilities in [0, 1]
        self.assertTrue(np.all(probs >= 0.0))
        self.assertTrue(np.all(probs <= 1.0))

    def test_failure_probabilities_mmi(self):
        positions = [(100.0, 100.0), (0.0, 0.0)]
        probs = self.loader.failure_probabilities(
            positions, method='mmi')
        self.assertEqual(len(probs), 2)
        self.assertGreater(probs[0], probs[1])
        self.assertTrue(np.all(probs >= 0.0))
        self.assertTrue(np.all(probs <= 1.0))

    def test_to_disaster_params(self):
        params = self.loader.to_disaster_params()
        self.assertIn('damage_radius', params)
        self.assertIn('max_mmi', params)
        self.assertIn('max_pga_g', params)
        self.assertGreater(params['damage_radius'], 0)
        self.assertAlmostEqual(params['max_mmi'], 9.0)

    def test_to_disaster_params_with_nodes(self):
        positions = [(50, 50), (100, 100), (150, 150)]
        params = self.loader.to_disaster_params(
            node_positions=positions)
        self.assertIn('node_failure_probs', params)
        self.assertIn('expected_kill_fraction', params)
        self.assertEqual(len(params['node_failure_probs']), 3)

    def test_heatmap_generation(self):
        X, Y, Z = self.loader.generate_damage_heatmap(
            field='MMI', resolution=10)
        self.assertEqual(X.shape, (10, 10))
        self.assertEqual(Y.shape, (10, 10))
        self.assertEqual(Z.shape, (10, 10))
        # Center should have higher MMI
        center_val = Z[5, 5]
        corner_val = Z[0, 0]
        self.assertGreater(center_val, corner_val)

    def test_save_and_load_parsed(self):
        npz_path = os.path.join(self.tmpdir, 'test_parsed.npz')
        self.loader.save_parsed(npz_path)
        self.assertTrue(os.path.exists(npz_path))

        # Load back and verify
        loader2 = ShakeMapLoader(event_id='test001')
        loader2.load_parsed(npz_path)
        self.assertTrue(loader2.is_loaded)
        self.assertEqual(loader2.grid.n_points, 9)
        self.assertAlmostEqual(loader2.grid.magnitude, 7.5)

        # Check interpolation still works
        val = loader2.grid.field_at_latlon('MMI', 37.0, 37.0)
        self.assertAlmostEqual(val, 9.0, places=1)

    def test_list_events(self):
        events = ShakeMapLoader.list_events()
        self.assertIn('turkey_syria_2023', events)
        self.assertIsInstance(events['turkey_syria_2023'], str)

    def test_get_citation(self):
        cite = ShakeMapLoader.get_citation()
        self.assertIn('Worden', cite)
        self.assertIn('USGS', cite)

    def test_to_disaster_event(self):
        event = self.loader.to_disaster_event(
            epicenter_x=100, epicenter_y=100,
            rng=np.random.default_rng(42))
        # Should be a DisasterEvent instance
        from models.disaster import DisasterEvent
        self.assertIsInstance(event, DisasterEvent)


class TestShakeMapNetworkIntegration(unittest.TestCase):
    """Test apply_to_network with a mock network."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        cls.xml_path = os.path.join(cls.tmpdir, 'test_grid.xml')
        with open(cls.xml_path, 'w') as f:
            f.write(MINI_GRID_XML)
        cls.loader = ShakeMapLoader(
            event_id='test001', area_width=200.0, area_height=200.0)
        cls.loader.load_from_file(cls.xml_path)

    def test_apply_to_network(self):
        """Apply ShakeMap damage to a real Network object."""
        from config import SimulationConfig
        from models.network import Network

        config = SimulationConfig(num_nodes=50, area_width=200, area_height=200)
        rng = np.random.default_rng(42)
        network = Network(config, rng)

        killed, survived = self.loader.apply_to_network(
            network, epicenter_sim=(100, 100), method='pga', rng=rng)

        # Some nodes should be killed, some survived
        total = len(killed) + len(survived)
        self.assertEqual(total, 50)
        # Not all should die (edge nodes have low PGA)
        self.assertGreater(len(survived), 0)
        # Some should die (center nodes have high PGA)
        self.assertGreater(len(killed), 0)

        # Verify killed nodes are actually dead
        for nid in killed:
            self.assertFalse(network.nodes[nid].alive)
            self.assertEqual(network.nodes[nid].energy, 0.0)


class TestCatalogEvents(unittest.TestCase):
    """Verify catalog data consistency."""

    def test_all_events_have_required_fields(self):
        required = {'event_id', 'magnitude', 'lat', 'lon',
                    'depth_km', 'date', 'description'}
        for key, info in SHAKEMAP_EVENTS.items():
            for field in required:
                self.assertIn(field, info,
                              f"Event '{key}' missing field '{field}'")

    def test_magnitudes_reasonable(self):
        for key, info in SHAKEMAP_EVENTS.items():
            self.assertGreaterEqual(info['magnitude'], 5.0,
                                    f"{key} magnitude too low")
            self.assertLessEqual(info['magnitude'], 10.0,
                                 f"{key} magnitude too high")

    def test_coordinates_valid(self):
        for key, info in SHAKEMAP_EVENTS.items():
            self.assertGreaterEqual(info['lat'], -90)
            self.assertLessEqual(info['lat'], 90)
            self.assertGreaterEqual(info['lon'], -180)
            self.assertLessEqual(info['lon'], 180)


class TestShakeMapOnline(unittest.TestCase):
    """
    Online tests — download real USGS ShakeMap data.
    Skipped if no internet connectivity.
    """

    @classmethod
    def setUpClass(cls):
        """Check if USGS API is reachable."""
        import urllib.request
        try:
            urllib.request.urlopen(
                'https://earthquake.usgs.gov/fdsnws/event/1/version',
                timeout=10)
            cls.online = True
        except Exception:
            cls.online = False

    def setUp(self):
        if not self.online:
            self.skipTest("USGS API not reachable (offline mode)")

    def test_download_turkey_syria(self):
        """Download and parse the Turkey-Syria 2023 ShakeMap."""
        loader = ShakeMapLoader(event_key='turkey_syria_2023')
        loader.download_and_parse()

        self.assertTrue(loader.is_loaded)
        self.assertGreater(loader.grid.n_points, 100_000)
        self.assertAlmostEqual(loader.grid.magnitude, 7.8, places=0)

        # Check fields present
        self.assertIn('MMI', loader.grid.field_names)
        self.assertIn('PGA', loader.grid.field_names)
        self.assertIn('PGV', loader.grid.field_names)

        # Check MMI at epicenter is high
        epi_mmi = loader.grid.field_at_latlon(
            'MMI', loader.grid.lat_epicenter, loader.grid.lon_epicenter)
        self.assertGreater(epi_mmi, 7.0)

        # Disaster params
        params = loader.to_disaster_params()
        self.assertGreater(params['damage_radius'], 10)
        self.assertGreater(params['max_pga_g'], 0.1)

        # Save/load round-trip
        tmpdir = tempfile.mkdtemp()
        npz_path = os.path.join(tmpdir, 'turkey_test.npz')
        loader.save_parsed(npz_path)
        loader2 = ShakeMapLoader(event_key='turkey_syria_2023')
        loader2.load_parsed(npz_path)
        self.assertEqual(loader2.grid.n_points, loader.grid.n_points)


if __name__ == '__main__':
    unittest.main(verbosity=2)
