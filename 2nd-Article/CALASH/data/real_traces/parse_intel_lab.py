#!/usr/bin/env python3
"""
Parse Raw Intel Berkeley Lab Sensor Data
==========================================
Downloads and processes the real Intel Lab dataset (Madden, 2004).

Raw data format (space-separated):
    date time epoch moteid temperature humidity light voltage

Source:
    http://db.csail.mit.edu/labdata/labdata.html
    Madden, S. (2004). "Intel Lab Data." MIT CSAIL.
    Deshpande, A. et al. (2004). "Model-Driven Data Acquisition in
    Sensor Networks." VLDB.

This script:
    1. Reads the raw data.txt (2.3M readings)
    2. Filters valid temperature readings (10–50°C)
    3. Extracts per-node temperature time series for 54 sensor nodes
    4. Saves as compressed NPZ for fast loading in simulations
"""

import os
import numpy as np
from collections import defaultdict

# Path to the raw data file
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_FILE = os.path.join(DATA_DIR, 'intel_lab_data.txt')
OUTPUT_FILE = os.path.join(DATA_DIR, 'intel_lab_parsed.npz')


def parse_intel_lab_raw(filepath: str, verbose: bool = True):
    """
    Parse the raw Intel Lab data.txt file.

    Parameters
    ----------
    filepath : str
        Path to the decompressed data.txt file.
    verbose : bool
        Print progress.

    Returns
    -------
    dict
        {node_id: np.ndarray of temperature readings}
    """
    node_temps = defaultdict(list)
    node_humidity = defaultdict(list)
    node_light = defaultdict(list)
    node_voltage = defaultdict(list)
    node_epochs = defaultdict(list)

    valid_count = 0
    skip_count = 0

    if verbose:
        print(f"Parsing {filepath} ...")

    with open(filepath, 'r') as f:
        for line_num, line in enumerate(f, 1):
            parts = line.strip().split()
            if len(parts) < 8:
                skip_count += 1
                continue

            try:
                # date time epoch moteid temperature humidity light voltage
                epoch = int(parts[2])
                mote_id = int(parts[3])
                temp = float(parts[4])
                humidity = float(parts[5])
                light = float(parts[6])
                voltage = float(parts[7])

                # Filter physically valid readings
                if not (5.0 <= temp <= 50.0):
                    skip_count += 1
                    continue
                if not (0.0 <= humidity <= 100.0):
                    humidity = np.nan
                if light < 0:
                    light = np.nan
                if not (1.5 <= voltage <= 3.5):
                    voltage = np.nan

                node_temps[mote_id].append(temp)
                node_humidity[mote_id].append(humidity)
                node_light[mote_id].append(light)
                node_voltage[mote_id].append(voltage)
                node_epochs[mote_id].append(epoch)
                valid_count += 1

            except (ValueError, IndexError):
                skip_count += 1
                continue

            if verbose and line_num % 500000 == 0:
                print(f"  Processed {line_num:,} lines, {valid_count:,} valid ...")

    if verbose:
        print(f"  Done: {valid_count:,} valid readings, "
              f"{skip_count:,} skipped, {len(node_temps)} unique nodes")

    return node_temps, node_humidity, node_light, node_voltage, node_epochs


def build_per_node_traces(node_temps: dict, node_epochs: dict,
                          signal_dim: int = 100,
                          min_readings: int = 500) -> dict:
    """
    Build fixed-length signal vectors from per-node temperature readings.

    For each node with enough readings, we:
    1. Sort by epoch (time)
    2. Extract consecutive windows of `signal_dim` readings
    3. Store multiple windows per node for reuse across simulation rounds

    Parameters
    ----------
    node_temps : dict
        {node_id: [temp_readings]}
    node_epochs : dict
        {node_id: [epochs]}
    signal_dim : int
        Length of each signal vector (must match config.signal_dim).
    min_readings : int
        Minimum readings required to include a node.

    Returns
    -------
    dict
        {node_id: np.ndarray of shape (n_windows, signal_dim)}
    """
    traces = {}
    for node_id in sorted(node_temps.keys()):
        temps = np.array(node_temps[node_id])
        epochs = np.array(node_epochs[node_id])

        if len(temps) < min_readings:
            continue

        # Sort by epoch
        order = np.argsort(epochs)
        temps = temps[order]

        # Extract non-overlapping windows
        n_windows = len(temps) // signal_dim
        if n_windows == 0:
            continue

        windows = temps[:n_windows * signal_dim].reshape(n_windows, signal_dim)
        traces[node_id] = windows

    return traces


def compute_statistics(node_temps: dict) -> dict:
    """Compute per-node and global statistics."""
    all_temps = []
    node_stats = {}

    for node_id in sorted(node_temps.keys()):
        temps = np.array(node_temps[node_id])
        if len(temps) < 100:
            continue
        all_temps.extend(temps.tolist())
        node_stats[node_id] = {
            'mean': float(np.mean(temps)),
            'std': float(np.std(temps)),
            'min': float(np.min(temps)),
            'max': float(np.max(temps)),
            'count': len(temps),
        }

    all_temps = np.array(all_temps)
    global_stats = {
        'mean': float(np.mean(all_temps)),
        'std': float(np.std(all_temps)),
        'min': float(np.min(all_temps)),
        'max': float(np.max(all_temps)),
        'total_readings': len(all_temps),
        'num_nodes': len(node_stats),
    }

    return global_stats, node_stats


def main():
    """Parse Intel Lab data and save as compressed NPZ."""
    if not os.path.exists(RAW_FILE):
        print(f"ERROR: Raw data file not found at {RAW_FILE}")
        print("Download it from: http://db.csail.mit.edu/labdata/labdata.html")
        print("  curl -o data/real_traces/intel_lab_data.txt.gz "
              "http://db.csail.mit.edu/labdata/data.txt.gz")
        print("  gunzip data/real_traces/intel_lab_data.txt.gz")
        return

    # Parse raw data
    node_temps, node_humidity, node_light, node_voltage, node_epochs = \
        parse_intel_lab_raw(RAW_FILE)

    # Compute statistics
    global_stats, node_stats = compute_statistics(node_temps)
    print(f"\nGlobal statistics:")
    print(f"  Temperature: {global_stats['mean']:.2f} ± {global_stats['std']:.2f} °C")
    print(f"  Range: [{global_stats['min']:.1f}, {global_stats['max']:.1f}] °C")
    print(f"  Total readings: {global_stats['total_readings']:,}")
    print(f"  Nodes with >100 readings: {global_stats['num_nodes']}")

    # Build fixed-length traces
    traces = build_per_node_traces(node_temps, node_epochs,
                                   signal_dim=100, min_readings=500)

    print(f"\nBuilt signal traces for {len(traces)} nodes:")
    total_windows = 0
    for nid, arr in sorted(traces.items()):
        print(f"  Node {nid:3d}: {arr.shape[0]:4d} windows of length {arr.shape[1]}")
        total_windows += arr.shape[0]
    print(f"  Total windows: {total_windows:,}")

    # Save as NPZ
    save_dict = {}
    node_ids = sorted(traces.keys())
    save_dict['node_ids'] = np.array(node_ids)
    save_dict['global_mean'] = np.float64(global_stats['mean'])
    save_dict['global_std'] = np.float64(global_stats['std'])

    for nid in node_ids:
        save_dict[f'node_{nid}'] = traces[nid]

    np.savez_compressed(OUTPUT_FILE, **save_dict)
    file_size = os.path.getsize(OUTPUT_FILE) / 1024 / 1024
    print(f"\nSaved to {OUTPUT_FILE} ({file_size:.1f} MB)")


if __name__ == '__main__':
    main()
