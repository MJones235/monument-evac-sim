#!/usr/bin/env python3
"""
Exit usage over time from real, hand-collected counts.

The real-data counterpart of ``exit_usage_plots.py``: one figure per street
exit showing how many people left through it in each time bin, with real train
arrivals (from ``monument-arrivals-logger.py``) marked as vertical lines
coloured by platform.

Unlike the synthetic data, a tally counter cannot tell which platform someone
came from, so the figure shows a single total series. The arrival lines carry
the platform information instead.

Inputs:
  * Counter CSVs (virtual volunteer app), e.g.
    ``data/calibration/collected/blackett-st-2026-05-10_10-03-31.csv``::

        STARTOFEVENT,05/10/2026 09:03:44,<device>
        0,05/10/2026 09:03:44,00:00:20
        ...
        ENDOFEVENT,05/10/2026 10:03:16

    Timestamps are the phone's local clock (DD/MM/YYYY). The exit is inferred
    from the filename prefix (``blackett-st`` -> ``blackett_street``).
  * Arrivals CSV from the logger: ``arrival_time`` is ISO-8601 with offset.

Usage:
    python analysis/real_exit_usage_plots.py \\
        --counts data/calibration/collected/blackett-st-2026-05-10_10-03-31.csv \\
        --arrivals monument_arrivals_20261005_071548.csv
    python analysis/real_exit_usage_plots.py --counts data/calibration/collected/*.csv \\
        --bin-seconds 120 --time-range 09:00-10:10

    # Observed vs simulated, same bins and axes:
    python analysis/real_exit_usage_plots.py \\
        --counts data/calibration/collected/blackett-st-2026-05-10_10-03-31.csv \\
        --sim-run results/Validation_20261005/run_20261005_150420
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.exit_usage_plots import (
    EXIT_LABELS,
    MATPLOTLIB_AVAILABLE,
    PLATFORM_COLOURS,
    TOTAL_COLOUR,
    _bin_label,
    _bin_series,
    _hhmm,
    _parse_time_range,
    draw_arrivals,
    draw_histogram,
    load_run,
    style_time_axis,
)

if MATPLOTLIB_AVAILABLE:
    import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).parent.parent
LOCAL_TZ = ZoneInfo("Europe/London")

# Counter filename prefix -> street exit id used by the simulation.
EXIT_ALIASES = {
    "blackett-st": "blackett_street",
    "blackett-street": "blackett_street",
    "grey-st": "grey_street",
    "grey-street": "grey_street",
    "eldon-sq": "eldon_square",
    "eldon-square": "eldon_square",
}


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _seconds_of_day(dt: datetime) -> float:
    return dt.hour * 3600 + dt.minute * 60 + dt.second + dt.microsecond / 1e6


def exit_from_filename(path: Path) -> str:
    """Map e.g. ``blackett-st-2026-05-10_10-03-31.csv`` to ``blackett_street``."""
    stem = path.stem.lower()
    for prefix in sorted(EXIT_ALIASES, key=len, reverse=True):
        if stem.startswith(prefix):
            return EXIT_ALIASES[prefix]
    raise ValueError(f"Cannot infer exit from {path.name} — pass --exit")


def load_counts(path: Path) -> tuple[date, list[float], tuple[float, float]]:
    """
    Read a counter CSV.

    Returns (day, exit_times_s, (start_s, end_s)) with times in seconds from
    local midnight, and the recording window from the START/END markers.
    """
    times: list[float] = []
    day: date | None = None
    start_s = end_s = None
    with path.open(newline="") as f:
        for row in csv.reader(f):
            if len(row) < 2:
                continue
            stamp = datetime.strptime(row[1].strip(), "%d/%m/%Y %H:%M:%S")
            if row[0] == "STARTOFEVENT":
                start_s, day = _seconds_of_day(stamp), stamp.date()
            elif row[0] == "ENDOFEVENT":
                end_s = _seconds_of_day(stamp)
            else:
                times.append(_seconds_of_day(stamp))
                day = day or stamp.date()
    if day is None:
        raise ValueError(f"No timestamps in {path}")
    times.sort()
    if start_s is None:
        start_s = times[0]
    if end_s is None:
        end_s = times[-1]
    return day, times, (start_s, end_s)


def load_arrivals(path: Path, day: date) -> list[dict]:
    """Return train arrivals on `day` as ``{time_s, platform, kind}`` events."""
    events: list[dict] = []
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            when = datetime.fromisoformat(row["arrival_time"]).astimezone(LOCAL_TZ)
            if when.date() != day:
                continue
            events.append(
                {
                    "time_s": _seconds_of_day(when),
                    "platform": str(row["platform"]).strip(),
                    "kind": "arrive",
                    "destination": row.get("destination", ""),
                }
            )
    events.sort(key=lambda e: e["time_s"])
    return events


def latest_arrivals_file() -> Path | None:
    files = sorted(REPO_ROOT.glob("monument_arrivals_*.csv"))
    return files[-1] if files else None


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------


def _legend(ax, ncol: int = 3) -> None:
    ax.legend(
        loc="upper left",
        frameon=True,
        facecolor="white",
        edgecolor="none",
        framealpha=0.9,
        fontsize=9,
        ncol=ncol,
    )


def _arrival_legend(ax, arrivals: list[dict]) -> None:
    """Key the arrival colours — real counts have no per-platform series to."""
    for platform in sorted({t["platform"] for t in arrivals}):
        ax.plot(
            [],
            [],
            color=PLATFORM_COLOURS.get(platform, TOTAL_COLOUR),
            linestyle="--",
            linewidth=1.5,
            label=f"Platform {platform} arrival",
        )


def _observed_series(
    exit_times: list[float], bin_seconds: float, t_start: float, t_end: float
) -> tuple[list[float], dict[str, list[int]]]:
    # Tagged with an origin other than "total" — _bin_series adds every event
    # to "total" itself, so reusing that key would double-count.
    events = [{"exit_time_s": t, "origin": "observed"} for t in exit_times]
    return _bin_series(events, bin_seconds, t_start, t_end)


def plot_exit(
    exit_name: str,
    exit_times: list[float],
    train_events: list[dict],
    bin_seconds: float,
    t_start: float,
    t_end: float,
    source_id: str,
    out_dir: Path,
    show_arrivals: bool = True,
) -> tuple[Path, list[float], list[int]]:
    """Render one figure; return (path, bin_edges, counts)."""
    edges, series = _observed_series(exit_times, bin_seconds, t_start, t_end)
    x_lo, x_hi = edges[0], edges[-1] + bin_seconds

    fig, ax = plt.subplots(figsize=(12, 5.5))
    arrivals = []
    if show_arrivals:
        arrivals = draw_arrivals(ax, train_events, set(PLATFORM_COLOURS), x_lo, x_hi, bin_seconds)
    draw_histogram(
        ax, edges, series, bin_seconds, stack_origins=False, total_label="Observed exits"
    )

    ax.set_title(
        f"{EXIT_LABELS.get(exit_name, exit_name)} — people leaving per "
        f"{_bin_label(bin_seconds)} (observed)\n"
        f"with real train arrivals by platform · {source_id}",
        fontsize=12,
        loc="left",
    )
    style_time_axis(ax, x_lo, x_hi, bin_seconds, max(series["total"], default=1))
    _arrival_legend(ax, arrivals)
    _legend(ax)

    fig.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"real_exit_usage_{exit_name}_{source_id}.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path, edges, series["total"]


def plot_comparison(
    exit_name: str,
    exit_times: list[float],
    sim_events: list[dict],
    train_events: list[dict],
    bin_seconds: float,
    t_start: float,
    t_end: float,
    source_id: str,
    run_id: str,
    out_dir: Path,
    show_arrivals: bool = True,
) -> tuple[Path, list[float], list[int], list[int]]:
    """
    Observed (top) vs simulated (bottom) for one exit, on identical bins and
    shared x/y axes so bar heights compare directly.
    """
    edges, observed = _observed_series(exit_times, bin_seconds, t_start, t_end)
    sim_edges, simulated = _bin_series(sim_events, bin_seconds, t_start, t_end)
    assert sim_edges == edges
    x_lo, x_hi = edges[0], edges[-1] + bin_seconds
    peak = max(observed["total"] + simulated["total"], default=1)

    fig, (ax_obs, ax_sim) = plt.subplots(2, 1, figsize=(12, 9), sharex=True, sharey=True)
    label = EXIT_LABELS.get(exit_name, exit_name)
    for ax, series, stack, title, total_label in (
        (ax_obs, observed, False, f"Observed · {source_id}", "Observed exits"),
        (
            ax_sim,
            simulated,
            True,
            f"Simulated · {run_id} · by originating platform",
            "Simulated exits",
        ),
    ):
        arrivals = []
        if show_arrivals:
            arrivals = draw_arrivals(
                ax, train_events, set(PLATFORM_COLOURS), x_lo, x_hi, bin_seconds, markers=False
            )
        draw_histogram(ax, edges, series, bin_seconds, stack_origins=stack, total_label=total_label)
        style_time_axis(ax, x_lo, x_hi, bin_seconds, peak)
        ax.set_title(title, fontsize=10.5, loc="left")
        if ax is ax_obs:
            _arrival_legend(ax, arrivals)
        _legend(ax, ncol=4)
    ax_obs.set_xlabel("")

    fig.suptitle(
        f"{label} — people leaving per {_bin_label(bin_seconds)}, observed vs simulated",
        x=0.01,
        ha="left",
        fontsize=12,
    )
    fig.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"compare_exit_usage_{exit_name}_{source_id}_{run_id}.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path, edges, observed["total"], simulated["total"]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--counts", type=Path, nargs="+", required=True, help="Counter CSV(s), one per exit/session"
    )
    parser.add_argument(
        "--arrivals",
        type=Path,
        default=None,
        help="Arrivals CSV (default: latest monument_arrivals_*.csv)",
    )
    parser.add_argument(
        "--sim-run",
        type=Path,
        default=None,
        help="Simulation run directory to compare against (adds an observed-vs-simulated figure)",
    )
    parser.add_argument(
        "--exit", default=None, help="Override the exit id inferred from the filename"
    )
    parser.add_argument(
        "--bin-seconds",
        type=float,
        default=60.0,
        help="Width of each time bin in seconds (default: 60)",
    )
    parser.add_argument(
        "--time-range",
        type=_parse_time_range,
        default=None,
        help="Restrict the x-axis, e.g. 09:00-10:10",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Directory for the PNGs (default: <counts dir>/figures)",
    )
    parser.add_argument("--csv", action="store_true", help="Also write the binned series as CSV")
    parser.add_argument(
        "--no-arrivals", action="store_true", help="Do not draw train arrival lines"
    )
    return parser.parse_args()


def main() -> int:
    if not MATPLOTLIB_AVAILABLE:
        print("matplotlib is required: pip install matplotlib", file=sys.stderr)
        return 1

    args = parse_args()
    arrivals_path = args.arrivals or latest_arrivals_file()
    if arrivals_path is None and not args.no_arrivals:
        print("No arrivals CSV found — pass --arrivals or --no-arrivals", file=sys.stderr)
        return 1

    sim_events: list[dict] = []
    if args.sim_run is not None:
        if not args.sim_run.exists():
            print(f"Run directory not found: {args.sim_run}", file=sys.stderr)
            return 1
        print(f"Simulation run: {args.sim_run}")
        sim_events, _ = load_run(args.sim_run)

    for counts_path in args.counts:
        exit_name = args.exit or exit_from_filename(counts_path)
        day, exit_times, (rec_start, rec_end) = load_counts(counts_path)
        print(
            f"{counts_path.name}: {exit_name}, {len(exit_times)} people, "
            f"{day} {_hhmm(rec_start)}–{_hhmm(rec_end)}"
        )

        train_events: list[dict] = []
        if not args.no_arrivals:
            train_events = load_arrivals(arrivals_path, day)
            in_window = [t for t in train_events if rec_start <= t["time_s"] <= rec_end]
            print(f"  {arrivals_path.name}: {len(in_window)} arrivals during recording")
            if not in_window:
                print(
                    f"  warning: no arrivals in {arrivals_path.name} overlap "
                    f"this recording ({day}) — check the files match",
                    file=sys.stderr,
                )

        t_start, t_end = args.time_range or (rec_start, rec_end + 1)
        source_id = counts_path.stem
        out_dir = args.out_dir or counts_path.parent / "figures"
        out_path, edges, counts = plot_exit(
            exit_name,
            exit_times,
            train_events,
            args.bin_seconds,
            t_start,
            t_end,
            source_id,
            out_dir,
            show_arrivals=not args.no_arrivals,
        )
        print(f"  -> {out_path}")

        if args.csv:
            csv_path = out_path.with_suffix(".csv")
            with csv_path.open("w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["bin_start_s", "time_of_day", "total"])
                for edge, count in zip(edges, counts, strict=True):
                    writer.writerow([edge, _hhmm(edge), count])
            print(f"    series CSV -> {csv_path}")

        if args.sim_run is not None:
            # Same exit, same window as the counter — anything outside it was
            # never observed, so it is not comparable.
            sim_exit = [
                e
                for e in sim_events
                if e["exit"] == exit_name and t_start <= e["exit_time_s"] < t_end
            ]
            cmp_path, edges, observed, simulated = plot_comparison(
                exit_name,
                exit_times,
                sim_exit,
                train_events,
                args.bin_seconds,
                t_start,
                t_end,
                source_id,
                args.sim_run.name,
                out_dir,
                show_arrivals=not args.no_arrivals,
            )
            print(
                f"  observed {sum(observed)} vs simulated {sum(simulated)} in window -> {cmp_path}"
            )
            if args.csv:
                csv_path = cmp_path.with_suffix(".csv")
                with csv_path.open("w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["bin_start_s", "time_of_day", "observed", "simulated"])
                    for edge, o, s in zip(edges, observed, simulated, strict=True):
                        writer.writerow([edge, _hhmm(edge), o, s])
                print(f"    series CSV -> {csv_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
