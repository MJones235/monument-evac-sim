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


def parse_args():
    parser = argparse.ArgumentParser(description="Run a Monument Station evacuation experiment")
    parser.add_argument("config", type=Path, help="Path to experiment config YAML (e.g. experiments/E1/config.yaml)")
    parser.add_argument("--agents", type=int, default=None, help="Override agent count from config")
    parser.add_argument("--max-steps", type=int, default=None, help="Override max simulation steps")
    parser.add_argument("--output-dir", type=str, default=None, help="Override output directory")
    parser.add_argument("--no-viewer", action="store_true", help="Disable live GUI viewer")
    parser.add_argument("--no-spatial-viewer", action="store_true", help="Disable spatial matplotlib viewer")
    parser.add_argument("--no-video", action="store_true", help="Skip MP4 rendering after simulation")
    parser.add_argument("--video-fps", type=int, default=20)
    parser.add_argument("--video-speedup", type=float, default=1.0)
    return parser.parse_args()


def run_simulation(config: dict, model, embedder, experiment_id: str,
                   launch_viewer: bool = True, launch_spatial: bool = True):
    """Orchestrate the full simulation run and return (results, run_id, decisions_file)."""
    runner = None

    jps_sim = JuPedSimSetup.create_simulation(config)
    station_layout = StationLayoutBuilder.build_layout(jps_sim, config)
    agents_config = AgentManager.create_and_populate_agents(jps_sim, config)
    run_id, output_dir, decisions_file = OutputManager.setup_output_directory(config)

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
        config=config,
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

        config = ConfigLoader.load_and_validate(
            config_path=str(args.config),
            agents=args.agents,
            max_steps=args.max_steps,
            output_dir=output_dir,
        )

        model, embedder = LLMSetup.setup_language_model(config)

        results, run_id, decisions_file = run_simulation(
            config, model, embedder,
            experiment_id=experiment_id,
            launch_viewer=not args.no_viewer,
            launch_spatial=not args.no_spatial_viewer,
        )

        if not args.no_video:
            network_path = Path(config.get("simulation", {}).get("network_path", "geometry/monument/network"))
            VideoGenerationHelper.generate_simulation_video(
                decisions_file=decisions_file,
                run_id=run_id,
                network_path=network_path,
                fps=args.video_fps,
                speedup=args.video_speedup,
            )

        logger.info("=" * 60)
        for key, value in results.items():
            logger.info(f"  {key}: {value}")
        elapsed = time.time() - script_start
        logger.info(f"Total time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Experiment {experiment_id} failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
