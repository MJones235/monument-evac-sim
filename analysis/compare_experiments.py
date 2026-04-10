#!/usr/bin/env python3
"""
Compare results across all E1–E5 experiments.

Loads the most recent run from each experiment's results directory and
produces comparison tables and charts across the five scenarios.

Usage:
    python analysis/compare_experiments.py
    python analysis/compare_experiments.py --results-dir /path/to/results
"""

import argparse
from pathlib import Path


EXPERIMENTS = ["E1", "E2", "E3", "E4", "E5"]


def find_latest_run(results_dir: Path, experiment_id: str) -> Path | None:
    """Return the most recent results directory for an experiment."""
    exp_dir = results_dir / experiment_id
    if not exp_dir.exists():
        return None
    runs = sorted(exp_dir.iterdir(), reverse=True)
    return runs[0] if runs else None


def main():
    parser = argparse.ArgumentParser(description="Compare E1–E5 experiment results")
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results"),
        help="Root results directory (default: results/)",
    )
    args = parser.parse_args()

    for exp_id in EXPERIMENTS:
        run = find_latest_run(args.results_dir, exp_id)
        if run is None:
            print(f"{exp_id}: no results found")
        else:
            print(f"{exp_id}: {run}")

    # TODO: load agent_decisions.json, population_timeseries, etc. from each run
    #       and produce evacuation time / compliance rate / LLM cost comparison table


if __name__ == "__main__":
    main()
