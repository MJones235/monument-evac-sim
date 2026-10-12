# E5 — PA with fire location and differential platform/concourse instructions

## Scenario

The fire alarm sounds at t=15 s. At t=20 s a repeated PA announcement gives specific,
directive information about both the incident and the appropriate response:

- **Incident**: "There is a suspected fire on the **North/South escalators** between
  the concourse and Platforms 1 and 2."
- **Platform passengers**: board the first available train.
- **Concourse passengers**: leave by the nearest street exit; do not use the lift.

No staff members are present. The N/S escalators are blocked at alarm time by fire
marshals (as in all five evacuations).

This is the verbatim PA wording from the real drill (Galea et al., 2008 / Proulx 1991).

## Hypothesis

Specific, location-aware PA instructions produce the fastest and safest evacuation:

- Concourse agents immediately move to street exits (understanding the fire is on the N/S
  escalators, which are already the blocked route for them).
- Platform agents board trains (the PA explicitly tells them to do so), clearing the
  platforms quickly compared to E3 where platform agents were left without guidance.
- Overall clearance should be faster than E1–E3 and competitive with E4.

## Key metrics

- Time for first concourse agents to start moving toward a street exit (compare to
  `time_to_move_concourse_s = 90 s` from Proulx Table 1).
- Time for first platform agents to start moving (compare to
  `time_to_move_escalator_s = 60 s`).
- Station clearance time (compare to `station_clear_s = 345 s`).
- Proportion of platform agents who board trains vs. use escalators.
- Comparison of exit choice distributions across E1–E5.

## Notes

This is the most informationally rich scenario and the most demanding for LLM reasoning.
It is also the most realistic model of how modern PA systems are used in practice.
