# E2 — Two Revenue Control Inspectors direct the evacuation

## Scenario

Based on the real Monument Station evacuation drill report. Two Revenue Control
Inspectors (RCIs) are on the platforms when the fire alarm sounds at t=15s.
They respond in two phases:

**Phase 1 — Both RCIs run to the concourse** (triggered by alarm)
Both RCIs immediately head upstairs to check the electronic notice board and
determine the location of the activated smoke detector.

**Phase 2 — Roles split once each RCI reaches the concourse**
- `rci_concourse`: Holds at the concourse, gives a PA at t=40s, and prevents
  passengers from entering or waiting. Concourse cleared ~3 min post-alarm.
- `rci_platforms`: Returns to the lower levels and patrols between platforms,
  directing remaining passengers to evacuate via the concourse escalators.
  Lower levels cleared ~5 min post-alarm.

RCIs are rule-based (no LLM). Phase transitions are driven by zone detection:
each RCI independently advances to phase 2 when they arrive at the concourse.

## Hypothesis

Split RCI roles (one holding the concourse, one clearing platforms) will be more
effective than undifferentiated patrol. Passengers receiving directives from a
recognised authority figure (Revenue Control Inspector) will respond more quickly
than in E1 (alarm only). Evacuation times should be shorter than E1.

## Key metrics

- Time for 50% / 90% / 100% of agents to exit (compare to E1)
- Proportion of agents who change behaviour after receiving an RCI directive
- Number of directive messages issued per RCI and per phase
- Time each RCI spends in phase 1 vs phase 2
- Concourse clearance time and platform clearance time

## Notes

RCIs are implemented as two separate `DirectorSystem` instances (`rci_concourse`,
`rci_platforms`) using the `phases:` config schema. Phase transitions use
`trigger: on_reach_zone` so each agent advances independently.
