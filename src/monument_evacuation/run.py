"""One simulation run: a scenario, a decision engine and a seed.

``run_scenario`` loads the parameters (scenario file + engine overlay +
command-line overrides), builds the simulation, runs it and writes the
results to ``results/<scenario>/run_<time>_<engine>_s<seed>/``, starting with
``manifest.json`` (evacusim.metrics.manifest).
"""

from __future__ import annotations

import time
from pathlib import Path

from dotenv import load_dotenv
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

from monument_evacuation.paths import REPO_ROOT, RESULTS, engine_config, scenario_config

logger = get_logger(__name__)

EXIT_OK, EXIT_FAILED, EXIT_INTERRUPTED = 0, 1, 130


def run_scenario(
    scenario: str,
    *,
    engine: str | None = None,
    seed: int | None = None,
    agents: int | None = None,
    max_steps: int | None = None,
    start_time_s: float | None = None,
    output_dir: str | None = None,
    fake_llm: bool = False,
    viewer: bool = False,
    spatial_viewer: bool = False,
    video: bool = False,
    video_fps: int | None = None,
    video_speedup: float | None = None,
) -> int:
    """Run one scenario and return the process exit code (0 ok, 1 failed, 130 interrupted).

    Args:
        scenario: Scenario name (``E1``, ``normal_day``) or config path.
        engine: Decision engine overlay (``llm``, ``rule_based``); ``None`` uses
            the scenario's own (LLM by default).
        seed: Overrides the master random seed.
        agents, max_steps, start_time_s, output_dir: Override the config.
        fake_llm: Use evacusim's deterministic fake model (testing only).
        viewer, spatial_viewer: Open the live viewers.
        video: Render an MP4 afterwards.
    """
    load_dotenv(REPO_ROOT / ".env")
    script_start = time.time()
    config_path = scenario_config(scenario)
    experiment_id = config_path.stem

    logger.info("=" * 60)
    logger.info(f"Monument Station  —  {experiment_id} ({engine or 'scenario engine'})")
    logger.info("=" * 60)

    try:
        params = ConfigLoader.load_run_config(
            config_path=str(config_path),
            agents=agents,
            max_steps=max_steps,
            output_dir=output_dir or str(RESULTS / experiment_id),
            start_time_s=start_time_s,
            overlays=[str(engine_config(engine))] if engine else [],
        )
        if seed is not None:
            params = params.model_copy(update={"seed": seed})
        # Every random component's seed derives from params.seed; this covers
        # code that still uses the random module directly.
        seed_global_rng(params.seed)

        model, embedder = _language_model(params, fake_llm)
        results, run_id, decisions_file = _simulate(
            params, model, embedder, config_path, viewer, spatial_viewer
        )

        if video:
            VideoGenerationHelper.generate_simulation_video(
                decisions_file=decisions_file,
                run_id=run_id,
                network_path=Path(params.simulation.network_path),
                fps=video_fps or params.video.fps,
                speedup=video_speedup or params.video.speedup,
            )

        logger.info("=" * 60)
        for key, value in results.items():
            logger.info(f"  {key}: {value}")
        elapsed = time.time() - script_start
        logger.info(f"Total time: {elapsed:.1f}s ({elapsed / 60:.1f} min)")
        logger.info("=" * 60)
        # An interrupted run saved its results but did not finish.
        return EXIT_INTERRUPTED if results.get("interrupted") else EXIT_OK

    except KeyboardInterrupt:
        logger.warning(f"{experiment_id} interrupted")
        return EXIT_INTERRUPTED
    except Exception as e:
        logger.error(f"{experiment_id} failed: {e}", exc_info=True)
        return EXIT_FAILED


def _language_model(params: RunConfig, fake_llm: bool):
    """The model and embedder for the LLM engine; ``(None, None)`` for rule-based."""
    if params.decision.engine != "llm":
        logger.info("Rule-based decision engine selected — no LLM or embedder is loaded.")
        return None, None
    if fake_llm:
        from evacusim.testing.fake_llm import FakeLanguageModel, fake_embedder

        logger.warning("Using the fake language model: decisions are not meaningful.")
        return FakeLanguageModel(), fake_embedder
    return LLMSetup.setup_language_model(params.llm)


def _simulate(params, model, embedder, config_path, viewer, spatial_viewer):
    """Build the simulation, run it, write the results and the manifest.

    Returns ``(results, run_id, decisions_file)``.
    """
    jps_sim = JuPedSimSetup.create_simulation(params)
    station_layout = StationLayoutBuilder.build_layout(jps_sim, params.station)

    # Staff are placed before passengers, so passengers never spawn on them.
    pre_built_systems, pre_built_agent_roles = HybridSimulationRunner.build_systems_for_pre_spawn(
        {name: as_dict(cfg) for name, cfg in params.systems.items()}, jps_sim, station_layout
    )
    agents_config = AgentManager.create_and_populate_agents(jps_sim, params)
    run_id, output_dir, decisions_file = OutputManager.setup_output_directory(
        params.output, engine=params.decision.engine, seed=params.seed
    )
    manifest = start_manifest(output_dir, params, config_path=config_path, study_root=REPO_ROOT)
    try:
        ViewerLauncher.launch_viewers(
            decisions_file=decisions_file,
            run_id=run_id,
            network_path=jps_sim.network_path,
            launch_gui=viewer,
            launch_spatial=spatial_viewer,
        )
        runner = SimulationRunnerFactory.create_runner(
            jps_sim=jps_sim,
            agents_config=agents_config,
            station_layout=station_layout,
            model=model,
            embedder=embedder,
            decisions_file=decisions_file,
            params=params,
            pace_to_realtime=(viewer or spatial_viewer),
            pre_built_systems=pre_built_systems,
            pre_built_agent_roles=pre_built_agent_roles,
        )
        try:
            # Ctrl-C ends the run at the current step; results are saved and
            # marked as interrupted.
            results = runner.run()
        except Exception:
            runner.cleanup()  # keep what was simulated, for diagnosis
            raise
        runner.decision_processor.log_cache_summary()
        ResultsWriter.save_final_results(decisions_file, runner.run_record())
    except BaseException as error:
        finish_manifest(output_dir, manifest, error=error, llm_provider=model)
        raise
    finish_manifest(output_dir, manifest, results=results, llm_provider=model)
    logger.info(f"Results saved to {output_dir}")
    return results, run_id, decisions_file
