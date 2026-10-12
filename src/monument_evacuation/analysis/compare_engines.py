"""Compare the decision engines on the Proulx drills: the study's main report.

    monument analyse compare_engines                       # the latest proulx_comparison batch
    monument analyse compare_engines --batch results/batches/proulx_comparison_...
    monument analyse compare_engines --runs results/E1/run_* results/E2/run_* ...

Four dimensions, one section each in ``report.md``:

1. **Fit to Proulx**: each measure against Table 1, RMSE on the fitting
   scenarios (E1, E3, E5) and the held-out staff drills (E2, E4), and
   Kendall's tau of the E1-E5 clearance ordering.
2. **Cost and runtime**: wall time, LLM requests, tokens and cost per run;
   repaired and fallback decisions.
3. **Authoring effort**: what each engine needed written (parameters, cue
   annotations, prompt lines) and the work logged in the authoring log.
4. **Variability**: spread across seeds, action mix, and a sample of the
   reasons the engine gave.

Writes ``results/comparison/<time>/``: ``report.md``, ``metrics.csv`` (one row
per run), ``fit.csv`` and figures.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from monument_evacuation.analysis.metrics import (
    RunMetrics,
    levels_at,
    read_csv,
    run_metrics,
    write_metrics_csv,
)
from monument_evacuation.analysis.proulx_fit import (
    MEASURES,
    Comparison,
    compare,
    ordering_tau,
    rmse,
)
from monument_evacuation.analysis.runs import alarm_time_s, manifest
from monument_evacuation.authoring import read_log
from monument_evacuation.paths import RESULTS

SCENARIOS = ["E1", "E2", "E3", "E4", "E5"]
TRAIN = ["E1", "E3", "E5"]
HELD_OUT = ["E2", "E4"]
ENGINES = ["rule_based", "llm"]
MEASURE_LABELS = {
    "start_move_concourse_s": "concourse starts to move",
    "start_move_platform_s": "escalator crowd starts to move",
    "clearance_s": "station clear",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--batch", type=Path, help="a batch results folder (has summary.json)")
    source.add_argument("--runs", type=Path, nargs="+", help="run directories")
    parser.add_argument("--out", type=Path, help="output folder")
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args()

    run_dirs = args.runs or _batch_runs(args.batch or _latest_batch())
    metrics = [run_metrics(d) for d in run_dirs]
    metrics = [m for m in metrics if m.status in ("ok", None)]
    if not metrics:
        raise SystemExit("no finished runs to compare")

    out = args.out or RESULTS / "comparison" / f"{datetime.now():%Y%m%d_%H%M%S}"
    out.mkdir(parents=True, exist_ok=True)
    write_metrics_csv(metrics, out / "metrics.csv")
    report = build_report(metrics, out, figures=not args.no_figures)
    (out / "report.md").write_text(report)
    print(report)
    print(f"Written to {out}")
    return 0


# ---------------------------------------------------------------------------
# The report
# ---------------------------------------------------------------------------


def build_report(metrics: list[RunMetrics], out: Path, *, figures: bool = True) -> str:
    """The report text; writes fit.csv and, if asked, the figures into ``out``."""
    groups = _group(metrics)
    engines = [e for e in ENGINES if any(k[0] == e for k in groups)]
    comparisons = {key: compare(key[1], runs) for key, runs in groups.items()}
    _write_fit_csv(comparisons, out / "fit.csv")

    lines = [
        "# LLM vs rule-based decisions on the Proulx (1991) drills",
        "",
        _runs_line(groups, engines),
        "",
        "Times are seconds after the alarm; simulated values are means over seeds "
        "(± standard deviation). See `analysis/metrics.py` for how each is measured.",
        "",
    ]
    lines += _fit_section(comparisons, engines)
    lines += _cost_section(groups, engines)
    lines += _authoring_section(metrics, engines)
    lines += _variability_section(groups, comparisons, engines)
    if figures:
        lines += _figures(groups, comparisons, engines, out)
    return "\n".join(lines) + "\n"


def _fit_section(comparisons, engines) -> list[str]:
    lines = ["## 1. Fit to Proulx", ""]
    header = "| Scenario | Measure | Proulx | " + " | ".join(engines) + " |"
    lines += [header, "|---|---|---:|" + "---:|" * len(engines)]
    for scenario in SCENARIOS:
        for i, measure in enumerate(MEASURES):
            cells = []
            target = None
            for engine in engines:
                c = _find(comparisons, engine, scenario, measure)
                if c is None:
                    cells.append("—")
                    continue
                target = c.target
                never = f" ({c.never}/{c.runs} never)" if c.never else ""
                cells.append(f"{c.simulated:.0f} ± {c.spread:.0f}{never}")
            if all(cell == "—" for cell in cells):
                continue
            tgt = "never" if target is None else f"{target:.0f}"
            lines.append(
                f"| {scenario if i == 0 else ''} | {MEASURE_LABELS[measure]} | {tgt} | "
                + " | ".join(cells)
                + " |"
            )
    lines += ["", "| | " + " | ".join(engines) + " |", "|---|" + "---:|" * len(engines)]
    for label, scenarios in (
        (f"RMSE, fitting scenarios ({', '.join(TRAIN)})", TRAIN),
        (f"RMSE, held out ({', '.join(HELD_OUT)})", HELD_OUT),
        ("RMSE, all", SCENARIOS),
    ):
        cells = []
        for engine in engines:
            cs = [
                c
                for (e, s), cl in comparisons.items()
                if e == engine and s in scenarios
                for c in cl
            ]
            cells.append(f"{rmse(cs):.0f} s" if cs else "—")
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    cells = []
    for engine in engines:
        clearance = {
            s: c.simulated
            for (e, s), cl in comparisons.items()
            if e == engine
            for c in cl
            if c.measure == "clearance_s"
        }
        cells.append(f"{ordering_tau(clearance):+.2f}" if len(clearance) > 1 else "—")
    lines.append("| Kendall tau, E1–E5 clearance order | " + " | ".join(cells) + " |")
    lines += [
        "",
        "The rule-based engine's response delays were fitted on E1, E3 and E5 "
        "(`monument fit`); E2 and E4 test it on drills it was not fitted to.",
        "",
    ]
    return lines


def _cost_section(groups, engines) -> list[str]:
    lines = [
        "## 2. Cost and runtime",
        "",
        "| Per run (mean) | " + " | ".join(engines) + " |",
        "|---|" + "---:|" * len(engines),
    ]
    rows = [
        ("wall time (s)", lambda m: m.wall_time_s or 0, "{:.0f}"),
        ("decisions", lambda m: m.decisions, "{:.0f}"),
        ("LLM requests", lambda m: m.llm_requests, "{:.0f}"),
        ("LLM tokens", lambda m: m.llm_tokens, "{:,.0f}"),
        ("LLM cost (£)", lambda m: m.llm_cost_gbp, "{:.2f}"),
        ("repaired decisions", lambda m: m.repairs, "{:.1f}"),
        ("fallback decisions", lambda m: m.fallbacks, "{:.1f}"),
    ]
    for label, get, fmt in rows:
        cells = []
        for engine in engines:
            runs = [m for (e, _), ms in groups.items() if e == engine for m in ms]
            cells.append(fmt.format(statistics.fmean(get(m) for m in runs)) if runs else "—")
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    totals = []
    for engine in engines:
        runs = [m for (e, _), ms in groups.items() if e == engine for m in ms]
        hours = sum(m.wall_time_s or 0 for m in runs) / 3600
        cost = sum(m.llm_cost_gbp for m in runs)
        totals.append(f"{len(runs)} runs, {hours:.1f} h, £{cost:.2f}")
    lines += ["| **all runs** | " + " | ".join(totals) + " |", ""]
    return lines


def _authoring_section(metrics: list[RunMetrics], engines) -> list[str]:
    lines = [
        "## 3. Authoring effort",
        "",
        "| | " + " | ".join(engines) + " |",
        "|---|" + "---:|" * len(engines),
    ]
    written = {e: authored_inputs(e, metrics) for e in engines}
    for key, label in (
        ("engine_parameters", "engine parameters"),
        ("cue_annotations", "cue annotations in the scenarios"),
        ("prompt_lines", "prompt template lines"),
    ):
        lines.append(f"| {label} | " + " | ".join(str(written[e][key]) for e in engines) + " |")
    log = read_log()
    for label, get in (
        ("logged manual work (h)", lambda rows: sum(float(r["minutes"] or 0) for r in rows) / 60),
        ("manual iterations", lambda rows: sum(r["kind"] == "manual" for r in rows)),
        ("automatic fits", lambda rows: sum(r["kind"] == "fit" for r in rows)),
        ("calibration runs", lambda rows: sum(int(r["runs"] or 0) for r in rows)),
        (
            "calibration compute (h)",
            lambda rows: sum(float(r["compute_s"] or 0) for r in rows) / 3600,
        ),
    ):
        cells = []
        for engine in engines:
            value = get([r for r in log if r["engine"] == engine])
            cells.append(f"{value:.1f}" if isinstance(value, float) else str(value))
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "Cue annotations (`cue`, `zone_cues`, `cues_by_zone`) tell the rule engine how "
        "strong each warning is; the LLM reads the messages themselves. Logged work is "
        "from `experiments/authoring_log.csv` (`monument log`, `monument fit`).",
        "",
    ]
    return lines


def _variability_section(groups, comparisons, engines) -> list[str]:
    lines = [
        "## 4. Variability",
        "",
        "Spread across seeds is the ± in section 1. Coefficient of variation of the "
        "time to clear (SD / mean; — if a run never cleared), and the entropy of the actions chosen after the "
        "alarm (bits; higher = a more varied mix):",
        "",
        "| Scenario | "
        + " | ".join(f"{e} CV" for e in engines)
        + " | "
        + " | ".join(f"{e} entropy" for e in engines)
        + " |",
        "|---|" + "---:|" * (2 * len(engines)),
    ]
    for scenario in SCENARIOS:
        cv, ent = [], []
        for engine in engines:
            c = _find(comparisons, engine, scenario, "clearance_s")
            # Not defined when a run never cleared (its time is only a lower bound).
            cv.append(f"{c.spread / c.simulated:.2f}" if c and c.simulated and not c.never else "—")
            runs = groups.get((engine, scenario), [])
            ent.append(
                f"{statistics.fmean(m.action_entropy_bits for m in runs):.2f}" if runs else "—"
            )
        lines.append(f"| {scenario} | " + " | ".join(cv + ent) + " |")
    lines += ["", "Sample reasons given after the alarm (E3 if run, first seed):", ""]
    for engine in engines:
        scenario = next((s for s in ["E3", *SCENARIOS] if groups.get((engine, s))), None)
        if scenario is None:
            continue
        runs = sorted(groups[(engine, scenario)], key=lambda m: m.seed or 0)
        lines.append(f"**{engine}** ({scenario}, seed {runs[0].seed})")
        lines.append("")
        for reason in sample_rationales(Path(runs[0].run_dir), n=4):
            lines.append(f"- {reason}")
        lines.append("")
    return lines


def _figures(groups, comparisons, engines, out: Path) -> list[str]:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return ["(matplotlib not installed: no figures)", ""]

    colours = {"rule_based": "tab:blue", "llm": "tab:orange"}
    fig, axes = plt.subplots(1, len(SCENARIOS), figsize=(4 * len(SCENARIOS), 3.4), sharey=True)
    for ax, scenario in zip(axes, SCENARIOS, strict=True):
        for engine in engines:
            curves = [remaining_curve(Path(m.run_dir)) for m in groups.get((engine, scenario), [])]
            curves = [c for c in curves if c[0]]
            if not curves:
                continue
            n = min(len(c[0]) for c in curves)
            t = [x / 60 for x in curves[0][0][:n]]
            ys = [c[1][:n] for c in curves]
            mean = [statistics.fmean(col) for col in zip(*ys, strict=True)]
            ax.fill_between(
                t,
                [min(col) for col in zip(*ys, strict=True)],
                [max(col) for col in zip(*ys, strict=True)],
                color=colours[engine],
                alpha=0.2,
            )
            ax.plot(t, mean, color=colours[engine], label=engine)
        c = _find(comparisons, engines[0], scenario, "clearance_s")
        if c and c.target:
            ax.axvline(c.target / 60, color="k", ls="--", lw=1, label="Proulx clear")
        ax.set_title(scenario)
        ax.set_xlabel("minutes after alarm")
    axes[0].set_ylabel("share of passengers still inside")
    axes[-1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "remaining.png", dpi=120)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
    for ax, measure in zip(axes, ("start_move_concourse_s", "start_move_platform_s"), strict=True):
        width = 0.8 / (len(engines) + 1)
        labelled: set[str] = set()

        def label(name: str, labelled: set[str] = labelled) -> str | None:
            if name in labelled:
                return None
            labelled.add(name)
            return name

        for i, scenario in enumerate(SCENARIOS):
            c0 = next((c for e in engines if (c := _find(comparisons, e, scenario, measure))), None)
            if c0 and c0.target is not None:
                ax.bar(i, c0.target / 60, width, color="0.6", label=label("Proulx"))
            for j, engine in enumerate(engines, start=1):
                c = _find(comparisons, engine, scenario, measure)
                if c:
                    ax.bar(
                        i + j * width,
                        c.simulated / 60,
                        width,
                        yerr=c.spread / 60,
                        color=colours[engine],
                        label=label(engine),
                    )
        ax.set_xticks([i + width * len(engines) / 2 for i in range(len(SCENARIOS))], SCENARIOS)
        ax.set_title(MEASURE_LABELS[measure])
    axes[0].set_ylabel("minutes after alarm")
    axes[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "start_to_move.png", dpi=120)
    plt.close(fig)
    return [
        "## Figures",
        "",
        "![Passengers remaining](remaining.png)",
        "",
        "![Time to start to move](start_to_move.png)",
        "",
    ]


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------


def authored_inputs(engine: str, metrics: list[RunMetrics]) -> dict[str, int]:
    """How much each engine needs written, from one of its runs' manifests.

    ``engine_parameters``: settings of the decision section;
    ``cue_annotations``: warning-cue labels in the scenarios (rule engine only);
    ``prompt_lines``: non-blank lines of the prompt templates (LLM only).
    """
    runs = [m for m in metrics if m.engine == engine]
    params = (manifest(Path(runs[0].run_dir)) or {}).get("parameters", {}) if runs else {}
    decision = {k: v for k, v in params.get("decision", {}).items() if k != "engine"}
    if engine == "llm":
        decision = params.get("llm", {})
    cues = 0
    if engine == "rule_based":
        for scenario in {m.scenario for m in runs}:
            run = next(m for m in runs if m.scenario == scenario)
            cues += count_cue_annotations((manifest(Path(run.run_dir)) or {}).get("parameters", {}))
    prompt_lines = 0
    if engine == "llm":
        prompt_lines = _prompt_lines(params.get("prompts", {}).get("decision_prompt_template_path"))
    return {
        "engine_parameters": _count_leaves(decision),
        "cue_annotations": cues,
        "prompt_lines": prompt_lines,
    }


def count_cue_annotations(params: dict) -> int:
    """Cue labels in a run's events and staff systems."""
    count = 0
    for event in params.get("events", []):
        count += bool(event.get("cue")) + len(event.get("zone_cues") or {})
    for system in (params.get("systems") or {}).values():
        for phase in system.get("phases", []) if isinstance(system, dict) else []:
            count += len(phase.get("cues_by_zone") or {})
    return count


def sample_rationales(run_dir: Path, n: int = 4, seed: int = 0) -> list[str]:
    """``n`` distinct post-alarm reasons from a run, picked reproducibly."""
    alarm = alarm_time_s(run_dir)
    reasons = sorted(
        {
            r["rationale"].strip()
            for r in read_csv(run_dir / "decisions.csv")
            if float(r["time_s"]) >= alarm and r.get("rationale", "").strip()
        }
    )
    picked = random.Random(seed).sample(reasons, min(n, len(reasons)))
    return [p if len(p) <= 240 else p[:237] + "..." for p in picked]


def remaining_curve(run_dir: Path, step_s: float = 5.0) -> tuple[list[float], list[float]]:
    """Share of the passengers present at the alarm still inside, every ``step_s``."""
    m = manifest(run_dir) or {}
    alarm = alarm_time_s(run_dir)
    end = float(m.get("results", {}).get("sim_time_s") or 0)
    passengers = {r["agent_id"] for r in read_csv(run_dir / "decisions.csv")}
    present = [a for a in levels_at(run_dir, alarm) if a in passengers]
    if not present or end <= alarm:
        return [], []
    left = {
        r["agent_id"]: float(r["time_s"]) - alarm
        for r in read_csv(run_dir / "exit_log.csv")
        if r["agent_id"] in present
    }
    times, shares = [], []
    t = 0.0
    while t <= end - alarm:
        times.append(t)
        shares.append(sum(1 for a in present if left.get(a, float("inf")) > t) / len(present))
        t += step_s
    return times, shares


def _group(metrics: list[RunMetrics]) -> dict[tuple[str, str], list[RunMetrics]]:
    groups: dict[tuple[str, str], list[RunMetrics]] = defaultdict(list)
    for m in metrics:
        if m.engine and m.scenario in SCENARIOS:
            groups[(m.engine, m.scenario)].append(m)
    return dict(groups)


def _find(comparisons, engine, scenario, measure) -> Comparison | None:
    return next((c for c in comparisons.get((engine, scenario), []) if c.measure == measure), None)


def _runs_line(groups, engines) -> str:
    parts = []
    for engine in engines:
        n = {s: len(groups.get((engine, s), [])) for s in SCENARIOS}
        parts.append(f"{engine}: " + ", ".join(f"{s}×{k}" for s, k in n.items() if k))
    return "Runs — " + "; ".join(parts) + "."


def _write_fit_csv(comparisons, path: Path) -> None:
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "engine",
                "scenario",
                "measure",
                "proulx_s",
                "simulated_s",
                "sd_s",
                "never",
                "runs",
                "error_s",
            ]
        )
        for (engine, scenario), cs in sorted(comparisons.items()):
            for c in cs:
                writer.writerow(
                    [
                        engine,
                        scenario,
                        c.measure,
                        c.target,
                        round(c.simulated, 1),
                        round(c.spread, 1),
                        c.never,
                        c.runs,
                        round(c.error, 1),
                    ]
                )


def _count_leaves(node) -> int:
    if isinstance(node, dict):
        return sum(_count_leaves(v) for v in node.values())
    return 1


def _prompt_lines(template_path: str | None) -> int:
    from evacusim.decision.llm_prompt import DEFAULT_TEMPLATE

    path = Path(template_path) if template_path else DEFAULT_TEMPLATE
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text().splitlines() if line.strip())


def _latest_batch() -> Path:
    batches = sorted((RESULTS / "batches").glob("proulx_comparison_*"))
    if not batches:
        raise SystemExit("no proulx_comparison batch in results/batches; pass --batch or --runs")
    return batches[-1]


def _batch_runs(batch_dir: Path) -> list[Path]:
    summary = json.loads((batch_dir / "summary.json").read_text())
    return [Path(j["run_dir"]) for j in summary["jobs"] if j.get("run_dir") and j["exit_code"] == 0]


if __name__ == "__main__":
    raise SystemExit(main())
