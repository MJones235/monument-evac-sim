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

### [TODO] Agent count calibration
Real study: ~66 passengers on the concourse + ~45 waiting at bottom of N/S escalators
+ continuous train arrivals ≈ 110+ agents over the exercise window.
Simulation: 50 static agents, no ongoing arrivals.
Document this as a calibration limitation in the README and/or compare_experiments output.
This may partly explain differences in absolute clearance times vs. reference values.

### [TODO] Continuous train arrivals
In the real drills passengers arrived continuously on trains throughout the exercise.
The simulation currently has a fixed 50-agent spawn with no subsequent arrivals.
Consider adding timed `train_arrival` events that spawn additional agents mid-simulation
to better reflect the dynamic population used in the real study.

---

## Metrics

### [TODO] Time-to-first-move metric
Post-process `agent_decisions.json` to extract the first decision timestep where each
agent's `action_type == "move"` and `target_type == "exit"` (post-alarm).
Report per-experiment: median and mean `time_to_first_move` for:
  - Concourse-starting agents (compare to `time_to_move_concourse_s` in reference)
  - Platform-starting agents (compare to `time_to_move_escalator_s` in reference)
Add this to `analysis/compare_experiments.py`.

### [TODO] Multi-run averaging in compare_experiments.py
Currently `--all-runs` outputs per-run tables.
Implement averaging of T50/T90/T100 and fraction-remaining across all runs per
experiment (with standard deviation) to reduce stochastic noise in results.

---

## Configuration

### [DONE] Monitoring interval reduced to 15 s
Changed from 60 s → 15 s in `experiments/base.yaml` to give sufficient resolution
for the 75–495 s timing values from Proulx Table 1.

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
