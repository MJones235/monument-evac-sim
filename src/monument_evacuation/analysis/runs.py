"""Finding runs and reading their outputs: the one place analysis scripts load from.

Runs live in ``results/<scenario>/run_<YYYYmmdd_HHMMSS>[_<engine>_s<seed>]/``.
Runs made before October 2026 lack the engine and seed in their name, a
``manifest.json`` and ``frames.jsonl`` (their frames are in
``agent_decisions_history.jsonl``); these helpers read both.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from monument_evacuation.paths import RESULTS

DEFAULT_ALARM_TIME_S = 15.0
"""The alarm time in E1-E5, for runs without a manifest."""


def find_runs(scenario: str, engine: str | None = None, results_dir: Path = RESULTS) -> list[Path]:
    """A scenario's run directories, newest first, optionally only one engine's."""
    folder = results_dir / scenario
    if not folder.is_dir():
        return []
    runs = [p for p in folder.iterdir() if p.is_dir() and p.name.startswith("run_")]
    if engine is not None:
        runs = [p for p in runs if run_engine(p) == engine]
    return sorted(runs, reverse=True)


def latest_run(
    scenario: str, engine: str | None = None, results_dir: Path = RESULTS
) -> Path | None:
    """The scenario's most recent run (of one engine, if given)."""
    runs = find_runs(scenario, engine, results_dir)
    return runs[0] if runs else None


def manifest(run_dir: Path) -> dict[str, Any] | None:
    """The run's manifest.json, or ``None`` for older runs."""
    path = run_dir / "manifest.json"
    return json.loads(path.read_text()) if path.exists() else None


def run_engine(run_dir: Path) -> str | None:
    """The decision engine a run used (from its manifest or directory name)."""
    m = manifest(run_dir)
    if m:
        return m.get("engine")
    for engine in ("rule_based", "llm"):
        if f"_{engine}_" in run_dir.name:
            return engine
    return None


def frames_path(run_dir: Path) -> Path:
    """The run's position-frames file (``frames.jsonl``, or its pre-October name)."""
    for name in ("frames.jsonl", "agent_decisions_history.jsonl"):
        if (run_dir / name).exists():
            return run_dir / name
    return run_dir / "frames.jsonl"


def alarm_time_s(run_dir: Path) -> float:
    """When the alarm sounded: the first event carrying a warning cue."""
    m = manifest(run_dir)
    events = (m or {}).get("parameters", {}).get("events", [])
    cue_times = [e["time"] for e in events if e.get("cue") or e.get("zone_cues")]
    return min(cue_times) if cue_times else DEFAULT_ALARM_TIME_S


def population_timeseries(run_dir: Path) -> list[dict[str, str]]:
    """Rows of population_timeseries.csv (empty if missing)."""
    path = run_dir / "population_timeseries.csv"
    if not path.exists():
        return []
    with path.open() as f:
        return list(csv.DictReader(f))
