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
from evacusim.metrics.manifest import finish_manifest, start_manifest
from evacusim.metrics.results_writer import ResultsWriter
from evacusim.setup.agent_manager import AgentManager
from evacusim.setup.jupedsim_setup import JuPedSimSetup
from evacusim.setup.llm_setup import LLMSetup
from evacusim.setup.output_manager import OutputManager
from evacusim.setup.simulation_runner_factory import SimulationRunnerFactory
from evacusim.setup.station_layout_builder import StationLayoutBuilder
from evacusim.utils.logger import get_logger
from evacusim.utils.seeding import seed_global_rng
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
    parser.add_argument(
        "--fake-llm",
        action="store_true",
        help="Use a deterministic fake language model (no API calls; for testing the LLM "
        "pipeline, not for results)",
    )
    parser.add_argument("--video-fps", type=int, default=None, help="Override video.fps")
    parser.add_argument("--video-speedup", type=float, default=None, help="Override video.speedup")
    return parser.parse_args()


def run_simulation(
    params: RunConfig,
    model,
    embedder,
    config_path: Path,
    launch_viewer: bool = True,
    launch_spatial: bool = True,
):
    """Orchestrate the full simulation run and return (results, run_id, decisions_file).

    The run directory gets a manifest.json (see evacusim.metrics.manifest)
    recording what produced the run and how it ended.
    """
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
    run_id, output_dir, decisions_file = OutputManager.setup_output_directory(
        params.output, engine=params.decision.engine, seed=params.seed
    )
    manifest = start_manifest(
        output_dir, params, config_path=config_path, study_root=Path(__file__).parent
    )
    try:
        results = _run_and_save(
            params,
            model,
            embedder,
            jps_sim,
            station_layout,
            agents_config,
            pre_built_systems,
            pre_built_agent_roles,
            run_id,
            decisions_file,
            launch_viewer,
            launch_spatial,
        )
    except BaseException as error:
        finish_manifest(output_dir, manifest, error=error, llm_provider=model)
        raise
    finish_manifest(output_dir, manifest, results=results, llm_provider=model)
    logger.info(f"Results saved to {output_dir}")
    return results, run_id, decisions_file


def _run_and_save(
    params,
    model,
    embedder,
    jps_sim,
    station_layout,
    agents_config,
    pre_built_systems,
    pre_built_agent_roles,
    run_id,
    decisions_file,
    launch_viewer,
    launch_spatial,
):
    """Build the runner, run it, and write the final results.

    Ctrl-C ends the run early; the runner stops at the end of the current step
    and its results are saved as usual, marked as interrupted.
    """
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
    try:
        results = runner.run()
    except Exception:
        # Keep what was simulated for diagnosis; main() then exits non-zero.
        runner.cleanup()
        raise
    runner.decision_processor.log_cache_summary()
    ResultsWriter.save_final_results(decisions_file, runner.run_record())
    return results


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
        # Every random component's seed derives from params.seed; this covers
        # code that still uses the random module directly.
        seed_global_rng(params.seed)

        # The rule-based engine needs no language model or embedder (and no
        # Azure credentials): evacusim then builds no Concordia agents and makes
        # zero LLM calls.
        if params.decision.engine == "llm" and args.fake_llm:
            from evacusim.testing.fake_llm import FakeLanguageModel, fake_embedder

            logger.warning("Using the fake language model: decisions are not meaningful.")
            model, embedder = FakeLanguageModel(), fake_embedder
        elif params.decision.engine == "llm":
            model, embedder = LLMSetup.setup_language_model(params.llm)
        else:
            logger.info("Rule-based decision engine selected — no LLM or embedder is loaded.")
            model, embedder = None, None

        results, run_id, decisions_file = run_simulation(
            params,
            model,
            embedder,
            config_path=args.config,
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

    except KeyboardInterrupt:
        logger.warning(f"Experiment {experiment_id} interrupted")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Experiment {experiment_id} failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
