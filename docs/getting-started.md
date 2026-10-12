# Getting started

Clone this repository and [evacusim](https://github.com/MJones235/llm-evacuation-sim)
side by side, then:

```bash
cd monument-evacuation
bash setup.sh                 # or: bash setup.sh /path/to/evacusim
source .venv/bin/activate
monument --help
```

`setup.sh` creates `.venv`, installs evacusim (editable) and this study, and
copies `.env.example` to `.env`. The LLM engine needs Azure credentials in
`.env` (`AZURE_LLM_ENDPOINT`, `AZURE_LLM_API_KEY`, `AZURE_LLM_MODEL`). The
rule-based engine and `--fake-llm` need none.

Your first run:

```bash
monument run E5 --engine rule_based
```

It takes about half a minute and writes
`results/E5/run_<time>_rule_based_s0/`. Open `manifest.json` first. The
files are described in [evacusim's outputs reference](https://github.com/MJones235/llm-evacuation-sim/blob/main/docs/outputs.md).

Then see [Running](how-to/running.md) for batches, videos and calibration
days.

## Layout

```
experiments/        configs
  base.yaml           the station, the population, shared staff
  scenarios/          E1–E5: what differs per drill
  engines/            llm.yaml, rule_based.yaml (fitted)
  calibration/        normal_day, test_window, validation_20261005
  batches/            scenario × engine × seed matrices
  fits/               parameter searches
  authoring_log.csv   the effort log
geometry/monument/  walkable areas, exits, escalator combs
data/               calibration inputs, logged train arrivals, hand counts
src/monument_evacuation/
  cli.py              the `monument` command
  run.py, batch.py    one run; a matrix of runs
  fit.py              fitting an engine to Proulx
  authoring.py        the authoring-effort log
  analysis/           metrics, the Proulx score, reports and plots
tools/              data collection and geometry helpers
tests/              golden runs and behaviour tests
results/            outputs (not committed)
```
