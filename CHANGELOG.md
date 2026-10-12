# Changelog

Changes to the study: scenarios, calibration, tooling and results. Pull
requests are on [GitHub](https://github.com/MJones235/monument-evac-sim/pulls).

## Unreleased

- Documentation site (MkDocs Material): the study, the drills, how-to guides,
  metrics, calibration, results, API.
- The video title comes from `video.title` (set in `base.yaml`);
  `monument video --title`.

## 2026-10-12: Fitting and comparison (#12)

- `monument fit` (Optuna) and `experiments/fits/rule_based.yaml`. The
  rule-based engine is fitted on E1/E3/E5 with E2/E4 held out, and the fitted
  parameters are adopted in `experiments/engines/rule_based.yaml`.
- `analysis/metrics.py` (time to start to move, clearance, cost),
  `analysis/proulx_fit.py`, and `monument analyse compare_engines`.
- The authoring-effort log (`monument log`, `experiments/authoring_log.csv`).
- `monument run --overlay`, `monument batch --engine`.
- Waiting passengers wait for their own platform's train
  (`target_from_zone`).

## 2026-10-12: Study-repo structure (#11)

- The `monument` command (`run`, `batch`, `video`, `analyse`) replaces the
  scripts. `src/monument_evacuation` is a package.
- `experiments/` reorganised: `scenarios/`, `engines/`, `calibration/` and
  `batches/`. `tools/` and `data/arrivals/` added.

## 2026-10-09: Scenarios match the drills (#10)

- Firefighters and the Fire Brigade restored; Proulx's crowd sizes; 15
  minutes for every drill; staff routes and patrols.

## 2026-10-09: Outputs (#9)

- Runs write a manifest and `decisions.csv`; exit-usage plots.

## 2026-10-08: Engine refactor, phases 0–4 (#3–#8)

- Golden-run tests, CI, the typed configuration, the decision seam, the
  runner fixes, and cue labels for the rule-based state machine.

## Earlier (#1, #2)

- Calibration from real Metro data, and escalator and routing fixes.
