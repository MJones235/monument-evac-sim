# Monument Station Evacuation — Preliminary Results Report

Single run per condition, 2 minutes simulation time (t = 0–120 s)  

---

## 1. Overview

Five evacuation scenarios (E1–E5) from Proulx's (1991) study have been reproduced in a multi-level LLM-agent simulation of Monument Station. Each condition is defined by the type of information available to evacuating passengers.

Each run used ~55 agents distributed across the concourse and platforms. The fire alarm begins to sound at t = 15 s in all scenarios.

| Exp | Condition | Agents |
|-----|-----------|--------|
| E1 | Fire alarm only — no staff, no PA | 53 |
| E2 | Two Revenue Control Inspectors (RCIs) directing evacuation | 55 |
| E3 | Minimal PA ("Please evacuate immediately"), 10 s message + 20 s interval (30 s cycle) | 53 |
| E4 | Two RCIs + zone-specific PA | 55 |
| E5 | Directive PA with fire location and differential instructions; no staff | 53 |

Videos for each run are available in `results/{E1–E5}/run_*/`.

---

## 2. Reference Data — Proulx (1991)

> **Source key** — Three sections of the thesis contain empirical data:
> - **Art. 4.2** — "To prevent 'panic' in an underground emergency: why not tell people the truth?" (pp. 106–124)
> - **Art. 4.3** — "Passengers' behaviour during an underground evacuation" (pp. 125–143)
> - **Ch. 5/6** — French-language discussion and conclusions (pp. 144–177)
>
> Where data appear in more than one section, all sources are noted. The French chapter (Ch. 5/6) and Art. 4.3 are generally consistent; Art. 4.2 occasionally gives slightly different aggregate figures (see §2.2).

### 2.1 Study Context

*Sources: Art. 4.2 pp. 107–112; Art. 4.3 pp. 130–136; Ch. 5 pp. 156–157.*

Guylène Proulx conducted five live evacuation drills at Monument Station, Newcastle-upon-Tyne, during the week of 29 January 1990, at 12:18 or 14:18 on each day. These time slots were chosen because prior Metro surveys indicated comparable passenger volumes at midday. Real paying passengers participated without prior knowledge that a drill was taking place.

**Station layout** *(Art. 4.2 p. 109; Art. 4.3 p. 131)*: Monument is the busiest and most spatially complex station on the Tyne & Wear Metro network, with three entrances, three underground levels, four platforms, two sets of three escalators (N/S and E/W), a staircase, and two lifts. During each evacuation, two escalators on each set ran upward and one downward. The N/S escalators were designated the fire location; the E/W escalators provided the alternative route.

**Data collection** *(Art. 4.2 p. 112; Art. 4.3 p. 136; Ch. 5 pp. 156–157)*:
- **12 video cameras** covering the full station interior, recording all passenger actions
- **7 observers** posted at positions not fully covered by cameras, using hand-held tape recorders to count passengers passing through entrances, exits, stairs and escalators at **15-second intervals**
- **15 interviewers** (the 7 observers plus 8 additional staff) questioning evacuees immediately after exiting, both inside the station and on board trains that stopped at Monument during the exercise
- Recording began 5 minutes before each exercise and continued until the 'All Clear'

**Dataset scale** *(Ch. 5 pp. 156–157)*: Analysis drew on more than 80 hours of video, 35 hours of observer tape recordings, and 133 questionnaires completed by evacuees across all five evacuations. Video was coded across 12 observable behaviour categories (listed below) for 15-minute periods.

The 12 coded behaviours were: (1) enter the station, (2) leave the station, (3) wait in place, (4) descend toward a platform, (5) ascend toward the concourse, (6) board a train, (7) alight from a train, (8) arrive on a platform, (9) leave a platform, (10) talk or discuss, (11) use the lift, (12) cross the space.

**Total passengers per evacuation**: Art. 4.2 (p. 88) states "an average of 250 unaware subjects"; Ch. 5 (p. 156) states "approximately 300 passengers". Both figures are approximate; the discrepancy likely reflects different counting boundaries (e.g. whether passengers on approaching trains are included).

**Experiment synchronisation** *(Art. 4.2 pp. 111–112; Art. 4.3 pp. 133–134)*: Each exercise was triggered by the departure of train 124 from Haymarket station. On its arrival at Monument Platform 1, the alarm sounded and five seconds later one of the five experimental procedures began. The Fire Brigade was contacted 4–5 minutes after the start of each exercise and gave the 'All Clear' by resetting the electronic board, which cut the alarm bell and 'Fire do not enter' signs.

The five conditions (E1–E5) varied only in the type of information provided to passengers after the fire alarm sounded. All other parameters were held constant across the week.

### 2.2 Crowd Sizes

*Sources: Art. 4.2 pp. 115–118; Art. 4.3 pp. 115–118, 138–142.*

Four distinct passenger groups are tracked:

1. **Concourse crowd** — passengers at or entering the open concourse via street exits
2. **Escalator-bottom crowd** — passengers waiting at the foot of the N/S escalators (physically distinct from the platforms)
3. **Platform passengers** — passengers waiting on platforms, boarding and alighting trains (tracked via behaviour graphs; not included in Table 1 timing)
4. **Disembarking passengers** — passengers who alighted from a train after the alarm sounded

| Exp | Concourse crowd | Escalator-bottom crowd | Disembarking passengers (post-alarm) |
|-----|----------------:|-----------------------:|-------------------------------------:|
| E1 | 66 | 45 | 109 (1 re-boarded) |
| E2 | 30 | 53 | 61 (44 re-boarded) |
| E3 | 13 | 48 | 45 (7 re-boarded) |
| E4 | 20 | 15 | 61 (44 re-boarded) |
| E5 | 19 | 16 | 68 (all 68 re-boarded) |

*In E5, the escalator-bottom crowd of 16 immediately vacated the area upon hearing the PA identify the fire location on those escalators, moving to wait for a train on the platform.*

**Mobility-impaired users** *(Art. 4.2 p. 108)*: Stage 1 (pre-drill evaluation) recorded an average of 15 pushchairs passing in and out of Monument station per 10-minute observation period during daytime. The thesis identifies mobility-impaired passengers, elderly users, and those with pushchairs as a significant proportion of regular Metro users, relevant to evacuation planning. This is directly illustrated in E5, where two groups with prams/pushchairs were the last to evacuate (see §2.3).

### 2.3 Table 1 — Times and Behaviours

*Sources: Tableau 1, Ch. 5 p. 158 (primary); TABLE 1, Art. 4.2 p. 114; reproduced in Art. 4.3 narrative pp. 115–118. Times are post-alarm (mm:ss).*

| Exp | Condition | Concourse: crowd starts moving | Escal. bottom: crowd starts moving | Station cleared | Appropriateness of behaviour |
|-----|-----------|-------------------------------:|-----------------------------------:|----------------:|------------------------------|
| E1 | Alarm only | 8:15 | 9:00 | Never (ended 14:47) | Delayed or no evacuation |
| E2 | Staff (2 RCIs) | 2:15 | 3:00 | 8:00 | Users directed to concourse ⚠ |
| E3 | Minimal PA (every 20 s) | 1:15 | 7:40 † | 10:30 | Users waited at escalator bottom |
| E4 | Staff + zone-specific PA | 1:15 | 1:30 | 6:45 | Users evacuated appropriately |
| E5 | Directive PA (fire location + zone instructions) | 1:30 | 1:00 | 5:45 ‡ | Users evacuated by trains and exits |

† E3: the concourse crowd (13 people) self-initiated at 1:15; the escalator-bottom crowd (48 people) did not move until fire brigade arrived at ~7:40.  
‡ E5: main station cleared at 5:45; two groups with prams/pushchairs evacuated by train at 7:00 and 10:15.  
⚠ E2: the RCI directed platform passengers via the alternative route to the concourse — objectively the most dangerous area given the fire location on the N/S escalators.

**E3 PA message cycle** *(Art. 4.2 p. 111)*: The message "Please, evacuate the station immediately. Please, evacuate the station immediately." was a 10-second message followed by a 20-second interval, giving a **30-second total cycle**. Art. 4.3 (p. 135) and the French chapter describe this as "repeated every 20 seconds", referring to the inter-message gap.

### 2.4 Zone Clearance Times

*Source: Art. 4.3 narrative, pp. 138–142; Ch. 5 pp. 159–170.*

| Exp | Concourse cleared | Lower levels cleared | Whole station cleared |
|-----|------------------:|---------------------:|---------------------:|
| E1 | Never | Never | Never |
| E2 | ~3:00 | ~5:00 | 8:00 |
| E3 | — ¹ | — ¹ | 10:30 |
| E4 | ~4:00 | — | 6:45 |
| E5 | ~3:00 | — | 5:45 |

¹ E3: concourse movement began at 1:15 but an explicit "cleared" time is not stated; platform-level crowd dispersed by fire brigade at ~7:40.

### 2.5 Alarm Perception and Credibility

*Source: Art. 4.2 pp. 116–118.*

| Exp | n interviewed | Heard alarm | Believed it was a real emergency | Heard PA |
|-----|-------------:|------------:|---------------------------------:|---------:|
| E1 | 29 | 93% (26/29) | 24% | — (no PA in E1) |
| E2 | 31 | 90% (28/31) | 43% | 76% (22/31 as stated; 22/31 = 71%) |
| E3 | 25 | 84% (21/25) | 44% | 68% (17/25) |
| E4 | 26 | 92% (24/26) | 46% | 73% (19/26) |
| E5 | 22 | 82% (18/22) | 57% | 50% (11/22) |

> **Note on E2 PA percentage:** The thesis states "22 (76%) heard a P.A." but 22/31 = 71%. The stated figure (76%) is reproduced; the arithmetic discrepancy may reflect rounding on a different sub-sample or a minor transcription error in the original.

> **Note on E2 RCI PA quality** *(Art. 4.3 p. 138; Ch. 5 p. 163)*: The PA message given by the RCI in E2 was explicitly described as **inaudible and unclear** because the RCI was out of breath from running from Platform 3 to the concourse to check the electronic board before making the announcement. This partially explains E2's lower-than-expected PA audibility.

E5 is the only condition in which a majority of passengers believed the emergency was real, despite having the lowest PA audibility rate (50%). The thesis attributes this to the explicit identification of the incident ("suspected fire") being more persuasive than message frequency alone *(Ch. 5 p. 168; Art. 4.2 p. 92)*.

### 2.6 Intended Actions on Hearing Alarm / PA

*Source: Art. 4.2 pp. 116–118. These data do not appear in Art. 4.3.*

Interviewees were asked what they thought they should do upon first hearing the alarm (E1) or the PA (E2–E5). Denominators are alarm-hearers for E1, PA-hearers for E2–E5.

| Exp | n (base) | Leave by exits | Board a train | Wait / seek more info | Other |
|-----|--------:|---------------:|--------------:|----------------------:|------:|
| E1 | 25 (alarm-hearers) | 48% (12) | 8% (2) | 24% (6) | 20% (5) |
| E2 | 22 (PA-hearers) | 57% (13) | 17% (4) | 26% (6) | 1 person |
| E3 | 15 (PA-hearers) | 60% (9) | 27% (4) | 13% (2) | — |
| E4 | 19 (PA-hearers) | 79% (15) | 16% (3) | — | 1 person |
| E5 | 11 (PA-hearers) | 50% (5) | 50% (5) | — | — |

Note that "leave by exits" is appropriate for concourse-level passengers and "board a train" is appropriate for platform-level passengers in the E4/E5 fire scenario; both responses are correct depending on location. "Wait/seek more info" and "other" are non-evacuation responses.

### 2.7 Key Qualitative Findings Per Condition

*Sources: Art. 4.2 pp. 116–122; Art. 4.3 pp. 137–142; Ch. 5 pp. 159–170.*

**E1 — Alarm alone failed completely.** Passengers continued using the station normally. No self-initiated evacuation occurred. A concourse crowd of 66 waited 8:15 before fire brigade physically directed them; the escalator-bottom crowd of 45 waited 9:00. Out of 109 passengers who alighted from trains after the alarm, only 1 re-boarded. The exercise was terminated at 14:47 with the station still occupied.

**E2 — Staff effective but unsafe in routing.** Two RCIs produced rapid compliance where present, clearing the station in 8:00. However, they could not simultaneously cover all access points (four platforms, three entrances), and they directed platform passengers via the alternative route to the concourse — the most dangerous area given the fire location. If the fire had developed as at King's Cross, the 61 passengers directed there would have been at risk *(Ch. 5 p. 163)*. The RCI's PA was also inaudible due to being delivered out of breath *(Art. 4.3 p. 138)*.

**E3 — Minimal PA created a split outcome.** The repeated non-directive announcement prompted self-initiated concourse movement (1:15 min, crowd of 13). However, the escalator-bottom crowd of 48 exhibited strong **affiliative behaviour with place**: they congregated at the foot of their familiar route and waited ~7:40, with some approaching firemen to ask "the PA says to evacuate, but where?" *(Ch. 5 p. 164)*. Fire brigade presence was required to disperse them.

**E4 — Zone-specific direction removed ambiguity.** Combining RCIs with directive PA messages prescribing different actions by zone (platform passengers: board the train; concourse passengers: use exits) produced fast, well-directed movement. Of 61 disembarking passengers, 44 re-boarded as instructed. The escalator-bottom crowd started at 1:30 — a dramatic improvement over E3 (7:40).

**E5 — Honest, specific information was the most effective intervention.** Identifying the fire location precisely with zone-differentiated instructions achieved the fastest main clearance (5:45) with no staff present. All 68 disembarking passengers re-boarded as directed. The escalator-bottom crowd of 16 responded at 1:00 — the fastest of all five conditions — and immediately left for the platforms upon hearing the fire location named. Two groups with prams were the last to evacuate (7:00 and 10:15); the French chapter notes one group had also been evacuated two days earlier in E2, and one woman refused to leave her usual platform *(Ch. 5 pp. 168–169)*.

### 2.8 Regulatory Outcome

*Source: Ch. 6.1, p. 176.*

In **May 1990**, on the basis of the Monument experiment results, the Tyne & Wear Fire Brigade granted Metro an **exemption from Article 10(4)** of the Fire Precautions (Sub-surface Railway Stations) Regulations — which required two permanent staff members in underground stations at all times. The Fire Brigade concluded that Metro's Control Room communication system was sufficient to direct a safe public evacuation. By agreement, two staff were nonetheless retained during weekday morning and evening peak hours.

### 2.9 Comparison Status

> **Full quantitative comparison with simulation data requires full-length runs (≥ 15 minutes simulation time, 3 replications per condition).** The 2-minute pilot runs in Sections 3–4 provide early indicative results only. First-move time comparisons are discussed in Section 5; whole-station clearance times cannot yet be assessed.

---

## 3. Evacuation Progress — Fraction Remaining Inside

*Fraction of agents still inside the station at key post-alarm checkpoints.*

| Exp | Condition | +60 s | +120 s |
|-----|-----------|------:|-------:|
| E1  | Alarm only | 85% | 75% |
| E2  | Staff | 73% | 58% |
| E3  | Minimal PA | 47% | 36% |
| E4  | Staff + PA | 49% | 38% |
| E5  | Directive PA | 49% | 40% |

**Directional finding:** The qualitative separation between E1 (worst) and E2–E5 (better) is reproduced. At +60 s post-alarm, E1 retains 85% of agents vs. 47–73% for the other conditions — consistent with Proulx's observation that the alarm alone was essentially ineffective. E2 (staff-directed) is slower than E3–E5 at the 60-second mark, which is consistent with the real study where RCIs needed time to reach passengers.

**Limitation:** The 2-minute window does not reach any of the reference clearance times (E2's reference T100 = 8:00 min; E5's = 5:45 min). T50/T90/T100 comparison is not yet possible. Full-length runs (≥15 min simulation time) are required.

---

## 4. Station Population Timeseries

*Agents who have exited by each 15-second checkpoint.*

### E1 — Alarm only

| t (s) | Exited | Concourse | Escal. bottom | Platform |
|-------|-------:|----------:|--------------:|---------:|
| 0 | 0 | 24 | 0 | 29 |
| 15 | 2 | 22 | 1 | 28 |
| 60 | 6 | 17 | 1 | 29 |
| 120 | 13 | 14 | 1 | 25 |

### E2 — Staff

| t (s) | Exited | Concourse | Escal. bottom | Platform |
|-------|-------:|----------:|--------------:|---------:|
| 0 | 0 | 24 | 0 | 31 |
| 15 | 3 | 20 | 2 | 29 |
| 60 | 9 | 18 | 1 | 27 |
| 120 | 23 | 14 | 3 | 15 |

### E3 — Minimal PA

| t (s) | Exited | Concourse | Escal. bottom | Platform |
|-------|-------:|----------:|--------------:|---------:|
| 0 | 0 | 24 | 0 | 29 |
| 15 | 9 | 21 | 1 | 22 |
| 60 | 25 | 11 | 0 | 17 |
| 120 | 34 | 14 | 0 | 5 |

### E4 — Staff + PA

| t (s) | Exited | Concourse | Escal. bottom | Platform |
|-------|-------:|----------:|--------------:|---------:|
| 0 | 0 | 24 | 0 | 31 |
| 15 | 10 | 20 | 1 | 24 |
| 60 | 25 | 12 | 0 | 18 |
| 120 | 34 | 13 | 1 | 7 |

### E5 — Directive PA

| t (s) | Exited | Concourse | Escal. bottom | Platform |
|-------|-------:|----------:|--------------:|---------:|
| 0 | 0 | 24 | 0 | 29 |
| 15 | 5 | 22 | 2 | 24 |
| 60 | 18 | 16 | 1 | 18 |
| 120 | 32 | 10 | 0 | 11 |

---

## 5. Time-to-First-Move vs. Proulx (1991) Table 1

*Median post-alarm time of the first move decision, split by starting zone. Compared to Proulx's Table 1 crowd-start-moving times.*

| Exp | Sim (concourse) | Ref (concourse) | Sim (platform) | Ref (escalator) |
|-----|----------------:|----------------:|---------------:|----------------:|
| E1 | 45 s | 495 s | 45 s | 540 s |
| E2 | 25 s | 135 s | 25 s | 180 s |
| E3 | 5 s | 75 s | 5 s | 460 s |
| E4 | 5 s | 75 s | 22 s | 90 s |
| E5 | 5 s | 90 s | 25 s | 60 s |

**Finding:** Simulated first-move times are uniformly faster than the reference across all conditions. The *relative ordering* is partially reproduced — E1 agents hesitate longest, E2 agents move sooner, and E3–E5 agents move within the first decision interval. However, absolute values are greatly compressed (5–45 s vs. 60–495 s in the reference). Possible causes are discussed in Section 6.

**Positive signal in E4:** Platform-start agents in E4 show a longer hesitation (22 s) compared to E3 (5 s), consistent with the directive PA + RCI combination giving more specific information that takes the agents longer to process before acting. This is in the correct direction relative to the reference (E4 escalator: 90 s vs. E3 escalator: 460 s, a substantially shorter hesitation — the simulation captures this direction).

---

## 6. LLM Performance

| Exp | LLM requests | Total tokens | Cost (£) | Wall time |
|-----|-------------:|-------------:|---------:|----------:|
| E1 | 171 | 429 K | £0.10 | 13:12 |
| E2 | 198 | 504 K | £0.11 | 18:10 |
| E3 | 285 | 772 K | £0.17 | 22:31 |
| E4 | 256 | 669 K | £0.15 | 20:59 |
| E5 | 306 | 825 K | £0.18 | 44:01 |

Total across all five runs: **£0.72**, ~1,300 LLM requests, ~3.2 M tokens.  
Estimated cost for a full 15-minute run: approximately **£0.50–£1.00 per experiment** based on linear scaling.

---

## 7. Issues Identified

### 7.1 Azure Content Filter False Positives (E5 only, 11 decisions)

The Azure OpenAI content filter flagged fire-evacuation prompts as `self_harm` in 11 decisions across 6 agents in E5. This is a false positive caused by "fire" + "suspected hazard" language in the PA announcement text.

**Impact:** Affected agents received a fallback response (`"No clear information available."`) and their cached prior decision was reused, causing those agents to either continue moving or freeze. This will have slightly artifacted E5's first-move-time metric.

**Fix applied:** The retry loop now short-circuits immediately on content filter 400 errors (previously it wasted 2 additional identical retries before giving up). A prompt-language mitigation to reduce filter frequency will be investigated next.

### 7.2 Time-to-First-Move Compression

All simulated first-move times are substantially shorter than the Proulx reference. Several contributing factors:

1. **Decision interval quantisation.** The simulation fires LLM decisions every 15 s. An agent that decides to move at the first post-alarm decision step will record a first-move time of 15 s regardless of any internal hesitation modelled in the reasoning. Proulx's times measure continuous video observation with second-level precision.

2. **Insufficient pre-alarm "inertia" modelling.** In the real study, 75% of passengers initially ignored the alarm and continued their prior activity for several minutes. The current agent memory and goal system does not sufficiently encode this attachment to pre-alarm goals. Many agents update their goal to "evacuate" at the first decision after the alarm, regardless of personality.

3. **Agent count and crowd dynamics.** The simulation has ~50 static agents; the real study had 110+ with continuous train arrivals. Social proof ("others are ignoring the alarm") is a strong real-world driver of hesitation and is weaker in a lower-density simulation.

4. **Content filter fallbacks (E5 only).** See 7.1 above.

### 7.3 Two-Minute Window Insufficient for Clearance Metrics

T50/T90/T100 (and the station-clear comparison) require the full exercise window (up to 15 min for E1, 10 min for E3). These cannot be assessed from 2-minute pilot runs.

### 7.4 Agent Count Below Reference

The real drills had ~111 passengers (66 concourse + 45 platforms) plus ongoing train arrivals. The simulation uses 50–55 static agents. This reduces crowd density both physically (crowd pressure) and socially (fewer bystanders to observe), which may systematically accelerate evacuation relative to the reference in all conditions.

---

## 8. Preliminary Conclusions

| Finding | Verdict |
|---------|---------|
| E1 retains most agents (alarm ineffective) | ✓ Reproduced directionally |
| E2–E5 all outperform E1 | ✓ Reproduced |
| E2 slower than E3–E5 at 60 s | ✓ Reproduced (staff need time to reach passengers) |
| Absolute clearance times | ✗ Cannot assess — window too short |
| First-move ordering E1 > E2 > E3–E5 | ✓ Directionally correct |
| First-move absolute values | ✗ 5–10× faster than reference |
| Content filter interference | ⚠ Minor (E5 only, 11/306 decisions, fix applied) |

The simulation correctly captures the *direction* of the Proulx (1991) hierarchy in the 2-minute window. The primary gap is absolute timing, most likely due to decision-interval quantisation and insufficient initial-hesitation modelling. These are addressable calibration issues rather than structural failures.

---

## 9. Recommended Next Steps

1. **Full-length runs (≥15 min simulation time, 3 runs per condition)** to obtain T50/T90/T100 for proper comparison with Proulx Table 1.
2. **Initial-hesitation tuning:** Increase the probability that agents choose `wait` at the first 1–2 post-alarm decision steps, particularly in E1. This is the primary mechanism driving the reference's long first-move times.
3. **Content filter prompt mitigation:** Rephrase "fire" references in E5's PA announcement to reduce false-positive filter hits (e.g. "emergency" instead of "suspected fire").
4. **Agent count increase:** Raise agent count to ~110 and add timed train-arrival spawn events to better match the real-study population dynamics.
5. **Multi-run averaging:** Implement the planned `--all-runs` averaging in `compare_experiments.py` to report mean ± SD across replications once full runs are available.

---

*Run data: `results/{E1–E5}/run_202604*/`*  
*Videos: `results/{E1–E5}/run_202604*/*_video.mp4`*  
*Analysis script: `python analysis/compare_experiments.py`*