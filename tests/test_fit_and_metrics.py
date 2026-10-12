"""Unit tests for the run measures, the Proulx score, the fit helpers and the authoring log."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from monument_evacuation.analysis.compare_engines import count_cue_annotations, remaining_curve
from monument_evacuation.analysis.metrics import half_time, run_metrics, start_times
from monument_evacuation.analysis.proulx_fit import E1_EXERCISE_END_S, compare, ordering_tau, rmse
from monument_evacuation.authoring import log_entry, read_log
from monument_evacuation.fit import FitSpec, overlay
from monument_evacuation.paths import EXPERIMENTS

DOWN = {"escalator_d_down"}


def _decision(t, agent, action, exit_id=""):
    return {"time_s": str(t), "agent_id": agent, "action": action, "exit_id": exit_id}


# -- when a crowd started to move ----------------------------------------------


def test_half_time_needs_half_the_crowd():
    assert half_time([10.0, None, 30.0, None]) == 30.0
    assert half_time([None, None, 5.0]) is None
    assert half_time([]) is None


def test_start_is_the_final_outbound_run():
    decisions = [
        _decision(0, "a", "evacuate", "escalator_b_up"),  # leaving, then stops
        _decision(15, "a", "wait"),
        _decision(40, "a", "evacuate", "escalator_b_up"),
        _decision(70, "a", "evacuate", "blackett_street"),
        _decision(0, "b", "evacuate", "escalator_d_down"),  # a journey down: not leaving
        _decision(30, "b", "wait"),
        _decision(0, "c", "wait"),  # boards a waiting train without deciding to
        _decision(0, "d", "seek_information"),  # never leaves
        _decision(20, "e", "leave_by_train"),
    ]
    starts = start_times(decisions, {"c": 50.0}, DOWN)
    assert starts == {"a": 40.0, "b": None, "c": 50.0, "d": None, "e": 20.0}


def _write_run(tmp_path: Path) -> Path:
    """A tiny finished run: alarm at 15 s, two on the concourse, two on a platform."""
    run = tmp_path / "E5" / "run_x_rule_based_s0"
    run.mkdir(parents=True, exist_ok=True)
    (run / "manifest.json").write_text(
        json.dumps(
            {
                "status": "ok",
                "engine": "rule_based",
                "seed": 0,
                "config_path": "experiments/scenarios/E5.yaml",
                "wall_time_s": 12.0,
                "results": {"sim_time_s": 300.0},
                "parameters": {
                    "events": [{"time": 15.0, "cue": {"strength": "weak"}}],
                    "station": {"platform_down_exits": {"platform_1": ["escalator_d_down"]}},
                },
            }
        )
    )
    rows = [
        _decision(0, "c1", "wait"),
        _decision(0, "c2", "wait"),
        _decision(0, "p1", "wait"),
        _decision(0, "p2", "evacuate", "escalator_b_up"),  # already leaving: not in the crowd
        _decision(30, "c1", "evacuate", "grey_street"),
        _decision(60, "c2", "evacuate", "grey_street"),
        _decision(45, "p1", "leave_by_train"),
    ]
    with (run / "decisions.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[*rows[0], "repair_status", "rationale"])
        writer.writeheader()
        writer.writerows(rows)
    with (run / "exit_log.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["agent_id", "time_s"])
        writer.writeheader()
        writer.writerows(
            [
                {"agent_id": "p2", "time_s": "40"},
                {"agent_id": "p1", "time_s": "50"},
                {"agent_id": "c1", "time_s": "80"},
                {"agent_id": "c2", "time_s": "115"},
            ]
        )
    levels = {"c1": "0", "c2": "0", "p1": "-1", "p2": "-1", "firefighter_0": "0"}
    frames = [{"time": 0.0, "agent_levels": levels}, {"time": 15.0, "agent_levels": levels}]
    (run / "frames.jsonl").write_text("".join(json.dumps(fr) + "\n" for fr in frames))
    return run


def test_run_metrics_end_to_end(tmp_path):
    m = run_metrics(_write_run(tmp_path))
    assert (m.scenario, m.engine, m.seed) == ("E5", "rule_based", 0)
    assert (m.passengers, m.crowd_concourse, m.crowd_platform) == (4, 2, 1)
    assert m.start_move_concourse_s == 15.0  # c1 at 30 s: half of two
    assert m.start_move_platform_s == 30.0  # p1 at 45 s
    assert m.clearance_s == 100.0  # c2 left at 115 s
    assert m.t50_s == 35.0 and m.remaining_at_end == 0
    assert m.window_s == 285.0


def test_remaining_curve(tmp_path):
    times, shares = remaining_curve(_write_run(tmp_path), step_s=50)
    assert times[:3] == [0.0, 50.0, 100.0]
    assert shares[:3] == [1.0, 0.5, 0.0]


# -- scoring against Proulx ----------------------------------------------------


def _metrics(tmp_path, **changes):
    m = run_metrics(_write_run(tmp_path))
    for key, value in changes.items():
        setattr(m, key, value)
    return m


def test_never_counts_as_the_window(tmp_path):
    m = _metrics(tmp_path, start_move_concourse_s=None, window_s=885.0)
    (c,) = [c for c in compare("E5", [m]) if c.measure == "start_move_concourse_s"]
    assert c.simulated == 885.0 and c.never == 1 and c.error == 885.0 - 90.0


def test_e1_clearance_is_only_wrong_if_it_clears_early(tmp_path):
    never = _metrics(tmp_path, clearance_s=None)
    early = _metrics(tmp_path, clearance_s=500.0)
    by_measure = {c.measure: c for c in compare("E1", [never])}
    assert by_measure["clearance_s"].error == 0.0
    by_measure = {c.measure: c for c in compare("E1", [early, never])}
    assert by_measure["clearance_s"].error == pytest.approx((500.0 - E1_EXERCISE_END_S) / 2)


def test_rmse_and_ordering(tmp_path):
    cs = compare("E5", [_metrics(tmp_path)])
    assert rmse(cs) == pytest.approx((sum(c.error**2 for c in cs) / 3) ** 0.5)
    proulx_like = {"E1": 900, "E3": 630, "E2": 480, "E4": 405, "E5": 345}
    assert ordering_tau(proulx_like) == 1.0
    assert ordering_tau({k: -v for k, v in proulx_like.items()}) == -1.0


# -- fitting and authoring -----------------------------------------------------


def test_overlay_nests_dotted_keys():
    assert overlay({"decision.social.threshold": 0.5, "decision.response_sigma": 0.3}) == {
        "decision": {"social": {"threshold": 0.5}, "response_sigma": 0.3}
    }


def test_rule_based_fit_file_is_valid():
    spec = FitSpec.load(EXPERIMENTS / "fits" / "rule_based.yaml")
    assert spec.engine == "rule_based"
    assert not set(spec.train) & set(spec.held_out)
    assert all(key.startswith("decision.") for key in spec.parameters)


def test_authoring_log_round_trip(tmp_path):
    path = tmp_path / "log.csv"
    log_entry("llm", "manual", "shorter prompt", minutes=20, author="me", path=path)
    log_entry("rule_based", "fit", "search", runs=9, compute_s=61.4, author="me", path=path)
    rows = read_log(path)
    assert [r["kind"] for r in rows] == ["manual", "fit"]
    assert rows[0]["minutes"] == "20" and rows[1]["compute_s"] == "61"
    with pytest.raises(ValueError):
        log_entry("llm", "guess", "x", path=path)


def test_count_cue_annotations():
    params = {
        "events": [
            {"cue": {"strength": "weak"}},
            {"cue": {"strength": "strong"}, "zone_cues": {"concourse": {}, "platform_1": {}}},
            {"type": "block_exit"},
        ],
        "systems": {"staff": {"phases": [{"cues_by_zone": {"concourse": {}}}, {}]}},
    }
    assert count_cue_annotations(params) == 5
