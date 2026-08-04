#!/usr/bin/env python3
"""Generate an MP4 video for an already completed run directory."""

import argparse
from pathlib import Path

from evacusim.visualization.video_generation_helper import VideoGenerationHelper


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate simulation video for an existing run directory"
    )
    parser.add_argument(
        "run_dir",
        type=Path,
        help="Path to run directory (e.g. results/Test/run_20260803_201802)",
    )
    parser.add_argument(
        "--decisions-file",
        type=Path,
        default=None,
        help="Path to decisions JSON file (defaults to run_dir/agent_decisions.json)",
    )
    parser.add_argument(
        "--network-path",
        type=Path,
        default=Path("geometry/monument/network"),
        help="Path to station network directory",
    )
    parser.add_argument("--fps", type=int, default=20)
    parser.add_argument("--speedup", type=float, default=1.0)
    return parser.parse_args()


def resolve_decisions_file(run_dir: Path, explicit_path: Path | None) -> Path:
    if explicit_path is not None:
        return explicit_path

    default_path = run_dir / "agent_decisions.json"
    if default_path.exists():
        return default_path

    raise FileNotFoundError(
        f"Could not find decisions file at: {default_path}. "
        "Pass --decisions-file explicitly."
    )


def main() -> None:
    args = parse_args()
    run_dir = args.run_dir

    if not run_dir.exists() or not run_dir.is_dir():
        raise NotADirectoryError(f"Run directory does not exist or is not a directory: {run_dir}")

    run_id = run_dir.name
    decisions_file = resolve_decisions_file(run_dir, args.decisions_file)

    VideoGenerationHelper.generate_simulation_video(
        decisions_file=decisions_file,
        run_id=run_id,
        network_path=args.network_path,
        fps=args.fps,
        speedup=args.speedup,
    )


if __name__ == "__main__":
    main()
