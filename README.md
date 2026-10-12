# Monument Station Evacuation Study

Re-runs the five Proulx (1991) evacuation drills at Monument Metro station,
Newcastle, with two ways of deciding what each passenger does:

- **`rule_based`**: a cue-driven state machine (unaware → aware → evacuating).
- **`llm`**: a language model reasoning over the same observations.

The engines are compared on fit to Proulx's timings, cost and runtime,
authoring effort, and run-to-run variability. The simulation engine itself
lives in [evacusim](https://github.com/MJones235/llm-evacuation-sim); this
repository holds the station, the scenarios, the calibration data and the
analysis.

## The flow

```
INPUTS                      PARAMETERS                SIMULATION         OUTPUTS                 ANALYSIS
geometry/monument/  ─┐
experiments/base.yaml ─┤    one validated config      evacusim           results/<scenario>/     monument analyse ...
  scenarios/E*.yaml  ─┼──▶  (scenario + engine    ──▶ (JuPedSim     ──▶  run_<time>_<engine>_  ──▶ figures, tables
  engines/*.yaml     ─┤     overlay + seed)           physics +            s<seed>/
data/calibration/   ─┘                                decisions)           manifest.json, ...
```

One run is **scenario × engine × seed**. Every run writes a `manifest.json`
(resolved config, git commits of both repositories, seed, timings, LLM usage),
so every figure traces back to its inputs. The output files are described in
evacusim's `docs/outputs.md`.

## Scenarios

| ID | Proulx drill | Details |
|----|--------------|---------|
| E1 | Fire alarm only | [docs/scenarios/E1.md](docs/scenarios/E1.md) |
| E2 | Staff direct the evacuation | [docs/scenarios/E2.md](docs/scenarios/E2.md) |
| E3 | Minimal PA message | [docs/scenarios/E3.md](docs/scenarios/E3.md) |
| E4 | Staff assist + PA to board the evacuation train | [docs/scenarios/E4.md](docs/scenarios/E4.md) |
| E5 | Directive PA with the fire's location | [docs/scenarios/E5.md](docs/scenarios/E5.md) |

Every scenario runs for 15 minutes with Proulx's crowd sizes. Calibration
against a normal day uses `experiments/calibration/` (see
[data/calibration/README.md](data/calibration/README.md)).

## Setup

Clone evacusim next to this repository, then:

```bash
bash setup.sh                 # or: bash setup.sh /path/to/evacusim
source .venv/bin/activate
```

The LLM engine needs Azure credentials in `.env` (`AZURE_LLM_ENDPOINT`,
`AZURE_LLM_API_KEY`, `AZURE_LLM_MODEL`); `setup.sh` creates it from
`.env.example`. The rule-based engine and `--fake-llm` need none.

## Running

```bash
monument run E1 --engine rule_based                  # one run, headless
monument run E4 --engine llm --seed 2 --video         # with an MP4 afterwards
monument run normal_day --start-time 07:30 --max-steps 36000   # 07:30–08:30
monument batch experiments/batches/proulx_comparison.yaml --jobs 4
monument video results/E1/run_...                     # render a finished run
monument analyse compare_experiments --engine rule_based
```

`monument run -h` lists every option. A scenario is a name from
`experiments/scenarios/` or `experiments/calibration/`, or a path to any config
file. `--engine` overlays `experiments/engines/<engine>.yaml`.

`--start-time` starts at a time of day, skipping earlier arrivals and events.
`--max-steps` is then the elapsed duration from that start.

A batch file lists `scenarios`, `engines` and `seeds`. `monument batch` runs
every combination, each in its own process. It writes logs and a `summary.json`
to `results/batches/`.

## The comparison study

```bash
monument fit experiments/fits/rule_based.yaml --jobs 12      # fit the rule engine (~1 h)
monument batch experiments/batches/proulx_comparison.yaml --jobs 6
monument analyse compare_engines                             # report on the latest batch
monument log llm 30 "PA cue wording in the prompt"           # record authoring effort
```

- **Fitting.** `monument fit` searches the rule engine's response delays with
  Optuna. It fits on E1, E3 and E5 against Proulx's times to start moving and
  to clear the station. It then runs the best parameters on all five drills
  with fresh seeds. The staff drills E2 and E4 are held out of the fit. Results
  go to `results/fits/`; adopt the parameters by copying `best.yaml` into
  `experiments/engines/rule_based.yaml`.
- **Comparing.** `compare_engines` writes `results/comparison/<time>/report.md`
  with four sections: fit to Proulx (including held-out error), cost and
  runtime, authoring effort, and variability across seeds.
- **Authoring effort.** Each engine's effort is recorded in
  `experiments/authoring_log.csv` (committed):
  - `monument fit` logs its searches automatically;
  - log manual work, such as editing the prompt, cue labels or parameters,
    with `monument log`.

## Analysis

`monument analyse NAME` runs one of the scripts in
`src/monument_evacuation/analysis/`. All of them read runs through `runs.py`.
`metrics.py` measures a run the same way for both engines, and `proulx_fit.py`
scores the measures against Proulx (1991).

| Script | What it shows |
|--------|---------------|
| `compare_engines` | The study report: LLM vs rule-based on all four dimensions |
| `compare_experiments` | Simulated E1–E5 timings against Proulx Table 1 (`proulx_1991.py`) |
| `evacuation_plots` | People remaining over time, per scenario |
| `compare_runs` | Two runs side by side |
| `escalator_plots` | Escalator flows and queues |
| `exit_usage_plots` | Per-exit use on a calibration day |
| `real_exit_usage_plots` | The same from logged Metro arrivals (`data/arrivals/`) |

## Layout

```
experiments/        configs: base.yaml, scenarios/, engines/, calibration/, batches/,
                    fits/; authoring_log.csv
geometry/monument/  station walkable areas, exits and network
data/               calibration inputs and logged train arrivals
src/monument_evacuation/
  cli.py            the `monument` command
  run.py, batch.py  one run; a matrix of runs
  fit.py            fitting an engine to Proulx
  authoring.py      the authoring-effort log
  paths.py          where everything lives
  analysis/         reading runs, Proulx reference data, plots
tools/              data collection and geometry helpers
docs/scenarios/     what each Proulx drill was and how it is modelled
tests/              regression and behaviour tests
results/            run outputs (not committed)
```

## Tests

```bash
pytest -m "not golden and not integration"   # fast unit tests (CI runs these)
pytest -m "golden or integration"            # full-geometry runs, a few minutes
```

The golden tests run short seeded simulations and compare a hash of their
outputs with snapshots in `tests/golden/`. A change in behaviour shows up as a
failure; re-record the snapshots only when the change is intended.
