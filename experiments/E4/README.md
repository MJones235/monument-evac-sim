# E4 — Two RCIs + Station Controller PA (evacuation train)

## Scenario

Same RCI phase-based behaviour as E2, plus a Station Controller PA issued 5
seconds after the alarm (simulating the radio exchange with the Control Room).

**Events:**
- t=15s — Fire alarm
- t=20s — Station Controller PA (zone-differentiated):
  - Platform passengers: board the evacuation train, do not go to the concourse
  - Concourse passengers: leave via the nearest street exit
- t=40s — RCI concourse PA: general evacuation announcement

**RCI phases** (identical structure to E2):
- `rci_concourse`: alarm → run to concourse → hold + "leave the station" directive
- `rci_platforms`: alarm → run to concourse → return to platforms + "board the
  train" directive (consistent with PA instructions)

This scenario tests a non-standard evacuation flow where platform passengers are
directed *onto* trains rather than upstairs, while the concourse RCI prevents
additional passengers from descending to the platforms.

## Hypothesis

The combination of an authoritative PA (differentiating instructions by zone)
and an RCI physically reinforcing the platform message will increase compliance
with the train-boarding instruction compared to E3 (PA only). The split RCI
roles prevent conflicting signals reaching the same passengers.

## Key metrics

- Proportion of platform agents who board the train vs. use escalators
- Proportion of concourse agents redirected toward trains after the PA
- Time for 50% / 90% / 100% of agents to exit (via any route)
- Comparison of compliance with E2 (staff only) and E3 (PA only)
- Decision text analysis: do agents reason explicitly about the train option?

## Notes

RCIs are two `DirectorSystem` instances (`rci_concourse`, `rci_platforms`) using
`phases:` config with `trigger: on_reach_zone` transitions. Phase 2 messages for
`rci_platforms` are zone-differentiated via `messages_by_zone` to match the PA.
