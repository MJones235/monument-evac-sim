#!/usr/bin/env python3
"""
Monument Station arrival/departure logger (v2 - KML feed).

The original per-platform /api/times endpoint now requires authorisation
(401 as of Sept 2026). This version instead polls the network-wide
trainstatuses.kml feed, which as of Sept 2026 is unauthenticated, and
filters for Monument.

Feed: https://metro-rti.nexus.org.uk/api/geo/trainstatuses.kml?d=<cachebuster>
Each Placemark's "details" CDATA table contains a "Last seen" cell like:
    "Arrived Monument platform 4 at 16:21"
    "Departed Monument platform 1 at 16:22"
    "Approaching Monument platform 2 at 16:23"

Caveats:
    - Timestamps are minute-resolution only (no seconds) - this is a
      property of the source feed, not the polling.
    - This is an unofficial, undocumented feed. It may be relocked or
      change shape without notice - re-test before relying on it.
    - No documented refresh cadence; a 15-20s poll interval is used by
      default to catch state transitions (Approaching -> Arrived ->
      Departed) reliably without hammering the endpoint.

Usage:
    python monument_arrivals_logger.py --duration-minutes 30
    python monument_arrivals_logger.py --start "2026-09-24 07:00:00" --duration-minutes 30
"""

import argparse
import csv
import datetime as dt
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

KML_URL = "https://metro-rti.nexus.org.uk/api/geo/trainstatuses.kml"
KML_NS = "{http://www.opengis.net/kml/2.2}"

STATUS_RE = re.compile(
    r"(Approaching|Arrived|Departed|Ready to start)\s+(.+?)\s+platform\s+(\d+)\s+at\s+(\d{2}:\d{2})"
)
CELL_RE = re.compile(r'<td data-title="([^"]*)">([^<]*)</td>')


def parse_args():
    p = argparse.ArgumentParser(description="Log Monument station arrivals/departures via trainstatuses.kml.")
    p.add_argument(
        "--station",
        type=str,
        default="Monument",
        help='Station name to filter for, as it appears in the feed (default: "Monument").',
    )
    p.add_argument(
        "--start",
        type=str,
        default=None,
        help='Start time as "YYYY-MM-DD HH:MM:SS" (default: now). Script waits until this time.',
    )
    p.add_argument(
        "--duration-minutes",
        type=float,
        default=30.0,
        help="How long to log for, in minutes (default: 30).",
    )
    p.add_argument(
        "--interval",
        type=float,
        default=15.0,
        help="Poll interval in seconds (default: 15).",
    )
    p.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output CSV path (default: monument_arrivals_<timestamp>.csv in the current directory).",
    )
    return p.parse_args()


def fetch_trains():
    """GET the network-wide trainstatuses.kml feed and return a list of train dicts."""
    cachebuster = dt.datetime.now().strftime("%Y%m%d%H%M")
    resp = requests.get(KML_URL, params={"d": cachebuster}, timeout=10)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    trains = []
    for pm in root.iter(f"{KML_NS}Placemark"):
        train_id = pm.get("id")
        value_el = pm.find(f".//{KML_NS}Data[@name='details']/{KML_NS}value")
        if value_el is None or not value_el.text:
            continue
        cells = dict(CELL_RE.findall(value_el.text))
        last_seen = cells.get("Last seen", "")
        trains.append({
            "id": train_id,
            "train_running_number": cells.get("Train running number", train_id),
            "last_seen": last_seen,
            "destination": cells.get("Destination", ""),
        })
    return trains


def main():
    args = parse_args()

    if args.start:
        start_time = dt.datetime.strptime(args.start, "%Y-%m-%d %H:%M:%S")
    else:
        start_time = dt.datetime.now()

    end_time = start_time + dt.timedelta(minutes=args.duration_minutes)

    out_path = Path(
        args.output
        or f"monument_arrivals_{start_time.strftime('%Y%m%d_%H%M%S')}.csv"
    )

    seen = set()  # dedupe key: (train_id, last_seen_text)

    print(f"Filtering for station: {args.station}")
    print(f"Window: {start_time} -> {end_time} (poll every {args.interval}s)")
    print(f"Output: {out_path}")

    now = dt.datetime.now()
    if start_time > now:
        wait_s = (start_time - now).total_seconds()
        print(f"Waiting {wait_s:.0f}s until start time...")
        time.sleep(wait_s)

    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["poll_time", "train_id", "event_type", "station", "platform",
             "event_time", "destination", "raw_last_seen"]
        )
        f.flush()

        while dt.datetime.now() < end_time:
            poll_time = dt.datetime.now().isoformat(timespec="seconds")

            try:
                trains = fetch_trains()
            except requests.RequestException as e:
                print(f"  [{poll_time}] request failed ({e})", file=sys.stderr)
                time.sleep(args.interval)
                continue
            except ET.ParseError as e:
                print(f"  [{poll_time}] KML parse failed ({e})", file=sys.stderr)
                time.sleep(args.interval)
                continue

            for t in trains:
                if args.station not in t["last_seen"]:
                    continue

                key = (t["id"], t["last_seen"])
                if key in seen:
                    continue
                seen.add(key)

                m = STATUS_RE.match(t["last_seen"])
                if m:
                    event_type, station, platform, event_time = m.groups()
                else:
                    event_type, station, platform, event_time = "UNKNOWN", args.station, "", ""

                writer.writerow([
                    poll_time, t["id"], event_type, station, platform,
                    event_time, t["destination"], t["last_seen"],
                ])
                f.flush()

                print(f"  [{poll_time}] train={t['id']} {event_type} "
                      f"platform {platform} at {event_time} -> {t['destination']}")

            time.sleep(args.interval)

    print(f"Done. Logged to {out_path}")


if __name__ == "__main__":
    main()