# Calibration

Before evacuations, the model is checked against normal operation: real
passenger volumes, the real train timetable, and real exit counts. The
decisions in calibration runs are rule-based and journey-only (no alarm), so
they test the station geometry, escalators, routing and walking. They do not
test the evacuation response.

## Data

| Source | Use |
|---|---|
| Tyne & Wear Metro annual boardings by station; patronage by time band | A day's arrivals by entrance and the alightings per train (`data/calibration/build_calibration_data.py`) |
| Train arrivals logged at Monument (`tools/monument_arrivals_logger.py`, `data/arrivals/`) | The real timetable of an observed morning |
| A hand count at the Blackett Street exit, Monday 5 October 2026, 09:03:44–10:03:16: 354 people | The observation the model is checked against |

How the CSVs are built, and the assumptions:

--8<-- "data/calibration/README.md"

## The check

`experiments/calibration/validation_20261005.yaml` replays that morning
(08:51–10:09):

- **Trains:** the real arrivals, with alighting sized so that 602 people
  leave during the counting window.
- **Exit split:** that total is Blackett's 354, plus Grey Street and Eldon
  Square at 35% of Blackett each.
- **What is tested:** which exit each person takes is the model's choice, so
  the simulated Blackett count is the test.

| Code | Blackett Street (3 seeds) | Grey Street | Eldon Square |
|---|---|---|---|
| Before the October 2026 engine fixes (evacusim 4971c42) | 357, 361, 358 | 197–208 | 59–76 |
| After (evacusim main, October 2026) | 358, 373, 344 | 200–209 | 57–84 |
| **Counted** | **354** | — | — |

The fixes that freed stuck and lost passengers (evacusim ADR 5) did not move
the calibration.

```bash
monument run validation_20261005 --seed 0
monument analyse real_exit_usage_plots \
    --counts data/calibration/collected/blackett-st-2026-05-10_10-03-31.csv \
    --sim-run results/validation_20261005/run_…
```
