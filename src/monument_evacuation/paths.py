"""Where things live in the study repository."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPERIMENTS = REPO_ROOT / "experiments"
SCENARIOS = EXPERIMENTS / "scenarios"
ENGINES = EXPERIMENTS / "engines"
CALIBRATION = EXPERIMENTS / "calibration"
RESULTS = REPO_ROOT / "results"
NETWORK = REPO_ROOT / "geometry" / "monument" / "network"
ARRIVALS = REPO_ROOT / "data" / "arrivals"
"""Real train arrivals logged at Monument (tools/monument_arrivals_logger.py)."""


def scenario_config(name_or_path: str) -> Path:
    """The config file for a scenario name (``E1``, ``normal_day``) or path.

    Names are looked up in ``experiments/scenarios`` then
    ``experiments/calibration``.
    """
    path = Path(name_or_path)
    if path.suffix in (".yaml", ".yml"):
        if not path.exists():
            raise FileNotFoundError(f"config file not found: {path}")
        return path
    for folder in (SCENARIOS, CALIBRATION):
        candidate = folder / f"{name_or_path}.yaml"
        if candidate.exists():
            return candidate
    known = sorted(p.stem for folder in (SCENARIOS, CALIBRATION) for p in folder.glob("*.yaml"))
    raise FileNotFoundError(f"unknown scenario {name_or_path!r}; known: {', '.join(known)}")


def engine_config(name: str) -> Path:
    """The overlay for a decision engine name (``llm``, ``rule_based``)."""
    path = ENGINES / f"{name}.yaml"
    if not path.exists():
        known = sorted(p.stem for p in ENGINES.glob("*.yaml"))
        raise FileNotFoundError(f"unknown engine {name!r}; known: {', '.join(known)}")
    return path
