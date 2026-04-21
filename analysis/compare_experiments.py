#!/usr/bin/env python3
"""
Compare simulated results across all E1–E5 experiments against the Proulx
(1991) ground-truth data from Monument Station.

Loads the most recent run from each experiment's results directory, computes
key evacuation metrics from population_timeseries.csv, and prints a comparison
table alongside the observed reference values.

Usage:
    python analysis/compare_experiments.py
    python analysis/compare_experiments.py --results-dir /path/to/results
    python analysis/compare_experiments.py --all-runs    # report over all runs
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Allow running as either `python analysis/compare_experiments.py` or
# `python -m analysis.compare_experiments` from the repo root.
sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.proulx_1991 import REFERENCE, qualitative_ordering

EXPERIMENTS = ["E1", "E2", "E3", "E4", "E5"]

# Alarm fires at t=15 s in every experiment config.
ALARM_T = 15.0


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SimMetrics:
    """Key metrics extracted from one simulation run."""
    experiment_id: str
    run_dir: Path
    agent_count: int

    # Simulation time (seconds) at which N% of agents had exited.
    # None if that fraction was never reached within the simulation window.
    t50_s: Optional[float]
    t90_s: Optional[float]
    t100_s: Optional[float]

    # Fraction of agents still in the station at key post-alarm times.
    frac_remaining_60s: Optional[float]
    frac_remaining_120s: Optional[float]
    frac_remaining_180s: Optional[float]

    remaining_at_end: int
    sim_end_time_s: float

    # Time-to-first-move (post-alarm seconds) by starting zone.
    # Median of the first post-alarm decision timestep where action_type='move',
    # split into concourse-starting and platform-starting agents.
    # None if no agents of that type moved during the simulation.
    tfm_concourse_median_s: Optional[float] = None
    tfm_platform_median_s: Optional[float] = None
    tfm_concourse_n: int = 0   # number of concourse agents that moved
    tfm_platform_n: int = 0    # number of platform agents that moved


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------

def find_latest_run(results_dir: Path, experiment_id: str) -> Optional[Path]:
    """Return the most recent run directory for an experiment."""
    exp_dir = results_dir / experiment_id
    if not exp_dir.exists():
        return None
    runs = sorted(
        (p for p in exp_dir.iterdir() if p.is_dir() and p.name.startswith("run_")),
        reverse=True,
    )
    return runs[0] if runs else None


def find_all_runs(results_dir: Path, experiment_id: str) -> list[Path]:
    """Return all run directories for an experiment, newest-first."""
    exp_dir = results_dir / experiment_id
    if not exp_dir.exists():
        return []
    return sorted(
        (p for p in exp_dir.iterdir() if p.is_dir() and p.name.startswith("run_")),
        reverse=True,
    )


def load_timeseries(run_dir: Path) -> list[dict]:
    """Load population_timeseries.csv and return list of row dicts."""
    csv_path = run_dir / "population_timeseries.csv"
    if not csv_path.exists():
        return []
    with csv_path.open() as f:
        return list(csv.DictReader(f))


def _extract_first_move(
    run_dir: Path,
    alarm_t: float,
) -> tuple[Optional[float], Optional[float], int, int]:
    """
    Parse agent_decisions.json and return:
      (concourse_median_s, platform_median_s, concourse_n_moved, platform_n_moved)

    Concourse agents: starting zone contains 'concourse'.
    Platform agents: everything else (Platform 1–4, underground platform level).
    First move: first post-alarm decision where action_type == 'move'.
    Times are seconds post-alarm.
    """
    json_path = run_dir / "agent_decisions.json"
    if not json_path.exists():
        return None, None, 0, 0

    with json_path.open() as f:
        data = json.load(f)

    decisions_map: dict = data.get("agent_decisions", data) if isinstance(data, dict) else {}
    if not decisions_map:
        return None, None, 0, 0

    concourse_times: list[float] = []
    platform_times: list[float] = []

    for agent_id, adata in decisions_map.items():
        decs = adata.get("decisions", [])
        if not decs:
            continue

        # Determine starting zone from first observation's "You are in" line.
        start_zone = ""
        for line in decs[0].get("observation", "").split("\n"):
            if "You are in" in line:
                start_zone = line.strip().lower()
                break
        is_concourse = "concourse" in start_zone

        # Find first post-alarm decision where action_type == 'move'.
        first_move_t: Optional[float] = None
        for dec in decs:
            if dec["time"] <= alarm_t:
                continue
            action = dec.get("translated", {}).get("action_type", "")
            if action == "move":
                first_move_t = dec["time"] - alarm_t
                break

        if first_move_t is not None:
            if is_concourse:
                concourse_times.append(first_move_t)
            else:
                platform_times.append(first_move_t)

    concourse_med = statistics.median(concourse_times) if concourse_times else None
    platform_med = statistics.median(platform_times) if platform_times else None
    return concourse_med, platform_med, len(concourse_times), len(platform_times)


def extract_metrics(experiment_id: str, run_dir: Path) -> Optional[SimMetrics]:
    """Compute SimMetrics from a run directory. Returns None if data is missing."""
    rows = load_timeseries(run_dir)
    if not rows:
        return None

    times = [float(r["sim_time_s"]) for r in rows]
    left = [int(r["left_station"]) for r in rows]

    first = rows[0]
    zone_cols = [c for c in first if c not in ("sim_time_s", "sim_time_min", "left_station")]
    agent_count = int(first["left_station"]) + sum(int(first[c]) for c in zone_cols)

    sim_end = times[-1]
    remaining_at_end = agent_count - left[-1]

    def t_at_fraction(frac: float) -> Optional[float]:
        target = frac * agent_count
        for t, n in zip(times, left):
            if n >= target:
                return t
        return None

    def frac_remaining_at(sim_t: float) -> Optional[float]:
        if not times:
            return None
        nearest = min(range(len(times)), key=lambda i: abs(times[i] - sim_t))
        return (agent_count - left[nearest]) / agent_count if agent_count else None

    tfm_c, tfm_p, tfm_cn, tfm_pn = _extract_first_move(run_dir, ALARM_T)

    return SimMetrics(
        experiment_id=experiment_id,
        run_dir=run_dir,
        agent_count=agent_count,
        t50_s=t_at_fraction(0.50),
        t90_s=t_at_fraction(0.90),
        t100_s=t_at_fraction(1.00),
        frac_remaining_60s=frac_remaining_at(ALARM_T + 60),
        frac_remaining_120s=frac_remaining_at(ALARM_T + 120),
        frac_remaining_180s=frac_remaining_at(ALARM_T + 180),
        remaining_at_end=remaining_at_end,
        sim_end_time_s=sim_end,
        tfm_concourse_median_s=tfm_c,
        tfm_platform_median_s=tfm_p,
        tfm_concourse_n=tfm_cn,
        tfm_platform_n=tfm_pn,
    )


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _fmt_time(t: Optional[float]) -> str:
    if t is None:
        return "—"
    post = t - ALARM_T
    return f"{post:>5.0f}s ({post / 60:.1f} min)"


def _fmt_pct(f: Optional[float]) -> str:
    if f is None:
        return "—"
    return f"{f * 100:.0f}%"


# ---------------------------------------------------------------------------
# Validation checks against Proulx (1991)
# ---------------------------------------------------------------------------

def check_qualitative_ordering(metrics_by_exp: dict[str, Optional[SimMetrics]]) -> None:
    """
    Check whether the simulation reproduces Proulx (1991)'s effectiveness
    ordering: E1 (worst) < E3 < E2 < E4 < E5 (best).

    Uses T90 as the primary ranking metric.
    """
    expected_order = qualitative_ordering()  # worst → best
    t90s = {exp: (m.t90_s if m else None) for exp, m in metrics_by_exp.items()}

    print("\n=== Qualitative ordering check (Proulx 1991: E1 worst → E5 best) ===")
    ranked = sorted(
        [(exp, t) for exp, t in t90s.items() if t is not None],
        key=lambda x: x[1],
    )
    sim_order = [exp for exp, _ in ranked]
    unranked = [exp for exp, t in t90s.items() if t is None]

    for i, (exp, t) in enumerate(ranked):
        print(f"  {exp:<6} T90={_fmt_time(t):<22}  sim rank #{i + 1}")
    for exp in unranked:
        print(f"  {exp:<6} T90=— (never reached within sim window)")

    available = [e for e in expected_order if e in sim_order]
    if sim_order == available:
        print(f"\n  ✓ Ordering matches Proulx (1991): {' < '.join(sim_order)}")
    else:
        print(f"\n  ✗ Simulated: {' < '.join(sim_order)}")
        print(f"    Expected:  {' < '.join(available)}")


def check_e2_clearance(metrics_by_exp: dict[str, Optional[SimMetrics]]) -> None:
    """
    E2-specific validation: Proulx (1991) reports the whole station cleared
    ~5 min post-alarm.
    """
    ref = REFERENCE["E2"].clearance
    m = metrics_by_exp.get("E2")
    print("\n=== E2 clearance check (Proulx 1991: whole station ~5 min post-alarm) ===")
    if m is None:
        print("  No E2 results found.")
        return
    ref_s = ref.whole_station_s
    sim_post = (m.t100_s - ALARM_T) if m.t100_s else None
    sim_str = f"{sim_post:.0f}s ({sim_post / 60:.1f} min)" if sim_post else "not reached"
    ref_str = f"~{ref_s:.0f}s ({ref_s / 60:.1f} min)" if ref_s else "—"
    print(f"  Simulated T100 post-alarm: {sim_str}")
    print(f"  Reference T100 post-alarm: {ref_str}")
    if sim_post is not None and ref_s is not None:
        err = abs(sim_post - ref_s)
        pct = err / ref_s * 100
        print(f"  Absolute error: {err:.0f}s  ({pct:.0f}% of reference)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Compare E1–E5 simulated results against Proulx (1991)"
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results"),
        help="Root results directory (default: results/)",
    )
    parser.add_argument(
        "--all-runs",
        action="store_true",
        help="List all available runs per experiment (not just the latest)",
    )
    args = parser.parse_args()

    # Collect metrics from latest run per experiment
    metrics_by_exp: dict[str, Optional[SimMetrics]] = {}
    for exp_id in EXPERIMENTS:
        if args.all_runs:
            runs = find_all_runs(args.results_dir, exp_id)
            print(f"{exp_id}: {len(runs)} run(s) found")
            for r in runs:
                print(f"  {r.name}")
        run = find_latest_run(args.results_dir, exp_id)
        metrics_by_exp[exp_id] = extract_metrics(exp_id, run) if run else None

    # Summary table
    print("\n" + "=" * 82)
    print("SIMULATED vs OBSERVED — Monument Station Evacuation  (Proulx 1991)")
    print("=" * 82)
    print(f"  {'':4}  {'T50 (post-alarm)':>22}  {'T90 (post-alarm)':>22}  {'T100 (post-alarm)':>22}  {'Left@end':>8}")
    print("-" * 82)
    for exp_id in EXPERIMENTS:
        m = metrics_by_exp[exp_id]
        if m is None:
            print(f"  {exp_id:<4}  {'-- no results --':>22}")
            continue
        print(
            f"  {exp_id:<4}"
            f"  {_fmt_time(m.t50_s):>22}"
            f"  {_fmt_time(m.t90_s):>22}"
            f"  {_fmt_time(m.t100_s):>22}"
            f"  {m.remaining_at_end:>3}/{m.agent_count}"
        )

    # Reference summary
    print("\n--- Proulx (1991) reference (post-alarm) ---")
    print(f"  {'':4}  {'Move concourse':>16}  {'Move escalator':>16}  {'Station clear':>16}")
    print("-" * 62)
    for exp_id in EXPERIMENTS:
        ref = REFERENCE[exp_id]
        c = ref.clearance
        mc = f"~{ref.time_to_move_concourse_s:.0f}s" if ref.time_to_move_concourse_s is not None else "—"
        me = f"~{ref.time_to_move_escalator_s:.0f}s" if ref.time_to_move_escalator_s is not None else "—"
        ws = f"~{c.whole_station_s:.0f}s" if c.whole_station_s is not None else "never cleared"
        print(f"  {exp_id:<4}  {mc:>16}  {me:>16}  {ws:>16}")

    # Fraction remaining at key post-alarm times
    print("\n--- Fraction of agents still inside at key post-alarm times ---")
    print(f"  {'':4}  {'+60 s':>8}  {'+120 s':>8}  {'+180 s':>8}")
    print("-" * 36)
    for exp_id in EXPERIMENTS:
        m = metrics_by_exp[exp_id]
        r60 = _fmt_pct(m.frac_remaining_60s) if m else "—"
        r120 = _fmt_pct(m.frac_remaining_120s) if m else "—"
        r180 = _fmt_pct(m.frac_remaining_180s) if m else "—"
        print(f"  {exp_id:<4}  {r60:>8}  {r120:>8}  {r180:>8}")

    # Time-to-first-move vs Proulx Table 1
    print("\n--- Time-to-first-move vs Proulx (1991) Table 1 ---")
    print("    (median post-alarm time of first 'move' decision per starting zone)")
    hdr = f"  {'':4}  {'Sim concourse':>18}  {'Ref concourse':>15}  {'Sim platform':>18}  {'Ref escalator':>15}"
    print(hdr)
    print("-" * len(hdr))
    for exp_id in EXPERIMENTS:
        m = metrics_by_exp[exp_id]
        ref = REFERENCE[exp_id]
        if m is None:
            print(f"  {exp_id:<4}  {'-- no results --':>18}")
            continue

        def _fmt_tfm(t: Optional[float], n: int) -> str:
            if t is None:
                return "— (none moved)"
            return f"{t:>4.0f}s ({t/60:.1f}min) n={n}"

        def _fmt_ref(t: Optional[float]) -> str:
            return f"~{t:.0f}s ({t/60:.1f}min)" if t is not None else "—"

        print(
            f"  {exp_id:<4}"
            f"  {_fmt_tfm(m.tfm_concourse_median_s, m.tfm_concourse_n):>18}"
            f"  {_fmt_ref(ref.time_to_move_concourse_s):>15}"
            f"  {_fmt_tfm(m.tfm_platform_median_s, m.tfm_platform_n):>18}"
            f"  {_fmt_ref(ref.time_to_move_escalator_s):>15}"
        )

    # Validation checks
    check_qualitative_ordering(metrics_by_exp)
    check_e2_clearance(metrics_by_exp)
    print()


if __name__ == "__main__":
    main()
