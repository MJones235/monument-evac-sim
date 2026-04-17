#!/usr/bin/env python3
"""
Per-experiment and cross-experiment evacuation visualisation.

Generates:
- Evacuation time-series plots (agents remaining vs. simulation time)
- Zone occupancy over time per scenario
- Cross-experiment overlay comparing all five conditions

Usage:
    python analysis/evacuation_plots.py --experiment E1
    python analysis/evacuation_plots.py --all
    python analysis/evacuation_plots.py --all --output-dir figures/
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Optional

# Allow running as either `python analysis/evacuation_plots.py` or
# `python -m analysis.evacuation_plots` from the repo root.
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from analysis.proulx_1991 import REFERENCE
from analysis.compare_experiments import (
    find_latest_run,
    find_all_runs,
    load_timeseries,
    ALARM_T,
    EXPERIMENTS,
)

# Colours consistent across all plots (one per experiment).
EXP_COLOURS = {
    "E1": "#d62728",   # red
    "E2": "#ff7f0e",   # orange
    "E3": "#2ca02c",   # green
    "E4": "#1f77b4",   # blue
    "E5": "#9467bd",   # purple
}

EXP_LABELS = {
    "E1": "E1 — Alarm only",
    "E2": "E2 — Staff direction",
    "E3": "E3 — Minimal PA",
    "E4": "E4 — Staff + zone PA",
    "E5": "E5 — Rich PA (fire location)",
}

# Reference clearance lines from Proulx (1991) — (exp_id, post_alarm_s, label).
_REF_LINES = [
    ("E2", REFERENCE["E2"].clearance.whole_station_s, "E2 observed\n(~5 min)"),
    ("E2", REFERENCE["E2"].clearance.concourse_s,     "E2 concourse\n(~3 min)"),
]


def _load_curve(run_dir: Path) -> tuple[list[float], list[float], int]:
    """
    Return (times_post_alarm, frac_remaining, agent_count) for a run.
    times_post_alarm[i] is simulation time minus ALARM_T.
    """
    rows = load_timeseries(run_dir)
    if not rows:
        return [], [], 0

    times = [float(r["sim_time_s"]) - ALARM_T for r in rows]
    left = [int(r["left_station"]) for r in rows]

    first = rows[0]
    zone_cols = [c for c in first if c not in ("sim_time_s", "sim_time_min", "left_station")]
    agent_count = int(first["left_station"]) + sum(int(first[c]) for c in zone_cols)

    frac_remaining = [(agent_count - n) / agent_count if agent_count else 0.0 for n in left]
    return times, frac_remaining, agent_count


def _load_zone_curves(run_dir: Path) -> dict[str, tuple[list[float], list[float]]]:
    """
    Return {zone_name: (times_post_alarm, counts)} for all zones in the CSV.
    """
    rows = load_timeseries(run_dir)
    if not rows:
        return {}
    times = [float(r["sim_time_s"]) - ALARM_T for r in rows]
    zone_cols = [c for c in rows[0] if c not in ("sim_time_s", "sim_time_min", "left_station")]
    result = {}
    for zone in zone_cols:
        result[zone] = (times, [int(r[zone]) for r in rows])
    result["left_station"] = (times, [int(r["left_station"]) for r in rows])
    return result


# ---------------------------------------------------------------------------
# Individual experiment plot
# ---------------------------------------------------------------------------

def plot_single_experiment(
    exp_id: str,
    results_dir: Path,
    output_dir: Optional[Path] = None,
) -> None:
    """Plot the evacuation curve (fraction remaining) for one experiment."""
    if not MATPLOTLIB_AVAILABLE:
        print("matplotlib not installed — skipping plot generation.")
        return

    run = find_latest_run(results_dir, exp_id)
    if run is None:
        print(f"  {exp_id}: no results found in {results_dir}/{exp_id}/")
        return

    times, frac, n = _load_curve(run)
    if not times:
        print(f"  {exp_id}: population_timeseries.csv missing or empty")
        return

    zone_curves = _load_zone_curves(run)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle(f"{exp_id}: {EXP_LABELS[exp_id]}  (n={n} agents)", fontsize=13)

    # Left panel: fraction remaining
    ax = axes[0]
    ax.plot(times, frac, color=EXP_COLOURS[exp_id], linewidth=2)
    ax.axhline(0.5, color="grey", linestyle="--", linewidth=0.8, label="50% threshold")
    ax.axhline(0.1, color="grey", linestyle=":",  linewidth=0.8, label="10% threshold")
    ax.set_xlabel("Time after alarm (s)")
    ax.set_ylabel("Fraction of agents still inside")
    ax.set_title("Evacuees remaining over time")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # Add Proulx reference clearance lines where available
    ref = REFERENCE[exp_id].clearance
    for ref_t, label in [
        (ref.whole_station_s, "Proulx T100"),
        (ref.concourse_s, "Proulx concourse"),
    ]:
        if ref_t is not None:
            ax.axvline(ref_t, color="black", linestyle="-.", linewidth=1.0, label=label)
    ax.legend(fontsize=8)

    # Right panel: zone occupancy
    ax2 = axes[1]
    zone_colours = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
    for i, (zone, (zt, zn)) in enumerate(zone_curves.items()):
        ax2.plot(zt, zn, label=zone.replace("_", " "), color=zone_colours[i % len(zone_colours)])
    ax2.set_xlabel("Time after alarm (s)")
    ax2.set_ylabel("Agent count")
    ax2.set_title("Zone occupancy over time")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        out = output_dir / f"{exp_id}_evacuation.png"
        fig.savefig(out, dpi=150)
        print(f"  Saved {out}")
    else:
        plt.show()
    plt.close(fig)


# ---------------------------------------------------------------------------
# Cross-experiment overlay
# ---------------------------------------------------------------------------

def plot_all_experiments(
    results_dir: Path,
    output_dir: Optional[Path] = None,
) -> None:
    """Overlay evacuation curves for all five experiments on one figure."""
    if not MATPLOTLIB_AVAILABLE:
        print("matplotlib not installed — skipping plot generation.")
        return

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_title(
        "Monument Station Evacuation — All Conditions vs Proulx (1991)",
        fontsize=13,
    )

    any_data = False
    for exp_id in EXPERIMENTS:
        run = find_latest_run(results_dir, exp_id)
        if run is None:
            continue
        times, frac, n = _load_curve(run)
        if not times:
            continue
        any_data = True
        ax.plot(
            times, frac,
            label=f"{EXP_LABELS[exp_id]} (n={n})",
            color=EXP_COLOURS[exp_id],
            linewidth=2,
        )

    # Proulx reference clearance lines
    for exp_id, ref_t, label in _REF_LINES:
        if ref_t is not None:
            ax.axvline(
                ref_t,
                color=EXP_COLOURS[exp_id],
                linestyle="--",
                linewidth=1.2,
                alpha=0.6,
                label=f"Proulx {label} ({exp_id})",
            )

    ax.axhline(0.0, color="black", linewidth=0.5)
    ax.set_xlabel("Time after alarm (s)", fontsize=11)
    ax.set_ylabel("Fraction of agents still inside", fontsize=11)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    ax.set_ylim(-0.05, 1.05)
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(True, alpha=0.3)

    if not any_data:
        ax.text(0.5, 0.5, "No simulation results found", transform=ax.transAxes,
                ha="center", va="center", fontsize=14, color="grey")

    plt.tight_layout()

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        out = output_dir / "all_experiments_overlay.png"
        fig.savefig(out, dpi=150)
        print(f"  Saved {out}")
    else:
        plt.show()
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate evacuation plots")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--experiment", choices=["E1", "E2", "E3", "E4", "E5"])
    group.add_argument("--all", action="store_true", help="Plot all experiments")
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Save figures to this directory instead of displaying interactively",
    )
    args = parser.parse_args()

    if not MATPLOTLIB_AVAILABLE:
        print("Error: matplotlib is required for plotting. Install with: pip install matplotlib")
        return

    if args.all:
        print("Generating per-experiment plots...")
        for exp_id in EXPERIMENTS:
            print(f"  {exp_id}...")
            plot_single_experiment(exp_id, args.results_dir, args.output_dir)
        print("Generating cross-experiment overlay...")
        plot_all_experiments(args.results_dir, args.output_dir)
    else:
        plot_single_experiment(args.experiment, args.results_dir, args.output_dir)


if __name__ == "__main__":
    main()
