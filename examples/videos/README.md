# Example videos: the Proulx drills, rule-based engine

These videos show the five Proulx (1991) drills simulated with the fitted
rule-based decision engine, three seeds each. Each is 90 seconds and covers
the 15 minutes after the alarm at 10× speed. The drills are described in
[docs/scenarios](../../docs/scenarios/index.md).

Names follow `<scenario>_<description>_<engine>_seed<seed>.mp4`. The **seed**
sets everything random in a run: who the passengers are and where they start,
and how long each takes to react. The three seeds are three equally plausible
versions of the same drill, so differences between them show how much is
chance.

| Scenario | Proulx: concourse starts to move / station clear | Videos |
|---|---|---|
| E1, fire alarm only | 8:15 / never | `E1_alarm-only_rule-based_seed{0,1,2}.mp4` |
| E2, staff direct the evacuation | 2:15 / 8:00 | `E2_staff-direct_rule-based_seed{0,1,2}.mp4` |
| E3, minimal PA | 1:15 (escalator crowd 7:40) / 10:30 | `E3_minimal-pa_rule-based_seed{0,1,2}.mp4` |
| E4, staff and PA, board the evacuation train | 1:15 / 6:45 | `E4_staff-and-pa-board-train_rule-based_seed{0,1,2}.mp4` |
| E5, directive PA naming the fire | 1:30 / 5:45 | `E5_directive-pa_rule-based_seed{0,1,2}.mp4` |

## Reading a video

- **Top left:** the concourse (street level). **Top right:** the platforms.
  The clock counts from the start of the run; the alarm sounds at 00:00:15.
- **Red dots** are passengers. **Larger coloured dots** are staff:
  firefighters, the Fire Brigade and Revenue Control Inspectors.
- **Grey rectangles** on the platforms are trains while they are in the
  station.
- **Bottom:** each escalator as a conveyor. It shows riders by lane (stand or
  walk), the queue at the boarding end, and CLOSED for escalators D, E and F,
  which close at the alarm.

The video does not show a passenger's state, i.e. whether they are unaware,
aware or evacuating. That is in each run's `decisions.csv`.

## How they were made

Runs from 12 October 2026, made with
`monument batch experiments/batches/proulx_comparison.yaml --engine rule_based`:
evacusim `64f1ca0`, study `fed69b3`. Their manifests mark the study as dirty
because the fitted parameters had not been committed yet; they are the ones
committed in `d32a3a3` (`experiments/engines/rule_based.yaml`). Rendered with
`monument video <run>` at the default 10× speed.

To make the same videos for new runs:

```bash
monument batch experiments/batches/proulx_comparison.yaml --engine rule_based --jobs 15
monument video results/E1/run_<time>_rule_based_s0       # one per run
```

Results for these runs: [docs/results.md](../../docs/results.md).
