"""Run a matrix of scenarios x decision engines x seeds.

A batch file (``experiments/batches/*.yaml``)::

    scenarios: [E1, E2, E3, E4, E5]
    engines: [rule_based, llm]
    seeds: [0, 1, 2]

Each combination runs as its own ``monument run`` process (several at once
with ``--jobs``). Logs and a ``summary.json`` (exit status, duration and run
directory of every job) go to ``results/batches/<batch>_<time>/``.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime
from itertools import product
from pathlib import Path

import yaml

from monument_evacuation.paths import REPO_ROOT, RESULTS


@dataclass
class Job:
    scenario: str
    engine: str
    seed: int
    exit_code: int | None = None
    duration_s: float | None = None
    run_dir: str | None = None

    @property
    def name(self) -> str:
        return f"{self.scenario}_{self.engine}_s{self.seed}"


def load_jobs(batch_file: Path) -> list[Job]:
    """The jobs a batch file describes, in scenario, engine, seed order."""
    spec = yaml.safe_load(batch_file.read_text()) or {}
    missing = {"scenarios", "engines", "seeds"} - set(spec)
    if missing:
        raise ValueError(f"{batch_file}: missing {', '.join(sorted(missing))}")
    return [
        Job(scenario, engine, int(seed))
        for scenario, engine, seed in product(spec["scenarios"], spec["engines"], spec["seeds"])
    ]


def run_batch(
    batch_file: Path, *, jobs: int = 1, dry_run: bool = False, run_args: list[str] = ()
) -> int:
    """Run every job; return 0 if all succeeded, else 1.

    ``run_args`` are passed to every ``monument run`` (e.g. ``--max-steps``).
    """
    todo = load_jobs(batch_file)
    if dry_run:
        for job in todo:
            print(job.name)
        print(f"{len(todo)} runs")
        return 0

    out = RESULTS / "batches" / f"{batch_file.stem}_{datetime.now():%Y%m%d_%H%M%S}"
    out.mkdir(parents=True)
    print(f"{len(todo)} runs, {jobs} at a time; logs in {out}")

    def run(job: Job) -> Job:
        cmd = run_command(job.scenario, job.engine, job.seed, run_args)
        started = time.time()
        with (out / f"{job.name}.log").open("w") as log:
            job.exit_code = subprocess.run(
                cmd, cwd=REPO_ROOT, stdout=log, stderr=subprocess.STDOUT
            ).returncode
        job.duration_s = round(time.time() - started, 1)
        job.run_dir = _find_run_dir(job, started)
        status = "ok" if job.exit_code == 0 else f"FAILED (exit {job.exit_code})"
        print(f"  {job.name:28s} {status:18s} {job.duration_s:7.0f} s  {job.run_dir or ''}")
        return job

    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        done = list(pool.map(run, todo))

    (out / "summary.json").write_text(
        json.dumps({"batch": str(batch_file), "jobs": [asdict(j) for j in done]}, indent=2) + "\n"
    )
    failed = [j.name for j in done if j.exit_code != 0]
    print(
        f"{len(done) - len(failed)}/{len(done)} succeeded"
        + (f"; failed: {failed}" if failed else "")
    )
    return 1 if failed else 0


def run_command(scenario: str, engine: str, seed: int, run_args: list[str] = ()) -> list[str]:
    """The command line for one ``monument run`` in a fresh Python process."""
    return [
        sys.executable,
        "-m",
        "monument_evacuation",
        "run",
        scenario,
        "--engine",
        engine,
        "--seed",
        str(seed),
        *run_args,
    ]


def _find_run_dir(job: Job, started: float) -> str | None:
    """The directory the job's run created (also for a run that failed)."""
    pattern = f"run_*_{job.engine}_s{job.seed}*"
    candidates = [
        d for d in (RESULTS / job.scenario).glob(pattern) if d.stat().st_mtime >= started - 1
    ]
    return str(max(candidates, key=lambda d: d.stat().st_mtime)) if candidates else None
