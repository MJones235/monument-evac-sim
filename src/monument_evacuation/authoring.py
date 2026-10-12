"""The authoring log: the effort spent making each decision engine fit the drills.

``experiments/authoring_log.csv`` (committed) has one row per piece of work:

=============  ==============================================================
``date``       when it was logged (UTC, ISO 8601)
``engine``     ``llm`` or ``rule_based``
``kind``       ``manual`` (a person editing prompts, cues or parameters) or
               ``fit`` (an automatic parameter search, logged by ``monument fit``)
``minutes``    a person's time spent (manual work)
``runs``       simulations run for it
``compute_s``  wall-clock time those simulations took
``author``     who did it (git user name)
``what``       what changed and why
=============  ==============================================================

Log manual work with ``monument log ENGINE MINUTES "what changed"``.
"""

from __future__ import annotations

import csv
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from monument_evacuation.paths import EXPERIMENTS, REPO_ROOT

LOG = EXPERIMENTS / "authoring_log.csv"
COLUMNS = ["date", "engine", "kind", "minutes", "runs", "compute_s", "author", "what"]
KINDS = ("manual", "fit")


def log_entry(
    engine: str,
    kind: str,
    what: str,
    *,
    minutes: float = 0,
    runs: int = 0,
    compute_s: float = 0,
    author: str | None = None,
    path: Path = LOG,
) -> dict[str, str]:
    """Append one row to the authoring log and return it."""
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}, not {kind!r}")
    row = {
        "date": datetime.now(UTC).isoformat(timespec="seconds"),
        "engine": engine,
        "kind": kind,
        "minutes": f"{minutes:g}",
        "runs": str(runs),
        "compute_s": f"{compute_s:.0f}",
        "author": author if author is not None else _git_user(),
        "what": what,
    }
    new = not path.exists()
    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        if new:
            writer.writeheader()
        writer.writerow(row)
    return row


def read_log(path: Path = LOG) -> list[dict[str, str]]:
    """Every row of the authoring log (empty if there is none)."""
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def _git_user() -> str:
    try:
        return subprocess.run(
            ["git", "config", "user.name"], cwd=REPO_ROOT, capture_output=True, text=True
        ).stdout.strip()
    except OSError:
        return ""
