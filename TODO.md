# Outstanding work

What each Proulx drill was and how it is modelled is in `docs/scenarios/`;
Proulx's Table 1 timings are in `src/monument_evacuation/analysis/proulx_1991.py`.

## Comparison study (next)

- `monument fit --engine rule_based`: fit the state-machine delays to Proulx
  Table 1 on E1/E3/E5 and hold out E2/E4 (the staff drills) for validation.
- `compare_engines`: one table and figure per dimension: fit to Proulx, cost
  and runtime, authoring effort, variability across seeds.
- Log every calibration iteration of either engine (prompt or parameter change,
  wall time) to `authoring_log.csv`.
- Average T50/T90/T100 and fraction remaining across seeds, with spread
  (`compare_experiments --all-runs` prints one table per run today).
- Pre-movement time can only be resolved to the decision cadence (each agent
  re-decides every `decision_interval`). E1 starts moving earlier than
  Proulx's 8:15. Consider a shorter interval for fitting.

## Scenario fidelity

- **Continuous train arrivals.** In the real drills, passengers kept arriving
  on trains. The scenarios spawn everyone at t=0, apart from the drills'
  scripted trains. Timed `train_arrival` events with alighting passengers would
  be closer.

## Documentation

- MkDocs site for this repository and evacusim: study overview, the
  scenarios, how to reproduce every figure, data provenance.
- The visualisation tools assume Monument's two levels and title.
