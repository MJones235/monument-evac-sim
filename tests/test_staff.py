"""Staff (E2's Revenue Control Inspectors) move and give directives that agents hear.

Staff stepping was silently disconnected for months; this guards against that.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.integration
def test_staff_patrol_and_directives_reach_agents(tmp_path: Path) -> None:
    config = tmp_path / "e2_rule_based.yaml"
    config.write_text(
        f"extends: {REPO_ROOT / 'experiments/E2/config.yaml'}\ndecision:\n  engine: rule_based\n"
    )
    proc = subprocess.run(
        [
            sys.executable,
            "run_experiment.py",
            str(config),
            "--agents",
            "30",
            "--max-steps",
            "3000",
            "--output-dir",
            str(tmp_path / "out"),
            "--no-viewer",
            "--no-spatial-viewer",
            "--no-video",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "(directive) →" in proc.stdout + proc.stderr, "no staff directive was given"

    (run_dir,) = (tmp_path / "out").iterdir()
    decisions = json.loads((run_dir / "agent_decisions.json").read_text())["agent_decisions"]
    cues = [c for a in decisions.values() for d in a["decisions"] for c in d.get("cue_types") or []]
    assert "staff_instruction" in cues, "no agent perceived a staff directive"

    frames = [json.loads(line) for line in (run_dir / "agent_decisions_history.jsonl").open()]
    path = [
        f["positions"]["rci_concourse_0"] for f in frames if "rci_concourse_0" in f["positions"]
    ]
    moved = ((path[-1][0] - path[0][0]) ** 2 + (path[-1][1] - path[0][1]) ** 2) ** 0.5
    assert moved > 10.0, "the patrolling inspector did not move"
