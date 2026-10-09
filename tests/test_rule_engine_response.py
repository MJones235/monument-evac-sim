"""The rule engine responds to warnings as Proulx (1991) observed, qualitatively.

A detailed PA (E5) gets people moving much sooner than the alarm alone (E1).
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
ALARM_TIME_S = 15.0


def _start_to_move_times(experiment: str, tmp_path: Path) -> list[float]:
    """Seconds after the alarm at which each agent began evacuating (rule engine)."""
    config = tmp_path / f"{experiment}.yaml"
    config.write_text(
        f"extends: {REPO_ROOT / 'experiments' / experiment / 'config.yaml'}\n"
        "decision:\n  engine: rule_based\n"
    )
    out = tmp_path / experiment
    proc = subprocess.run(
        [
            sys.executable,
            "run_experiment.py",
            str(config),
            "--agents",
            "40",
            "--max-steps",
            "3000",
            "--output-dir",
            str(out),
            "--no-viewer",
            "--no-spatial-viewer",
            "--no-video",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    (run_dir,) = out.iterdir()
    decisions = json.loads((run_dir / "agent_decisions.json").read_text())["agent_decisions"]
    return [
        min(d["time"] for d in agent["decisions"] if d.get("stage") == "evacuating") - ALARM_TIME_S
        for agent in decisions.values()
        if any(d.get("stage") == "evacuating" for d in agent["decisions"])
    ]


@pytest.mark.integration
def test_detailed_pa_gets_people_moving_sooner_than_the_alarm_alone(tmp_path: Path) -> None:
    alarm_only = _start_to_move_times("E1", tmp_path)
    detailed_pa = _start_to_move_times("E5", tmp_path)
    assert len(detailed_pa) > 2 * max(1, len(alarm_only))
    assert sorted(detailed_pa)[len(detailed_pa) // 2] < 120.0


@pytest.mark.integration
def test_evacuating_people_never_head_down_to_the_platforms(tmp_path: Path) -> None:
    """Leaving means going up and out, unless told to board a train.

    Agents used to be offered only the exits they could see; one who saw only
    a down escalator took it, then bounced between levels.
    """
    config = tmp_path / "E2.yaml"
    config.write_text(
        f"extends: {REPO_ROOT / 'experiments' / 'E2' / 'config.yaml'}\n"
        "decision:\n  engine: rule_based\n"
    )
    out = tmp_path / "out"
    proc = subprocess.run(
        [
            sys.executable,
            "run_experiment.py",
            str(config),
            "--max-steps",
            "4000",
            "--output-dir",
            str(out),
            "--no-viewer",
            "--no-spatial-viewer",
            "--no-video",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    (run_dir,) = out.iterdir()
    rows = list(csv.DictReader((run_dir / "decisions.csv").open()))
    downward = [
        r
        for r in rows
        if r["stage"] == "evacuating" and r["exit_id"] in ("escalator_a_down", "escalator_d_down")
    ]
    assert not downward, downward[:3]
