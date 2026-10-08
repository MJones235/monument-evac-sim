"""Golden-run regression tests: refactors must not change simulation behaviour.

Each case runs a short, real Monument simulation (full geometry, rule-based
engine, no LLM) and compares a fingerprint of its outputs with a committed
snapshot in ``tests/golden/``.

The fingerprint has two parts:

* ``sha256`` of each output file. An exact match proves the behaviour is
  unchanged, down to every agent position in every frame.
* ``summary``: human-readable counts (exits per street exit, final population
  row). When the hashes differ, this shows *how much* the behaviour changed.

Runs are deterministic given the config's ``seed``. ``PYTHONHASHSEED`` is
deliberately *not* fixed, so each test run also checks that no behaviour
depends on Python's per-process string-hash randomisation.

Usage::

    pytest -m golden                      # check against snapshots (~1 min)
    UPDATE_GOLDEN=1 pytest -m golden      # re-record after an intended change

Re-record only when a behaviour change is intended, and say why in the commit.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DIR = Path(__file__).parent / "golden"

# Outputs whose bytes must not change. Files that embed wall-clock timings or
# run paths (simulation.log, performance_report.txt, ...) are deliberately
# excluded.
FINGERPRINTED_FILES = (
    "exit_log.csv",
    "population_timeseries.csv",
    "escalator_log.csv",
    "agent_decisions_history.jsonl",  # per-frame agent positions
    "route_changes.txt",
    "calibration_arrivals.csv",  # calibration runs only
    "llm_prompt_log.jsonl",  # LLM runs only: every prompt and response
)

CASES = {
    # Evacuation scenario, rule-based engine: 20 agents for 200 s (dt 0.05).
    "rule_based_evacuation": [
        "experiments/RuleBased/config.yaml",
        "--agents",
        "20",
        "--max-steps",
        "4000",
    ],
    # Normal operations at the morning peak: 08:00-08:10 (dt 0.1). Exercises
    # Poisson arrivals, timetabled trains, escalators and all street exits.
    "calibration_peak_window": [
        "experiments/Calibration/config.yaml",
        "--start-time",
        "08:00",
        "--max-steps",
        "6000",
    ],
    # The LLM decision pipeline (prompts, Concordia agents, cache, schema
    # repair) on E4: zone PA, staff and trains. evacusim's deterministic fake
    # model stands in for the LLM, so this costs nothing and is reproducible.
    "llm_pipeline_e4": [
        "tests/golden/configs/llm_fake_e4.yaml",
        "--fake-llm",
        "--agents",
        "30",
        "--max-steps",
        "3000",
    ],
}


def _run_case(args: list[str], output_dir: Path) -> Path:
    """Run one simulation headless and return its run directory."""
    env = {k: v for k, v in os.environ.items() if k != "PYTHONHASHSEED"}
    cmd = [
        sys.executable,
        "run_experiment.py",
        *args,
        "--output-dir",
        str(output_dir),
        "--no-viewer",
        "--no-spatial-viewer",
        "--no-video",
    ]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, env=env, capture_output=True, text=True)
    assert proc.returncode == 0, f"simulation failed:\n{proc.stderr[-3000:]}"
    run_dirs = sorted(p for p in output_dir.iterdir() if p.is_dir())
    assert len(run_dirs) == 1, f"expected one run directory, found {run_dirs}"
    return run_dirs[0]


def _fingerprint(run_dir: Path) -> dict:
    """Hash the behavioural outputs of a run and summarise them."""
    hashes = {
        name: hashlib.sha256((run_dir / name).read_bytes()).hexdigest()
        for name in FINGERPRINTED_FILES
        if (run_dir / name).exists()
    }
    with open(run_dir / "exit_log.csv", newline="") as f:
        exits = Counter(row["exit_name"] for row in csv.DictReader(f))
    with open(run_dir / "population_timeseries.csv", newline="") as f:
        rows = list(csv.reader(f))
    return {
        "sha256": hashes,
        "summary": {
            "exits": dict(sorted(exits.items())),
            "population_header": rows[0],
            "population_final_row": rows[-1],
        },
    }


@pytest.mark.golden
@pytest.mark.parametrize("case", sorted(CASES))
def test_golden_run(case: str, tmp_path: Path) -> None:
    actual = _fingerprint(_run_case(CASES[case], tmp_path))
    snapshot = SNAPSHOT_DIR / f"{case}.json"

    if os.environ.get("UPDATE_GOLDEN") == "1":
        SNAPSHOT_DIR.mkdir(exist_ok=True)
        snapshot.write_text(json.dumps(actual, indent=2) + "\n")
        pytest.skip(f"re-recorded {snapshot.name}")

    assert snapshot.exists(), f"no snapshot; record one with UPDATE_GOLDEN=1 ({snapshot})"
    expected = json.loads(snapshot.read_text())
    assert actual["summary"] == expected["summary"], "behaviour changed (see summary diff)"
    assert actual["sha256"] == expected["sha256"], (
        "summary unchanged but outputs differ: agent paths or timings moved"
    )
