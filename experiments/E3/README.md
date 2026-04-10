# E3 — Public address system: generic evacuation instruction

## Scenario

The fire alarm sounds at t=15s. At t=20s a PA announcement instructs all passengers
to evacuate immediately via the nearest exit. No staff are present.

## Hypothesis

A clear PA instruction will increase the evacuation rate compared to E1 (alarm only),
but may be less effective than direct staff interaction (E2) because it is impersonal
and some passengers may discount it or be unsure it applies to them.

## Key metrics

- Time for 50% / 90% / 100% of agents to exit (compare to E1, E2)
- Proportion of agents who begin moving toward an exit within 30s of the PA
- Decision text analysis: do agents reference the PA in their reasoning?

## Notes

The PA is implemented as a broadcast `EventManager` message with `type: pa_announcement`,
which is rendered differently in agent observations compared to ambient alarm events.
