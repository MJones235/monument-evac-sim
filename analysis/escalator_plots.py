#!/usr/bin/env python3
"""
Escalator conveyor diagnostics for a run.

One figure per escalator, four panels:

1. Space–time diagram: each rider's position along the incline over time.
   Standers ride at belt speed (shallow lines), walkers climb faster (steeper);
   a flat run of lines means the belt was paused (far landing full).
2. Boarding per minute by lane, against the conveyor's theoretical ceiling.
3. Queue length on the boarding landing over time, by lane.
4. Ride-time distribution by lane.

Inputs, all written by the engine into the run directory:
  escalator_log.csv               one row per completed ride
  escalators.json                 conveyor geometry and parameters
  agent_decisions_history.jsonl   per-frame conveyor state (queues, riders)

Figures go to <run_dir>/figures/<escalator>.png (e.g. escalator_f_up.png) by default.

Usage:
    python analysis/escalator_plots.py --run results/Validation_20261005/run_...
    python analysis/escalator_plots.py --run ... --time-range 09:00-09:30
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.exit_usage_plots import (  # noqa: E402
    MATPLOTLIB_AVAILABLE,
    _hhmm,
    _parse_time_range,
    _tick_step,
)

if MATPLOTLIB_AVAILABLE:
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker

# Okabe-Ito pair, validated (normal ΔE 31, protan ΔE 22). Lane is also encoded
# by line style / bar position, so identity never rests on colour alone.
LANE_COLOURS = {"stand": "#0072B2", "walk": "#D55E00"}
LANE_STYLE = {"stand": "-", "walk": (0, (4, 1.5))}
INK = "#333333"
LANES = ("stand", "walk")


def load_rides(run_dir: Path) -> list[dict]:
    path = run_dir / "escalator_log.csv"
    if not path.exists():
        raise FileNotFoundError(f"No escalator_log.csv in {run_dir} — run predates the conveyor model?")
    rides = []
    with path.open() as f:
        for row in csv.DictReader(f):
            for key in ("queue_join_s", "board_s", "alight_s", "ride_s", "stall_wait_s"):
                row[key] = float(row[key])
            row["chose_s"] = float(row.get("chose_s") or row["queue_join_s"])
            rides.append(row)
    return rides


def load_frames(run_dir: Path, t_lo: float, t_hi: float) -> dict:
    """Per escalator: rider tracks {agent: [(t, s, lane)]} and queue series."""
    tracks: dict = defaultdict(lambda: defaultdict(list))
    queues: dict = defaultdict(list)
    paused: dict = defaultdict(list)
    path = run_dir / "agent_decisions_history.jsonl"
    with path.open() as f:
        for line in f:
            i = line.find('"time":')
            t = float(line[i + 7:line.find(",", i)])
            if t < t_lo:
                continue
            if t > t_hi:
                break
            frame = json.loads(line)
            for name, esc in (frame.get("escalators") or {}).items():
                for agent_id, lane, s in esc["riders"]:
                    tracks[name][agent_id].append((t, s, lane))
                queues[name].append((t, esc["queue"].get("stand", 0), esc["queue"].get("walk", 0)))
                paused[name].append((t, bool(esc.get("stalled"))))
    return {"tracks": tracks, "queues": queues, "paused": paused}


def _time_axis(ax, x_lo, x_hi):
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_hhmm))
    ax.xaxis.set_major_locator(mticker.MultipleLocator(_tick_step(x_hi - x_lo, 6)))
    ax.set_xlim(x_lo, x_hi)


def _recessive(ax):
    ax.grid(True, axis="y", alpha=0.25, linewidth=0.7)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def plot_escalator(name: str, geom: dict, rides: list[dict], frames: dict,
                   t_lo: float, t_hi: float, run_id: str, out_dir: Path,
                   bin_seconds: float = 60.0) -> Path:
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    (ax_st, ax_flow), (ax_queue, ax_ride) = axes
    length = geom["length_m"]
    belt = geom["belt_speed"]
    step = geom["step_depth"]

    # 1. Space–time.
    tracks = frames["tracks"].get(name, {})
    for agent_id, pts in tracks.items():
        lane = pts[0][2]
        ax_st.plot([p[0] for p in pts], [p[1] for p in pts], color=LANE_COLOURS[lane],
                   linestyle=LANE_STYLE[lane], linewidth=1.0, alpha=0.7)
    pause_times = [t for t, p in frames["paused"].get(name, []) if p]
    for t in pause_times:
        ax_st.axvspan(t - 0.25, t + 0.25, color="#B00020", alpha=0.08, linewidth=0)
    for lane in LANES:
        ax_st.plot([], [], color=LANE_COLOURS[lane], linestyle=LANE_STYLE[lane], label=f"{lane} lane")
    if pause_times:
        ax_st.fill_between([], [], color="#B00020", alpha=0.15, label="belt paused (landing full)")
    ax_st.set_ylim(0, length)
    ax_st.set_ylabel("Distance from boarding comb (m)")
    ax_st.set_title(f"Riders over time  ·  belt {belt} m/s, {length:.1f} m", loc="left", fontsize=10)
    ax_st.legend(loc="upper left", fontsize=8, frameon=False)
    _time_axis(ax_st, t_lo, t_hi)
    _recessive(ax_st)

    # 2. Boarding per minute by lane (side-by-side bars, 2px gap via edges).
    grid_lo = math.floor(t_lo / bin_seconds) * bin_seconds
    n_bins = max(1, math.ceil((t_hi - grid_lo) / bin_seconds))
    edges = [grid_lo + i * bin_seconds for i in range(n_bins)]
    counts = {lane: [0] * n_bins for lane in LANES}
    for r in rides:
        idx = int((r["board_s"] - grid_lo) // bin_seconds)
        if 0 <= idx < n_bins and r["lane"] in counts:
            counts[r["lane"]][idx] += 1
    width = bin_seconds * 0.42
    for k, lane in enumerate(LANES):
        ax_flow.bar([e + bin_seconds * (0.08 + 0.46 * k) for e in edges], counts[lane], width=width,
                    align="edge", color=LANE_COLOURS[lane], edgecolor="white", linewidth=1,
                    label=f"{lane}  (n={sum(counts[lane])})")
    ceiling = belt / step * bin_seconds
    ax_flow.axhline(ceiling, color=INK, linestyle=":", linewidth=1.2,
                    label=f"stand-lane ceiling ({ceiling:.0f}/min, one per step)")
    ax_flow.set_ylim(0, max(ceiling, max(max(c) for c in counts.values())) * 1.25)
    ax_flow.set_ylabel(f"People boarding per {bin_seconds / 60:.0f} min")
    ax_flow.set_title("Boarding rate", loc="left", fontsize=10)
    ax_flow.legend(loc="upper left", fontsize=8, frameon=False)
    _time_axis(ax_flow, grid_lo, grid_lo + n_bins * bin_seconds)
    _recessive(ax_flow)

    # 3. Queue length.
    q = frames["queues"].get(name, [])
    for k, lane in enumerate(LANES):
        ax_queue.plot([p[0] for p in q], [p[1 + k] for p in q], color=LANE_COLOURS[lane],
                      linestyle=LANE_STYLE[lane], linewidth=2, label=f"{lane} lane")
    ax_queue.set_ylim(bottom=0)
    ax_queue.set_ylabel("People queueing on the landing")
    ax_queue.set_title("Queue at the boarding comb", loc="left", fontsize=10)
    ax_queue.legend(loc="upper left", fontsize=8, frameon=False)
    _time_axis(ax_queue, t_lo, t_hi)
    _recessive(ax_queue)

    # 4. Ride time distribution.
    ride_times = {lane: [r["ride_s"] for r in rides if r["lane"] == lane] for lane in LANES}
    all_times = [t for v in ride_times.values() for t in v]
    if all_times:
        bins = [x * 2.0 for x in range(int(min(all_times) // 2), int(max(all_times) // 2) + 2)]
        for lane in LANES:
            if ride_times[lane]:
                ax_ride.hist(ride_times[lane], bins=bins, histtype="step", linewidth=2,
                             color=LANE_COLOURS[lane], linestyle=LANE_STYLE[lane],
                             label=f"{lane}  (median {sorted(ride_times[lane])[len(ride_times[lane]) // 2]:.0f} s)")
    ax_ride.axvline(length / belt, color=INK, linestyle=":", linewidth=1.2,
                    label=f"standing ride {length / belt:.0f} s")
    ax_ride.set_xlabel("Ride time (s)")
    ax_ride.set_ylabel("Riders")
    ax_ride.set_title("Ride time", loc="left", fontsize=10)
    ax_ride.legend(loc="upper center", fontsize=8, frameon=False)
    _recessive(ax_ride)

    arrow = "up" if geom["direction"] == "up" else "down"
    waits = [r["board_s"] - r["queue_join_s"] for r in rides]
    fig.suptitle(
        f"Escalator {geom['letter']} ({arrow}) — {len(rides)} rides, "
        f"queue wait at the landing median {sorted(waits)[len(waits) // 2] if waits else 0:.0f} s "
        f"(max {max(waits) if waits else 0:.0f} s), "
        f"belt paused {sum(r['stall_wait_s'] for r in rides):.0f} rider-s  ·  {run_id}",
        x=0.01, ha="left", fontsize=12)
    fig.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{name}.png"
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    return out_path


def main() -> int:
    if not MATPLOTLIB_AVAILABLE:
        print("matplotlib is required", file=sys.stderr)
        return 1
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", type=Path, required=True, help="Run directory")
    parser.add_argument("--time-range", type=_parse_time_range, default=None,
                        help="Restrict to e.g. 09:00-09:30")
    parser.add_argument("--bin-seconds", type=float, default=60.0)
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="Directory for PNGs (default: <run>/figures)")
    args = parser.parse_args()

    rides = load_rides(args.run)
    geometry = json.loads((args.run / "escalators.json").read_text())
    if args.time_range:
        t_lo, t_hi = args.time_range
    else:
        t_lo = min(r["chose_s"] for r in rides)
        t_hi = max(r["alight_s"] for r in rides)
    frames = load_frames(args.run, t_lo, t_hi)
    out_dir = args.out_dir or args.run / "figures"

    print(f"{len(rides)} rides, {_hhmm(t_lo)}–{_hhmm(t_hi)}")
    for name in sorted(geometry, key=lambda n: geometry[n]["letter"]):
        mine = [r for r in rides if r["escalator"] == name
                and t_lo <= r["board_s"] <= t_hi]
        if not mine:
            print(f"  {name}: no rides in window")
            continue
        path = plot_escalator(name, geometry[name], mine, frames, t_lo, t_hi,
                              args.run.name, out_dir, args.bin_seconds)
        lanes = {lane: sum(1 for r in mine if r["lane"] == lane) for lane in LANES}
        print(f"  {name}: {len(mine)} rides {lanes} -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
