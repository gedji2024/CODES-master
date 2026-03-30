#!/usr/bin/env python3
"""
Standalone ShakeMap Download Script
====================================
Downloads USGS ShakeMap grid.xml data for one or more earthquake events
and saves them as compressed .npz files for fast offline loading.

Usage
-----
    # Download Turkey-Syria 2023 event
    python fetch_shakemap.py turkey_syria_2023

    # Download all pre-cataloged events
    python fetch_shakemap.py --all

    # Download by raw USGS event ID
    python fetch_shakemap.py --event-id us6000jllz

    # List available pre-cataloged events
    python fetch_shakemap.py --list

Data Provenance
---------------
    Source:  USGS Earthquake Hazards Program — ShakeMap
    URL:     https://earthquake.usgs.gov/data/shakemap/
    Licence: Public domain (U.S. Government work, 17 U.S.C. §105)
"""

import sys
import os
import argparse
import logging

# Add parent directories to path so imports work when run standalone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.shakemap_loader import (
    ShakeMapLoader, SHAKEMAP_EVENTS, _CACHE_DIR
)


def main():
    parser = argparse.ArgumentParser(
        description='Download USGS ShakeMap grid.xml data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)

    parser.add_argument(
        'events', nargs='*',
        help='Pre-cataloged event key(s) to download')
    parser.add_argument(
        '--all', action='store_true',
        help='Download all pre-cataloged events')
    parser.add_argument(
        '--event-id', type=str, default=None,
        help='Raw USGS event ID (e.g. us6000jllz)')
    parser.add_argument(
        '--list', action='store_true',
        help='List all pre-cataloged events and exit')
    parser.add_argument(
        '--save-npz', action='store_true', default=True,
        help='Save parsed data as .npz (default: True)')
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help='Enable verbose logging')

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
        datefmt='%H:%M:%S')

    if args.list:
        print("\n╔══════════════════════════════════════════════════════╗")
        print("║         Pre-cataloged USGS ShakeMap Events          ║")
        print("╠══════════════════════════════════════════════════════╣")
        for key, info in SHAKEMAP_EVENTS.items():
            print(f"║ {key:<24s} │ {info['event_id']:<14s} │ "
                  f"Mw {info['magnitude']:.1f} ║")
        print("╚══════════════════════════════════════════════════════╝")
        print(f"\nCache dir: {_CACHE_DIR}")
        return

    # Determine events to download
    events_to_download = []

    if args.all:
        events_to_download = list(SHAKEMAP_EVENTS.keys())
    elif args.event_id:
        events_to_download = [args.event_id]
    elif args.events:
        events_to_download = args.events
    else:
        parser.print_help()
        print("\nError: specify event key(s), --all, or --event-id")
        sys.exit(1)

    # Download each event
    success = 0
    failed = []

    for event in events_to_download:
        print(f"\n{'='*60}")
        print(f"Downloading: {event}")
        print(f"{'='*60}")

        try:
            if event in SHAKEMAP_EVENTS:
                loader = ShakeMapLoader(event_key=event)
            else:
                loader = ShakeMapLoader(event_id=event)

            loader.download_and_parse()

            # Print summary
            summary = loader.grid.summary()
            print(f"  Event ID:    {summary['event_id']}")
            print(f"  Magnitude:   Mw {summary['magnitude']:.1f}")
            print(f"  Epicenter:   {summary['epicenter']}")
            print(f"  Depth:       {summary['depth_km']:.1f} km")
            print(f"  Grid shape:  {summary['grid_shape']}")
            print(f"  Grid points: {summary['grid_points']:,}")
            print(f"  Fields:      {', '.join(summary['fields'])}")
            for f in summary['fields']:
                key = f'{f}_range'
                if key in summary:
                    lo, hi = summary[key]
                    print(f"    {f:>8s}:  [{lo:.4f}, {hi:.4f}]")

            # Save as .npz for fast future loading
            if args.save_npz:
                loader.save_parsed()
                print(f"  Saved parsed .npz ✓")

            # Print disaster params
            params = loader.to_disaster_params()
            print(f"\n  CALASH disaster parameters:")
            print(f"    damage_radius:  {params['damage_radius']:.1f} m")
            print(f"    max_mmi:        {params['max_mmi']:.1f}")
            print(f"    max_pga:        {params['max_pga_g']:.3f} g")
            print(f"    max_pgv:        {params['max_pgv_cms']:.1f} cm/s")
            print(f"    frac(MMI≥6):    {params['frac_mmi_ge_6']:.1%}")
            print(f"    frac(MMI≥8):    {params['frac_mmi_ge_8']:.1%}")

            success += 1

        except Exception as e:
            print(f"  FAILED: {e}")
            failed.append((event, str(e)))

    # Summary
    print(f"\n{'='*60}")
    print(f"Done. {success}/{len(events_to_download)} events downloaded.")
    if failed:
        print("Failed events:")
        for ev, err in failed:
            print(f"  {ev}: {err}")
    print(f"Cache: {_CACHE_DIR}")


if __name__ == '__main__':
    main()
