# Fitting an engine to Proulx

`monument fit` searches an engine's parameters so that its runs match Proulx's
Table 1.

```bash
monument fit experiments/fits/rule_based.yaml --jobs 12
```

The fit file says what to fit, on which drills, and how hard to search:

```yaml
engine: rule_based
train: [E1, E3, E5]          # fitted on
held_out: [E2, E4]           # never seen by the search
seeds: [0, 1, 2]             # per trial
validation_seeds: [100, 101, 102, 103, 104]
trials: 60
parameters:                  # dotted config keys
  decision.response_median_s.weak: {low: 60, high: 1200, log: true}
  decision.social.strength: {choices: [weak, medium, strong]}
  ...
```

Each trial does the following:

1. Writes the proposed parameters as an overlay.
2. Runs every training drill with every seed (`monument run --overlay`).
3. Measures the runs and scores them: the root-mean-square error in seconds
   over each drill's three measures. See [Metrics](../metrics.md).

Optuna's TPE sampler proposes trials. The best trial is then run on **all**
drills with fresh seeds, so the reported error is not flattered by the seeds
the search used. The staff drills E2 and E4 are held out: they test whether
the fitted response delays carry over to staff instructions.

Output, in `results/fits/<fit>_<time>/`:

| File | Contents |
|---|---|
| `trials.csv` | every trial: parameters, RMSE, and each measure's error |
| `best.yaml` | the best parameters as an overlay |
| `validation/metrics.csv` | the validation runs, one row each |
| `report.md` | training and held-out error per drill and measure |

To adopt the result, copy `best.yaml` into `experiments/engines/<engine>.yaml`
with a comment saying where it came from. Then re-record the rule-based golden
snapshot: `UPDATE_GOLDEN=1 pytest -m golden -k rule_based`.

A fit is logged automatically in the [authoring log](comparing.md#authoring-effort).

!!! warning "Do not change the code during a fit"
    Every simulation starts a fresh process that imports evacusim and reads
    `experiments/` as they are *then*. Edits during a fit (about 1.5 hours
    for 60 trials) produce trials from different code.

`--trials 2 --max-steps 3000 --no-log` checks the tooling quickly without
logging it.
