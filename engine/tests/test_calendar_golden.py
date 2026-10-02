"""Lunisolar calendar versus Swiss Ephemeris and PyJHora (oracle/generate_calendar_fixtures.py).

Swiss Ephemeris gives the astronomy independently (new moons, the Sun's sign at
each, sankrantis, sunsets); the naming rules applied to it must reproduce the
engine exactly. PyJHora gives a second implementation of the conventions: its
month, day, adhika flag and era years agree everywhere. Its other differences are
all explained case by case:

* **Purnimanta months.** It moves the dark half of an adhika month into the next
  month. The adhika month keeps both halves: adhika Shravana 2023 ran from 18 July
  to 16 August in both reckonings.
* **Nija flag.** It compares a 1-based month from one of its functions with a
  0-based one from another, so the flag is not compared.
* **Tamil day.** It walks back one sunset at a time and stops at the first sunset
  where the Sun is less than 1 degree into its sign. When the sankranti falls
  shortly before a sunset, the next sunset also qualifies and it counts one day
  short. When the Sun is already more than 1 degree in at the first sunset, it
  misses the month's start altogether.

Every fourth case is run here; the accuracy report covers all of them.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from jyotish_engine.astro.bodies import Body
from jyotish_engine.astro.riseset import next_sunset
from jyotish_engine.astro.series import jd_ut_to_tt
from jyotish_engine.astro.time import Instant
from jyotish_engine.panchanga.calendar import (
    lunar_month,
    lunar_year,
    purnimanta_month,
    tamil_solar_date,
)
from jyotish_engine.panchanga.elements import Limb
from jyotish_engine.panchanga.timing import limb_index_at
from jyotish_engine.transit.search import longitude_at

FIXTURE = Path(__file__).parent / "fixtures" / "calendar_reference.json"


def _cases() -> list[dict[str, Any]]:
    data: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return list(data["cases"][::4])


CASES = _cases()


def _seconds_tt(ours_ut: float, theirs_ut: float, theirs_delta_t: float) -> float:
    return float(abs(jd_ut_to_tt([ours_ut])[0] - theirs_ut - theirs_delta_t) * 86400)


def _into_sign(jd_ut: float) -> float:
    return longitude_at(Body.SUN, jd_ut) % 30.0


@pytest.mark.golden
@pytest.mark.parametrize(
    "case", CASES, ids=[f"{c['kind']}-{c['place']}-{c['date']}" for c in CASES]
)
def test_calendar_against_references(case: dict[str, Any]) -> None:
    sunrise, sunset = case["sunrise"], case["sunset"]
    moons, delta_t = case["new_moons"], case["new_moon_delta_t"]
    month = lunar_month(sunrise)
    assert _seconds_tt(month.start_jd_ut, moons[1], delta_t[1]) < 0.5
    assert _seconds_tt(month.end_jd_ut, moons[2], delta_t[2]) < 0.5

    # The naming rule applied to the reference astronomy.
    before, first, last = case["sun_signs"]
    assert month.index == (first + 1) % 12
    assert month.adhika == (last == first)
    assert month.nija == (before == first != last)
    assert month.kshaya == ((last - first) % 12 == 2)

    # PyJHora.
    tithi = limb_index_at(Limb.TITHI, sunrise)
    theirs = case["pyjhora"]
    assert theirs["amanta"][:3] == [month.index + 1, tithi + 1, month.adhika]
    index, adhika = purnimanta_month(month, tithi)
    if month.adhika and tithi >= 15:
        assert theirs["purnimanta"][0] == (month.index + 1) % 12 + 1
    else:
        assert [theirs["purnimanta"][0], theirs["purnimanta"][2]] == [index + 1, adhika]
    year = lunar_year(month)
    assert [theirs["kali"], theirs["vikram"], theirs["shaka"]] == [
        year.kali,
        year.vikram,
        year.shaka,
    ]

    # Tamil date: the sankranti, and the sunset rule on the reference sunsets.
    lat, lon, elevation = case["latitude"], case["longitude"], case["elevation_m"]
    solar = tamil_solar_date(date.fromisoformat(case["date"]), sunset, lat, lon, elevation)
    assert _seconds_tt(solar.sankranti_jd_ut, case["sankranti"], case["sankranti_delta_t"]) < 0.5
    assert solar.day == round(sunset - case["first_sunset"]) + 1
    if theirs["tamil"] == [solar.month, solar.day]:
        return
    assert theirs["tamil"][0] == solar.month
    if _into_sign(case["first_sunset"]) >= 1.0:
        assert theirs["tamil"][1] >= solar.day + 29  # it missed the month's start
    else:
        second = next_sunset(Instant.from_jd_ut(case["first_sunset"] + 0.5), lat, lon, elevation)
        assert second is not None and _into_sign(second.jd_ut) < 1.0
        assert theirs["tamil"][1] == solar.day - 1  # it started from the second sunset
