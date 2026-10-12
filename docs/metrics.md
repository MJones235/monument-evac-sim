# Metrics

`analysis/metrics.py` measures every run the same way for both engines. All
times are seconds after the alarm.

## Time to start to move

Proulx reports when "the crowd started to move" on the concourse and at the
bottom of the N/S escalators. The simulation measures:

- **Outbound decision:** `leave_by_train`, or `evacuate` towards anything but
  a down escalator. `evacuate` alone is not enough, because both engines also
  use it for an ordinary journey down to a platform.
- **A passenger starts to move** at the first decision of the unbroken run of
  outbound decisions they ended with. Someone who left without one, such as
  boarding a waiting train, starts when they left. Someone who stopped and set
  off again started when they set off again.
- **The crowds** are the passengers on the street level (concourse) or the
  platform level at the alarm who had not already started to move.
- **The crowd starts to move** when half of it has started. If half never
  does within the run, this is "never".

The platform-level crowd stands in for Proulx's crowd at the bottom of the N/S
escalators, which is where most of the platform level gathers once D, E and F
close.

## Clearance and progress

| Measure | Meaning |
|---|---|
| `clearance_s` | When the last passenger left; "never" if anyone was inside at the end. |
| `t50_s`, `t90_s` | When half / 90% of those present at the alarm had left. |
| `remaining_at_end` | Passengers still inside at the end. |

## Cost, effort and variability

| Measure | Meaning |
|---|---|
| `wall_time_s` | Wall-clock time of the run. |
| `decisions` | Decisions made (rows of `decisions.csv`). |
| `llm_requests`, `llm_tokens`, `llm_cost_gbp` | From `manifest.json` (LLM engine). |
| `repairs`, `fallbacks` | LLM decisions answered after a correction, or not at all. |
| `action_entropy_bits` | Shannon entropy of the actions chosen after the alarm. |

## Scoring against Proulx

`analysis/proulx_fit.py` compares the mean over seeds with Proulx.

- **"Never" counts as the end of the window.** For start-to-move and
  clearance, a run where it never happened is scored at the window's end
  (885 s), a lower bound, so the error is never overstated.
- **E1 clearance is a special case.** Proulx's E1 never cleared before the
  exercise stopped (887 s). It scores zero unless a run clears before then.
- **The fit's objective** is the RMSE over the three measures of the training
  drills.
- **Ordering** is Kendall's tau between the simulated and Proulx's order of
  the drills by clearance, from E1 (worst) to E5 (best).
