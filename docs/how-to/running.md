# Running simulations

## One run

```bash
monument run E1 --engine rule_based               # headless
monument run E4 --engine llm --seed 2 --video      # an MP4 afterwards
monument run E5 --engine llm --fake-llm            # LLM pipeline, no model, no cost
```

| Option | Effect |
|---|---|
| `scenario` | A name from `experiments/scenarios/` or `experiments/calibration/`, or a path to any config. |
| `--engine` | Overlays `experiments/engines/<engine>.yaml`. Without it, the scenario's own engine (LLM by default). |
| `--seed` | The master seed. Same seed and config, same run (rule-based or fake LLM). |
| `--overlay FILE` | Merge another config on top (repeatable), e.g. trial parameters. |
| `--agents`, `--max-steps` | Override the population size and duration, for quick checks. |
| `--start-time HH:MM` | Start a calibration day at a time of day, skipping earlier arrivals. |
| `--viewer`, `--spatial-viewer` | Live views while it runs. |

Results go to `results/<config name>/run_<time>_<engine>_s<seed>/`. Exit code
0 means finished, 1 failed (the manifest has the error), and 130 interrupted.

## A batch

A batch file lists scenarios, engines and seeds:

```yaml
# experiments/batches/proulx_comparison.yaml
scenarios: [E1, E2, E3, E4, E5]
engines: [rule_based, llm]
seeds: [0, 1, 2]
```

```bash
monument batch experiments/batches/proulx_comparison.yaml --dry-run      # list the runs
monument batch experiments/batches/proulx_comparison.yaml --engine rule_based --jobs 15
```

Each run is its own process. `--jobs` runs several at once (a rule-based
drill uses about one core). Logs and a `summary.json`, with each job's exit
code, duration and run directory, go to `results/batches/<batch>_<time>/`.

!!! warning "The LLM engine costs money"
    A real LLM run of a 15-minute drill makes on the order of a thousand
    requests. Try one run and check `manifest.json`'s `llm` block before you
    run a batch.

## A calibration day

```bash
monument run normal_day --start-time 07:30 --max-steps 36000   # 07:30–08:30 (dt 0.1 s)
monument run validation_20261005                               # the counted Monday morning
```

See [Calibration](../calibration.md).

## A video of a finished run

```bash
monument video results/E1/run_20261012_162724_rule_based_s0
```
