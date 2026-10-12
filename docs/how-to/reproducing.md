# Reproducing the results

Every figure and table comes from runs, and every run's `manifest.json`
records its configuration, seed and the commits of both repositories. To
reproduce a run exactly, check out those commits and run its `command`.

| Result | Command |
|---|---|
| The rule-based fit | `monument fit experiments/fits/rule_based.yaml --jobs 12` |
| The comparison runs | `monument batch experiments/batches/proulx_comparison.yaml --jobs 6` (`--engine rule_based` for the free half) |
| The comparison report | `monument analyse compare_engines` |
| E1–E5 against Proulx (one engine) | `monument analyse compare_experiments --engine rule_based` |
| People remaining over time | `monument analyse evacuation_plots --all` |
| Escalator diagnostics | `monument analyse escalator_plots --run results/<…>/run_…` |
| Exit use on a calibration day | `monument analyse exit_usage_plots` |
| Observed vs simulated Blackett Street | `monument analyse real_exit_usage_plots --counts data/calibration/collected/blackett-st-2026-05-10_10-03-31.csv --sim-run results/validation_20261005/run_…` |

The rule-based engine and `--fake-llm` are deterministic: the same seed,
config and code give byte-identical outputs. The golden tests rely on this:

```bash
pytest -m "golden or integration"     # about 2 minutes
```

A real LLM samples (temperature 0.7), so its runs reproduce only in
distribution. That is why every comparison uses several seeds.
