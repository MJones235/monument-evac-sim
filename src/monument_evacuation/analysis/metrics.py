"""The measures of one run, computed the same way for both decision engines.

Proulx (1991) Table 1 reports, per drill, when the crowd on the concourse and
the crowd at the bottom of the North/South escalators *started to move*, and
when the station was clear. ``run_metrics`` measures the same from a run's
``decisions.csv``, ``exit_log.csv`` and ``frames.jsonl``:

- **Outbound.** A decision to ``leave_by_train``, or to ``evacuate`` towards
  anything but a down escalator. (``evacuate`` alone is not enough: both
  engines also use it for an ordinary journey down to a platform.)
- **Starting to move.** The first decision of the unbroken run of outbound
  decisions a passenger ended with; or, for someone who left without one
  (boarding a waiting train), the time they left. Someone who stopped and set
  off again started when they set off again.
- **Crowds.** The passengers on the street level (concourse) or the platform
  level at the alarm who had not already started to move.
- **Time to start to move.** When half of a crowd had started (Proulx's
  "the crowd started to move"); ``None`` if half never did.
- **Clearance.** When the last passenger left, if everyone did.

All times are seconds after the alarm. Cost, effort and variability measures
(wall time, LLM use, fallbacks, action mix) are here too, so one loader feeds
every comparison.
"""

from __future__ import annotations

import csv
import json
import math
from collections import Counter
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from monument_evacuation.analysis.runs import alarm_time_s, frames_path, manifest

OUTBOUND_ACTIONS = {"evacuate", "leave_by_train"}


@dataclass
class RunMetrics:
    """What one run measured. Times are seconds after the alarm."""

    run_dir: str
    scenario: str
    engine: str | None
    seed: int | None
    status: str | None
    window_s: float
    """Simulated time after the alarm (a censoring limit for the times below)."""

    passengers: int
    crowd_concourse: int
    crowd_platform: int
    start_move_concourse_s: float | None
    start_move_platform_s: float | None
    present_at_alarm: int
    t50_s: float | None
    """Half of the passengers present at the alarm had left."""
    t90_s: float | None
    clearance_s: float | None
    """The last passenger left; ``None`` if anyone was still inside at the end."""
    remaining_at_end: int

    wall_time_s: float | None
    decisions: int
    llm_requests: int
    llm_tokens: int
    llm_cost_gbp: float
    fallbacks: int
    """LLM decisions with no valid answer (the safe default was used)."""
    repairs: int
    """LLM decisions answered only after a correction."""
    action_entropy_bits: float
    """Shannon entropy of the actions chosen after the alarm (0: all identical)."""

    def as_row(self) -> dict[str, object]:
        """A flat dict for CSV writing."""
        return asdict(self)

    @classmethod
    def columns(cls) -> list[str]:
        return [f.name for f in fields(cls)]


def run_metrics(run_dir: Path) -> RunMetrics:
    """Measure one finished run."""
    run_dir = Path(run_dir)
    m = manifest(run_dir) or {}
    params = m.get("parameters", {})
    station = params.get("station", {})
    alarm = alarm_time_s(run_dir)
    end = float(m.get("results", {}).get("sim_time_s") or _last_frame_time(run_dir))
    down_exits = {e for exits in station.get("platform_down_exits", {}).values() for e in exits}
    street_level = str(station.get("street_level", "0"))
    platform_level = str(station.get("platform_level", "-1"))

    decisions = read_csv(run_dir / "decisions.csv")
    exits = read_csv(run_dir / "exit_log.csv")
    passengers = {r["agent_id"] for r in decisions}
    exit_time = {r["agent_id"]: float(r["time_s"]) for r in exits if r["agent_id"] in passengers}

    # Who was where at the alarm, and who was already on their way out.
    levels = levels_at(run_dir, alarm)
    started = {
        a: t - alarm
        for a, t in start_times(decisions, exit_time, down_exits).items()
        if t is not None
    }

    def crowd(level: str) -> list[str]:
        return [
            a
            for a, lvl in levels.items()
            if lvl == level and a in passengers and started.get(a, math.inf) >= 0
        ]

    concourse, platform = crowd(street_level), crowd(platform_level)
    present = [a for a in levels if a in passengers]
    left_after = sorted(exit_time[a] - alarm for a in present if a in exit_time)
    remaining = len(passengers) - len(exit_time)

    post_alarm_actions = Counter(r["action"] for r in decisions if float(r["time_s"]) >= alarm)
    repair = Counter(r.get("repair_status", "") for r in decisions)
    llm = m.get("llm") or {}

    return RunMetrics(
        run_dir=str(run_dir),
        scenario=_scenario(run_dir, m),
        engine=m.get("engine"),
        seed=m.get("seed"),
        status=m.get("status"),
        window_s=round(end - alarm, 2),
        passengers=len(passengers),
        crowd_concourse=len(concourse),
        crowd_platform=len(platform),
        start_move_concourse_s=half_time([started.get(a) for a in concourse]),
        start_move_platform_s=half_time([started.get(a) for a in platform]),
        present_at_alarm=len(present),
        t50_s=_fraction_time(left_after, len(present), 0.5),
        t90_s=_fraction_time(left_after, len(present), 0.9),
        clearance_s=(
            round(max(exit_time.values()) - alarm, 2) if remaining == 0 and exit_time else None
        ),
        remaining_at_end=remaining,
        wall_time_s=m.get("wall_time_s"),
        decisions=len(decisions),
        llm_requests=int(llm.get("total_requests") or 0),
        llm_tokens=int(llm.get("total_tokens") or 0),
        llm_cost_gbp=float(llm.get("estimated_cost_gbp") or 0.0),
        fallbacks=repair.get("fallback", 0),
        repairs=repair.get("repair_1", 0) + repair.get("repair_2", 0),
        action_entropy_bits=round(entropy_bits(post_alarm_actions), 3),
    )


def start_times(
    decisions: list[dict[str, str]], exit_time: dict[str, float], down_exits: set[str]
) -> dict[str, float | None]:
    """When each passenger started the move that took them out (absolute time).

    ``None`` for someone whose last decision was not outbound and who never left.
    """
    streak: dict[str, float | None] = {}
    for r in decisions:  # decisions.csv is ordered by time
        a = r["agent_id"]
        if not _is_outbound(r, down_exits):
            streak[a] = None
        elif streak.get(a) is None:
            streak[a] = float(r["time_s"])
    return {a: (t if t is not None else exit_time.get(a)) for a, t in streak.items()}


def half_time(start_times: list[float | None]) -> float | None:
    """When half of a crowd had started; ``None`` if half never did (or no crowd).

    ``start_times`` has one entry per member, ``None`` for those who never started.
    """
    if not start_times:
        return None
    times = sorted(t for t in start_times if t is not None)
    needed = math.ceil(len(start_times) / 2)
    return times[needed - 1] if len(times) >= needed else None


def entropy_bits(counts: Counter) -> float:
    """Shannon entropy (bits) of a distribution given as counts."""
    total = sum(counts.values())
    return -sum(c / total * math.log2(c / total) for c in counts.values() if c) if total else 0.0


def _fraction_time(sorted_times: list[float], population: int, fraction: float) -> float | None:
    needed = math.ceil(fraction * population)
    if population == 0 or len(sorted_times) < needed:
        return None
    return round(sorted_times[max(needed, 1) - 1], 2)


def _is_outbound(row: dict[str, str], down_exits: set[str]) -> bool:
    if row["action"] == "leave_by_train":
        return True
    return row["action"] == "evacuate" and row.get("exit_id", "") not in down_exits


def levels_at(run_dir: Path, t: float) -> dict[str, str]:
    """Each person's level in the first frame at or after time ``t``."""
    path = frames_path(run_dir)
    if not path.exists():
        return {}
    with path.open() as f:
        for line in f:
            frame = json.loads(line)
            if frame["time"] >= t:
                return {a: str(lvl) for a, lvl in frame.get("agent_levels", {}).items()}
    return {}


def _last_frame_time(run_dir: Path) -> float:
    path = frames_path(run_dir)
    last = 0.0
    if path.exists():
        with path.open() as f:
            for line in f:
                last = json.loads(line)["time"]
    return last


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def _scenario(run_dir: Path, m: dict) -> str:
    config_path = m.get("config_path")
    return Path(config_path).stem if config_path else run_dir.parent.name


def write_metrics_csv(metrics: list[RunMetrics], path: Path) -> None:
    """Write one row per run."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RunMetrics.columns())
        writer.writeheader()
        for row in metrics:
            writer.writerow(row.as_row())
