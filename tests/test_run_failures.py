"""A run that fails must say so: non-zero exit, and partial outputs kept.

The physics step is made to raise part-way through a short real run.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

INJECT_FAILURE = """
import runpy, sys
from evacusim.jps.multi_level_simulation import MultiLevelJuPedSimulation
original = MultiLevelJuPedSimulation.step
def failing_step(self):
    if self.current_step == 50:
        raise RuntimeError("injected physics failure")
    return original(self)
MultiLevelJuPedSimulation.step = failing_step
sys.argv = ["run_experiment.py", *sys.argv[1:]]
runpy.run_path("run_experiment.py", run_name="__main__")
"""


@pytest.mark.integration
def test_physics_failure_exits_non_zero_and_keeps_partial_outputs(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            INJECT_FAILURE,
            "experiments/RuleBased/config.yaml",
            "--agents",
            "10",
            "--max-steps",
            "400",
            "--output-dir",
            str(tmp_path),
            "--no-viewer",
            "--no-spatial-viewer",
            "--no-video",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    log = proc.stdout + proc.stderr
    assert proc.returncode != 0, "a failed simulation exited 0"
    assert "injected physics failure" in log
    assert "Simulation FAILED" in log
    (run_dir,) = tmp_path.iterdir()
    assert (run_dir / "population_timeseries.csv").exists()
    assert (run_dir / "agent_decisions.json").exists()
