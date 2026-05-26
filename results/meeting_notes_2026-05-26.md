# Monument evacuation model: meeting notes (26 May 2026)

## 1) What we are doing

- Build an LLM-agent evacuation model of Monument station.
- Reproduce the five Proulx (1991) drill conditions (E1-E5).
- Calibrate first to E1 (alarm-only), then validate on E2-E5.
- Overall goal: demonstrate an adaptive evacuation model where behavior changes realistically when scenario inputs change (alarm/staff/PA, blocked routes, train availability, etc.).
- Planning goal: allow evacuation strategies to be tested under new conditions without reprogramming agents for each new scenario.
- Population goal: handle changing crowd size and composition (for example, event-day surges or demographic shifts) and estimate how those changes affect outcomes such as first-move times and clearance.

## 2) What has been achieved so far

- E1-E5 scenario configs are implemented and aligned to the study conditions.
- Key infrastructure is in place: multi-level geometry, blocked N/S escalators, staff/director systems, event system, run outputs, and comparison scripts.
- Pilot runs completed for all five experiments (Apr 2026, ~2 min windows).
- Multiple longer E1 runs completed (May 2026), including runs with behavior-prior prompting.
- Comparison tooling exists (`analysis/compare_experiments.py`) to extract T50/T90/T100, fraction remaining, and first-move metrics.

## 3) The five experiments (scenario + people)

- E1: Alarm only, no staff, no PA.
- E2: Two RCIs direct evacuation.
- E3: Minimal repeated PA: "Please evacuate immediately".
- E4: Two RCIs + zone-specific PA (platform board train, concourse use exits).
- E5: Directive PA with fire location + differential instructions, no staff.

People counts in the real drill (Proulx)
- E1: ~111 people (66 concourse + 45 escalator-bottom).
- E2: ~83 people (30 concourse + 53 escalator-bottom).
- E3: ~61 people (13 concourse + 48 escalator-bottom).
- E4: ~96 people (~35 already in station + 61 disembarking passengers).
- E5: ~103 people (~35 already in station + 68 disembarking passengers).

## 4) Output data and behavior observed

Reference targets from Proulx (post-alarm)
- E1: move concourse 495s, move escalator 540s, never fully cleared.
- E2: 135s, 180s, clear 480s.
- E3: 75s, 460s, clear 630s.
- E4: 75s, 90s, clear 405s.
- E5: 90s, 60s, clear 345s.

Pilot simulation outputs (Apr runs, 2 min window)
- E1 (53 agents): first-move medians 45s (concourse) / 45s (platform); 75.5% still inside at +120s.
- E2 (55): 25s / 25s; 58.2% still inside at +120s.
- E3 (53): 5s / 5s; T50 reached at +105s; 49.1% still inside at +120s.
- E4 (55): 5s / 22.5s; T50 reached at +60s; 38.2% still inside at +120s.
- E5 (53): 5s / 25s; T50 reached at +60s; 39.6% still inside at +120s.

Pilot summary
- Directional ranking is partly sensible (E1 worst, E4/E5 best in early window).
- Absolute timing is too fast throughout.

Second experiment: behavioural priors (long E1 runs)
- We inserted this explicit prior into the prompt for alarm-only situations with no visible fire / no added instructions: ~10% evacuate immediately, ~15% decide to leave but delay, ~75% initially hesitate / wait / ignore at first.
- E1 slowed down: first-move shifted from ~25s / ~25s (concourse/platform, before priors) to 115s / 430s (after priors).
- This is clearly closer to E1 targets (495s / 540s), but not a perfect match.
- A perfect single-run match is not expected; this should be tested across multiple runs with varying population structure.

## 5) Key methodological concern

- Current prompt-based behavioral priors help numerically, but this risks "telling the model what to do" rather than getting behavior from situation reasoning.
- We likely need a stronger person/decision model so hesitation emerges from cues and beliefs, not mainly from top-down percentages.

## 6) Next steps (short list)

- Define agent attributes explicitly from literature (e.g., age, mobility, familiarity, risk perception, social influence, trust in alarms/messages).
- Formalize decision mechanism using a protective-action style framework (environmental cue -> interpretation -> action selection), including explicit false-alarm belief handling.
- Run E1 sensitivity sweeps over plausible person-mix assumptions and show whether observed E1 metrics fall within the modeled range.
- Then run full-length validation for E2-E5 (>= 3 replications each) and compare against Proulx timings.
- Test multiple LLMs with the same scenario/config to quantify model dependence.
- Fix result-pipeline hygiene (ensure all runs write full timeseries; add multi-run averaging + uncertainty reporting).

## 7) Suggested line to use in the meeting

- "We have a working experimental platform and can reproduce directional differences between scenarios, but we are not yet calibrated on absolute timings. E1 calibration is the immediate priority, then full-length validation on E2-E5 with replications and sensitivity analysis."