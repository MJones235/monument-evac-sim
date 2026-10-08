#!/usr/bin/env python3
"""
Build calibration inputs that replay a real, observed time window.

Takes a hand-collected exit count (virtual volunteer counter CSV) and the real
train arrivals logged by ``scripts/monument-arrivals-logger.py`` over the same
period, and writes the two CSVs a Calibration-style run consumes:

  * ``timetable.csv``       — the *real* train arrivals, each alighting a
                              number of passengers sized from the exit count.
  * ``entrance_usage.csv``  — street arrivals (boarders) matching the exits:
                              each entrance receives as many people as leave
                              through it (counted, or assumed via the share).

Sizing the alighting volume
---------------------------
Only one exit was counted. With each other street exit assumed to see
``--other-exit-share`` of the counted exit's footfall, the total leaving is::

    total = counted x (1 + n_other x share)       e.g. 354 x 1.70 = 602

That total is spread over the trains whose passengers would leave *during* the
counting window — those arriving in ``[start - lag, end - lag]``, where ``lag``
is the platform-to-street walk (~2 min, measured from the counter data). Within
that set, trains are weighted by platform using the per-train alighting of the
existing all-day ``timetable.csv`` over the same hours (which carries the
Monument Lower vs Upper split, platforms 1-2 vs 3-4). Trains in the warm-up
before the window, and between ``end - lag`` and ``end``, alight at the same
per-train rate so the station is in steady state at both edges, but they are
not counted towards the total.

Entrances use the same per-exit volumes in reverse — boarding/alighting
symmetry, as in ``build_calibration_data.py``: the counted exit receives
``counted`` arrivals over the window and each other exit ``counted x share``,
as a Poisson process at that rate. The warm-up gets the same rate, so the
concourse already carries counter-flow when counting starts.

Note the simulation chooses exits itself, so this fixes the *total* and the
counted exit's share is a model output to compare against the observation.

Usage:
    python data/calibration/build_window_timetable.py \\
        --counts data/calibration/collected/blackett-st-2026-05-10_10-03-31.csv \\
        --arrivals monument_arrivals_20261005_071548.csv \\
        --out-dir data/calibration/blackett_20261005
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from analysis.real_exit_usage_plots import (  # noqa: E402
    _hhmm,
    exit_from_filename,
    load_arrivals,
    load_counts,
)

STREET_EXITS = ("blackett_street", "grey_street", "eldon_square")
DEFAULT_DWELL_S = 30


def platform_weights(timetable_path: Path, start_s: float, end_s: float) -> dict[str, float]:
    """Mean alighting per train for each platform within [start_s, end_s)."""
    totals: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    with timetable_path.open(newline="") as f:
        for row in csv.DictReader(f):
            if start_s <= float(row["arrival_s"]) < end_s:
                totals[row["platform"]] += int(row["alighting"])
                counts[row["platform"]] += 1
    return {p: totals[p] / counts[p] for p in totals}


def largest_remainder(values: list[float], total: int) -> list[int]:
    """Round `values` to integers that sum exactly to `total`."""
    floors = [math.floor(v) for v in values]
    short = total - sum(floors)
    order = sorted(range(len(values)), key=lambda i: values[i] - floors[i], reverse=True)
    for i in order[:short]:
        floors[i] += 1
    return floors


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--counts", type=Path, required=True, help="Counter CSV for the observed exit"
    )
    parser.add_argument(
        "--arrivals", type=Path, required=True, help="Arrivals CSV from monument-arrivals-logger.py"
    )
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument(
        "--other-exit-share",
        type=float,
        default=0.35,
        help="Each unobserved exit's footfall as a fraction of the observed exit's (default: 0.35)",
    )
    parser.add_argument(
        "--lag-s",
        type=float,
        default=120.0,
        help="Typical train-arrival-to-street time (default: 120)",
    )
    parser.add_argument(
        "--warmup-s",
        type=float,
        default=600.0,
        help="Trains replayed before the window to reach steady state (default: 600)",
    )
    parser.add_argument(
        "--reference-timetable",
        type=Path,
        default=REPO_ROOT / "data/calibration/timetable.csv",
        help="All-day timetable giving the per-platform split",
    )
    args = parser.parse_args()

    observed_exit = exit_from_filename(args.counts)
    day, exit_times, (rec_start, rec_end) = load_counts(args.counts)
    counted = len(exit_times)
    n_other = len(STREET_EXITS) - 1
    total = round(counted * (1 + n_other * args.other_exit_share))

    attr_lo, attr_hi = rec_start - args.lag_s, rec_end - args.lag_s
    replay_lo = attr_lo - args.warmup_s
    trains = [t for t in load_arrivals(args.arrivals, day) if replay_lo <= t["time_s"] <= rec_end]
    if not trains:
        print("No train arrivals overlap the counting window", file=sys.stderr)
        return 1

    weights = platform_weights(
        args.reference_timetable,
        math.floor(rec_start / 3600) * 3600,
        math.ceil(rec_end / 3600) * 3600,
    )
    missing = {t["platform"] for t in trains} - set(weights)
    if missing:
        print(f"No reference alighting for platform(s) {sorted(missing)}", file=sys.stderr)
        return 1

    attributed = [t for t in trains if attr_lo <= t["time_s"] <= attr_hi]
    scale = total / sum(weights[t["platform"]] for t in attributed)
    attributed_ids = {id(t) for t in attributed}
    exact = [weights[t["platform"]] * scale for t in attributed]
    rounded = dict(zip((id(t) for t in attributed), largest_remainder(exact, total), strict=True))
    for t in trains:
        t["alighting"] = (
            rounded[id(t)] if id(t) in attributed_ids else round(weights[t["platform"]] * scale)
        )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    timetable_path = args.out_dir / "timetable.csv"
    with timetable_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["arrival_s", "platform", "alighting", "dwell_s"])
        for t in trains:
            writer.writerow(
                [int(round(t["time_s"])), t["platform"], t["alighting"], DEFAULT_DWELL_S]
            )

    # Arrivals per entrance mirror exits per exit; the warm-up runs at the
    # same rate so the window itself gets exactly the per-exit volume.
    footfall = {
        e: (counted if e == observed_exit else round(counted * args.other_exit_share))
        for e in STREET_EXITS
    }
    warmup_start, window_start = int(replay_lo), int(rec_start)
    usage_path = args.out_dir / "entrance_usage.csv"
    with usage_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["interval_start_s", "interval_end_s", "entrance_id", "arrivals"])
        for entrance in STREET_EXITS:
            rate = footfall[entrance] / (rec_end - rec_start)
            writer.writerow(
                [warmup_start, window_start, entrance, round(rate * (window_start - warmup_start))]
            )
            writer.writerow([window_start, int(rec_end), entrance, footfall[entrance]])

    # --- Summary -----------------------------------------------------------
    print(
        f"Observed: {counted} people via {observed_exit} on {day}, "
        f"{_hhmm(rec_start)}:{int(rec_start) % 60:02d}–"
        f"{_hhmm(rec_end)}:{int(rec_end) % 60:02d}"
    )
    print(
        f"Total alighting to leave in window: {counted} x "
        f"(1 + {n_other} x {args.other_exit_share}) = {total}"
    )
    print(
        "Per-train weights by platform: "
        + ", ".join(f"P{p}={w:.1f}" for p, w in sorted(weights.items()))
    )
    print(
        f"Trains replayed: {len(trains)} ({_hhmm(trains[0]['time_s'])}–"
        f"{_hhmm(trains[-1]['time_s'])}), of which {len(attributed)} arriving "
        f"{_hhmm(attr_lo)}–{_hhmm(attr_hi)} carry the {total}"
    )
    per_platform: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for t in trains:
        per_platform[t["platform"]][0] += 1
        per_platform[t["platform"]][1] += t["alighting"]
    for p, (n, a) in sorted(per_platform.items()):
        print(f"  platform {p}: {n} trains, {a} alighting")
    print(f"  all replayed trains: {sum(t['alighting'] for t in trains)} alighting")
    print(
        "Street arrivals (boarders) in window: "
        + ", ".join(f"{e}={n}" for e, n in footfall.items())
        + f" (total {sum(footfall.values())})"
    )
    print(f"Suggested simulation.start_time_s: {int(replay_lo) // 60 * 60} ({_hhmm(replay_lo)})")
    print(f"Wrote {timetable_path} and {usage_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
