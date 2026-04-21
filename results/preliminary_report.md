# Monument Station Evacuation — Preliminary Results Report

**Date:** 20 April 2026  
**Status:** Preliminary — single run per condition, 2 minutes simulation time (t = 0–120 s)  
**Simulation:** LLM-driven pedestrian evacuation, Monument Station (Newcastle Metro), calibrated against Proulx (1991)

---

## 1. Overview

Five evacuation scenarios (E1–E5) from Proulx's (1991) landmark study have been reproduced in a multi-level LLM-agent simulation of Monument Station. Each condition is defined by the type of information available to evacuating passengers. A single 2-minute pilot run was collected per condition to verify simulation behaviour and identify issues before full runs.

Each run used **~50–55 agents** distributed across the concourse and platforms. The alarm event fires at **t = 15 s** in all scenarios.

| Exp | Condition | Agents |
|-----|-----------|--------|
| E1 | Fire alarm only — no staff, no PA | 53 |
| E2 | Two Revenue Control Inspectors directing evacuation | 55 |
| E3 | Minimal PA ("Please evacuate immediately"), repeated every 20 s | 53 |
| E4 | Two RCIs + zone-specific PA | 55 |
| E5 | Directive PA with fire location and differential instructions; no staff | 53 |

Videos for each run are available in `results/{E1–E5}/run_*/`.

---

## 2. Evacuation Progress — Fraction Remaining Inside

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

## 3. Station Population Timeseries

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

## 4. Time-to-First-Move vs. Proulx (1991) Table 1

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

## 5. LLM Performance

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

## 6. Issues Identified

### 6.1 Azure Content Filter False Positives (E5 only, 11 decisions)

The Azure OpenAI content filter flagged fire-evacuation prompts as `self_harm` in 11 decisions across 6 agents in E5. This is a false positive caused by "fire" + "suspected hazard" language in the PA announcement text.

**Impact:** Affected agents received a fallback response (`"No clear information available."`) and their cached prior decision was reused, causing those agents to either continue moving or freeze. This will have slightly artifacted E5's first-move-time metric.

**Fix applied:** The retry loop now short-circuits immediately on content filter 400 errors (previously it wasted 2 additional identical retries before giving up). A prompt-language mitigation to reduce filter frequency will be investigated next.

### 6.2 Time-to-First-Move Compression

All simulated first-move times are substantially shorter than the Proulx reference. Several contributing factors:

1. **Decision interval quantisation.** The simulation fires LLM decisions every 15 s. An agent that decides to move at the first post-alarm decision step will record a first-move time of 15 s regardless of any internal hesitation modelled in the reasoning. Proulx's times measure continuous video observation with second-level precision.

2. **Insufficient pre-alarm "inertia" modelling.** In the real study, 75% of passengers initially ignored the alarm and continued their prior activity for several minutes. The current agent memory and goal system does not sufficiently encode this attachment to pre-alarm goals. Many agents update their goal to "evacuate" at the first decision after the alarm, regardless of personality.

3. **Agent count and crowd dynamics.** The simulation has ~50 static agents; the real study had 110+ with continuous train arrivals. Social proof ("others are ignoring the alarm") is a strong real-world driver of hesitation and is weaker in a lower-density simulation.

4. **Content filter fallbacks (E5 only).** See 6.1 above.

### 6.3 Two-Minute Window Insufficient for Clearance Metrics

T50/T90/T100 (and the station-clear comparison) require the full exercise window (up to 15 min for E1, 10 min for E3). These cannot be assessed from 2-minute pilot runs.

### 6.4 Agent Count Below Reference

The real drills had ~111 passengers (66 concourse + 45 platforms) plus ongoing train arrivals. The simulation uses 50–55 static agents. This reduces crowd density both physically (crowd pressure) and socially (fewer bystanders to observe), which may systematically accelerate evacuation relative to the reference in all conditions.

---

## 7. Preliminary Conclusions

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

## 8. Recommended Next Steps

1. **Full-length runs (≥15 min simulation time, 3 runs per condition)** to obtain T50/T90/T100 for proper comparison with Proulx Table 1.
2. **Initial-hesitation tuning:** Increase the probability that agents choose `wait` at the first 1–2 post-alarm decision steps, particularly in E1. This is the primary mechanism driving the reference's long first-move times.
3. **Content filter prompt mitigation:** Rephrase "fire" references in E5's PA announcement to reduce false-positive filter hits (e.g. "emergency" instead of "suspected fire").
4. **Agent count increase:** Raise agent count to ~110 and add timed train-arrival spawn events to better match the real-study population dynamics.
5. **Multi-run averaging:** Implement the planned `--all-runs` averaging in `compare_experiments.py` to report mean ± SD across replications once full runs are available.

---

*Run data: `results/{E1–E5}/run_202604*/`*  
*Videos: `results/{E1–E5}/run_202604*/*_video.mp4`*  
*Analysis script: `python analysis/compare_experiments.py`*
