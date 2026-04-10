#!/usr/bin/env python3
"""
Per-experiment and cross-experiment evacuation visualisation.

Generates:
- Evacuation time-series plots (agents remaining vs. simulation time)
- Zone occupancy heatmaps
- Decision timeline charts per scenario

Usage:
    python analysis/evacuation_plots.py --experiment E1
    python analysis/evacuation_plots.py --all
"""

import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Generate evacuation plots")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--experiment", choices=["E1", "E2", "E3", "E4", "E5"])
    group.add_argument("--all", action="store_true", help="Plot all experiments")
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results"),
    )
    args = parser.parse_args()

    experiments = ["E1", "E2", "E3", "E4", "E5"] if args.all else [args.experiment]

    for exp_id in experiments:
        print(f"Plotting {exp_id}...")
        # TODO: load results and generate matplotlib figures


if __name__ == "__main__":
    main()
