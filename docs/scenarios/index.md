# The Proulx drills

In 1991 Guylène Proulx ran five unannounced evacuation drills at Monument
Metro station, Newcastle, each giving passengers different information. Her
thesis reports, for each drill, when the crowd on the concourse and the crowd
at the bottom of the North/South escalators **started to move**, and when the
station was **clear** (Table 1). The data are in
`src/monument_evacuation/analysis/proulx_1991.py`.

| | Information given | Concourse moves | Escalator crowd moves | Station clear | People |
|---|---|---:|---:|---:|---:|
| [E1](E1.md) | Fire alarm only | 8:15 | 9:00 | never (stopped at 14:47) | ~111 |
| [E2](E2.md) | Staff direct people; one PA | 2:15 | 3:00 | 8:00 | ~83 |
| [E3](E3.md) | Minimal PA, repeated | 1:15 | 7:40 | 10:30 | ~61 |
| [E4](E4.md) | Staff + PA to board the evacuation train | 1:15 | 1:30 | 6:45 | ~96 |
| [E5](E5.md) | Directive PA with the fire's location | 1:30 | 1:00 | 5:45 | ~103 |

Times are minutes:seconds after the alarm.

## Common to every scenario

- **15 minutes** after the alarm (`experiments/base.yaml`: 18,000 steps of
  0.05 s), and the alarm sounds at t = 15 s.
- **The fire is on the North/South escalators.** Escalators D, E and F close
  at the alarm. Platforms 1 and 2 must use B or C (via the platform-level
  passage), and Platforms 3 and 4 use B and C directly.
- **Four firefighters** stand at the top and bottom of the N/S escalators from
  the alarm, saying only "Please evacuate the station". In E1 the crowd
  ignored them for about 8 minutes, so their cue is **weak**.
- **The Fire Brigade** arrives later and patrols the concourse and the bottom
  of the N/S escalators with a **strong** cue: at 4:30 by default, at 8:00 in
  E1 and at 7:25 in E3, as observed.
- **People** are sampled at Proulx's crowd sizes, with knowledge profiles
  (`commuter`, `novice`) and roles (heading to a platform, waiting for a
  train, just arrived).

## Cue labels (rule-based engine)

The rule engine reads a `strength` and `instruction` per warning instead of
its text ([evacusim: events, cues and staff](https://github.com/MJones235/llm-evacuation-sim/blob/main/docs/concepts/events-and-staff.md)).
The labels follow one rule:

| Strength | Used for |
|---|---|
| weak | the alarm; the firefighters' "Please evacuate the station" (ignored for minutes in E1) |
| medium | a non-directive or general PA ("Please evacuate the station immediately") |
| strong | a directive PA naming the danger or the action; staff directing people; the Fire Brigade |

`instruction` is `board_train` where people are told to board, and
`leave_station` where they are told to leave.
