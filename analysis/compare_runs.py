#!/usr/bin/env python3
"""
Compare performance and behaviour metrics across simulation runs.

Useful for A/B performance experiments (e.g. comparing different decision
cadence or LLM settings) as well as ad-hoc inspection of any set of runs.

Usage
-----
# Auto-discover and compare the N most-recent Test runs (default 3):
    python analysis/compare_runs.py

# Specify an experiment folder to discover from:
    python analysis/compare_runs.py --experiment Test

# Compare explicit run directories:
    python analysis/compare_runs.py --runs \
        results/Test/run_20260803_195757 \
        results/Test/run_20260803_200947 \
        results/Test/run_20260803_201802

# Label runs for nicer table headers:
    python analysis/compare_runs.py \
        --runs results/Test/run_20260803_195757 results/Test/run_20260803_200947 \
        --labels baseline variant_A

# Save CSV output alongside the printed table:
    python analysis/compare_runs.py --csv results/comparison.csv

# Mark the baseline (index into --runs, 0-based, default 0):
    python analysis/compare_runs.py --baseline 0
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class RunMetrics:
    """All metrics extracted from a single simulation run directory."""
    label: str
    run_dir: Path

    # --- Performance ---
    wall_time_s: Optional[float] = None          # TOTAL wall-clock (seconds)
    jps_time_s: Optional[float] = None           # jupedsim_step total
    decision_time_s: Optional[float] = None      # decision_processing total

    # --- LLM usage ---
    llm_requests: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_gbp: Optional[float] = None
    llm_calls_made: Optional[int] = None
    llm_calls_skipped: Optional[int] = None
    skip_rate_pct: Optional[float] = None
    avg_llm_ms: Optional[float] = None
    p50_llm_ms: Optional[float] = None
    p90_llm_ms: Optional[float] = None
    p99_llm_ms: Optional[float] = None

    # --- Decision cadence ---
    decision_cycles: Optional[int] = None        # total targeted cycles
    single_agent_cycles: Optional[int] = None    # 1-agent targeted cycles (transfers)

    # --- Behaviour ---
    route_changes: Optional[int] = None
    wait_events: Optional[int] = None
    messages_sent: Optional[int] = None
    message_deliveries: Optional[int] = None

    # --- Actions from LLM responses ---
    move_count: Optional[int] = None
    wait_count: Optional[int] = None

    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def _grep(path: Path, pattern: str) -> list[str]:
    """Return all lines in *path* matching the regex *pattern*."""
    if not path.exists():
        return []
    rx = re.compile(pattern)
    return [line for line in path.read_text(errors="replace").splitlines() if rx.search(line)]


def _first_float(lines: list[str], pattern: str) -> Optional[float]:
    """Return the first float matching *pattern* inside *lines*."""
    rx = re.compile(pattern)
    for line in lines:
        m = rx.search(line)
        if m:
            try:
                return float(m.group(1).replace(",", "").strip())
            except (ValueError, IndexError):
                pass
    return None


def _first_int(lines: list[str], pattern: str) -> Optional[int]:
    v = _first_float(lines, pattern)
    return int(v) if v is not None else None


def _extract_performance(m: RunMetrics) -> None:
    perf_file = m.run_dir / "performance_report.txt"
    if not perf_file.exists():
        m.errors.append("performance_report.txt missing")
        return
    lines = perf_file.read_text(errors="replace").splitlines()
    m.wall_time_s = _first_float(_grep(perf_file, r"TOTAL \(wall-clock\)"), r":\s*([\d.]+)s")
    m.jps_time_s = _first_float(_grep(perf_file, r"jupedsim_step"), r":\s*([\d.]+)s total")
    m.decision_time_s = _first_float(_grep(perf_file, r"decision_processing"), r":\s*([\d.]+)s total")


def _extract_financial(m: RunMetrics) -> None:
    fin_file = m.run_dir / "financial_report.txt"
    if not fin_file.exists():
        m.errors.append("financial_report.txt missing")
        return
    lines = fin_file.read_text(errors="replace").splitlines()
    m.prompt_tokens   = _first_int(lines,   r"Prompt tokens:\s+([\d,]+)")
    m.completion_tokens = _first_int(lines, r"Completion tokens:\s+([\d,]+)")
    m.total_tokens    = _first_int(lines,   r"Total tokens:\s+([\d,]+)")
    m.llm_requests    = _first_int(lines,   r"Total requests:\s+([\d,]+)")
    m.cost_gbp        = _first_float(lines, r"TOTAL COST:\s+£([\d.]+)")


def _extract_llm_logs(m: RunMetrics) -> None:
    log_file = m.run_dir / "llm_prompt_log.jsonl"
    if not log_file.exists():
        m.errors.append("llm_prompt_log.jsonl missing")
        return
    durations: list[float] = []
    move_count = 0
    wait_count = 0
    for raw in log_file.read_text(errors="replace").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue
        lc = rec.get("latency_checkpoint", {}) or {}
        dur = lc.get("total_duration_ms")
        if dur is None:
            usage = rec.get("usage", {})
            inner = (usage or {}).get("latency_checkpoint", {})
            if inner:
                dur = inner.get("total_duration_ms")
        if dur is not None:
            try:
                durations.append(float(dur))
            except (ValueError, TypeError):
                pass
        # Action counts from response
        try:
            resp = json.loads(rec.get("response", "") or "{}")
            action = resp.get("action_type", "")
            if action == "move":
                move_count += 1
            elif action == "wait":
                wait_count += 1
        except (json.JSONDecodeError, TypeError):
            pass

    if durations:
        durations.sort()
        n = len(durations)
        m.avg_llm_ms = statistics.mean(durations)
        m.p50_llm_ms = durations[n // 2]
        m.p90_llm_ms = durations[int(n * 0.9)]
        m.p99_llm_ms = durations[int(n * 0.99)]
    m.move_count = move_count
    m.wait_count = wait_count


def _extract_sim_log(m: RunMetrics) -> None:
    sim_log = m.run_dir / "simulation.log"
    if not sim_log.exists():
        m.errors.append("simulation.log missing")
        return

    llm_made_lines  = _grep(sim_log, r"LLM calls made:")
    llm_skip_lines  = _grep(sim_log, r"LLM calls skipped:")
    skip_rate_lines = _grep(sim_log, r"Skip rate:")

    m.llm_calls_made    = _first_int(llm_made_lines,  r"LLM calls made:\s+([\d]+)")
    m.llm_calls_skipped = _first_int(llm_skip_lines,  r"LLM calls skipped:\s+([\d]+)")
    m.skip_rate_pct     = _first_float(skip_rate_lines, r"Skip rate:\s+([\d.]+)%")

    targeted_lines = _grep(sim_log, r"Targeted agent decisions at t=")
    m.decision_cycles = len(targeted_lines)
    m.single_agent_cycles = sum(
        1 for line in targeted_lines
        if re.search(r" for 1 agents", line)
    )


def _extract_behaviour(m: RunMetrics) -> None:
    route_file = m.run_dir / "route_changes.txt"
    if route_file.exists():
        m.route_changes = _first_int(route_file.read_text(errors="replace").splitlines(),
                                     r"Total route changes:\s+([\d]+)")

    wait_file = m.run_dir / "wait_behavior.txt"
    if wait_file.exists():
        m.wait_events = _first_int(wait_file.read_text(errors="replace").splitlines(),
                                   r"Total wait events:\s+([\d]+)")

    msg_file = m.run_dir / "message_analytics.txt"
    if msg_file.exists():
        lines = msg_file.read_text(errors="replace").splitlines()
        m.messages_sent     = _first_int(lines, r"Total messages sent:\s+([\d]+)")
        m.message_deliveries = _first_int(lines, r"Total message deliveries:\s+([\d]+)")


def load_run(run_dir: Path, label: str) -> RunMetrics:
    """Extract all metrics from a run directory and return a RunMetrics object."""
    m = RunMetrics(label=label, run_dir=run_dir)
    _extract_performance(m)
    _extract_financial(m)
    _extract_llm_logs(m)
    _extract_sim_log(m)
    _extract_behaviour(m)
    return m


# ---------------------------------------------------------------------------
# Auto-discovery
# ---------------------------------------------------------------------------

def discover_runs(results_dir: Path, experiment: str, n: int) -> list[Path]:
    """Return the N most-recent run directories for *experiment*."""
    exp_dir = results_dir / experiment
    if not exp_dir.exists():
        return []
    candidates = sorted(
        (d for d in exp_dir.iterdir() if d.is_dir() and d.name.startswith("run_")),
        key=lambda d: d.name,
        reverse=True,
    )
    return candidates[:n]


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _pct_delta(val: Optional[float], base: Optional[float]) -> str:
    """Return a '±X.X%' string showing change from base to val, or '—'."""
    if val is None or base is None or base == 0:
        return "—"
    pct = (val - base) / abs(base) * 100
    return f"{pct:+.1f}%"


def _fmt(val: Optional[float | int], precision: int = 1) -> str:
    if val is None:
        return "—"
    if isinstance(val, int):
        return f"{val:,}"
    return f"{val:,.{precision}f}"


def _col_width(rows: list[str], header: str, min_width: int = 10) -> int:
    return max(min_width, len(header), *(len(r) for r in rows))


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_table(runs: list[RunMetrics], baseline_idx: int = 0) -> None:
    base = runs[baseline_idx]

    # Define rows: (section, field_label, extractor, format_precision)
    # extractor is a lambda: RunMetrics -> value
    ROWS: list[tuple[str, str, object, int]] = [
        # Performance
        ("Performance", "Wall-clock time (s)", lambda m: m.wall_time_s, 1),
        ("Performance", "JuPedSim physics (s)", lambda m: m.jps_time_s, 1),
        ("Performance", "Decision processing (s)", lambda m: m.decision_time_s, 1),
        # LLM usage
        ("LLM calls", "Requests", lambda m: m.llm_requests, 0),
        ("LLM calls", "  Calls made (cache miss)", lambda m: m.llm_calls_made, 0),
        ("LLM calls", "  Calls skipped (cache hit)", lambda m: m.llm_calls_skipped, 0),
        ("LLM calls", "  Cache skip rate (%)", lambda m: m.skip_rate_pct, 1),
        ("LLM tokens", "Prompt tokens", lambda m: m.prompt_tokens, 0),
        ("LLM tokens", "Completion tokens", lambda m: m.completion_tokens, 0),
        ("LLM tokens", "Total tokens", lambda m: m.total_tokens, 0),
        ("LLM cost", "Cost (£)", lambda m: m.cost_gbp, 4),
        ("LLM latency", "Avg latency (ms)", lambda m: m.avg_llm_ms, 0),
        ("LLM latency", "P50 latency (ms)", lambda m: m.p50_llm_ms, 0),
        ("LLM latency", "P90 latency (ms)", lambda m: m.p90_llm_ms, 0),
        ("LLM latency", "P99 latency (ms)", lambda m: m.p99_llm_ms, 0),
        # Decision cycles
        ("Decision cycles", "Total targeted cycles", lambda m: m.decision_cycles, 0),
        ("Decision cycles", "  Single-agent (transfer)", lambda m: m.single_agent_cycles, 0),
        # Behaviour
        ("Behaviour", "Route changes", lambda m: m.route_changes, 0),
        ("Behaviour", "Wait events", lambda m: m.wait_events, 0),
        ("Behaviour", "Messages sent", lambda m: m.messages_sent, 0),
        ("Behaviour", "Message deliveries", lambda m: m.message_deliveries, 0),
        ("Behaviour", "Move decisions", lambda m: m.move_count, 0),
        ("Behaviour", "Wait decisions", lambda m: m.wait_count, 0),
    ]

    label_col_w = max(len("Metric"), max(len(r[1]) for r in ROWS)) + 2

    # Build formatted value cells
    val_cells: list[list[str]] = []   # val_cells[run_idx][row_idx]
    delta_cells: list[list[str]] = [] # delta_cells[run_idx][row_idx]
    for i, m in enumerate(runs):
        vcol = []
        dcol = []
        for _, _, extractor, prec in ROWS:
            val = extractor(m)
            base_val = extractor(base)
            vcol.append(_fmt(val, precision=prec))
            dcol.append("—" if i == baseline_idx else _pct_delta(
                float(val) if val is not None else None,
                float(base_val) if base_val is not None else None,
            ))
        val_cells.append(vcol)
        delta_cells.append(dcol)

    # Column widths
    val_ws = [
        _col_width([val_cells[i][j] for j in range(len(ROWS))], m.label, min_width=12)
        for i, m in enumerate(runs)
    ]
    delta_ws = [
        _col_width([delta_cells[i][j] for j in range(len(ROWS))], "Δ vs base", min_width=9)
        for i, m in enumerate(runs)
    ]

    # Separator
    total_w = label_col_w + 3 + sum(val_ws[i] + delta_ws[i] + 7 for i in range(len(runs)))

    def sep(char="-"): print(char * total_w)

    def header_row():
        row = " " * label_col_w + " │"
        for i, m in enumerate(runs):
            row += f" {m.label:^{val_ws[i]}} │ {'Δ vs base':^{delta_ws[i]}} │"
        print(row)

    def divider_row():
        row = "─" * label_col_w + "─┼"
        for i in range(len(runs)):
            row += "─" * (val_ws[i] + 2) + "─┼─" + "─" * delta_ws[i] + "─┼"
        print(row)

    def data_row(label: str, j: int):
        row = f" {label:<{label_col_w - 1}}│"
        for i in range(len(runs)):
            row += f" {val_cells[i][j]:>{val_ws[i]}} │ {delta_cells[i][j]:>{delta_ws[i]}} │"
        print(row)

    def section_header(section: str):
        print(f" {section}")
        sep("·")

    # ── Print ────────────────────────────────────────────────────────────────
    print()
    sep("═")
    header_row()
    sep("═")

    current_section = None
    for j, (section, label, _, _) in enumerate(ROWS):
        if section != current_section:
            if current_section is not None:
                sep()
            section_header(section)
            current_section = section
        data_row(label, j)

    sep("═")
    print()

    # Print run directories for traceability
    print("Run directories")
    for m in runs:
        marker = " (baseline)" if m == base else ""
        print(f"  {m.label:<20} {m.run_dir}{marker}")
    if any(m.errors for m in runs):
        print()
        print("Warnings / missing files")
        for m in runs:
            for e in m.errors:
                print(f"  [{m.label}] {e}")
    print()


def write_csv(runs: list[RunMetrics], baseline_idx: int, csv_path: Path) -> None:
    """Write a flat CSV of all metrics plus delta columns."""
    FIELDS: list[tuple[str, object]] = [
        ("wall_time_s", lambda m: m.wall_time_s),
        ("jps_time_s", lambda m: m.jps_time_s),
        ("decision_time_s", lambda m: m.decision_time_s),
        ("llm_requests", lambda m: m.llm_requests),
        ("llm_calls_made", lambda m: m.llm_calls_made),
        ("llm_calls_skipped", lambda m: m.llm_calls_skipped),
        ("skip_rate_pct", lambda m: m.skip_rate_pct),
        ("prompt_tokens", lambda m: m.prompt_tokens),
        ("completion_tokens", lambda m: m.completion_tokens),
        ("total_tokens", lambda m: m.total_tokens),
        ("cost_gbp", lambda m: m.cost_gbp),
        ("avg_llm_ms", lambda m: m.avg_llm_ms),
        ("p50_llm_ms", lambda m: m.p50_llm_ms),
        ("p90_llm_ms", lambda m: m.p90_llm_ms),
        ("p99_llm_ms", lambda m: m.p99_llm_ms),
        ("decision_cycles", lambda m: m.decision_cycles),
        ("single_agent_cycles", lambda m: m.single_agent_cycles),
        ("route_changes", lambda m: m.route_changes),
        ("wait_events", lambda m: m.wait_events),
        ("messages_sent", lambda m: m.messages_sent),
        ("message_deliveries", lambda m: m.message_deliveries),
        ("move_count", lambda m: m.move_count),
        ("wait_count", lambda m: m.wait_count),
    ]

    base = runs[baseline_idx]
    headers = ["label", "run_dir"] + [f[0] for f in FIELDS] + [f"{f[0]}_delta_pct" for f in FIELDS]

    rows = []
    for m in runs:
        row = [m.label, str(m.run_dir)]
        deltas = []
        for _, ext in FIELDS:
            val = ext(m)
            row.append("" if val is None else val)
            base_val = ext(base)
            if val is None or base_val is None or base_val == 0:
                deltas.append("")
            elif m is base:
                deltas.append("")
            else:
                deltas.append(round((float(val) - float(base_val)) / abs(float(base_val)) * 100, 2))
        rows.append(row + deltas)

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"CSV saved → {csv_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Compare performance and behaviour across simulation runs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--runs", nargs="+", type=Path, default=None,
        help="Explicit run directories to compare.",
    )
    p.add_argument(
        "--labels", nargs="+", default=None,
        help="Labels for each run (must match --runs in count).",
    )
    p.add_argument(
        "--experiment", default="Test",
        help="Experiment ID to auto-discover runs from (default: Test).",
    )
    p.add_argument(
        "--n", type=int, default=3,
        help="Number of most-recent runs to auto-discover (default: 3).",
    )
    p.add_argument(
        "--results-dir", type=Path, default=None,
        help="Root results directory (default: <repo_root>/results).",
    )
    p.add_argument(
        "--baseline", type=int, default=0,
        help="Index (0-based) into --runs to treat as baseline (default: 0).",
    )
    p.add_argument(
        "--csv", type=Path, default=None,
        help="If given, also write a CSV file to this path.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).parent.parent
    results_dir = args.results_dir or (repo_root / "results")

    if args.runs:
        run_dirs = [Path(r) for r in args.runs]
    else:
        run_dirs = discover_runs(results_dir, args.experiment, args.n)
        if not run_dirs:
            print(
                f"No run directories found under {results_dir / args.experiment}. "
                "Use --runs to specify paths explicitly.",
                file=sys.stderr,
            )
            sys.exit(1)
        # Reverse so oldest→newest (chronological, not newest-first)
        run_dirs.reverse()

    if args.labels:
        if len(args.labels) != len(run_dirs):
            print(
                f"--labels count ({len(args.labels)}) must match --runs count ({len(run_dirs)}).",
                file=sys.stderr,
            )
            sys.exit(1)
        labels = args.labels
    else:
        # Auto-generate labels: use the run folder name, or sequential numbering
        labels = [d.name for d in run_dirs]

    baseline_idx = args.baseline
    if not (0 <= baseline_idx < len(run_dirs)):
        print(
            f"--baseline {baseline_idx} is out of range (0–{len(run_dirs) - 1}).",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"\nLoading {len(run_dirs)} run(s)...")
    runs = [load_run(d, lbl) for d, lbl in zip(run_dirs, labels)]

    print_table(runs, baseline_idx=baseline_idx)

    if args.csv:
        write_csv(runs, baseline_idx, args.csv)


if __name__ == "__main__":
    main()
