"""
Real Intel Lab Data Loader
============================
Loads the parsed Intel Berkeley Lab deployment data for use in
compressive sensing validation with genuine sensor readings.

Dataset provenance:
    Name:     Intel Lab Data
    Source:   MIT CSAIL / Intel Research Berkeley
    URL:      http://db.csail.mit.edu/labdata/labdata.html
    Download: http://db.csail.mit.edu/labdata/data.txt.gz (34 MB)
    Format:   TSV — date, time, epoch, moteid, temperature, humidity,
              light, voltage (2.3 million readings)
    Nodes:    54 Mica2 motes deployed in the Intel Berkeley Research lab
    Period:   February 28 to April 5, 2004
    Sampling: ~31 seconds per reading per mote
    Licence:  Public domain (MIT CSAIL research data)
    Parsed:   data/real_traces/parse_intel_lab.py -> intel_lab_parsed.npz

Citation:
    Madden, S. "Intel Lab Data." MIT CSAIL, 2004.
    http://db.csail.mit.edu/labdata/labdata.html

    Also referenced in:
    Bodik, P. et al. "Intel Lab Data." MIT CSAIL & Intel Research, 2004.

Why this dataset:
    - Gold standard for WSN compressive sensing evaluation
    - Real temperature readings (not synthetic) with spatial correlation
    - 54 nodes matches typical small-to-medium WSN deployment
    - Widely cited in CS-WSN literature (Haupt et al. 2008, Luo et al. 2009)
    - Temperature signals are approximately 1-sparse in DCT domain,
      enabling near-perfect CS reconstruction even at low compression ratios

This module provides:
    - RealIntelLabLoader: load actual temperature readings
    - get_signal(): return a real signal vector for CS testing
"""

import os
import numpy as np


_PARSED_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'real_traces', 'intel_lab_parsed.npz'
)


class RealIntelLabLoader:
    """
    Load real Intel Lab temperature traces for simulation.

    Each call to get_signal() returns a genuine 100-dim temperature
    vector from the Berkeley Lab deployment, cycling through windows.

    Parameters
    ----------
    signal_dim : int
        Signal vector length (default 100, matching parsed windows).
    rng : np.random.Generator
        Random number generator for node assignment.
    """

    def __init__(self, signal_dim: int = 100,
                 rng: np.random.Generator = None):
        self.signal_dim = signal_dim
        self.rng = rng or np.random.default_rng(42)
        self._loaded = False
        self._data = {}
        self._node_ids = []
        self._counters = {}  # per-node window index
        self._global_mean = 22.0
        self._global_std = 3.65

    def _load(self):
        """Lazy-load the parsed NPZ file."""
        if self._loaded:
            return

        if not os.path.exists(_PARSED_FILE):
            raise FileNotFoundError(
                f"Parsed Intel Lab data not found at {_PARSED_FILE}. "
                f"Run: python data/real_traces/parse_intel_lab.py"
            )

        npz = np.load(_PARSED_FILE, allow_pickle=True)
        self._node_ids = list(npz['node_ids'])
        self._global_mean = float(npz['global_mean'])
        self._global_std = float(npz['global_std'])

        for nid in self._node_ids:
            key = f'node_{nid}'
            if key in npz:
                self._data[nid] = npz[key]
                self._counters[nid] = 0

        self._loaded = True

    @property
    def available(self) -> bool:
        """Check if the parsed data file exists."""
        return os.path.exists(_PARSED_FILE)

    @property
    def num_nodes(self) -> int:
        self._load()
        return len(self._node_ids)

    @property
    def global_mean(self) -> float:
        self._load()
        return self._global_mean

    @property
    def global_std(self) -> float:
        self._load()
        return self._global_std

    def get_signal(self, sim_node_id: int = None) -> np.ndarray:
        """
        Get a real temperature signal vector.

        Parameters
        ----------
        sim_node_id : int, optional
            Simulation node ID. Maps to a real Intel Lab node
            via modular arithmetic.

        Returns
        -------
        np.ndarray
            Temperature signal of shape (signal_dim,).
        """
        self._load()

        if sim_node_id is not None:
            # Deterministic mapping: sim_node → real Intel Lab node
            idx = sim_node_id % len(self._node_ids)
            real_nid = self._node_ids[idx]
        else:
            real_nid = self.rng.choice(self._node_ids)

        windows = self._data[real_nid]
        counter = self._counters.get(real_nid, 0)

        # Cycle through windows
        signal = windows[counter % len(windows)]
        self._counters[real_nid] = counter + 1

        # Ensure correct dimension
        if len(signal) != self.signal_dim:
            if len(signal) > self.signal_dim:
                signal = signal[:self.signal_dim]
            else:
                signal = np.pad(signal, (0, self.signal_dim - len(signal)),
                                mode='edge')

        return signal.copy()

    def get_batch(self, n_signals: int,
                  node_ids: list = None) -> np.ndarray:
        """
        Get a batch of real signals.

        Parameters
        ----------
        n_signals : int
            Number of signals to return.
        node_ids : list, optional
            Specific simulation node IDs.

        Returns
        -------
        np.ndarray
            Shape (n_signals, signal_dim).
        """
        if node_ids is None:
            node_ids = range(n_signals)

        signals = np.empty((n_signals, self.signal_dim))
        for i, nid in enumerate(node_ids):
            signals[i] = self.get_signal(nid)
        return signals

    def statistics(self) -> dict:
        """Return summary statistics of the real data."""
        self._load()
        all_data = []
        for nid in self._node_ids:
            all_data.append(self._data[nid].ravel())
        all_data = np.concatenate(all_data)
        return {
            'source': 'Intel Berkeley Lab (Madden, 2004)',
            'url': 'http://db.csail.mit.edu/labdata/labdata.html',
            'num_nodes': len(self._node_ids),
            'total_windows': sum(len(self._data[n]) for n in self._node_ids),
            'signal_dim': self.signal_dim,
            'mean': float(np.mean(all_data)),
            'std': float(np.std(all_data)),
            'min': float(np.min(all_data)),
            'max': float(np.max(all_data)),
        }


# Module-level singleton for convenience
_loader = None

def get_real_signal(sim_node_id: int = None,
                    signal_dim: int = 100) -> np.ndarray:
    """Get a single real Intel Lab temperature signal (convenience function)."""
    global _loader
    if _loader is None:
        _loader = RealIntelLabLoader(signal_dim=signal_dim)
    return _loader.get_signal(sim_node_id)


def is_real_data_available() -> bool:
    """Check if parsed Intel Lab data exists."""
    return os.path.exists(_PARSED_FILE)
