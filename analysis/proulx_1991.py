"""
Ground-truth reference data from Proulx (1991).

Guylène Proulx, "Variations de l'information livrée aux usagers pendant
l'évacuation d'urgence d'une station de métro et développement d'un modèle de
stress." PhD thesis, Université de Montréal, 1991.

Five live evacuation drills were conducted at Monument Station,
Newcastle-upon-Tyne (Tyne & Wear Metro), each exposing real passengers to a
different information condition:

  E1 — Fire alarm only (no staff, no PA)
  E2 — Two Revenue Control Inspectors direct the evacuation on foot
  E3 — Minimal PA ("Please evacuate the station immediately."), repeated every 20 s
  E4 — Two RCIs + zone-specific PA directing platform passengers to board the
        evacuation train and concourse passengers to use street exits
  E5 — Rich PA: identifies fire location (North/South escalators), gives
        differential instructions by zone, repeated every 20 s; no staff

All times below are measured from when the fire alarm first sounds (t_alarm).
In the simulation the alarm event fires at t=15 s, so:

    sim_time = t_alarm_relative + 15

Sources — directly extracted from the thesis text (Proulx 1991):
  • TABLE 1 (English article, p. 114–115): "Times and movement for the 5
    evacuations (in mins:secs)" — primary tabular source.
  • Article 3 narrative (pp. 139–142): per-zone clearance descriptions.
  • General discussion (pp. 158–165): French summary with additional detail.

TABLE 1 (verbatim structure)
─────────────────────────────────────────────────────────────────────
                        Time to start to move   Time to clear
Evacuation            Concourse  Bottom escal.   the station
─────────────────────────────────────────────────────────────────────
E1  Bell only          8:15        9:00          exercise ended 14:47
                                                 (station never cleared)
E2  Staff              2:15        3:00          8:00
E3  PA (minimal)       1:15        7:40          10:30
E4  Staff + PA+        1:15        1:30          6:45
E5  PA++ (directive)   1:30        1:00          5:45  (10:15 last group)
─────────────────────────────────────────────────────────────────────
Note: E5 cleared except two groups with prams/pushchair at 7:00 and 10:15.

Additional zone detail from Article 3 narrative:
  E2: concourse cleared ~3 min post-alarm; lower levels ~5 min post-alarm.
  E3: concourse movement started at 1:15; bottom-of-escalator crowd (48
      people) did not move until firemen arrived at ~7:40 min.
  E4: concourse cleared ~4 min post-alarm (Article 3, p. 140).
  E5: concourse cleared ~3 min post-alarm; platform-level crowd at bottom
      of N/S escalators moved immediately on hearing "suspected fire" line.
"""

from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ZoneClearance:
    """Time in seconds (post-alarm) at which a zone was fully cleared."""
    concourse_s: Optional[float]   # time from alarm until concourse empty
    platform_s: Optional[float]   # time from alarm until all platforms empty
    whole_station_s: Optional[float]  # time from alarm until last person exited


@dataclass
class ExperimentReference:
    """Observed outcomes for one Proulx (1991) evacuation trial."""
    experiment_id: str
    description: str

    # Zone clearance times (seconds post-alarm; None = not observed / exceeded).
    clearance: ZoneClearance

    # Time from alarm until half-or-more of the crowd at each location started
    # moving (seconds post-alarm).  Measured from video recording.  These are
    # the primary per-condition discriminators (Table 1).
    time_to_move_concourse_s: Optional[float]   # crowd at open concourse area
    time_to_move_escalator_s: Optional[float]   # crowd at bottom of N/S escalators

    # Fraction of passengers who had *started moving toward an exit* within
    # 60 s of the alarm (0–1).  None = not reliably quantified.
    immediate_response_rate: Optional[float]

    # Qualitative outcome from the thesis summary.
    outcome: str

    # Key behaviours noted by Proulx.
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

REFERENCE: dict[str, ExperimentReference] = {
    "E1": ExperimentReference(
        experiment_id="E1",
        description="Fire alarm only — no staff, no PA",
        clearance=ZoneClearance(
            # Exercise terminated at 14:47 min; station was NEVER fully cleared.
            # Concourse crowd (66 people) started moving only at 8:15 min when
            # the fire brigade arrived.  Bottom-escalator crowd (45 people) moved
            # at 9:00 min when the FB told them to leave.  (Table 1; p. 115)
            concourse_s=None,       # not cleared before exercise ended
            platform_s=None,        # not cleared before exercise ended
            whole_station_s=None,   # exercise terminated at 887 s; never clear
        ),
        # Time to start moving: 8:15 (concourse), 9:00 (bottom escalator)
        time_to_move_concourse_s=495.0,   # 8 min 15 s
        time_to_move_escalator_s=540.0,   # 9 min 00 s
        immediate_response_rate=None,  # effectively 0 — no self-initiated evac
        outcome=(
            "Complete failure. Passengers continued circulating normally. "
            "The alarm alone did not trigger evacuation behaviour. "
            "Exercise was terminated at 14:47 min with the station still occupied."
        ),
        notes=[
            "Alarm alone insufficient to initiate evacuation.",
            "93% heard the alarm; 76% thought it was not a real emergency.",
            "Crowd of 66 at concourse waited 8:15 before FB moved them.",
            "Crowd of 45 at bottom of N/S escalator waited 9:00 min.",
            "This is the control condition against which E2–E5 are compared.",
        ],
    ),

    "E2": ExperimentReference(
        experiment_id="E2",
        description="Two Revenue Control Inspectors direct the evacuation",
        clearance=ZoneClearance(
            # Article 3, p. 139: "3 minutes after the alarm the concourse was
            # cleared."  "The lower levels were cleared 5 minutes after the
            # alarm."  Table 1: whole station clear at 8:00 min.
            concourse_s=180.0,        # ~3 min post-alarm
            platform_s=300.0,         # ~5 min post-alarm (lower levels clear)
            whole_station_s=480.0,    # 8:00 min post-alarm (table 1)
        ),
        # Time to start moving: 2:15 (concourse crowd of 30), 3:00 (escalator crowd of 53)
        time_to_move_concourse_s=135.0,   # 2 min 15 s
        time_to_move_escalator_s=180.0,   # 3 min 00 s
        immediate_response_rate=None,
        outcome=(
            "Whole station cleared 8:00 min post-alarm. Concourse cleared ~3 min, "
            "lower levels ~5 min. Fast but passengers were directed via the "
            "fire-affected (N/S escalator) route to the concourse — objectively unsafe."
        ),
        notes=[
            "Split RCI roles: one holding concourse, one clearing platforms.",
            "Passengers responded immediately to RCI directives.",
            "Staff could not cover all access points simultaneously.",
            "Passengers directed to concourse across the 'fire' location — unsafe route.",
            "90% heard alarm; 76% still thought it was not a real emergency.",
        ],
    ),

    "E3": ExperimentReference(
        experiment_id="E3",
        description="Minimal non-directive PA repeated every 20 s",
        clearance=ZoneClearance(
            # Table 1: station cleared 10:30 min post-alarm (under FB supervision).
            # Article 3, p. 140: concourse crowd (13 people) moved at 1:15 min;
            # bottom-of-escalator crowd (48 people) waited until FB arrived at
            # ~7:40 min.
            concourse_s=None,         # movement only; concourse not explicitly
                                      # 'cleared' at a stated time
            platform_s=None,          # lower levels cleared by FB ~7:40+ min
            whole_station_s=630.0,    # 10:30 min post-alarm (Table 1)
        ),
        # Time to start moving: 1:15 (concourse), 7:40 (escalator — only when FB arrived)
        time_to_move_concourse_s=75.0,    # 1 min 15 s
        time_to_move_escalator_s=460.0,   # 7 min 40 s (FB-initiated)
        immediate_response_rate=None,
        outcome=(
            "Station cleared 10:30 min post-alarm (with FB assistance). Clear "
            "improvement over E1: concourse crowd moved at 1:15 min. However "
            "bottom-of-escalator crowd (48 people) waited ~7:40 min until "
            "fire brigade arrived to disperse them."
        ),
        notes=[
            "Minimal PA ('Please evacuate the station immediately.') better than alarm only.",
            "Platform-level crowd at bottom of N/S escalators did not self-evacuate.",
            "Affiliative behaviour: familiar route blocked → passengers waited rather"
            " than seeking alternative route.",
            "56% still thought it was not a real emergency.",
        ],
    ),

    "E4": ExperimentReference(
        experiment_id="E4",
        description="Two RCIs + zone-specific PA (platform: board train; concourse: street exit)",
        clearance=ZoneClearance(
            # Article 3, p. 140: "Four minutes after the alarm the concourse was
            # cleared."
            # Table 1: whole station cleared 6:45 min post-alarm.
            concourse_s=240.0,        # ~4 min post-alarm
            platform_s=None,          # platform levels cleared by combined RCI+PA;
                                      # exact sub-5-min time not stated separately
            whole_station_s=405.0,    # 6:45 min post-alarm (Table 1)
        ),
        # Time to start moving: 1:15 (concourse crowd of 20), 1:30 (escalator crowd of 15)
        time_to_move_concourse_s=75.0,   # 1 min 15 s
        time_to_move_escalator_s=90.0,   # 1 min 30 s
        immediate_response_rate=None,
        outcome=(
            "Station cleared 6:45 min post-alarm. Concourse cleared ~4 min. "
            "Joint RCI + directive zone-specific PA produced rapid, well-directed "
            "evacuation. 44 of 61 disembarking passengers re-boarded the train."
        ),
        notes=[
            "Fastest staff-assisted condition after E5.",
            "Zone-targeted PA removed ambiguity about which exit/route to use.",
            "92% heard alarm; 73% heard PA; 79% of PA-hearers chose correct action.",
            "54% still thought it was not a real emergency (lowest after E5).",
        ],
    ),

    "E5": ExperimentReference(
        experiment_id="E5",
        description="Rich directive PA with fire location + differential zone instructions; no staff",
        clearance=ZoneClearance(
            # Article 3, p. 140: "This level [concourse] was cleared 3 minutes
            # after the alarm was sounded."  Table 1: station cleared 5:45 min
            # post-alarm (10:15 min for last group with pram/pushchair).
            concourse_s=180.0,        # ~3 min post-alarm
            platform_s=None,          # platform crowd evacuated by train immediately
            whole_station_s=345.0,    # 5:45 min post-alarm (10:15 for last 2 groups)
        ),
        # Time to start moving: 1:30 (concourse crowd of 19), 1:00 (escalator crowd of 16)
        time_to_move_concourse_s=90.0,   # 1 min 30 s
        time_to_move_escalator_s=60.0,   # 1 min 00 s — fastest of all conditions
        immediate_response_rate=None,    # described as essentially immediate on PA line 2
        outcome=(
            "Station cleared 5:45 min post-alarm (10:15 for last group). Concourse "
            "cleared ~3 min. Fastest overall evacuation. No staff required — PA "
            "alone sufficient when information is specific enough. First condition "
            "where a majority (57%) thought it was a real emergency."
        ),
        notes=[
            "Specific fire location ('N/S escalators between concourse & platforms 1/2')"
            " was the critical trigger for immediate action.",
            "Bottom-of-escalator crowd moved at 1:00 min — fastest of all 5 conditions.",
            "68 disembarking platform passengers all re-boarded as instructed.",
            "57% thought it was a real emergency — first majority across all trials.",
            "Only 50% heard the PA (vs 68–92% in other conditions) — yet most effective.",
            "Two groups with prams/pushchair evacuated by train at 7:00 and 10:15 min.",
        ],
    ),
}

# ---------------------------------------------------------------------------
# Metric extraction helpers
# ---------------------------------------------------------------------------

def get_clearance_times() -> dict[str, dict[str, Optional[float]]]:
    """
    Return a nested dict of zone clearance times (seconds post-alarm) for all
    experiments.

      clearance_times["E2"]["concourse_s"]    →  180.0
      clearance_times["E2"]["whole_station_s"] →  480.0
    """
    result = {}
    for exp_id, ref in REFERENCE.items():
        result[exp_id] = {
            "concourse_s": ref.clearance.concourse_s,
            "platform_s": ref.clearance.platform_s,
            "whole_station_s": ref.clearance.whole_station_s,
            "time_to_move_concourse_s": ref.time_to_move_concourse_s,
            "time_to_move_escalator_s": ref.time_to_move_escalator_s,
        }
    return result


def to_sim_time(post_alarm_s: float, alarm_t: float = 15.0) -> float:
    """Convert a post-alarm time (seconds) to simulation time (seconds)."""
    return post_alarm_s + alarm_t


def qualitative_ordering() -> list[str]:
    """
    Return experiments ordered from worst to best evacuation effectiveness,
    as described by Proulx (1991).
    """
    return ["E1", "E3", "E2", "E4", "E5"]
