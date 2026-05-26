# Monument Evacuation — Outstanding Work

Calibrating and validating the simulation against Proulx (1991) five-drill dataset.

---

## Scenario Fidelity

### [DONE] Experiment output directories
Output now goes to `results/{experiment_id}/run_XXXXXX/` (was flat `results/run_XXXXXX/`).

### [DONE] Proulx Table 1 reference data
`analysis/proulx_1991.py` contains all Table 1 timing values for E1–E5 with source citations.

### [DONE] Comparison and plotting scripts
`analysis/compare_experiments.py` and `analysis/evacuation_plots.py` are fully implemented.

### [DONE] N/S escalator blocking
The North/South escalators (D/E/F bank, serving Platforms 1 and 2) are now blocked at
alarm time (t=15 s) in all five experiments via `type: block_exit` events in `base.yaml`.
This models the firemen powering off the escalators and physically blocking them.
Exits blocked: `escalator_d_down`, `escalator_e_up`, `escalator_f_up`.

### [DONE] Fire fighter agents
Four uniformed fire fighters are present in all five evacuations (added to `base.yaml`):
- Two at the **top** of the N/S escalators (concourse level)
- Two at the **bottom** of the N/S escalators (platform level, near Platforms 1/2)

They activate on the alarm event and hold position, broadcasting only:
> "Please evacuate the station."

The fully operational Fire Brigade arriving ~4–5 min post-alarm is modelled as a
`firefighter_brigade` director that activates via an `after_seconds: 270` phase trigger
(t ≈ 285 s) with the stronger message: "You must leave the station now."

### [DONE] Agent count calibration per experiment
Agent counts updated per experiment to better reflect Proulx Table 1 crowd sizes:
  - E1: 80 agents  (real study: ~111)
  - E2: 65 agents  (real study: ~83)
  - E3: 50 agents  (real study: ~61)
  - E4: 70 agents  (real study: ~35 station + 61 disembarking train ≈ 96)
  - E5: 70 agents  (real study: ~35 station + 68 disembarking trains ≈ 103)
These are computationally feasible approximations; social-proof effects in E1 will
remain weaker than the real study due to lower agent density.

### [TODO] Continuous train arrivals
In the real drills passengers arrived continuously on trains throughout the exercise.
The simulation currently has a fixed spawn at t=0 with no ongoing arrivals.
Consider adding timed `train_arrival` events that spawn additional agents mid-simulation
to better reflect the dynamic population used in the real study.

---

## Metrics

### [DONE] Time-to-first-move metric
`analysis/compare_experiments.py` post-processes `agent_decisions.json` to find
the first post-alarm decision where `action_type == "move"` for each agent.
Reports per-experiment median (post-alarm) split by starting zone:
  - Concourse-starting agents → compared to `time_to_move_concourse_s` in reference
  - Platform-starting agents  → compared to `time_to_move_escalator_s` in reference
New fields on `SimMetrics`: `tfm_concourse_median_s`, `tfm_platform_median_s`,
`tfm_concourse_n`, `tfm_platform_n`. Output appears as a dedicated table section.

### [TODO] Multi-run averaging in compare_experiments.py
Currently `--all-runs` outputs per-run tables.
Implement averaging of T50/T90/T100 and fraction-remaining across all runs per
experiment (with standard deviation) to reduce stochastic noise in results.

---

## Configuration

### [DONE] Simulation duration calibrated per experiment
max_iterations set per experiment to cover the full real-study exercise window:
  - E1: 18 000 steps (900 s = 15 min) — exercise ran to 14:47, station never cleared
  - E2: 12 000 steps (600 s = 10 min) — station cleared at 8:00 min
  - E3: 14 400 steps (720 s = 12 min) — station cleared at 10:30 min
  - E4: 10 000 steps (500 s ≈ 8:20)  — station cleared at 6:45 min
  - E5: 14 400 steps (720 s = 12 min) — last pram group at 10:15 min
Previously all experiments used the base default of 2 400 steps (120 s), which was far too
short to observe any clearance events or meaningful comparison with Proulx Table 1.

### [DONE] Train 124 added to E1 and E2
All five real drills were triggered by train 124 arriving at Monument Platform 1.
E1 and E2 configs now include a train_arrival event at t=10 s, platforms=[1],
dwell_seconds=30 (normal departure schedule; not an evacuation train).

### [DONE] Evacuation train dwell time corrected for E4 and E5
In the real drills, the evacuation train waited at all platforms until passengers
boarded (44/61 re-boarded in E4; 68/68 in E5).  dwell_seconds changed from 30 s
to 600 s in both E4 and E5 so the train is still available throughout the
evacuation window.

### [DONE] Fire Brigade physical arrival timing per experiment
firefighter_brigade trigger_after_seconds overridden in E1 and E3 to match
observed physical arrival times from Proulx Table 1 / Article 3:
  - E1: trigger_after_seconds=480 (8 min) — FB directed concourse crowd at 8:15 min
  - E3: trigger_after_seconds=445 (7:25 min onset → on-scene by ~7:40 min)
    • Also: patrol_zones changed to platform_def first (bottom of N/S escalators
      where the 48-person stuck crowd was in E3), then concourse.
Base default of 270 s (4.5 min notification call) retained for E2, E4, E5
where the station is clear before FB physical arrival matters.

### [DONE] E3 train dwell extended
dwell_seconds changed from 30 s to 60 s in E3 to allow agents a realistic time
window to choose whether to board before the train departs.

---

## Documentation

### [DONE] E5 README corrected
Describes the correct Proulx E5 scenario: directive PA with fire location, platform
passengers board trains, concourse passengers use alternative exits.

### [TODO] Create experiment run guide
Write a short `RUN_EXPERIMENTS.md` or expand the README with:
  - How to run each experiment: `python run_experiment.py experiments/E1/config.yaml`
  - How to run all five: a simple shell loop or Makefile target
  - How to compare results: `python analysis/compare_experiments.py`
  - How to generate plots: `python analysis/evacuation_plots.py`

---

## Experiments to Run

Once the above scenario-fidelity items are confirmed, run each experiment 3+ times:

```bash
for exp in E1 E2 E3 E4 E5; do
    for i in 1 2 3; do
        python run_experiment.py experiments/$exp/config.yaml --no-viewer
    done
done
```

Results go to `results/{experiment_id}/run_XXXXXX/`.

---

## Key Proulx (1991) Reference Values — Table 1

All times in seconds post-alarm:

| Exp | Move concourse | Move escalator | Station clear |
|-----|---------------|----------------|---------------|
| E1  | 495 s (8:15)  | 540 s (9:00)   | Never         |
| E2  | 135 s (2:15)  | 180 s (3:00)   | 480 s (8:00)  |
| E3  |  75 s (1:15)  | 460 s (7:40)   | 630 s (10:30) |
| E4  |  75 s (1:15)  |  90 s (1:30)   | 405 s (6:45)  |
| E5  |  90 s (1:30)  |  60 s (1:00)   | 345 s (5:45)  |

"Move concourse" = time until concourse crowd starts moving toward exits.
"Move escalator" = time until group at bottom of N/S escalators starts moving.
"Station clear"  = time until last agent leaves the station.

---

## Proulx Fire Marshal Setup (identical across all 5 drills)

- 4 uniformed fire fighters pre-positioned in staff room
- On alarm: emerge, split to top (2) and bottom (2) of N/S escalators
- Turn off escalator power; physically block passage
- Only verbal response to queries: **"Please evacuate the station."**
- "Fire do not enter" signs lit automatically at 3 entrances + top of N/S escalators
- Fully operational Fire Brigade arrived ~4–5 min post-alarm; gave "All Clear"
- In E3: firemen at bottom did NOT tell waiting passengers about an alternative route
