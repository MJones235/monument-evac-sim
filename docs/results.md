# Results

*Rule-based engine, fitted. 15 runs: E1–E5 × seeds 0–2, evacusim main and
study main, October 2026. Regenerate with `monument batch
experiments/batches/proulx_comparison.yaml --engine rule_based` and `monument
analyse compare_engines`.*

## The fit

The rule engine's response delays were fitted on E1, E3 and E5 (60 trials,
Optuna):

| Parameter | Fitted |
|---|---:|
| median delay after a weak cue (alarm, firefighters) | 804 s |
| … a medium cue (general PA, seeing others leave) | 403 s |
| … a strong cue (directive PA, staff, Fire Brigade) | 136 s |
| lognormal sigma | 0.52 |
| social cue | medium, when ≥ 21% of neighbours are leaving |

## Against Proulx (seconds after the alarm, mean ± SD over 3 seeds)

| | Concourse moves | | Escalator crowd moves | | Station clear | |
|---|---:|---:|---:|---:|---:|---:|
| | Proulx | sim | Proulx | sim | Proulx | sim |
| **E1** (fit) | 495 | 397 ± 6 | 540 | 567 ± 23 | never | never |
| **E2** (held out) | 135 | 178 ± 6 | 180 | 192 ± 50 | 480 | 796 ± 81 |
| **E3** (fit) | 75 | 275 ± 10 | 460 | 255 ± 10 | 630 | 590 ± 66 |
| **E4** (held out) | 75 | 137 ± 6 | 90 | 117 ± 25 | 405 | 517 ± 24 |
| **E5** (fit) | 90 | 123 ± 6 | 60 | 103 ± 15 | 345 | 366 ± 31 |

| | |
|---|---:|
| RMSE, fitted drills (E1, E3, E5) | 104 s |
| RMSE, held out (E2, E4) | 141 s |
| Kendall tau, E1–E5 clearance order | +0.80 |

## What it shows so far

- **Cue strength explains a lot.** With one delay per strength, the rule
  engine reproduces E1's long wait, E5's quick response, and Proulx's ordering
  of the drills, except one pair.
- **E3 is a structural misfit.** Its two crowds heard the same PA but
  responded 6 minutes apart; one cue cannot do both ([E3](scenarios/E3.md)).
- **The staff drills clear late.** People start moving close to Proulx's
  times, but a tail of slow responders holds the station open (E2 by about
  5 minutes, E4 by about 2). Staff directives may need to be a different kind
  of cue from a PA.
- **Cost:** about a minute and nothing per run.

The LLM half of the comparison is still to run.
