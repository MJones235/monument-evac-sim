#!/usr/bin/env python3
"""Build EvacuSim calibration CSVs for a single day of the week, from real data.

This script turns two real Tyne & Wear Metro open-data sources into the two
CSVs the EvacuSim calibration harness consumes (Feature A, non-evacuation run):

  * ``entrance_usage.csv``  — per-entrance passenger arrivals over the day
                              (people arriving at street level to board a train).
  * ``timetable.csv``       — train arrivals per platform, each alighting a
                              burst of passengers.

Both outputs describe a single 24-hour day that starts at midnight
(simulation time ``0 s`` == 00:00, ``86400 s`` == 24:00).

--------------------------------------------------------------------------------
Inputs (real data, committed alongside this script)
--------------------------------------------------------------------------------
metro-passenger-boardings-by-station.csv
    Annual boardings (people starting a journey) at every Metro station, one
    column per financial year.  Monument appears as two rows — "Monument Lower"
    and "Monument Upper" (the two platform levels); we sum them.

metro-patronage-by-timeband.csv
    System-wide annual patronage split into time bands, separately for
    Weekday / Saturday / Sunday, one row per financial year.  This gives the
    *shape* of demand across the day; it is network-wide, so we assume Monument
    follows the average timeband pattern.

--------------------------------------------------------------------------------
Method (deliberately simple and inspectable — every number traces to the data)
--------------------------------------------------------------------------------
1. Use the most recent financial year only (auto-detected; override with --year).
2. Monument annual boardings = Monument Lower + Monument Upper.
3. Split that annual total across the calendar in proportion to how busy the
   network is on each *day type*, then take one representative day of the
   requested type:

       daily(day type) = annual x  (patronage on that day type / total patronage)
                                 -----------------------------------------------
                                        (number of such days in the year)

   The patronage share comes from the timeband table (weekday vs Saturday vs
   Sunday annual totals); the day counts are ~261 weekdays / 52 Saturdays /
   52 Sundays.  This conserves the annual total (summing over all 365 days
   returns the annual figure) while giving each day type its own volume.
   (Assumption: usage is constant *within* a day type — every weekday is
   modelled identically, as is every Saturday and every Sunday.)
4. For the chosen day of week, take that day type's time bands from the
   patronage table and normalise them to fractions of that day's total.  These
   fractions are the within-day demand profile (assume Monument == network avg).
5. Entrances: each band's arrivals are split equally across the station's
   street entrances (assumption: entrances are equally used).
6. Trains: alightings mirror boardings (a boarding somewhere is an alighting
   elsewhere; over a day, Monument's alightings ~= its boardings).  Monument
   Lower boardings drive platforms 1 & 2; Monument Upper drives platforms 3 & 4.
   Each platform's daily alightings are spread over its trains, weighted by the
   same timeband profile.

Note on realism of arrival times: the EvacuSim scheduler treats each entrance
interval as a Poisson process and samples exponential inter-arrival times, so
agents do NOT arrive on a fixed grid — a coarse (multi-hour) band still yields
naturally jittered arrival instants.  Train alighting is an intentional burst at
the train's arrival second.

Usage
-----
    python data/calibration/build_calibration_data.py                # Monday (weekday)
    python data/calibration/build_calibration_data.py --day saturday
    python data/calibration/build_calibration_data.py --day sunday --year 2024/25
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

# --------------------------------------------------------------------------- #
# Static configuration
# --------------------------------------------------------------------------- #

HERE = Path(__file__).resolve().parent
BOARDINGS_CSV = HERE / "metro-passenger-boardings-by-station.csv"
PATRONAGE_CSV = HERE / "metro-patronage-by-timeband.csv"

# Monument is recorded as two platform-level rows in the boardings data.
MONUMENT_LOWER = "Monument Lower"   # main through platforms -> platforms 1 & 2
MONUMENT_UPPER = "Monument Upper"   # loop platforms         -> platforms 3 & 4

# Street entrances modelled in the Monument geometry (equally used, by assumption).
ENTRANCES = ("blackett_street", "grey_street", "eldon_square")

DAYS_IN_YEAR = 365

# Approximate number of each day type in a year (261 + 52 + 52 = 365).  Used to
# turn an annual per-day-type total into a single representative day.
DAY_TYPE_COUNT = {"weekday": 261, "saturday": 52, "sunday": 52}


def hms(h: int, m: int = 0) -> int:
    """Seconds from midnight for a wall-clock time."""
    return h * 3600 + m * 60


# Time bands per day type, in the SAME order as the patronage-table columns for
# that day type.  Each band maps to a [start_s, end_s) window over the 24h day.
# Bands are contiguous and cover the full day (00:00 -> 24:00).
DAY_TYPE_BANDS: dict[str, list[tuple[int, int]]] = {
    "weekday": [
        (hms(0), hms(7, 30)),     # Before 07:30
        (hms(7, 30), hms(9)),     # 07:30 - 08:59
        (hms(9), hms(15, 30)),    # 09:00 - 15:29
        (hms(15, 30), hms(18)),   # 15:30 - 17:59
        (hms(18), hms(24)),       # After 17:59
    ],
    "saturday": [
        (hms(0), hms(9)),         # Before 09:00
        (hms(9), hms(18)),        # 09:00 - 17:59
        (hms(18), hms(24)),       # After 17:59
    ],
    "sunday": [
        (hms(0), hms(11)),        # Before 11:00
        (hms(11), hms(18)),       # 11:00 - 17:59
        (hms(18), hms(24)),       # After 17:59
    ],
}

# Column index ranges of each day type within the patronage table (after the
# leading year column).  Matches the fixed column layout of the source file.
DAY_TYPE_COLUMNS: dict[str, slice] = {
    "weekday": slice(0, 5),
    "saturday": slice(5, 8),
    "sunday": slice(8, 11),
}

DOW_TO_TYPE = {
    "monday": "weekday", "tuesday": "weekday", "wednesday": "weekday",
    "thursday": "weekday", "friday": "weekday",
    "saturday": "saturday", "sunday": "sunday",
    # allow passing the day type directly
    "weekday": "weekday",
}

# --------------------------------------------------------------------------- #
# Train service specification (from the published Tyne & Wear Metro timetable
# summary supplied for this task).  Times are the first/last train each day; a
# headway (train spacing) applies within each phase.  "~" values in the source
# are treated as exact for scheduling purposes.
# --------------------------------------------------------------------------- #

EVENING_START = hms(18, 20)      # evening frequency kicks in ~18:15-18:30 -> 18:20
EVENING_HEADWAY = 15 * 60        # 15 min every evening on every platform
SUNDAY_AM_END = hms(9)           # Sunday early service is sparse until ~09:00
SUNDAY_AM_HEADWAY = 20 * 60      # "15-30 min AM, tightening" -> 20 min representative

# Representative daytime headways (source gives 10-13 / 10-12 min ranges).
HEADWAY_THROUGH = 12 * 60        # platforms 1 & 2 (10-13 min)
HEADWAY_LOOP = 11 * 60           # platforms 3 & 4 (10-12 min)

# Per day type -> per platform: (first_train_s, last_train_s).
SERVICE_WINDOWS: dict[str, dict[str, tuple[int, int]]] = {
    "weekday": {
        "1": (hms(5, 12), hms(23, 44)),
        "2": (hms(5, 10), hms(23, 45)),
        "3": (hms(5, 0), hms(23, 40)),
        "4": (hms(6, 55), hms(23, 30)),
    },
    "saturday": {
        "1": (hms(5, 11), hms(23, 45)),
        "2": (hms(5, 10), hms(23, 45)),
        "3": (hms(5, 0), hms(23, 40)),
        "4": (hms(6, 55), hms(23, 30)),
    },
    "sunday": {
        "1": (hms(6, 15), hms(23, 15)),
        "2": (hms(6, 15), hms(23, 15)),
        "3": (hms(6, 0), hms(23, 0)),
        "4": (hms(7, 15), hms(23, 0)),
    },
}

# Daytime headway per platform (evening/Sunday-AM overrides handled separately).
PLATFORM_DAY_HEADWAY = {"1": HEADWAY_THROUGH, "2": HEADWAY_THROUGH,
                        "3": HEADWAY_LOOP, "4": HEADWAY_LOOP}

# Which Monument boardings row feeds which platforms (see module docstring).
PLATFORM_SOURCE = {"1": "lower", "2": "lower", "3": "upper", "4": "upper"}

TRAIN_DWELL_S = 30               # typical Metro station dwell

# --------------------------------------------------------------------------- #
# Parsing helpers
# --------------------------------------------------------------------------- #


def _to_int(raw: str) -> int:
    """Parse a quoted, thousands-separated, space-padded integer like ' 2,617,172 '."""
    return int(raw.replace(",", "").strip())


def load_boardings(year: str | None) -> tuple[int, int, str]:
    """Return (monument_lower, monument_upper, year) for the chosen/most-recent year."""
    with open(BOARDINGS_CSV, newline="") as fh:
        rows = list(csv.reader(fh))
    header = rows[0]
    years = header[1:]
    col = _resolve_year_column(years, year)
    lower = upper = None
    for row in rows[1:]:
        if not row:
            continue
        name = row[0].strip()
        if name == MONUMENT_LOWER:
            lower = _to_int(row[1:][col])
        elif name == MONUMENT_UPPER:
            upper = _to_int(row[1:][col])
    if lower is None or upper is None:
        raise SystemExit("Could not find both Monument Lower and Monument Upper rows.")
    return lower, upper, years[col].strip()


def load_patronage(day_type: str, year: str | None) -> tuple[list[float], float, str]:
    """Return (band_fractions, day_type_share, year) for the chosen day type/year.

    ``band_fractions`` are the share of that day type's patronage falling in each
    band, in the band order of ``DAY_TYPE_BANDS[day_type]`` — i.e. the within-day
    demand profile.

    ``day_type_share`` is that day type's fraction of total annual network
    patronage (weekday + Saturday + Sunday), used to weight the annual total by
    day type.
    """
    with open(PATRONAGE_CSV, newline="") as fh:
        rows = list(csv.reader(fh))
    data_rows = [r for r in rows[1:] if r and r[0].strip()]
    year_labels = [r[0].strip() for r in data_rows]
    idx = _resolve_year_column(year_labels, year)
    values = [_to_int(v) for v in data_rows[idx][1:]]

    band_values = values[DAY_TYPE_COLUMNS[day_type]]
    total = sum(band_values)
    if total <= 0:
        raise SystemExit(f"No patronage for day type '{day_type}' in {year_labels[idx]}.")
    fractions = [v / total for v in band_values]

    grand_total = sum(sum(values[sl]) for sl in DAY_TYPE_COLUMNS.values())
    day_type_share = total / grand_total
    return fractions, day_type_share, year_labels[idx]


def _resolve_year_column(labels: list[str], year: str | None) -> int:
    """Index of the requested year (or the most recent) within ``labels``."""
    clean = [l.strip() for l in labels]
    if year is None:
        return len(clean) - 1  # most recent = last column/row
    if year not in clean:
        raise SystemExit(f"Year '{year}' not found. Available: {', '.join(clean)}")
    return clean.index(year)


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #


def build_entrance_usage(daily_total: float, fractions: list[float],
                         bands: list[tuple[int, int]]) -> list[dict]:
    """One row per (entrance, band): arrivals split equally across entrances."""
    rows = []
    for entrance in ENTRANCES:
        for frac, (start_s, end_s) in zip(fractions, bands):
            arrivals = round(daily_total * frac / len(ENTRANCES))
            rows.append({
                "interval_start_s": start_s,
                "interval_end_s": end_s,
                "entrance_id": entrance,
                "arrivals": arrivals,
            })
    return rows


def _headway_at(t: int, day_type: str, platform: str) -> int:
    """Train spacing (seconds) applicable at time ``t`` on ``platform``."""
    if t >= EVENING_START:
        return EVENING_HEADWAY
    if day_type == "sunday" and t < SUNDAY_AM_END:
        return SUNDAY_AM_HEADWAY
    return PLATFORM_DAY_HEADWAY[platform]


def _train_times(day_type: str, platform: str) -> list[int]:
    """Scheduled arrival seconds for a platform, walking the headway phases."""
    start, end = SERVICE_WINDOWS[day_type][platform]
    times, t = [], start
    while t <= end:
        times.append(t)
        t += _headway_at(t, day_type, platform)
    return times


def _band_of(t: int, bands: list[tuple[int, int]]) -> int:
    """Index of the band containing time ``t``."""
    for i, (start_s, end_s) in enumerate(bands):
        if start_s <= t < end_s:
            return i
    return len(bands) - 1  # a last train exactly at end-of-day falls in the final band


def build_timetable(daily_lower: float, daily_upper: float, fractions: list[float],
                    bands: list[tuple[int, int]], day_type: str) -> list[dict]:
    """Train rows with alighting counts spread over each platform's trains.

    Each platform's daily alightings (= its share of Monument boardings, by the
    boarding/alighting symmetry) are distributed across its trains, weighted by
    the within-day timeband profile.
    """
    daily_by_source = {"lower": daily_lower, "upper": daily_upper}
    rows = []
    for platform in ("1", "2", "3", "4"):
        times = _train_times(day_type, platform)
        # This platform carries half of its level's alightings.
        platform_daily = daily_by_source[PLATFORM_SOURCE[platform]] / 2.0
        # Group this platform's trains by band, then share the band's alightings.
        trains_by_band: dict[int, list[int]] = {}
        for t in times:
            trains_by_band.setdefault(_band_of(t, bands), []).append(t)
        for band_idx, band_times in trains_by_band.items():
            band_alight = platform_daily * fractions[band_idx]
            per_train = round(band_alight / len(band_times))
            for t in band_times:
                rows.append({
                    "arrival_s": t,
                    "platform": platform,
                    "alighting": per_train,
                    "dwell_s": TRAIN_DWELL_S,
                })
    rows.sort(key=lambda r: (r["arrival_s"], r["platform"]))
    return rows


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--day", default="monday",
                        help="Day of week (monday..sunday) or day type "
                             "(weekday/saturday/sunday). Default: monday.")
    parser.add_argument("--year", default=None,
                        help="Financial year e.g. 2025/26. Default: most recent.")
    parser.add_argument("--out-dir", type=Path, default=HERE,
                        help="Directory to write the CSVs into (default: alongside raw data).")
    args = parser.parse_args()

    day_key = args.day.strip().lower()
    if day_key not in DOW_TO_TYPE:
        raise SystemExit(f"Unknown day '{args.day}'. Choose one of "
                         f"{', '.join(sorted(DOW_TO_TYPE))}.")
    day_type = DOW_TO_TYPE[day_key]
    bands = DAY_TYPE_BANDS[day_type]

    lower, upper, boardings_year = load_boardings(args.year)
    fractions, day_type_share, patronage_year = load_patronage(day_type, args.year)

    annual_total = lower + upper
    # Weight the annual total by day type: this day type's share of annual
    # patronage, divided by how many such days there are in the year.
    day_weight = day_type_share / DAY_TYPE_COUNT[day_type]
    daily_total = annual_total * day_weight
    daily_lower = lower * day_weight
    daily_upper = upper * day_weight

    entrance_rows = build_entrance_usage(daily_total, fractions, bands)
    timetable_rows = build_timetable(daily_lower, daily_upper, fractions, bands, day_type)

    _write_csv(args.out_dir / "entrance_usage.csv",
               ["interval_start_s", "interval_end_s", "entrance_id", "arrivals"],
               entrance_rows)
    _write_csv(args.out_dir / "timetable.csv",
               ["arrival_s", "platform", "alighting", "dwell_s"],
               timetable_rows)

    # ---- Inspectable summary -------------------------------------------------
    total_entrance = sum(r["arrivals"] for r in entrance_rows)
    total_alight = sum(r["alighting"] for r in timetable_rows)
    print(f"Day requested        : {args.day}  (day type: {day_type})")
    print(f"Boardings year       : {boardings_year}   Patronage year: {patronage_year}")
    print(f"Monument annual board: {annual_total:,}  "
          f"(Lower {lower:,} + Upper {upper:,})")
    print(f"Day-type weighting   : {day_type} = {day_type_share*100:.1f}% of annual "
          f"patronage over {DAY_TYPE_COUNT[day_type]} days/yr")
    print(f"Daily boardings      : {daily_total:,.0f}  "
          f"(vs flat annual/365 = {annual_total/DAYS_IN_YEAR:,.0f})")
    print()
    print("Within-day demand profile (band -> fraction -> entrance arrivals):")
    for frac, (start_s, end_s) in zip(fractions, bands):
        hh = f"{start_s//3600:02d}:{(start_s%3600)//60:02d}-{end_s//3600:02d}:{(end_s%3600)//60:02d}"
        print(f"  {hh}  {frac*100:5.1f}%  ->  {round(daily_total*frac):>6,} arrivals")
    print()
    print(f"entrance_usage.csv : {len(entrance_rows)} rows, "
          f"{total_entrance:,} total arrivals across {len(ENTRANCES)} entrances")
    for platform in ("1", "2", "3", "4"):
        n = sum(1 for r in timetable_rows if r["platform"] == platform)
        a = sum(r["alighting"] for r in timetable_rows if r["platform"] == platform)
        print(f"timetable.csv      : platform {platform}: {n:>3} trains, {a:,} alighting")
    print(f"timetable.csv      : {len(timetable_rows)} trains total, "
          f"{total_alight:,} alighting passengers")


if __name__ == "__main__":
    main()
