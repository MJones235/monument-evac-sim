#!/usr/bin/env python3
"""
Monument Station arrival logger (v3 - popapp departures API).

Polls the popapp.co.uk per-station departures API for both Monument
station codes and logs each train's ARRIVED event at Monument.

    MTS = Monument N-S (platforms 1, 2)
    MTW = Monument W-E (platforms 3, 4)

Feed: https://www.popapp.co.uk/api/stations/<code>/departures
Each entry carries the train's most recent event, e.g.
    "last_event": "ARRIVED",
    "last_event_location": "Monument Platform 2",
    "last_event_time": "2026-10-05T05:55:58.000Z"

Caveats:
    - ARRIVED times are whole-second resolution (UTC in the feed,
      converted to Europe/London in the output).
    - The server refreshes roughly every 30s ("polled_at"). A train whose
      dwell is shorter than that can go straight from APPROACHING to
      DEPARTED between snapshots, so its arrival is never seen. These
      misses are reported on stderr and counted at the end, not written
      to the CSV.
    - This is an unofficial, undocumented API. It may change shape or
      disappear without notice - re-test before relying on it.

Usage:
    python monument-arrivals-logger.py --duration-minutes 30
    python monument-arrivals-logger.py --start "2026-09-24 07:00:00" --duration-minutes 30
"""

import argparse
import csv
import datetime as dt
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

API_URL = "https://www.popapp.co.uk/api/stations/{code}/departures"
STATION_CODES = ("MTS", "MTW")
STATION_NAME = "Monument"
LOCAL_TZ = ZoneInfo("Europe/London")


def parse_args():
    p = argparse.ArgumentParser(
        description="Log Monument station arrivals via the popapp departures API."
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
        default=10.0,
        help="Poll interval in seconds (default: 10; the server itself refreshes ~every 30s).",
    )
    p.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output CSV path (default: monument_arrivals_<timestamp>.csv in the current directory).",
    )
    return p.parse_args()


def parse_utc(s):
    """Parse an ISO-8601 'Z' timestamp from the API into a local-time datetime."""
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(LOCAL_TZ)


def fetch_trains(code):
    """GET the departures list for one station code."""
    resp = requests.get(API_URL.format(code=code), timeout=10)
    resp.raise_for_status()
    return resp.json().get("departures", [])


def main():
    args = parse_args()

    if args.start:
        start_time = dt.datetime.strptime(args.start, "%Y-%m-%d %H:%M:%S")
    else:
        start_time = dt.datetime.now()

    end_time = start_time + dt.timedelta(minutes=args.duration_minutes)

    out_path = Path(args.output or f"monument_arrivals_{start_time.strftime('%Y%m%d_%H%M%S')}.csv")

    # (train_id, platform, event_time) keys, so each event is handled once.
    arrivals = set()
    departures = set()
    missed = 0

    print(f"Station codes: {', '.join(STATION_CODES)}")
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
            [
                "arrival_time",
                "train_id",
                "station_code",
                "platform",
                "destination",
                "scheduled_time",
                "poll_time",
            ]
        )
        f.flush()

        while dt.datetime.now() < end_time:
            poll_time = dt.datetime.now().isoformat(timespec="seconds")

            for code in STATION_CODES:
                try:
                    trains = fetch_trains(code)
                except (requests.RequestException, ValueError) as e:
                    print(f"  [{poll_time}] {code} request failed ({e})", file=sys.stderr)
                    continue

                for t in trains:
                    location = t.get("last_event_location", "")
                    if not location.startswith(f"{STATION_NAME} Platform"):
                        continue

                    platform = location.rsplit(" ", 1)[-1]
                    event_time = parse_utc(t["last_event_time"])
                    key = (t["train_id"], platform, event_time)

                    if t["last_event"] == "ARRIVED":
                        if key in arrivals:
                            continue
                        arrivals.add(key)
                        scheduled = t.get("actual_scheduled_time")
                        writer.writerow(
                            [
                                event_time.isoformat(timespec="seconds"),
                                t["train_id"],
                                code,
                                platform,
                                t.get("destination", ""),
                                parse_utc(scheduled).isoformat(timespec="seconds")
                                if scheduled
                                else "",
                                poll_time,
                            ]
                        )
                        f.flush()
                        print(
                            f"  [{poll_time}] train={t['train_id']} arrived platform {platform} "
                            f"at {event_time:%H:%M:%S} -> {t.get('destination', '')}"
                        )

                    elif t["last_event"] == "DEPARTED":
                        if key in departures:
                            continue
                        departures.add(key)
                        # An arrival for this stop must precede the departure.
                        if not any(
                            a[0] == t["train_id"]
                            and a[1] == platform
                            and a[2] <= event_time
                            and event_time - a[2] < dt.timedelta(minutes=10)
                            for a in arrivals
                        ):
                            missed += 1
                            print(
                                f"  [{poll_time}] MISSED arrival: train={t['train_id']} platform {platform} "
                                f"departed {event_time:%H:%M:%S} with no ARRIVED seen",
                                file=sys.stderr,
                            )

            time.sleep(args.interval)

    print(f"Done. Logged {len(arrivals)} arrivals to {out_path} ({missed} missed).")


if __name__ == "__main__":
    main()
