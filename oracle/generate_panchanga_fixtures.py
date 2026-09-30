"""Generate panchanga references with Swiss Ephemeris (development only).

For random civil dates at eight cities (five Indian ones weighted most), the script
finds independently, with Swiss Ephemeris (Lahiri, apparent positions):

* sunrise (Hindu definition: centre of the disc, no refraction, geocentric), the
  following sunset and sunrise, and the previous sunset;
* the first moonrise and moonset after local midnight (upper limb, refraction);
* every change of tithi, nakshatra, yoga and karana from 1.3 days before sunrise to
  1.3 days after the next sunrise, by scanning and bisection, with Swiss
  Ephemeris' Delta T at each change so times can be compared in TT.

Only numbers are written, to ``engine/tests/fixtures/panchanga_swisseph.json``.

    oracle/.venv/bin/python oracle/generate_panchanga_fixtures.py
"""

from __future__ import annotations

import json
import random
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import swisseph as swe

ROOT = Path(__file__).resolve().parent.parent
EPHE = ROOT / "oracle" / "cache" / "ephe"
OUT = ROOT / "engine" / "tests" / "fixtures" / "panchanga_swisseph.json"
SEED = 20261115
FLAGS = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
#: name, latitude, longitude, elevation (m), standard UTC offset (hours), dates.
CITIES = [
    ("New Delhi", 28.6139, 77.2090, 216.0, 5.5, 100),
    ("Mumbai", 19.0760, 72.8777, 14.0, 5.5, 100),
    ("Chennai", 13.0827, 80.2707, 6.0, 5.5, 100),
    ("Kolkata", 22.5726, 88.3639, 9.0, 5.5, 100),
    ("Bengaluru", 12.9716, 77.5946, 920.0, 5.5, 100),
    ("London", 51.5074, -0.1278, 11.0, 0.0, 20),
    ("New York", 40.7128, -74.0060, 10.0, -5.0, 20),
    ("Sydney", -33.8688, 151.2093, 58.0, 10.0, 20),
]
WIDTH = {"tithi": 12.0, "nakshatra": 360.0 / 27, "yoga": 360.0 / 27, "karana": 6.0}
COUNT = {"tithi": 30, "nakshatra": 27, "yoga": 27, "karana": 60}


def _sun_moon(jd_ut: float) -> tuple[float, float]:
    sun = swe.calc_ut(jd_ut, swe.SUN, FLAGS)[0][0]
    moon = swe.calc_ut(jd_ut, swe.MOON, FLAGS)[0][0]
    return float(sun), float(moon)


def _index(limb: str, jd_ut: float) -> int:
    sun, moon = _sun_moon(jd_ut)
    if limb in ("tithi", "karana"):
        angle = (moon - sun) % 360.0
    elif limb == "nakshatra":
        angle = moon % 360.0
    else:
        angle = (sun + moon) % 360.0
    return min(int(angle // WIDTH[limb]), COUNT[limb] - 1)


def _changes(limb: str, start: float, end: float) -> list[list[float]]:
    found = []
    t, value = start, _index(limb, start)
    step = 0.05
    while t < end:
        t_next = min(t + step, end)
        v_next = _index(limb, t_next)
        if v_next != value:
            low, high = t, t_next
            while high - low > 1e-8:
                middle = 0.5 * (low + high)
                if _index(limb, middle) == value:
                    low = middle
                else:
                    high = middle
            found.append([high, value, v_next, float(swe.deltat(high))])
        t, value = t_next, v_next
    return found


def _event(start: float, body: int, flags: int, geopos: tuple[float, float, float]) -> float:
    result, times = swe.rise_trans(start, body, flags, geopos, 1013.25, 15.0)
    if result != 0:
        raise RuntimeError("no rise or set found")
    return float(times[0])


def main() -> None:
    swe.set_ephe_path(str(EPHE))
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    rng = random.Random(SEED)
    cases: list[dict[str, Any]] = []
    hindu = swe.BIT_HINDU_RISING
    for name, lat, lon, elevation, offset, count in CITIES:
        geopos = (lon, lat, elevation)
        for _ in range(count):
            day = date(1950, 1, 1) + timedelta(days=rng.randrange(0, 33000))
            midnight = datetime(day.year, day.month, day.day, tzinfo=UTC) - timedelta(hours=offset)
            midnight_jd = swe.julday(
                midnight.year, midnight.month, midnight.day, midnight.hour + midnight.minute / 60
            )
            sunrise = _event(midnight_jd, swe.SUN, swe.CALC_RISE | hindu, geopos)
            sunset = _event(sunrise, swe.SUN, swe.CALC_SET | hindu, geopos)
            next_sunrise = _event(sunset, swe.SUN, swe.CALC_RISE | hindu, geopos)
            previous_sunset = _event(sunrise - 1.0, swe.SUN, swe.CALC_SET | hindu, geopos)
            record: dict[str, Any] = {
                "city": name,
                "latitude": lat,
                "longitude": lon,
                "elevation_m": elevation,
                "date": day.isoformat(),
                "midnight_jd_ut": midnight_jd,
                "sunrise": sunrise,
                "sunset": sunset,
                "next_sunrise": next_sunrise,
                "previous_sunset": previous_sunset,
                "moonrise": _event(midnight_jd, swe.MOON, swe.CALC_RISE, geopos),
                "moonset": _event(midnight_jd, swe.MOON, swe.CALC_SET, geopos),
            }
            low, high = sunrise - 1.3, next_sunrise + 1.3
            record["changes"] = {limb: _changes(limb, low, high) for limb in WIDTH}
            cases.append(record)
    payload = {
        "generator": "oracle/generate_panchanga_fixtures.py",
        "reference": f"Swiss Ephemeris {swe.version} (Lahiri, apparent; Hindu sunrise)",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "seed": SEED,
        "cases": cases,
    }
    OUT.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {len(cases)} cases to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
