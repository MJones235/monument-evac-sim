"""The ``monument`` command.

monument run E1 --engine rule_based            one run (headless)
monument run E4 --engine llm --seed 2 --video
monument run normal_day --start-time 07:30      a calibration day
monument batch experiments/batches/proulx_comparison.yaml --jobs 4
monument fit experiments/fits/rule_based.yaml --jobs 12
monument log llm 30 "PA cue wording in the prompt"   log authoring effort
monument video results/E1/run_...               render a finished run
monument analyse compare_experiments ...        analysis scripts (see analysis/)
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

from monument_evacuation.paths import NETWORK


def parse_start_time(value: str) -> float:
    """``HH:MM[:SS]`` or seconds since midnight, as seconds since midnight."""
    text = value.strip()
    try:
        if ":" not in text:
            seconds = float(text)
        else:
            parts = text.split(":")
            if len(parts) not in (2, 3):
                raise ValueError
            hours, minutes = int(parts[0]), int(parts[1])
            secs = float(parts[2]) if len(parts) == 3 else 0.0
            if hours < 0 or minutes not in range(60) or not 0 <= secs < 60:
                raise ValueError
            seconds = hours * 3600 + minutes * 60 + secs
        if not 0 <= seconds < 86400:
            raise ValueError
        return seconds
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "start time must be HH:MM[:SS] or seconds since midnight (0-86399)"
        ) from exc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="monument", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run one scenario")
    run.add_argument("scenario", help="scenario name (E1, normal_day, ...) or config path")
    run.add_argument("--engine", help="decision engine: llm or rule_based")
    run.add_argument(
        "--overlay",
        action="append",
        default=[],
        metavar="YAML",
        help="config merged on top of scenario and engine (repeatable)",
    )
    run.add_argument("--seed", type=int, help="master random seed")
    run.add_argument("--agents", type=int, help="override agents.count")
    run.add_argument("--max-steps", type=int, help="override simulation.max_iterations")
    run.add_argument(
        "--start-time",
        type=parse_start_time,
        metavar="HH:MM[:SS]",
        help="start at a time of day, skipping earlier arrivals and events",
    )
    run.add_argument("--output-dir", help="override output.directory")
    run.add_argument(
        "--fake-llm",
        action="store_true",
        help="deterministic fake language model (tests the LLM pipeline; not for results)",
    )
    run.add_argument("--viewer", action="store_true", help="open the live GUI viewer")
    run.add_argument("--spatial-viewer", action="store_true", help="open the live map viewer")
    run.add_argument("--video", action="store_true", help="render an MP4 afterwards")
    run.add_argument("--video-fps", type=int, help="override video.fps")
    run.add_argument("--video-speedup", type=float, help="override video.speedup")

    batch = sub.add_parser("batch", help="run a scenario x engine x seed matrix")
    batch.add_argument("batch_file", type=Path)
    batch.add_argument("--jobs", type=int, default=1, help="runs at once")
    batch.add_argument("--dry-run", action="store_true", help="list the runs only")
    batch.add_argument("--max-steps", type=int, help="passed to every run (quick checks)")
    batch.add_argument("--agents", type=int, help="passed to every run (quick checks)")
    batch.add_argument("--fake-llm", action="store_true", help="passed to every run")

    fit = sub.add_parser("fit", help="fit an engine's parameters to Proulx (1991)")
    fit.add_argument("fit_file", type=Path)
    fit.add_argument("--jobs", type=int, default=1, help="runs at once")
    fit.add_argument("--trials", type=int, help="override the fit file's trial count")
    fit.add_argument("--max-steps", type=int, help="passed to every run (quick checks)")
    fit.add_argument("--agents", type=int, help="passed to every run (quick checks)")
    fit.add_argument(
        "--no-log", action="store_true", help="do not record in the authoring log (tool checks)"
    )

    log = sub.add_parser("log", help="record authoring effort (experiments/authoring_log.csv)")
    log.add_argument("engine", choices=["llm", "rule_based"])
    log.add_argument("minutes", type=float, help="time a person spent")
    log.add_argument("what", help="what changed and why")
    log.add_argument("--runs", type=int, default=0, help="simulations run for it")

    video = sub.add_parser("video", help="render the MP4 of a finished run")
    video.add_argument("run_dir", type=Path)
    video.add_argument("--fps", type=int, default=20)
    video.add_argument("--speedup", type=float, default=1.0)
    video.add_argument("--network-path", type=Path, default=NETWORK)

    analyse = sub.add_parser("analyse", help="run an analysis script (monument analyse NAME -h)")
    analyse.add_argument("name", help="module in monument_evacuation.analysis")
    analyse.add_argument("args", nargs=argparse.REMAINDER)
    return parser


def _passed_run_args(args: argparse.Namespace) -> list[str]:
    """Options of batch and fit that are passed on to every run."""
    run_args = []
    if args.max_steps is not None:
        run_args += ["--max-steps", str(args.max_steps)]
    if args.agents is not None:
        run_args += ["--agents", str(args.agents)]
    return run_args


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    if args.command == "run":
        from monument_evacuation.run import run_scenario

        return run_scenario(
            args.scenario,
            engine=args.engine,
            overlays=args.overlay,
            seed=args.seed,
            agents=args.agents,
            max_steps=args.max_steps,
            start_time_s=args.start_time,
            output_dir=args.output_dir,
            fake_llm=args.fake_llm,
            viewer=args.viewer,
            spatial_viewer=args.spatial_viewer,
            video=args.video,
            video_fps=args.video_fps,
            video_speedup=args.video_speedup,
        )

    if args.command == "batch":
        from monument_evacuation.batch import run_batch

        run_args = _passed_run_args(args)
        if args.fake_llm:
            run_args.append("--fake-llm")
        return run_batch(args.batch_file, jobs=args.jobs, dry_run=args.dry_run, run_args=run_args)

    if args.command == "fit":
        from monument_evacuation.fit import run_fit

        return run_fit(
            args.fit_file,
            jobs=args.jobs,
            trials=args.trials,
            run_args=_passed_run_args(args),
            log=not args.no_log,
        )

    if args.command == "log":
        from monument_evacuation.authoring import LOG, log_entry

        log_entry(args.engine, "manual", args.what, minutes=args.minutes, runs=args.runs)
        print(f"logged to {LOG}")
        return 0

    if args.command == "video":
        from evacusim.visualization.video_generation_helper import VideoGenerationHelper

        decisions = args.run_dir / "agent_decisions.json"
        if not decisions.exists():
            raise SystemExit(f"no agent_decisions.json in {args.run_dir}")
        VideoGenerationHelper.generate_simulation_video(
            decisions_file=decisions,
            run_id=args.run_dir.name,
            network_path=args.network_path,
            fps=args.fps,
            speedup=args.speedup,
        )
        return 0

    module = importlib.import_module(f"monument_evacuation.analysis.{args.name}")
    sys.argv = [f"monument analyse {args.name}", *args.args]
    return module.main() or 0


if __name__ == "__main__":
    sys.exit(main())
