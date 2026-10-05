#!/usr/bin/env python3
"""
Exit usage over time for a Calibration run.

Produces one figure per street exit showing how many people used that exit in
each time bin, split by the platform they originally alighted from, with train
arrivals marked as vertical lines.

Data source, in order of preference:
  1. ``exit_log.csv`` — written directly by the engine (newer runs).
  2. ``agent_decisions_history.jsonl`` — reconstructed post-hoc. Each agent's
     last-seen position gives the exit used and the time, and their first-seen
     position gives the originating platform. This reproduces the engine's own
     exit counts exactly; see the module tests in the plan for validation.

Figures are written to <run_dir>/figures/ by default (override with
--out-dir), so they stay grouped with the run they came from.

Usage:
    python analysis/exit_usage_plots.py
    python analysis/exit_usage_plots.py --run results/Calibration/run_20260916_174007
    python analysis/exit_usage_plots.py --bin-seconds 300 --time-range 07:00-09:30
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Iterator, Optional

# Allow running as either `python analysis/exit_usage_plots.py` or
# `python -m analysis.exit_usage_plots` from the repo root.
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    import matplotlib.transforms as transforms
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from analysis.compare_experiments import find_latest_run
from evacusim.config.config_loader import ConfigLoader

REPO_ROOT = Path(__file__).parent.parent
CALIBRATION_CONFIG = REPO_ROOT / "experiments" / "Calibration" / "config.yaml"

# Matches ExitTracker's own exit_validation_radius — an agent whose last known
# position is further than this from any street exit did not leave by one.
EXIT_MATCH_RADIUS_M = 15.0

# A platform spawn point is a train door; the doors of adjacent platforms are
# >=11 m apart, so a generous radius still attributes unambiguously.
ORIGIN_MATCH_RADIUS_M = 10.0

# Okabe-Ito — chosen over the tab10 set used elsewhere in analysis/ because
# tab10's green/orange pair is indistinguishable under protanopia (dE 0.7).
# This palette passes the categorical checks on all pairs; its worst CVD pair
# sits in the 6-8 band, so platform is also encoded by position: bars always
# stack 1-4 from the bottom, in legend order, separated by white edges.
PLATFORM_COLOURS = {
    "1": "#0072B2",  # blue
    "2": "#D55E00",  # vermillion
    "3": "#009E73",  # green
    "4": "#CC79A7",  # pink
}
TOTAL_COLOUR = "#333333"

EXIT_LABELS = {
    "blackett_street": "Blackett Street",
    "grey_street": "Grey Street",
    "eldon_square": "Eldon Square",
}


# ---------------------------------------------------------------------------
# Geometry from config
# ---------------------------------------------------------------------------

def load_geometry(config_path: Path) -> tuple[dict[str, tuple[float, float]],
                                               dict[str, list[tuple[float, float]]]]:
    """
    Return (street_exits, platform_doors) from the Calibration config.

    street_exits:    exit_id -> (x, y) of the walkable point inside the exit.
    platform_doors:  platform_id -> list of (x, y) train door points.
    """
    config = ConfigLoader.load_config(str(config_path))
    spawn_points = config["calibration"]["spawn_points"]
    street_exit_ids = config["station"]["street_exits"]

    street_exits: dict[str, tuple[float, float]] = {}
    platform_doors: dict[str, list[tuple[float, float]]] = {}

    for name, sp in spawn_points.items():
        xy = sp.get("xy")
        if name in street_exit_ids and xy is not None:
            street_exits[name] = (float(xy[0]), float(xy[1]))
        doors = sp.get("door_points")
        if doors:
            platform_doors[str(name)] = [(float(d[0]), float(d[1])) for d in doors]

    if not street_exits:
        raise ValueError(f"No street exits found in {config_path}")
    return street_exits, platform_doors


def _nearest(point: tuple[float, float],
             candidates: dict[str, list[tuple[float, float]]]) -> tuple[Optional[str], float]:
    """Return (key, distance) of the candidate point nearest to `point`."""
    best_key, best_dist = None, math.inf
    for key, points in candidates.items():
        for px, py in points:
            dist = math.hypot(point[0] - px, point[1] - py)
            if dist < best_dist:
                best_key, best_dist = key, dist
    return best_key, best_dist


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def _iter_frames(history_path: Path) -> Iterator[dict]:
    """Stream frames from a history JSONL. These files reach ~850 MB."""
    with history_path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def extract_from_history(run_dir: Path,
                         street_exits: dict[str, tuple[float, float]],
                         platform_doors: dict[str, list[tuple[float, float]]],
                         trains_only: bool = False,
                         ) -> tuple[list[dict], list[dict]]:
    """
    Reconstruct exit events and train departures from the position history.

    Returns (exit_events, train_events) where an exit event is
    ``{agent_id, exit, exit_time_s, origin, spawn_time_s}`` and a train event is
    ``{time_s, platform, kind}`` with kind in {"arrive", "depart"}.
    """
    history_path = run_dir / "agent_decisions_history.jsonl"
    if not history_path.exists():
        raise FileNotFoundError(f"No position history in {run_dir}")

    first_seen: dict[str, tuple[float, tuple[float, float]]] = {}
    last_seen: dict[str, tuple[float, tuple[float, float]]] = {}
    last_level: dict[str, str] = {}
    train_events: list[dict] = []

    active_trains: set[str] = set()
    final_frame_ids: set[str] = set()
    final_time = 0.0

    for frame in _iter_frames(history_path):
        time_s = float(frame["time"])
        positions = {} if trains_only else (frame.get("positions") or {})

        for agent_id, pos in positions.items():
            point = (float(pos[0]), float(pos[1]))
            if agent_id not in first_seen:
                first_seen[agent_id] = (time_s, point)
            last_seen[agent_id] = (time_s, point)

        if not trains_only:
            for agent_id, level in (frame.get("agent_levels") or {}).items():
                last_level[agent_id] = str(level)

        current_trains = set(frame.get("active_train_exits") or [])
        for exit_name in current_trains - active_trains:
            train_events.append({"time_s": time_s,
                                 "platform": exit_name.rsplit("_", 1)[-1],
                                 "kind": "arrive"})
        for exit_name in active_trains - current_trains:
            train_events.append({"time_s": time_s,
                                 "platform": exit_name.rsplit("_", 1)[-1],
                                 "kind": "depart"})
        active_trains = current_trains

        final_frame_ids = set(positions)
        final_time = time_s

    exit_targets = {name: [xy] for name, xy in street_exits.items()}
    exit_events: list[dict] = []
    skipped_far = 0

    for agent_id, (exit_time, last_point) in last_seen.items():
        # Still inside the station when the run ended.
        if agent_id in final_frame_ids:
            continue
        # Agents who vanish below ground boarded a train; they did not use a
        # street exit. This filter is what makes the street-exit counts exact.
        if last_level.get(agent_id) != "0":
            continue

        exit_name, dist = _nearest(last_point, exit_targets)
        if exit_name is None or dist > EXIT_MATCH_RADIUS_M:
            skipped_far += 1
            continue

        spawn_time, spawn_point = first_seen[agent_id]
        origin, origin_dist = _nearest(spawn_point, platform_doors)
        if origin is None or origin_dist > ORIGIN_MATCH_RADIUS_M:
            origin = "entrance"

        exit_events.append({
            "agent_id": agent_id,
            "exit": exit_name,
            "exit_time_s": exit_time,
            "origin": origin,
            "spawn_time_s": spawn_time,
        })

    if skipped_far:
        print(f"  note: {skipped_far} agent(s) vanished on level 0 but were not "
              f"within {EXIT_MATCH_RADIUS_M:.0f} m of a street exit — excluded",
              file=sys.stderr)

    exit_events.sort(key=lambda e: e["exit_time_s"])
    train_events.sort(key=lambda e: (e["time_s"], e["platform"]))
    arrivals = sum(1 for t in train_events if t["kind"] == "arrive")
    if trains_only:
        print(f"  read {arrivals} train arrivals up to t={final_time:.0f}s")
    else:
        print(f"  reconstructed {len(exit_events)} exit events and {arrivals} "
              f"train arrivals up to t={final_time:.0f}s")
    return exit_events, train_events


def extract_from_exit_log(run_dir: Path) -> list[dict]:
    """Read the engine-written exit_log.csv, keeping only street exits."""
    rows: list[dict] = []
    with (run_dir / "exit_log.csv").open() as f:
        for row in csv.DictReader(f):
            exit_name = row["exit_name"]
            if exit_name.startswith("train_platform_") or exit_name.startswith("escalator_"):
                continue
            location = row.get("spawn_location") or ""
            if location in PLATFORM_COLOURS:
                origin = location
            elif location:
                origin = "entrance"
            else:
                # Pre-placed agents (E1-E5 snapshots) have no spawn record.
                origin = "unknown"
            rows.append({
                "agent_id": row["agent_id"],
                "exit": exit_name,
                "exit_time_s": float(row["time_s"]),
                "origin": origin,
                "spawn_time_s": float(row["spawn_time_s"] or 0.0),
            })
    rows.sort(key=lambda e: e["exit_time_s"])
    return rows


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------

_EXIT_FIELDS = ["agent_id", "exit", "exit_time_s", "origin", "spawn_time_s"]
_TRAIN_FIELDS = ["time_s", "platform", "kind"]


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path, floats: tuple[str, ...]) -> list[dict]:
    with path.open() as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        for key in floats:
            row[key] = float(row[key])
    return rows


def load_run(run_dir: Path, use_cache: bool = True) -> tuple[list[dict], list[dict]]:
    """Return (exit_events, train_events), using or populating the cache."""
    exit_cache = run_dir / "exit_usage.csv"
    train_cache = run_dir / "exit_usage_trains.csv"

    if use_cache and exit_cache.exists() and train_cache.exists():
        print(f"  using cached {exit_cache.name}")
        return (_read_csv(exit_cache, ("exit_time_s", "spawn_time_s")),
                _read_csv(train_cache, ("time_s",)))

    street_exits, platform_doors = load_geometry(CALIBRATION_CONFIG)

    # The engine's own log is authoritative when present, but it carries no
    # train schedule, so departures still come from the position history.
    if (run_dir / "exit_log.csv").exists():
        print("  reading engine-written exit_log.csv")
        exit_events = extract_from_exit_log(run_dir)
        _, train_events = extract_from_history(
            run_dir, street_exits, platform_doors, trains_only=True
        )
    else:
        print("  reconstructing from agent_decisions_history.jsonl (streaming)")
        exit_events, train_events = extract_from_history(
            run_dir, street_exits, platform_doors
        )

    _write_csv(exit_cache, exit_events, _EXIT_FIELDS)
    _write_csv(train_cache, train_events, _TRAIN_FIELDS)
    return exit_events, train_events


# ---------------------------------------------------------------------------
# Binning and plotting
# ---------------------------------------------------------------------------

def _bin_series(events: list[dict], bin_seconds: float,
                t_start: float, t_end: float) -> tuple[list[float], dict[str, list[int]]]:
    """
    Bin exit events into counts per bin, per origin, plus a "total" series.

    Returns (bin_left_edges, {origin: counts}).
    """
    # Snap the grid down to a whole multiple of the bin width so that bin edges
    # land on clock boundaries — otherwise a bin starting at 07:35:32 is
    # labelled "07:35" and bins are not comparable between runs.
    grid_start = math.floor(t_start / bin_seconds) * bin_seconds
    n_bins = max(1, int(math.ceil((t_end - grid_start) / bin_seconds)))
    edges = [grid_start + i * bin_seconds for i in range(n_bins)]

    origins = sorted({e["origin"] for e in events})
    series = {origin: [0] * n_bins for origin in origins}
    series["total"] = [0] * n_bins

    for event in events:
        idx = int((event["exit_time_s"] - grid_start) // bin_seconds)
        if 0 <= idx < n_bins:
            series[event["origin"]][idx] += 1
            series["total"][idx] += 1
    return edges, series


_TICK_STEPS_S = [30, 60, 120, 300, 600, 900, 1800, 3600, 7200, 10800, 21600]


def _tick_step(span_s: float, target_ticks: int = 10) -> int:
    """Pick a whole-clock tick interval giving roughly `target_ticks` ticks."""
    ideal = max(1.0, span_s / target_ticks)
    for step in _TICK_STEPS_S:
        if step >= ideal:
            return step
    return _TICK_STEPS_S[-1]


def _hhmm(seconds: float, _pos=None) -> str:
    """Format seconds-from-midnight as HH:MM (Calibration runs are a real day)."""
    total = int(seconds) % 86400
    return f"{total // 3600:02d}:{(total % 3600) // 60:02d}"


def _bin_label(bin_seconds: float) -> str:
    if bin_seconds == 60:
        return "minute"
    if bin_seconds >= 60:
        return f"{bin_seconds / 60:.0f} min"
    return f"{bin_seconds:.0f} s"


def _origin_label(origin: str) -> str:
    if origin in PLATFORM_COLOURS:
        return f"Platform {origin}"
    if origin == "entrance":
        return "Station entrance"
    return "Origin unknown"


def draw_arrivals(ax, train_events: list[dict], platforms: set[str],
                  x_lo: float, x_hi: float, bin_seconds: float,
                  markers: bool = True) -> list[dict]:
    """
    Draw train arrivals on `platforms` as vertical lines; return those drawn.

    Shared with the real-data plots so observed and simulated figures carry
    identical arrival marks.
    """
    arrivals = [t for t in train_events
                if t["kind"] == "arrive"
                and t["platform"] in platforms
                and x_lo <= t["time_s"] <= x_hi]
    # "Dense" is about visual crowding, not a raw count: arrivals packed
    # closer together than a bin width would overlap into a solid wall at
    # full strength, so fall back to a soft rug instead of individual lines.
    span = x_hi - x_lo
    avg_spacing = span / len(arrivals) if arrivals else span
    dense = avg_spacing < bin_seconds
    # y in axes-fraction, x in data coords, so the marker sits at the top
    # of the plot regardless of the y-scale (set later, from the peak).
    top_transform = transforms.blended_transform_factory(ax.transData, ax.transAxes)
    for train in arrivals:
        colour = PLATFORM_COLOURS.get(train["platform"], TOTAL_COLOUR)
        if dense:
            ax.axvline(train["time_s"], color=colour, linewidth=1.0,
                       alpha=0.22, zorder=1.5)
        else:
            ax.axvline(train["time_s"], color=colour, linestyle="--",
                       linewidth=1.5, alpha=0.8, zorder=4)
            if markers:
                ax.plot(train["time_s"], 1.0, marker="v", color=colour,
                        markersize=8, markeredgecolor="white", markeredgewidth=0.8,
                        transform=top_transform, clip_on=False, zorder=6)
    return arrivals


def draw_histogram(ax, edges: list[float], series: dict[str, list[int]],
                   bin_seconds: float, stack_origins: bool = True,
                   total_label: str = "Total") -> None:
    """
    Draw binned counts as a histogram: bars stacked by origin, outlined by a
    step line for the total. With `stack_origins` off (or no per-origin data,
    as with real counts) the total is drawn as a filled step histogram alone.

    The total outline is styled identically in both modes, so a simulated and
    an observed figure read the same way.
    """
    total = series["total"]
    x_hi = edges[-1] + bin_seconds
    origins = [o for o in sorted(series) if o != "total" and any(series[o])]

    if stack_origins and origins:
        bottom = [0] * len(edges)
        for origin in origins:
            counts = series[origin]
            ax.bar(edges, counts, width=bin_seconds, bottom=bottom, align="edge",
                   color=PLATFORM_COLOURS.get(origin, "#888888"),
                   edgecolor="white", linewidth=0.5, zorder=2,
                   label=f"{_origin_label(origin)}  (n={sum(counts)})")
            bottom = [b + c for b, c in zip(bottom, counts)]
    else:
        ax.fill_between(edges + [x_hi], total + [total[-1]], step="post",
                        color=TOTAL_COLOUR, alpha=0.12, zorder=2)

    ax.step(edges + [x_hi], total + [total[-1]], where="post", color=TOTAL_COLOUR,
            linewidth=1.6, label=f"{total_label}  (n={sum(total)})", zorder=3)


def style_time_axis(ax, x_lo: float, x_hi: float, bin_seconds: float,
                    peak: float) -> None:
    """Shared axis styling: clock ticks, recessive grid, legend headroom."""
    bin_label = _bin_label(bin_seconds)
    ax.set_xlabel("Time of day")
    ax.set_ylabel(f"People per {bin_label}")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_hhmm))
    ax.xaxis.set_major_locator(mticker.MultipleLocator(_tick_step(x_hi - x_lo)))
    ax.set_xlim(x_lo, x_hi)
    # Headroom so the legend does not sit on top of the tallest peak.
    ax.set_ylim(0, max(peak, 1) * 1.35)
    # Recessive axes and grid — the data should carry the ink.
    ax.grid(True, axis="y", alpha=0.25, linewidth=0.7)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def plot_exit(exit_name: str,
              events: list[dict],
              train_events: list[dict],
              bin_seconds: float,
              t_start: float,
              t_end: float,
              run_id: str,
              out_dir: Path,
              show_arrivals: bool = True) -> Path:
    """Render one figure for one exit and return the path written."""
    edges, series = _bin_series(events, bin_seconds, t_start, t_end)
    # Plot against the snapped grid, not the raw request, or the first bin is
    # clipped off the left edge and reads as a partial value.
    x_lo, x_hi = edges[0], edges[-1] + bin_seconds

    fig, ax = plt.subplots(figsize=(12, 5.5))

    platforms_present = {
        origin for origin in series
        if origin not in ("total", "entrance") and any(series[origin])
    }
    if show_arrivals:
        draw_arrivals(ax, train_events, platforms_present, x_lo, x_hi, bin_seconds)
    draw_histogram(ax, edges, series, bin_seconds)

    ax.set_title(
        f"{EXIT_LABELS.get(exit_name, exit_name)} — people leaving per "
        f"{_bin_label(bin_seconds)}\nby originating platform · {run_id}",
        fontsize=12, loc="left",
    )
    style_time_axis(ax, x_lo, x_hi, bin_seconds, max(series["total"], default=1))

    if show_arrivals and platforms_present:
        ax.plot([], [], color=TOTAL_COLOUR, linestyle="--", linewidth=1.5,
                alpha=0.8, label="Train arrival")
    ax.legend(loc="upper left", frameon=True, facecolor="white", edgecolor="none",
              framealpha=0.9, fontsize=9, ncol=3)

    fig.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"exit_usage_{exit_name}.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_time_range(text: str) -> tuple[float, float]:
    """Parse 'HH:MM-HH:MM' into (start_s, end_s) from midnight."""
    try:
        start_text, end_text = text.split("-")
        def to_seconds(value: str) -> float:
            hours, minutes = value.strip().split(":")
            return int(hours) * 3600 + int(minutes) * 60
        return to_seconds(start_text), to_seconds(end_text)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid time range {text!r} — expected HH:MM-HH:MM"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", type=Path, default=None,
                        help="Run directory (default: latest Calibration run)")
    parser.add_argument("--bin-seconds", type=float, default=60.0,
                        help="Width of each time bin in seconds (default: 60)")
    parser.add_argument("--time-range", type=_parse_time_range, default=None,
                        help="Restrict the x-axis, e.g. 07:00-09:30")
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="Directory for the PNGs (default: <run_dir>/figures)")
    parser.add_argument("--csv", action="store_true",
                        help="Also write the binned series as CSV")
    parser.add_argument("--no-cache", action="store_true",
                        help="Re-extract even if exit_usage.csv exists")
    parser.add_argument("--no-arrivals", action="store_true",
                        help="Do not draw train arrival lines")
    return parser.parse_args()


def main() -> int:
    if not MATPLOTLIB_AVAILABLE:
        print("matplotlib is required: pip install matplotlib", file=sys.stderr)
        return 1

    args = parse_args()

    run_dir = args.run
    if run_dir is None:
        run_dir = find_latest_run(REPO_ROOT / "results", "Calibration")
        if run_dir is None:
            print("No Calibration runs found under results/", file=sys.stderr)
            return 1
    if not run_dir.exists():
        print(f"Run directory not found: {run_dir}", file=sys.stderr)
        return 1

    print(f"Run: {run_dir}")

    exit_events, train_events = load_run(run_dir, use_cache=not args.no_cache)
    if not exit_events:
        print("No exit events found — nothing to plot.", file=sys.stderr)
        return 1

    # Origin attribution is calibrated for runtime-spawned (timetable) arrivals.
    # Pre-placed agents (E1-E5 snapshots) are scattered along the platform rather
    # than at train doors, so they resolve to "unknown" — report that rather than
    # quietly drawing a chart whose platform split means nothing.
    unattributed = sum(1 for e in exit_events if e["origin"] == "unknown")
    if unattributed:
        print(f"  warning: {unattributed}/{len(exit_events)} people have no "
              f"identifiable origin platform — the per-platform split is "
              f"incomplete for this run", file=sys.stderr)

    times = [e["exit_time_s"] for e in exit_events]
    t_start, t_end = min(times), max(times)
    if args.time_range:
        t_start, t_end = args.time_range
    # Pad by one bin so the last event is not clipped at the axis edge.
    t_end += args.bin_seconds

    run_id = run_dir.name
    # Colocate with the run by default, so figures are grouped and never
    # collide with another run's — same convention as population_timeseries.png.
    out_dir = args.out_dir if args.out_dir is not None else run_dir / "figures"
    by_exit: dict[str, list[dict]] = {}
    for event in exit_events:
        by_exit.setdefault(event["exit"], []).append(event)

    for exit_name in sorted(by_exit):
        window = [e for e in by_exit[exit_name] if t_start <= e["exit_time_s"] <= t_end]
        if not window:
            print(f"  {exit_name}: no events in window, skipped")
            continue
        out_path = plot_exit(exit_name, window, train_events, args.bin_seconds,
                             t_start, t_end, run_id, out_dir,
                             show_arrivals=not args.no_arrivals)
        counts: dict[str, int] = {}
        for event in window:
            counts[event["origin"]] = counts.get(event["origin"], 0) + 1
        breakdown = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
        print(f"  {exit_name}: {len(window)} people ({breakdown}) -> {out_path}")

        if args.csv:
            edges, series = _bin_series(window, args.bin_seconds, t_start, t_end)
            csv_path = out_dir / f"exit_usage_{exit_name}.csv"
            with csv_path.open("w", newline="") as f:
                writer = csv.writer(f)
                keys = [k for k in sorted(series) if k != "total"] + ["total"]
                writer.writerow(["bin_start_s", "time_of_day"] + keys)
                for i, edge in enumerate(edges):
                    writer.writerow([edge, _hhmm(edge)] + [series[k][i] for k in keys])
            print(f"    series CSV -> {csv_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
