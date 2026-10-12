# Comparing the engines

```bash
monument batch experiments/batches/proulx_comparison.yaml --jobs 6
monument analyse compare_engines                     # the latest proulx_comparison batch
monument analyse compare_engines --runs results/E*/run_*_s[012]   # or any runs
```

`compare_engines` writes `results/comparison/<time>/` containing:

- `report.md`;
- `metrics.csv`, one row per run ([Metrics](../metrics.md));
- `fit.csv`, each measure against Proulx;
- two figures: the share of people still inside over time, with the range
  across seeds, and the time to start moving against Proulx.

The report has one section per research question:

1. **Fit to Proulx.**
    - Each measure, mean ± SD over seeds.
    - RMSE on the fitting drills (E1, E3, E5), the held-out drills (E2, E4) and
      all five.
    - Kendall's tau between the simulated and Proulx's E1–E5 clearance order.
2. **Cost and runtime.** Wall time, decisions, LLM requests, tokens and cost
   per run. Also repaired and fallback LLM decisions.
3. **Authoring effort.** What each engine needed written: engine parameters,
   cue labels in the scenarios (rule engine) and prompt-template lines (LLM).
   Also the work in the authoring log.
4. **Variability.** The coefficient of variation of clearance, and the entropy
   of the action mix. Also a sample of the reasons each engine gave.

## Authoring effort

`experiments/authoring_log.csv` (committed) records the work spent making each
engine fit the drills. `monument fit` logs its own searches: runs and compute
time. Log manual work as you do it:

```bash
monument log llm 45 "Reworded the PA section of the prompt; E3 agents ignored it"
monument log rule_based 20 "Relabelled E2 RCI directives strong" --runs 6
```

Log anything that changes how an engine behaves on the drills: prompts, cue
labels, parameters, scenario wording. Include the time spent judging results,
not only editing. The comparison is only as fair as this log.
