"""Panchanga limbs, names, periods of the day, and the assembled day panchanga."""

from __future__ import annotations

from datetime import date, timedelta
from itertools import pairwise

import numpy as np
import pytest

from jyotish_engine.astro.bodies import Body
from jyotish_engine.models import PlaceInput
from jyotish_engine.panchanga import muhurta
from jyotish_engine.panchanga.day import compute_panchanga
from jyotish_engine.panchanga.elements import (
    TITHIS,
    VARAS,
    YOGAS,
    Limb,
    karana_name,
    limb_indices,
    limb_name,
    paksha,
)
from jyotish_engine.panchanga.timing import all_limb_spans, limb_index_at, limb_spans

DELHI = PlaceInput(name="New Delhi", latitude=28.6139, longitude=77.2090, elevation_m=216)
# 06:00 to 18:00 and on to 06:00 next day, as Julian days (a round 12-hour day).
SUNRISE, SUNSET, NEXT = 0.0, 0.5, 1.0


def test_names() -> None:
    assert (len(TITHIS), len(YOGAS), len(VARAS)) == (30, 27, 7)
    assert TITHIS[14] == "Purnima" and TITHIS[29] == "Amavasya" and TITHIS[15] == "Pratipada"
    assert paksha(14) == "shukla" and paksha(15) == "krishna"
    assert [karana_name(i) for i in (0, 1, 7, 8, 56, 57, 58, 59)] == [
        "Kimstughna", "Bava", "Vishti", "Bava", "Vishti", "Shakuni", "Chatushpada", "Naga",
    ]  # fmt: skip
    assert limb_name(Limb.NAKSHATRA, 26) == "Revati" and limb_name(Limb.YOGA, 26) == "Vaidhriti"


def test_limb_indices() -> None:
    sun, moon = np.array([10.0, 350.0, 0.0]), np.array([22.0, 5.0, 359.99])
    assert list(limb_indices(Limb.TITHI, sun, moon)) == [1, 1, 29]
    assert list(limb_indices(Limb.KARANA, sun, moon)) == [2, 2, 59]
    assert list(limb_indices(Limb.NAKSHATRA, sun, moon)) == [1, 0, 26]
    assert list(limb_indices(Limb.YOGA, sun, moon)) == [2, 26, 26]


def test_kalams_follow_the_weekday_tables() -> None:
    hour = 1.0 / 24.0
    # Sunday: Rahu 16:30-18:00, Yamaganda 12:00-13:30, Gulika 15:00-16:30.
    rahu, yama, gulika = muhurta.kalams(SUNRISE, SUNSET, 0)
    assert (rahu.start_jd_ut, rahu.end_jd_ut) == pytest.approx((10.5 * hour, 12 * hour))
    assert yama.start_jd_ut == pytest.approx(6 * hour)
    assert gulika.start_jd_ut == pytest.approx(9 * hour)
    # Monday Rahu kalam is the second eighth: 07:30-09:00.
    assert muhurta.kalams(SUNRISE, SUNSET, 1)[0].start_jd_ut == pytest.approx(1.5 * hour)


def test_muhurtas() -> None:
    minute = 1.0 / 1440.0
    abhijit = muhurta.abhijit(SUNRISE, SUNSET)  # 11:36 to 12:24 for a 12-hour day
    assert (abhijit.start_jd_ut, abhijit.end_jd_ut) == pytest.approx((336 * minute, 384 * minute))
    brahma = muhurta.brahma_muhurta(SUNSET - 1.0, SUNRISE)  # 04:24 to 05:12
    assert brahma.end_jd_ut == pytest.approx(-48 * minute)
    assert brahma.start_jd_ut == pytest.approx(-96 * minute)
    # Tuesday: the 4th day muhurta and the 7th of the night.
    day, night = muhurta.durmuhurtas(SUNRISE, SUNSET, NEXT, 2)
    assert day.start_jd_ut == pytest.approx(3 * 48 * minute)
    assert night.start_jd_ut == pytest.approx(SUNSET + 6 * 48 * minute)
    # Wednesday's durmuhurta is the Abhijit muhurta itself.
    [wednesday] = muhurta.durmuhurtas(SUNRISE, SUNSET, NEXT, 3)
    assert wednesday.start_jd_ut == pytest.approx(abhijit.start_jd_ut)


def test_horas_and_choghadiyas() -> None:
    horas = muhurta.horas(SUNRISE, SUNSET, NEXT, 0)
    assert len(horas) == 24 and horas[0].lord is Body.SUN and horas[1].lord is Body.VENUS
    # The first hora of the next day belongs to the next weekday lord (Monday: Moon).
    assert muhurta.HORA_ORDER[(muhurta.HORA_ORDER.index(horas[-1].lord) + 1) % 7] is Body.MOON
    for before, after in pairwise(horas):
        assert before.end_jd_ut == pytest.approx(after.start_jd_ut)
    chogs = muhurta.choghadiyas(SUNRISE, SUNSET, NEXT, 0)
    assert [c.name for c in chogs[:8]] == [
        "Udveg", "Chal", "Labh", "Amrit", "Kaal", "Shubh", "Rog", "Udveg",
    ]  # fmt: skip
    assert chogs[8].name == "Shubh"  # Sunday night starts with Jupiter's choghadiya
    assert {c.quality for c in chogs} == {"good", "neutral", "bad"}


def test_day_panchanga_is_consistent() -> None:
    day = date(2026, 9, 30)  # a Wednesday
    p = compute_panchanga(day, DELHI)
    assert p.weekday == 3 and p.vara == "Budhavara" and p.vara_lord is Body.MERCURY
    assert p.zone == "Asia/Kolkata" and p.utc_offset_seconds == 19800.0
    assert p.sunrise_jd_ut < p.sunset_jd_ut < p.next_sunrise_jd_ut
    local_sunrise = p.sunrise + timedelta(seconds=p.utc_offset_seconds)
    assert local_sunrise.date() == day and 5 <= local_sunrise.hour <= 7
    for spans in (p.tithis, p.nakshatras, p.yogas, p.karanas):
        assert spans[0].start_jd_ut <= p.sunrise_jd_ut < spans[0].end_jd_ut
        assert spans[-1].end_jd_ut >= p.next_sunrise_jd_ut
        for before, after in pairwise(spans):
            assert before.end_jd_ut == after.start_jd_ut and before.number != after.number
    assert p.tithis[0].paksha in ("shukla", "krishna")
    assert p.tithis[0].number == limb_index_at(Limb.TITHI, p.sunrise_jd_ut) + 1
    assert [h.lord for h in p.horas[:2]] == [Body.MERCURY, Body.MOON]
    assert p.choghadiyas[0].name == "Labh"
    assert p.abhijit.start_jd_ut == p.durmuhurtas[0].start_jd_ut


def test_combined_search_matches_single_limb_search() -> None:
    start = 2461313.5
    together = all_limb_spans(start, start + 1.0)
    for limb in Limb:
        alone = limb_spans(limb, start, start + 1.0)
        assert [(s.index, s.start_jd_ut, s.end_jd_ut) for s in alone] == [
            (s.index, s.start_jd_ut, s.end_jd_ut) for s in together[limb]
        ]


def test_polar_night_is_reported() -> None:
    tromso = PlaceInput(name="Tromso", latitude=69.6492, longitude=18.9553)
    with pytest.raises(ValueError, match="polar"):
        compute_panchanga(date(2026, 12, 21), tromso)
