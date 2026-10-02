"""Generate lunisolar calendar references (development only).

Places are on UTC. PyJHora takes the month at local sunrise but reads that local
Julian day as UT; with a zero offset the two agree.

For random civil dates, and for dates in and around every adhika month and near
sankrantis, the script records:

* **From Swiss Ephemeris** (Lahiri, apparent positions, Hindu sunrise):
  * sunrise and sunset;
  * the new moons before and after sunrise, and the one before those, with the
    Sun's sidereal sign at each;
  * the last sankranti before sunset, and the first sunset after it.
* **From PyJHora**, switched to apparent positions:
  * the amanta and purnimanta month and day, with its adhika and nija flags;
  * its Kali, Vikram and Shaka years;
  * the Tamil solar month and day (``null`` where PyJHora fails). Its solar
    samvatsara function passed Swiss Ephemeris a date thousands of years away on
    the first date tried, so it is not recorded.

Only numbers are written, to ``engine/tests/fixtures/calendar_reference.json``.

    oracle/.venv/bin/python oracle/generate_calendar_fixtures.py
"""

from __future__ import annotations

import contextlib
import io
import json
import random
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Any

import swisseph as swe
from jhora import const, utils
from jhora.panchanga import drik

ROOT = Path(__file__).resolve().parent.parent
EPHE = ROOT / "oracle" / "cache" / "ephe"
OUT = ROOT / "engine" / "tests" / "fixtures" / "calendar_reference.json"
SEED = 20261201
FLAGS = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
HINDU = swe.BIT_HINDU_RISING
#: name, latitude, longitude, elevation (m); all keep UTC as civil time.
PLACES = [
    ("London", 51.5074, -0.1278, 11.0),
    ("Accra", 5.6037, -0.1870, 61.0),
    ("Dakar", 14.7167, -17.4677, 22.0),
    ("Reykjavik", 64.1466, -21.9426, 30.0),
]
FIRST, LAST = date(1950, 1, 1), date(2040, 12, 31)
RANDOM_DATES = 400


def _sun(jd_ut: float) -> float:
    return float(swe.calc_ut(jd_ut, swe.SUN, FLAGS)[0][0])


def _elongation(jd_ut: float) -> float:
    return (float(swe.calc_ut(jd_ut, swe.MOON, FLAGS)[0][0]) - _sun(jd_ut)) % 360.0


def _bisect(inside: Callable[[float], bool], low: float, high: float) -> float:
    """First time in (low, high] where ``inside`` holds, given it fails at ``low``."""
    while high - low > 1e-9:
        middle = 0.5 * (low + high)
        if inside(middle):
            high = middle
        else:
            low = middle
    return high


def _new_moon_after(jd_ut: float) -> float:
    """First new moon after ``jd_ut`` (the elongation wraps from 360 to 0)."""
    t, value = jd_ut, _elongation(jd_ut)
    while True:
        after = _elongation(t + 0.25)
        if after < value:
            return _bisect(partial(_wrapped_below, value), t, t + 0.25)
        t, value = t + 0.25, after


def _wrapped_below(reference: float, jd_ut: float) -> bool:
    return _elongation(jd_ut) < reference


def _new_moon_before(jd_ut: float) -> float:
    """Latest new moon at or before ``jd_ut``. The elongation grows by 10.8 to 14.5
    degrees a day, so reading it at 10 degrees a day starts the search between the
    new moon wanted and the one before it."""
    found = _new_moon_after(jd_ut - _elongation(jd_ut) / 10.0 - 1.0)
    if found > jd_ut:
        raise RuntimeError("new moon search started too late")
    return found


def _last_sankranti(jd_ut: float) -> float:
    sign = int(_sun(jd_ut) // 30.0)
    t = jd_ut
    while int(_sun(t) // 30.0) == sign:
        t -= 0.5
    return _bisect(lambda x: int(_sun(x) // 30.0) == sign, t, t + 0.5)


def _safely(call: Callable[[], Any]) -> Any:
    """PyJHora's result, or None where it fails (its sankranti helpers sometimes
    pass Swiss Ephemeris a date thousands of years away)."""
    try:
        return call()
    except (swe.Error, ValueError, IndexError):
        return None


def _event(start: float, flags: int, geopos: tuple[float, float, float]) -> float:
    result, times = swe.rise_trans(start, swe.SUN, flags | HINDU, geopos, 1013.25, 15.0)
    if result != 0:
        raise RuntimeError("no rise or set")
    return float(times[0])


def _dates(rng: random.Random) -> list[tuple[date, str]]:
    span = (LAST - FIRST).days
    chosen = [(FIRST + timedelta(days=rng.randrange(span)), "random") for _ in range(RANDOM_DATES)]
    # Adhika months: new moons with the Sun in the same sign at both ends.
    t = swe.julday(FIRST.year, FIRST.month, FIRST.day, 0.0)
    end = swe.julday(LAST.year, LAST.month, LAST.day, 0.0)
    start = _new_moon_after(t)
    while start < end:
        following = _new_moon_after(start + 1.0)
        if int(_sun(start) // 30.0) == int(_sun(following) // 30.0):
            for offset, label in (
                (1.0, "adhika"),
                (15.0, "adhika"),
                (31.0, "nija"),
                (45.0, "nija"),
            ):
                y, m, d, _ = swe.revjul(start + offset)
                chosen.append((date(y, m, d), label))
        start = following
    # Dates on and after sankrantis, where the Tamil sunset rule decides the day.
    for _ in range(80):
        day = FIRST + timedelta(days=rng.randrange(span))
        y, m, d = day.year, day.month, day.day
        sankranti = _last_sankranti(swe.julday(y, m, d, 12.0))
        y, m, d, _ = swe.revjul(sankranti)
        for offset in (0, 1):
            chosen.append((date(y, m, d) + timedelta(days=offset), "sankranti"))
    return chosen


def main() -> None:
    swe.set_ephe_path(str(EPHE))
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    drik.set_ayanamsa_mode("LAHIRI")
    const.set_planet_positions_true(False)
    drik.refresh_planet_flags()
    rng = random.Random(SEED)
    cases: list[dict[str, Any]] = []
    for day, kind in _dates(rng):
        name, lat, lon, elevation = PLACES[rng.randrange(len(PLACES))]
        geopos = (lon, lat, elevation)
        midnight = swe.julday(day.year, day.month, day.day, 0.0)
        sunrise = _event(midnight, swe.CALC_RISE, geopos)
        sunset = _event(sunrise, swe.CALC_SET, geopos)
        start = _new_moon_before(sunrise)
        previous = _new_moon_before(start - 1.0)
        end = _new_moon_after(sunrise)
        moons = [previous, start, end]
        sankranti = _last_sankranti(sunset)
        place = drik.Place(name, lat, lon, 0.0)
        place_date = drik.Date(day.year, day.month, day.day)
        noon = utils.julian_day_number(place_date, (12, 0, 0))
        with contextlib.redirect_stdout(io.StringIO()):
            amanta = drik.lunar_month_date(noon, place, False)
            purnimanta = drik.lunar_month_date(noon, place, True)
            kali, vikrama, saka = drik.elapsed_year(noon, amanta[0])
            tamil = _safely(partial(drik.tamil_solar_month_and_date, place_date, place))
        cases.append(
            {
                "kind": kind,
                "place": name,
                "latitude": lat,
                "longitude": lon,
                "elevation_m": elevation,
                "date": day.isoformat(),
                "sunrise": sunrise,
                "sunset": sunset,
                "new_moons": moons,
                "new_moon_delta_t": [float(swe.deltat(t)) for t in moons],
                "sun_signs": [int(_sun(t) // 30.0) for t in moons],
                "sankranti": sankranti,
                "sankranti_delta_t": float(swe.deltat(sankranti)),
                "first_sunset": _event(sankranti, swe.CALC_SET, geopos),
                "pyjhora": {
                    "amanta": [int(amanta[0]), int(amanta[1]), bool(amanta[3]), bool(amanta[4])],
                    "purnimanta": [int(purnimanta[0]), int(purnimanta[1]), bool(purnimanta[3])],
                    "kali": int(kali),
                    "vikram": int(vikrama),
                    "shaka": int(saka),
                    "tamil": None if tamil is None else [int(tamil[0]), int(tamil[1])],
                },
            }
        )
    payload = {
        "generator": "oracle/generate_calendar_fixtures.py",
        "reference": (
            f"Swiss Ephemeris {swe.version} (Lahiri, apparent; Hindu sunrise) and PyJHora "
            "(apparent positions)"
        ),
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "seed": SEED,
        "cases": cases,
    }
    OUT.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {len(cases)} cases to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
