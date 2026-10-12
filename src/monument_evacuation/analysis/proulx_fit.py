"""How well runs reproduce Proulx (1991) Table 1: the fit and comparison score.

Three measures per drill, all seconds after the alarm (see ``metrics``):

==========================  ==============================================
``start_move_concourse_s``  the concourse crowd started to move
``start_move_platform_s``   the crowd at the bottom of the N/S escalators
``clearance_s``             the last person left
==========================  ==============================================

A scenario's simulated value is the mean over its runs (seeds). A crowd that
never started, or a station that never cleared, counts as the end of the
simulated window: a lower bound, so the error is never overstated. E1's
station was never cleared (the exercise ended at 14:47), so E1 clearance
scores zero unless the simulation clears it before then.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from monument_evacuation.analysis.metrics import RunMetrics
from monument_evacuation.analysis.proulx_1991 import REFERENCE, qualitative_ordering

MEASURES = ("start_move_concourse_s", "start_move_platform_s", "clearance_s")

E1_EXERCISE_END_S = 887.0
"""E1 was stopped 14:47 after the alarm with people still inside."""


def target(scenario: str, measure: str) -> float | None:
    """Proulx's value; ``None`` means 'never' (only E1 clearance)."""
    ref = REFERENCE[scenario]
    return {
        "start_move_concourse_s": ref.time_to_move_concourse_s,
        "start_move_platform_s": ref.time_to_move_escalator_s,
        "clearance_s": ref.clearance.whole_station_s,
    }[measure]


@dataclass
class Comparison:
    """One simulated measure against Proulx's."""

    scenario: str
    measure: str
    target: float | None
    simulated: float
    """Mean over runs, a run's 'never' counted as its window."""
    spread: float
    """Standard deviation over runs (0 for one run)."""
    runs: int
    never: int
    """Runs in which it never happened within the window."""
    error: float
    """Simulated minus Proulx (s). For 'never' (E1 clearance): how much earlier
    than the end of the exercise the runs cleared, on average (0 if they did not)."""


def compare(scenario: str, runs: Sequence[RunMetrics]) -> list[Comparison]:
    """Each measure of a scenario's runs against Proulx."""
    out = []
    for measure in MEASURES:
        values = [_value(r, measure) for r in runs]
        goal = target(scenario, measure)
        if goal is None:
            error = statistics.fmean(
                min(0.0, getattr(r, measure) - E1_EXERCISE_END_S)
                if getattr(r, measure) is not None
                else 0.0
                for r in runs
            )
        else:
            error = statistics.fmean(values) - goal
        out.append(
            Comparison(
                scenario=scenario,
                measure=measure,
                target=goal,
                simulated=statistics.fmean(values),
                spread=statistics.stdev(values) if len(values) > 1 else 0.0,
                runs=len(values),
                never=sum(getattr(r, measure) is None for r in runs),
                error=error,
            )
        )
    return out


def rmse(comparisons: Iterable[Comparison]) -> float:
    """Root-mean-square error (s) over comparisons."""
    errors = [c.error for c in comparisons]
    return math.sqrt(statistics.fmean(e * e for e in errors)) if errors else math.nan


def ordering_tau(clearance_by_scenario: dict[str, float]) -> float:
    """Kendall's tau between the simulated and Proulx's E1-E5 ordering.

    Proulx ranks the drills by how quickly the station cleared
    (``qualitative_ordering``: E1 worst to E5 best). +1: same order;
    -1: reversed. Ties count as neither.
    """
    proulx = [s for s in qualitative_ordering() if s in clearance_by_scenario]
    # Worse = later clearance, so Proulx's rank should rise as clearance falls.
    pairs = [(a, b) for i, a in enumerate(proulx) for b in proulx[i + 1 :]]
    if not pairs:
        return math.nan
    score = 0
    for worse, better in pairs:
        diff = clearance_by_scenario[worse] - clearance_by_scenario[better]
        score += (diff > 0) - (diff < 0)
    return score / len(pairs)


def _value(run: RunMetrics, measure: str) -> float:
    value = getattr(run, measure)
    return run.window_s if value is None else value
