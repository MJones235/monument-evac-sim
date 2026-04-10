# E5 — PA with detailed fire location and differential instructions

## Scenario

The fire alarm sounds at t=15s. At t=20s a PA announcement gives specific information:
- The fire is located near the Monument Street entrance on the concourse
- Platform passengers are told NOT to use the escalators and to await further instructions
- Concourse passengers are directed to alternative exits (Grey Street / Grainger Street)

No staff are present.

## Hypothesis

Detailed, actionable information will produce the most differentiated behaviour between
platform and concourse agents. Platform agents given "stay put" instructions represent a
real tension: following the PA conflicts with the general instinct to evacuate. This tests
whether LLM agents can reason about differential instructions and act appropriately.

Expected outcomes:
- Concourse agents avoid the Monument Street exit and use alternatives
- Platform agents show higher rates of hesitation / compliance with "stay" instruction
- Overall evacuation time may be longer than E3 (less clear single instruction)
  but safety-optimal behaviour (avoiding the fire) is higher

## Key metrics

- Proportion of concourse agents who use Grey St / Grainger St exits (vs. Monument St)
- Proportion of platform agents who remain on platforms after t=30s, t=60s
- Decision text analysis: do agents reference the fire location and differential instructions?
- Comparison of exit choice distributions across E1–E5

## Notes

This is the most informationally rich scenario and the most demanding for LLM reasoning.
It is also the most realistic model of how modern PA systems are used in practice.
