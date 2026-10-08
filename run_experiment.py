#!/usr/bin/env python3
"""
Run a single Monument Station evacuation experiment.

Usage:
    python run_experiment.py experiments/E1/config.yaml
    python run_experiment.py experiments/E2/config.yaml --agents 100
    python run_experiment.py experiments/E5/config.yaml --no-viewer
    python run_experiment.py experiments/E5/config.yaml --no-viewer --no-video
"""

import argparse
import signal
import sys
import time
from pathlib import Path

# Allow running from the repo root without pip install
sys.path.insert(0, str(Path(__file__).parent))

# Load .env from the monument-evacuation repo root before any other imports
# (load_dotenv() inside llm_setup searches from CWD which may not be reliable
# when called as an installed package)
from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).parent / ".env")

from evacusim.config.config_loader import ConfigLoader
from evacusim.config.schema import RunConfig, as_dict
from evacusim.coordination.hybrid_simulation import HybridSimulationRunner
from evacusim.metrics.results_writer import ResultsWriter
from evacusim.setup.agent_manager import AgentManager
from evacusim.setup.jupedsim_setup import JuPedSimSetup
from evacusim.setup.llm_setup import LLMSetup
from evacusim.setup.output_manager import OutputManager
from evacusim.setup.simulation_runner_factory import SimulationRunnerFactory
from evacusim.setup.station_layout_builder import StationLayoutBuilder
from evacusim.utils.logger import get_logger
from evacusim.visualization.video_generation_helper import VideoGenerationHelper
from evacusim.visualization.viewer_launcher import ViewerLauncher

logger = get_logger(__name__)


def parse_start_time(value: str) -> float:
    """Parse HH:MM[:SS] or seconds-since-midnight."""
    text = value.strip()
    try:
        if ":" not in text:
            seconds = float(text)
        else:
            parts = text.split(":")
            if len(parts) not in (2, 3):
                raise ValueError
            hours, minutes = int(parts[0]), int(parts[1])
            seconds_part = float(parts[2]) if len(parts) == 3 else 0.0
            if hours < 0 or minutes not in range(60) or not 0 <= seconds_part < 60:
                raise ValueError
            seconds = hours * 3600 + minutes * 60 + seconds_part
        if not 0 <= seconds < 86400:
            raise ValueError
        return seconds
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "start time must be HH:MM[:SS] or seconds since midnight (0-86399)"
        ) from exc


def parse_args():
    parser = argparse.ArgumentParser(description="Run a Monument Station evacuation experiment")
    parser.add_argument(
        "config", type=Path, help="Path to experiment config YAML (e.g. experiments/E1/config.yaml)"
    )
    parser.add_argument("--agents", type=int, default=None, help="Override agent count from config")
    parser.add_argument("--max-steps", type=int, default=None, help="Override max simulation steps")
    parser.add_argument(
        "--start-time",
        type=parse_start_time,
        default=None,
        metavar="HH:MM[:SS]",
        help="Start at an absolute time of day, skipping earlier arrivals/events",
    )
    parser.add_argument("--output-dir", type=str, default=None, help="Override output directory")
    parser.add_argument("--no-viewer", action="store_true", help="Disable live GUI viewer")
    parser.add_argument(
        "--no-spatial-viewer", action="store_true", help="Disable spatial matplotlib viewer"
    )
    parser.add_argument(
        "--no-video", action="store_true", help="Skip MP4 rendering after simulation"
    )
    parser.add_argument("--video-fps", type=int, default=None, help="Override video.fps")
    parser.add_argument("--video-speedup", type=float, default=None, help="Override video.speedup")
    return parser.parse_args()


def run_simulation(
    params: RunConfig,
    model,
    embedder,
    experiment_id: str,
    launch_viewer: bool = True,
    launch_spatial: bool = True,
):
    """Orchestrate the full simulation run and return (results, run_id, decisions_file)."""
    runner = None

    jps_sim = JuPedSimSetup.create_simulation(params)
    station_layout = StationLayoutBuilder.build_layout(jps_sim, params.station)

    # Pre-spawn director agents (fire marshals, RCI staff, etc.) into JuPedSim
    # BEFORE random passengers are spawned.  JuPedSim then enforces minimum
    # separation around their positions so no passenger can land on top of a
    # fire-marshal spawn point (fixes spawn-collision RuntimeError).
    pre_built_systems, pre_built_agent_roles = HybridSimulationRunner.build_systems_for_pre_spawn(
        {name: as_dict(cfg) for name, cfg in params.systems.items()}, jps_sim, station_layout
    )

    agents_config = AgentManager.create_and_populate_agents(jps_sim, params)
    run_id, output_dir, decisions_file = OutputManager.setup_output_directory(params.output)

    ViewerLauncher.launch_viewers(
        decisions_file=decisions_file,
        run_id=run_id,
        network_path=jps_sim.network_path,
        launch_gui=launch_viewer,
        launch_spatial=launch_spatial,
    )

    runner = SimulationRunnerFactory.create_runner(
        jps_sim=jps_sim,
        agents_config=agents_config,
        station_layout=station_layout,
        model=model,
        embedder=embedder,
        decisions_file=decisions_file,
        params=params,
        pace_to_realtime=(launch_viewer or launch_spatial),
        pre_built_systems=pre_built_systems,
        pre_built_agent_roles=pre_built_agent_roles,
    )

    def signal_handler(signum, frame):
        logger.warning("Simulation interrupted — saving partial results...")
        if runner:
            runner.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        results = runner.run()
    except KeyboardInterrupt:
        runner.cleanup()
        sys.exit(0)

    agent_levels = getattr(runner.jps_sim, "agent_levels", None)

    if hasattr(runner, "decision_processor"):
        runner.decision_processor.log_cache_summary()

    ResultsWriter.save_final_results(
        decisions_file,
        runner.agent_decisions,
        runner.jps_sim.get_all_agent_positions(),
        runner.current_sim_time,
        runner.event_manager.event_history,
        runner.event_manager.blocked_exits,
        runner.message_system.message_history,
        runner.wait_events,
        runner.decision_interval,
        runner.max_steps,
        len(runner.concordia_agents),
        runner.perf_timer.report(),
        runner.llm_provider,
        agent_levels,
        exit_log=getattr(runner, "exit_log", None),
        spawn_log=getattr(runner, "spawn_log", None),
        escalator_system=getattr(runner.jps_sim, "escalator_system", None),
    )
    logger.info(f"Results saved to {output_dir}")
    return results, run_id, decisions_file


def main():
    script_start = time.time()
    args = parse_args()

    if not args.config.exists():
        print(f"Error: config file not found: {args.config}", file=sys.stderr)
        sys.exit(1)

    # Derive experiment ID from the config's parent directory (e.g. "E1")
    experiment_id = args.config.parent.name

    logger.info("=" * 60)
    logger.info(f"Monument Station Evacuation  —  Experiment {experiment_id}")
    logger.info("=" * 60)

    try:
        # Default output directory is results/<experiment_id>/ so that each
        # experiment's runs are grouped together for cross-experiment analysis.
        output_dir = args.output_dir or f"results/{experiment_id}"

        params = ConfigLoader.load_run_config(
            config_path=str(args.config),
            agents=args.agents,
            max_steps=args.max_steps,
            output_dir=output_dir,
            start_time_s=args.start_time,
        )

        # The rule-based engine needs no language model or embedder (and no
        # Azure credentials): evacusim then builds no Concordia agents and makes
        # zero LLM calls.
        if params.decision.engine == "llm":
            model, embedder = LLMSetup.setup_language_model(params.llm)
        else:
            logger.info("Rule-based decision engine selected — no LLM or embedder is loaded.")
            model, embedder = None, None

        results, run_id, decisions_file = run_simulation(
            params,
            model,
            embedder,
            experiment_id=experiment_id,
            launch_viewer=not args.no_viewer,
            launch_spatial=not args.no_spatial_viewer,
        )

        if not args.no_video:
            VideoGenerationHelper.generate_simulation_video(
                decisions_file=decisions_file,
                run_id=run_id,
                network_path=Path(params.simulation.network_path),
                fps=args.video_fps or params.video.fps,
                speedup=args.video_speedup or params.video.speedup,
            )

        logger.info("=" * 60)
        for key, value in results.items():
            logger.info(f"  {key}: {value}")
        elapsed = time.time() - script_start
        logger.info(f"Total time: {elapsed:.1f}s ({elapsed / 60:.1f} min)")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Experiment {experiment_id} failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
