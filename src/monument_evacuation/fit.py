"""Fit a decision engine's parameters to Proulx (1991): ``monument fit``.

A fit file (``experiments/fits/*.yaml``) names the engine, the training and
held-out scenarios, the seeds, and the parameters to search with their
ranges. Each trial:

1. writes the trial's parameters as a config overlay,
2. runs every training scenario with every seed (``monument run --overlay``),
3. measures the runs (``analysis.metrics``) and scores them against Proulx
   Table 1 (``analysis.proulx_fit``: RMSE in seconds).

Optuna's TPE sampler proposes the trials. The best parameters are then run
on all scenarios (training and held out) with fresh seeds, so the reported
error is not flattered by the seeds the search happened to use.

Everything goes to ``results/fits/<fit>_<time>/``:

- ``trials.csv``: every trial's parameters, loss and per-measure errors;
- ``best.yaml``: the best parameters as an overlay (copy into
  ``experiments/engines/<engine>.yaml`` to adopt them);
- ``validation/``: the validation runs and ``metrics.csv``;
- ``report.md``: training and held-out error per scenario and measure.

The search is logged to the authoring log (``authoring.py``).
"""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from monument_evacuation.analysis.metrics import RunMetrics, run_metrics, write_metrics_csv
from monument_evacuation.analysis.proulx_fit import Comparison, compare, ordering_tau, rmse
from monument_evacuation.authoring import log_entry
from monument_evacuation.batch import run_command
from monument_evacuation.paths import REPO_ROOT, RESULTS


@dataclass
class FitSpec:
    """A fit file."""

    name: str
    engine: str
    train: list[str]
    held_out: list[str]
    seeds: list[int]
    validation_seeds: list[int]
    trials: int
    sampler_seed: int
    parameters: dict[str, dict[str, Any]]

    @classmethod
    def load(cls, path: Path) -> FitSpec:
        spec = yaml.safe_load(Path(path).read_text())
        for key, space in spec["parameters"].items():
            if "choices" not in space and not {"low", "high"} <= set(space):
                raise ValueError(f"{path}: {key} needs low/high or choices")
        return cls(
            name=Path(path).stem,
            engine=spec["engine"],
            train=list(spec["train"]),
            held_out=list(spec.get("held_out", [])),
            seeds=[int(s) for s in spec["seeds"]],
            validation_seeds=[int(s) for s in spec.get("validation_seeds", spec["seeds"])],
            trials=int(spec["trials"]),
            sampler_seed=int(spec.get("sampler_seed", 0)),
            parameters=spec["parameters"],
        )


def overlay(params: dict[str, Any]) -> dict[str, Any]:
    """Dotted keys as a nested config: ``{"a.b": 1}`` -> ``{"a": {"b": 1}}``."""
    nested: dict[str, Any] = {}
    for dotted, value in params.items():
        node = nested
        *parents, leaf = dotted.split(".")
        for key in parents:
            node = node.setdefault(key, {})
        node[leaf] = value
    return nested


def run_fit(
    fit_file: Path,
    *,
    jobs: int = 1,
    trials: int | None = None,
    run_args: list[str] = (),
    log: bool = True,
) -> int:
    """Run the search, validate the best trial, write the report. Returns 0.

    ``log=False`` leaves the authoring log alone (for trial runs of the tooling).
    """
    import optuna

    spec = FitSpec.load(fit_file)
    n_trials = trials or spec.trials
    out = RESULTS / "fits" / f"{spec.name}_{datetime.now():%Y%m%d_%H%M%S}"
    out.mkdir(parents=True)
    print(f"Fitting {spec.engine} on {spec.train}: {n_trials} trials, logs in {out}")
    started = time.time()
    total_runs = 0

    def objective(trial: optuna.Trial) -> float:
        nonlocal total_runs
        params = {key: _suggest(trial, key, space) for key, space in spec.parameters.items()}
        trial.set_user_attr("params", params)  # as run (rounded)
        trial_dir = out / "trials" / f"{trial.number:03d}"
        metrics = _run_all(
            spec, params, spec.train, spec.seeds, trial_dir, jobs=jobs, run_args=run_args
        )
        total_runs += len(metrics)
        comparisons = _compare(metrics, spec.train)
        loss = rmse(comparisons)
        _append_trial(out / "trials.csv", trial.number, params, loss, comparisons, metrics)
        shutil.rmtree(trial_dir / "runs", ignore_errors=True)  # keep metrics.csv only
        print(f"  trial {trial.number:3d}  RMSE {loss:7.1f} s  {_short(params)}")
        return loss

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(
        direction="minimize", sampler=optuna.samplers.TPESampler(seed=spec.sampler_seed)
    )
    study.optimize(objective, n_trials=n_trials, catch=(RuntimeError,))

    best = study.best_trial
    best_params = best.user_attrs["params"]
    (out / "best.yaml").write_text(
        f"# Best of {n_trials} trials (RMSE {best.value:.1f} s on {', '.join(spec.train)});\n"
        f"# from {out.relative_to(REPO_ROOT)}\n" + yaml.safe_dump(overlay(best_params))
    )

    print("Validating the best parameters on every scenario with fresh seeds")
    scenarios = spec.train + spec.held_out
    validation = _run_all(
        spec,
        best_params,
        scenarios,
        spec.validation_seeds,
        out / "validation",
        jobs=jobs,
        run_args=run_args,
    )
    total_runs += len(validation)
    write_metrics_csv(validation, out / "validation" / "metrics.csv")
    report = _report(spec, best.number, best_params, best.value, validation)
    (out / "report.md").write_text(report)
    print(report)

    compute_s = time.time() - started
    if not log:
        return 0
    log_entry(
        spec.engine,
        "fit",
        f"monument fit {fit_file.name}: {n_trials} trials; best RMSE {best.value:.0f} s "
        f"({out.relative_to(REPO_ROOT)})",
        runs=total_runs,
        compute_s=compute_s,
    )
    return 0


def _suggest(trial: Any, key: str, space: dict[str, Any]) -> Any:
    if "choices" in space:
        return trial.suggest_categorical(key, space["choices"])
    low, high = space["low"], space["high"]
    if isinstance(low, int) and isinstance(high, int) and not space.get("log"):
        return trial.suggest_int(key, low, high)
    return round(trial.suggest_float(key, float(low), float(high), log=space.get("log", False)), 3)


def _run_all(
    spec: FitSpec,
    params: dict[str, Any],
    scenarios: list[str],
    seeds: list[int],
    out: Path,
    *,
    jobs: int,
    run_args: list[str],
) -> list[RunMetrics]:
    """Run scenarios x seeds with ``params`` overlaid; measure every run that finished."""
    out.mkdir(parents=True, exist_ok=True)
    overlay_file = out / "parameters.yaml"
    overlay_file.write_text(yaml.safe_dump(overlay(params)))

    def one(job: tuple[str, int]) -> RunMetrics | None:
        scenario, seed = job
        run_root = out / "runs" / scenario
        args = ["--overlay", str(overlay_file), "--output-dir", str(run_root), *run_args]
        log = out / f"{scenario}_s{seed}.log"
        with log.open("w") as f:
            code = subprocess.run(
                run_command(scenario, spec.engine, seed, args),
                cwd=REPO_ROOT,
                stdout=f,
                stderr=subprocess.STDOUT,
            ).returncode
        run_dirs = sorted(run_root.glob(f"run_*_s{seed}*"))
        if code != 0 or not run_dirs:
            print(f"    {scenario} seed {seed} failed (exit {code}); see {log}")
            return None
        log.unlink()
        return run_metrics(run_dirs[-1])

    jobs_list = [(s, seed) for s in scenarios for seed in seeds]
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        results = [m for m in pool.map(one, jobs_list) if m is not None]
    write_metrics_csv(results, out / "metrics.csv")
    return results


def _compare(metrics: list[RunMetrics], scenarios: list[str]) -> list[Comparison]:
    comparisons: list[Comparison] = []
    for scenario in scenarios:
        runs = [m for m in metrics if m.scenario == scenario]
        if not runs:  # every run failed: the trial fails
            raise RuntimeError(f"no {scenario} run finished")
        comparisons += compare(scenario, runs)
    return comparisons


def _append_trial(
    path: Path,
    number: int,
    params: dict[str, Any],
    loss: float,
    comparisons: list[Comparison],
    metrics: list[RunMetrics],
) -> None:
    row: dict[str, Any] = {"trial": number, "rmse_s": round(loss, 2), "runs": len(metrics)}
    row.update(params)
    row.update({f"err_{c.scenario}_{c.measure}": round(c.error, 1) for c in comparisons})
    new = not path.exists()
    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row))
        if new:
            writer.writeheader()
        writer.writerow(row)


def _report(
    spec: FitSpec, number: int, params: dict[str, Any], loss: float, runs: list[RunMetrics]
) -> str:
    scenarios = spec.train + spec.held_out
    by_scenario = {s: [m for m in runs if m.scenario == s] for s in scenarios}
    comparisons = {s: compare(s, r) for s, r in by_scenario.items() if r}
    train = [c for s in spec.train for c in comparisons.get(s, [])]
    held = [c for s in spec.held_out for c in comparisons.get(s, [])]
    clearance = {
        s: next(c.simulated for c in cs if c.measure == "clearance_s")
        for s, cs in comparisons.items()
    }

    lines = [
        f"# Fit report: {spec.name} ({spec.engine})",
        "",
        f"Best of the search: trial {number}, RMSE {loss:.1f} s on {', '.join(spec.train)} "
        f"(seeds {spec.seeds}).",
        "",
        "```yaml",
        yaml.safe_dump(overlay(params)).rstrip(),
        "```",
        "",
        f"Validation with fresh seeds {spec.validation_seeds}:",
        "",
        f"- training ({', '.join(spec.train)}): RMSE **{rmse(train):.1f} s**",
        f"- held out ({', '.join(spec.held_out)}): RMSE **{rmse(held):.1f} s**"
        if held
        else "- held out: none",
        f"- E1-E5 clearance ordering vs Proulx: Kendall tau **{ordering_tau(clearance):+.2f}**",
        "",
        "| Scenario | Set | Measure | Proulx (s) | Simulated (s) | SD | Never | Error (s) |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for s in scenarios:
        role = "train" if s in spec.train else "held out"
        for c in comparisons.get(s, []):
            tgt = "never" if c.target is None else f"{c.target:.0f}"
            lines.append(
                f"| {s} | {role} | {c.measure} | {tgt} | {c.simulated:.0f} | {c.spread:.0f} "
                f"| {c.never}/{c.runs} | {c.error:+.0f} |"
            )
    lines += ["", "'Never': runs where it did not happen in the window (counted as the window)."]
    return "\n".join(lines) + "\n"


def _short(params: dict[str, Any]) -> str:
    return json.dumps({k.split(".")[-1]: v for k, v in params.items()})
