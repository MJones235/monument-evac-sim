# E2 — Station staff direct the evacuation

## Scenario

The fire alarm sounds at t=15s. Four station staff are present and immediately begin
directing passengers to the nearest exits. Staff are rule-based (not LLM-driven): they
move toward high-density areas and issue verbal directives to passengers within 12m.

## Hypothesis

Staff presence will reduce hesitation and increase the rate of immediate evacuation,
particularly for passengers with lower confidence or novice knowledge profiles.
Evacuation times should be shorter than E1 for the same agent population.

## Key metrics

- Time for 50% / 90% / 100% of agents to exit (compare to E1)
- Proportion of agents who change behaviour after receiving a staff directive
- Number of directive messages issued per staff member
- Staff movement patterns (where do they spend their time?)

## Notes

Staff are implemented as `StaffDirectorSystem` agents in `evacusim.systems.staff`.
They generate `DirectiveMessage` objects received by nearby passengers via the
existing `MessageSystem`.
