"""Finding runs, resolving scenario names and expanding batches (no simulation)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from monument_evacuation.analysis import runs
from monument_evacuation.batch import load_jobs
from monument_evacuation.paths import engine_config, scenario_config


def make_run(root: Path, scenario: str, name: str, manifest: dict | None = None) -> Path:
    run = root / scenario / name
    run.mkdir(parents=True)
    if manifest is not None:
        (run / "manifest.json").write_text(json.dumps(manifest))
    return run


def test_runs_are_newest_first_and_filtered_by_engine(tmp_path: Path) -> None:
    old = make_run(tmp_path, "E1", "run_20260401_120000")  # before manifests
    rule = make_run(tmp_path, "E1", "run_20261009_120000_rule_based_s0", {"engine": "rule_based"})
    llm = make_run(tmp_path, "E1", "run_20261009_130000_llm_s0", {"engine": "llm"})
    assert runs.find_runs("E1", results_dir=tmp_path) == [llm, rule, old]
    assert runs.latest_run("E1", "rule_based", tmp_path) == rule
    assert runs.latest_run("E9", results_dir=tmp_path) is None


def test_frames_file_new_and_old_names(tmp_path: Path) -> None:
    run = make_run(tmp_path, "E1", "run_x")
    (run / "agent_decisions_history.jsonl").write_text("")
    assert runs.frames_path(run).name == "agent_decisions_history.jsonl"
    (run / "frames.jsonl").write_text("")
    assert runs.frames_path(run).name == "frames.jsonl"


def test_alarm_time_comes_from_the_first_warning_event(tmp_path: Path) -> None:
    events = [
        {"time": 10.0, "type": "train_arrival"},
        {"time": 15.0, "message": "alarm", "cue": {"strength": "weak"}},
        {"time": 40.0, "type": "pa_announcement", "cue": {"strength": "medium"}},
    ]
    run = make_run(tmp_path, "E1", "run_x", {"parameters": {"events": events}})
    assert runs.alarm_time_s(run) == 15.0
    assert runs.alarm_time_s(make_run(tmp_path, "E1", "run_old")) == runs.DEFAULT_ALARM_TIME_S


def test_scenario_and_engine_names_resolve() -> None:
    assert scenario_config("E3").name == "E3.yaml"
    assert scenario_config("normal_day").parent.name == "calibration"
    assert engine_config("rule_based").name == "rule_based.yaml"
    with pytest.raises(FileNotFoundError, match="known"):
        scenario_config("E9")


def test_batch_expands_scenarios_engines_and_seeds(tmp_path: Path) -> None:
    batch = tmp_path / "b.yaml"
    batch.write_text("scenarios: [E1, E2]\nengines: [rule_based, llm]\nseeds: [0, 1, 2]\n")
    jobs = load_jobs(batch)
    assert len(jobs) == 12
    assert jobs[0].name == "E1_rule_based_s0"
    assert jobs[-1].name == "E2_llm_s2"
