# Monument calibration data

These files drive a **non-evacuation, rule-based** EvacuSim run (the
`Calibration` experiment): a normal 24-hour operating day at Monument Metro
station, starting at midnight (`t = 0 s`) and ending at `t = 86400 s`.
Passengers are *not* placed at the start — they arrive over time from the two
generated CSVs.

## Files

| File | Kind | Description |
|------|------|-------------|
| `metro-passenger-boardings-by-station.csv` | raw input | Annual boardings per station, per financial year (Tyne & Wear Metro open data). |
| `metro-patronage-by-timeband.csv` | raw input | System-wide annual patronage split by time band, per day type, per year. |
| `build_calibration_data.py` | generator | Combines the two raw inputs into the two outputs below. |
| `entrance_usage.csv` | **generated** | Per-entrance arrivals over the day (people arriving to board). |
| `timetable.csv` | **generated** | Train arrivals per platform, each alighting a burst of passengers. |

## Regenerating

```bash
# Default: a weekday (Monday), most recent year.
python data/calibration/build_calibration_data.py

# A specific day of the week, and/or a specific year:
python data/calibration/build_calibration_data.py --day saturday
python data/calibration/build_calibration_data.py --day sunday --year 2024/25
```

The script prints an inspectable summary (daily total, the within-day demand
profile, and train/alighting counts per platform) so the numbers can be traced
back to the source data.

## Method

The goal is to estimate how many people arrive at Monument throughout the day,
and turn that into the format EvacuSim consumes. It is kept deliberately simple
so every output number is justifiable from the raw data:

1. **Most recent year only** (auto-detected, e.g. `2025/26`).
2. **Monument scale** — annual boardings = `Monument Lower` + `Monument Upper`
   (the station's two platform levels).
3. **Day-type weighting** — the annual total is distributed across the calendar
   in proportion to how busy the network is on each day type, then one
   representative day of the requested type is taken:

   ```
   daily(day type) = annual x (day-type patronage / total patronage) / (days of that type per year)
   ```

   The patronage shares come from the timeband table (weekday / Saturday /
   Sunday annual totals); day counts are ≈261 weekdays / 52 Saturdays / 52
   Sundays. This conserves the annual total (summing over all 365 days returns
   the annual figure) while giving each day type its own volume. For `2025/26`
   this yields ≈11,200 (weekday), ≈12,200 (Saturday), ≈7,000 (Sunday).
   *Assumption:* usage is constant *within* a day type (every weekday identical,
   every Saturday identical, every Sunday identical).
4. **Within-day shape** — the chosen day type's time bands from the patronage
   table are normalised to fractions. *Assumption:* Monument follows the
   network-average timeband pattern.
5. **Entrances** (`entrance_usage.csv`) — each band's arrivals are split
   **equally** across the three street entrances (`blackett_street`,
   `grey_street`, `eldon_square`).
6. **Trains** (`timetable.csv`) — train times come from the published service
   frequencies (first/last train per platform, daytime vs evening headway from
   ~18:20; Sunday starts later with a sparser early service). Alighting counts
   use boarding↔alighting **symmetry**: over a day a station's alightings
   roughly equal its boardings. `Monument Lower` boardings feed platforms 1 & 2
   (main through platforms); `Monument Upper` feeds platforms 3 & 4 (the loop).
   Each platform's daily alightings are spread over its trains, weighted by the
   same timeband profile.

### Realistic arrival times

`entrance_usage.csv` gives an arrival **count** per band, not a schedule. The
EvacuSim scheduler treats each band as a Poisson process and samples
exponential inter-arrival times, so agents arrive at naturally jittered instants
(inter-arrival gaps range from a fraction of a second to several minutes) — not
on a fixed grid. Train alighting is an intentional burst at the train's arrival
second.

## Known simplifications

These are the trade-offs made for a first, inspectable model:

- **Constant within a day type.** Every weekday is modelled identically (as is
  every Saturday / Sunday). Day-of-week within the weekday group is not
  distinguished, and seasonal / holiday variation is ignored. Note the day-type
  weighting reflects the real data faithfully — on this network Saturdays come
  out marginally busier per day than an average weekday (weekend leisure travel
  in the city centre), which may look surprising but is what the source says.
- **Constant rate within a band.** Bands are the native resolution of the real
  data (e.g. a single 09:00–15:29 block), so demand is flat within each band.
- **Equal entrance split** and **equal split between the two platforms of a
  level.** No entrance- or platform-level weighting is applied.
- **Representative headways.** The source gives ranges (e.g. 10–13 min); a
  single representative headway is used per platform/phase.
