# E4 — Staff assist + PA instructs passengers to board trains to evacuate

## Scenario

The fire alarm sounds at t=15s. At t=20s a PA announces that evacuation trains are being
dispatched and asks passengers to board them. Four staff members are present and direct
passengers toward platforms, consistent with the PA message.

## Hypothesis

This scenario reverses the typical evacuation flow (away from platforms) and instead
directs passengers *onto* trains. This tests whether:
- Agents comply with a non-standard instruction that conflicts with their initial instinct
  to leave the building
- Staff reinforcing the PA message increases compliance
- Agents already heading for surface exits are redirected to platforms

## Key metrics

- Proportion of agents who move toward platforms (vs. surface exits) after t=20s
- Time for 50% / 90% / 100% of agents to exit (noting "exit" may be via train)
- Comparison of compliance rates with E2 (staff only) and E3 (PA only)
- Decision text analysis: do agents reason about the train option explicitly?

## Notes

This scenario requires the simulation to handle "evacuation by train" as an exit type.
Platform exits may need to be configured differently from surface exits in the geometry.
