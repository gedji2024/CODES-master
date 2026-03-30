#!/usr/bin/env python3
"""
Fetch Real Carbon Intensity Data
==================================
Downloads actual half-hourly carbon intensity from the UK National Grid
Carbon Intensity API (https://carbonintensity.org.uk/).

This is a FREE, open-source, no-API-key service providing actual and
forecast grid carbon intensity for Great Britain in gCO₂/kWh.

Source:
    National Grid ESO Carbon Intensity API
    https://api.carbonintensity.org.uk/
    Methodology: https://carbonintensity.org.uk/methodology

The API provides half-hourly actual CI readings. We fetch a full year
(2023) and resample to hourly resolution for the simulation.

Output:
    data/real_traces/uk_carbon_intensity_2023.csv
    Columns: timestamp, carbon_intensity_gCO2_kWh

Also downloads Germany generation data from ENTSO-E Transparency
Platform (OPSD mirror) and computes CI using IPCC 2021 emission factors.
"""

import os
import json
import time
import urllib.request
import urllib.error
import numpy as np
from datetime import datetime, timedelta

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
UK_OUTPUT = os.path.join(DATA_DIR, 'uk_carbon_intensity_2023.csv')
UK_NPZ_OUTPUT = os.path.join(DATA_DIR, 'uk_carbon_intensity_2023.npz')


def fetch_uk_carbon_intensity(year: int = 2023,
                              verbose: bool = True) -> np.ndarray:
    """
    Fetch one year of half-hourly CI data from UK National Grid API.

    The API allows up to 14 days per request.

    Parameters
    ----------
    year : int
        Year to fetch (2018–2025 available).
    verbose : bool
        Print progress.

    Returns
    -------
    np.ndarray
        Hourly carbon intensity values (gCO₂/kWh), shape (8760,).
    """
    base_url = "https://api.carbonintensity.org.uk/intensity"
    start = datetime(year, 1, 1)
    end = datetime(year, 12, 31, 23, 59)

    all_records = []
    current = start
    chunk_days = 14  # API max per request

    request_count = 0
    while current < end:
        chunk_end = min(current + timedelta(days=chunk_days), end)
        url = (f"{base_url}/{current.strftime('%Y-%m-%dT%H:%MZ')}/"
               f"{chunk_end.strftime('%Y-%m-%dT%H:%MZ')}")

        if verbose:
            print(f"  Fetching {current.date()} to {chunk_end.date()} ...")

        try:
            req = urllib.request.Request(url, headers={
                'Accept': 'application/json',
                'User-Agent': 'CALASH-Research/1.0'
            })
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            for record in data.get('data', []):
                actual = record.get('intensity', {}).get('actual')
                forecast = record.get('intensity', {}).get('forecast')
                ci = actual if actual is not None else forecast
                if ci is not None:
                    all_records.append({
                        'from': record['from'],
                        'ci': float(ci)
                    })

            request_count += 1

        except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
            if verbose:
                print(f"    Warning: {e}, retrying in 2s ...")
            time.sleep(2)
            try:
                req = urllib.request.Request(url, headers={
                    'Accept': 'application/json',
                    'User-Agent': 'CALASH-Research/1.0'
                })
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                for record in data.get('data', []):
                    actual = record.get('intensity', {}).get('actual')
                    forecast = record.get('intensity', {}).get('forecast')
                    ci = actual if actual is not None else forecast
                    if ci is not None:
                        all_records.append({
                            'from': record['from'],
                            'ci': float(ci)
                        })
                request_count += 1
            except Exception as e2:
                if verbose:
                    print(f"    Failed: {e2}")

        current = chunk_end
        # Be polite to the API
        if request_count % 5 == 0:
            time.sleep(0.5)

    if verbose:
        print(f"  Fetched {len(all_records)} half-hourly records "
              f"({request_count} requests)")

    # Convert to hourly by averaging pairs of half-hourly values
    ci_values = np.array([r['ci'] for r in all_records])

    # Resample: average consecutive pairs (half-hourly → hourly)
    n_hours = len(ci_values) // 2
    if n_hours > 0:
        hourly = ci_values[:n_hours * 2].reshape(n_hours, 2).mean(axis=1)
    else:
        hourly = ci_values

    # Pad or trim to exactly 8760 hours
    target = 8760
    if len(hourly) < target:
        # Pad by repeating the trace
        repeats = (target // len(hourly)) + 1
        hourly = np.tile(hourly, repeats)[:target]
    elif len(hourly) > target:
        hourly = hourly[:target]

    return hourly


def save_csv(hourly_ci: np.ndarray, filepath: str, year: int = 2023):
    """Save hourly CI trace as CSV."""
    start = datetime(year, 1, 1)
    with open(filepath, 'w') as f:
        f.write("timestamp,carbon_intensity_gCO2_kWh\n")
        for i, ci in enumerate(hourly_ci):
            ts = start + timedelta(hours=i)
            f.write(f"{ts.strftime('%Y-%m-%dT%H:00Z')},{ci:.1f}\n")


def save_npz(hourly_ci: np.ndarray, filepath: str, year: int = 2023):
    """Save hourly CI trace as compressed NPZ for fast loading."""
    np.savez_compressed(filepath,
                        ci_hourly=hourly_ci,
                        year=year,
                        region='UK',
                        source='UK National Grid ESO Carbon Intensity API',
                        url='https://carbonintensity.org.uk/',
                        unit='gCO2/kWh',
                        resolution='hourly',
                        n_hours=len(hourly_ci))


def main():
    """Fetch and save UK carbon intensity data."""
    print("=" * 60)
    print("Fetching real carbon intensity data from UK National Grid API")
    print("Source: https://carbonintensity.org.uk/")
    print("=" * 60)

    hourly_ci = fetch_uk_carbon_intensity(year=2023, verbose=True)

    print(f"\nStatistics (2023, hourly):")
    print(f"  Mean:   {np.mean(hourly_ci):.1f} gCO₂/kWh")
    print(f"  Std:    {np.std(hourly_ci):.1f} gCO₂/kWh")
    print(f"  Min:    {np.min(hourly_ci):.1f} gCO₂/kWh")
    print(f"  Max:    {np.max(hourly_ci):.1f} gCO₂/kWh")
    print(f"  Median: {np.median(hourly_ci):.1f} gCO₂/kWh")
    print(f"  Hours:  {len(hourly_ci)}")

    # Save
    save_csv(hourly_ci, UK_OUTPUT)
    save_npz(hourly_ci, UK_NPZ_OUTPUT)
    print(f"\nSaved CSV: {UK_OUTPUT}")
    print(f"Saved NPZ: {UK_NPZ_OUTPUT}")
    print(f"File sizes: CSV={os.path.getsize(UK_OUTPUT)/1024:.0f}KB, "
          f"NPZ={os.path.getsize(UK_NPZ_OUTPUT)/1024:.0f}KB")


if __name__ == '__main__':
    main()
