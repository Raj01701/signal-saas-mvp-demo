"""Lunar months, adhika and kshaya months, era years, samvatsara and Tamil dates."""

from __future__ import annotations

from datetime import UTC, date, datetime
from itertools import pairwise

import pytest

from jyotish_engine.astro.riseset import next_sunrise, next_sunset
from jyotish_engine.astro.time import Instant, jd_to_datetime
from jyotish_engine.models import PlaceInput
from jyotish_engine.panchanga.calendar import (
    MASAS,
    RITUS,
    SAMVATSARAS,
    LunarMonth,
    ayana,
    last_sankranti,
    lunar_month,
    lunar_year,
    new_moons,
    purnimanta_month,
    ritu,
    tamil_solar_date,
)
from jyotish_engine.panchanga.day import compute_panchanga
from jyotish_engine.place.timezone import resolve_local_time

DELHI = PlaceInput(name="New Delhi", latitude=28.6139, longitude=77.2090, elevation_m=216)
CHENNAI = PlaceInput(name="Chennai", latitude=13.0827, longitude=80.2707, elevation_m=6)


def _jd(year: int, month: int, day: int, hour: float = 0.0) -> float:
    return Instant.from_utc(datetime(year, month, day, tzinfo=UTC)).jd_ut + hour / 24.0


def _month(year: int, month: int, day: int) -> LunarMonth:
    return lunar_month(_jd(year, month, day, 1.0))


@pytest.mark.parametrize(
    ("day", "name"),
    [
        (date(2012, 8, 28), "Bhadrapada"),
        (date(2015, 6, 27), "Ashadha"),
        (date(2018, 5, 26), "Jyeshtha"),
        (date(2020, 9, 28), "Ashvina"),
        (date(2023, 7, 28), "Shravana"),
        (date(2026, 5, 27), "Jyeshtha"),
    ],
)
def test_published_adhika_months(day: date, name: str) -> None:
    adhika = _month(day.year, day.month, day.day)
    assert adhika.adhika and not adhika.nija and adhika.name == name
    assert 29.2 < adhika.end_jd_ut - adhika.start_jd_ut < 29.9
    nija = lunar_month(adhika.end_jd_ut + 10.0)
    assert nija.nija and not nija.adhika and nija.name == name
    assert nija.start_jd_ut == pytest.approx(adhika.end_jd_ut, abs=1e-6)
    before = lunar_month(adhika.start_jd_ut - 10.0)
    assert not (before.adhika or before.nija) and before.index == (adhika.index - 1) % 12


def test_new_moons_bound_the_months() -> None:
    start = _jd(2026, 1, 1)
    moons = new_moons(start, start + 365.0)
    assert len(moons) == 12
    for first, second in pairwise(moons):
        assert 29.2 < second - first < 29.9
        month = lunar_month(first + 1.0)
        assert (month.start_jd_ut, month.end_jd_ut) == pytest.approx((first, second), abs=2e-7)
    sankranti, sign = last_sankranti(_jd(2026, 9, 30))
    assert sign == 5  # Kanya
    assert jd_to_datetime(sankranti).date() == date(2026, 9, 17)


def test_kshaya_months_come_between_two_adhika_months() -> None:
    # 1982-83: adhika Ashvina, kshaya Pausha (with Magha), adhika Phalguna.
    assert _month(1982, 9, 27).adhika and _month(1982, 9, 27).name == "Ashvina"
    kshaya = _month(1983, 1, 25)
    assert (kshaya.name, kshaya.kshaya_index) == ("Pausha", MASAS.index("Magha"))
    assert _month(1983, 2, 25).adhika and _month(1983, 2, 25).name == "Phalguna"
    # 1963-64: adhika Kartika, then nija Kartika absorbing Margashirsha (the Sun
    # enters Vrischika and Dhanu within it), then adhika Chaitra.
    assert _month(1963, 10, 28).adhika and _month(1963, 10, 28).name == "Kartika"
    kshaya = _month(1963, 11, 27)
    assert (kshaya.name, kshaya.kshaya_index) == ("Kartika", MASAS.index("Margashirsha"))
    assert kshaya.nija and not kshaya.adhika
    assert _month(1964, 3, 25).adhika and _month(1964, 3, 25).name == "Chaitra"
    # An ordinary month is neither.
    assert not _month(2024, 1, 25).kshaya


def test_years_turn_at_chaitra_and_kartika() -> None:
    before = lunar_year(_month(2024, 4, 7))  # Phalguna Amavasya, the day before Ugadi
    after = lunar_year(_month(2024, 4, 10))  # Chaitra Shukla
    assert (before.shaka, before.vikram, before.kali) == (1945, 2080, 5124)
    assert (after.shaka, after.vikram, after.kali) == (1946, 2081, 5125)
    assert (before.samvatsara_name, after.samvatsara_name) == ("Shobhakrit", "Krodhi")
    assert SAMVATSARAS[(1909 + 11) % 60] == "Prabhava"  # 1987-88 opened the cycle
    # The Gujarati year turns at Kartika: 2080 until Diwali 2024, 2081 after.
    assert lunar_year(_month(2024, 10, 20)).vikram_kartikadi == 2080
    assert lunar_year(_month(2024, 11, 10)).vikram_kartikadi == 2081
    assert lunar_year(_month(2025, 2, 10)).vikram_kartikadi == 2081
    # Adhika Chaitra (2029) already belongs to the new year.
    adhika_chaitra = _month(2029, 3, 25)
    assert adhika_chaitra.adhika and adhika_chaitra.index == 0
    assert lunar_year(adhika_chaitra).shaka == 2029 - 78


def test_purnimanta_months_and_seasons() -> None:
    month = LunarMonth(index=5, start_jd_ut=0.0, end_jd_ut=29.5)
    assert purnimanta_month(month, 3) == (5, False)  # bright half: same month
    assert purnimanta_month(month, 20) == (6, False)  # dark half: the next month
    adhika = LunarMonth(index=4, start_jd_ut=0.0, end_jd_ut=29.5, adhika=True)
    assert purnimanta_month(adhika, 20) == (4, True)  # an adhika month keeps both halves
    assert purnimanta_month(LunarMonth(index=11, start_jd_ut=0.0, end_jd_ut=1.0), 29) == (0, False)
    assert [RITUS[ritu(LunarMonth(index=i, start_jd_ut=0, end_jd_ut=1))] for i in (0, 3, 11)] == [
        "Vasanta", "Grishma", "Shishira",
    ]  # fmt: skip
    assert ayana(280.0) == ayana(10.0) == "uttarayana"
    assert ayana(90.0) == ayana(269.9) == "dakshinayana"


def _tamil(day: date, place: PlaceInput) -> tuple[str, int, str]:
    lat, lon, elevation = place.latitude, place.longitude, place.elevation_m
    local = resolve_local_time(datetime(day.year, day.month, day.day), lat, lon)
    rise = next_sunrise(Instant.from_utc(local.chosen.utc), lat, lon, elevation)
    assert rise is not None
    sunset = next_sunset(rise, lat, lon, elevation)
    assert sunset is not None
    solar = tamil_solar_date(day, sunset.jd_ut, lat, lon, elevation)
    return solar.month_name, solar.day, SAMVATSARAS[solar.samvatsara]


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        # Pongal: Makara sankranti after sunset on 14 Jan 2023, so Thai 1 was the 15th.
        (date(2023, 1, 14), ("Margazhi", 30, "Shubhakrit")),
        (date(2023, 1, 15), ("Thai", 1, "Shubhakrit")),
        (date(2024, 1, 15), ("Thai", 1, "Shobhakrit")),
        (date(2025, 1, 14), ("Thai", 1, "Krodhi")),
        # Puthandu, the Tamil new year, and its samvatsara.
        (date(2023, 4, 14), ("Chittirai", 1, "Shobhakrit")),
        (date(2024, 4, 13), ("Panguni", 31, "Shobhakrit")),
        (date(2024, 4, 14), ("Chittirai", 1, "Krodhi")),
        (date(2025, 4, 14), ("Chittirai", 1, "Vishvavasu")),
    ],
)
def test_tamil_festival_dates(day: date, expected: tuple[str, int, str]) -> None:
    assert _tamil(day, CHENNAI) == expected


def test_day_panchanga_calendar() -> None:
    calendar = compute_panchanga(date(2026, 9, 30), DELHI).calendar
    assert (calendar.amanta.name, calendar.amanta.number) == ("Bhadrapada", 6)
    assert not (calendar.amanta.adhika or calendar.amanta.nija or calendar.amanta.kshaya_name)
    assert (calendar.purnimanta_name, calendar.paksha) == ("Ashvina", "krishna")
    assert calendar.ritu == "Varsha"
    assert calendar.ayana_sidereal == calendar.ayana_tropical == "dakshinayana"
    assert (calendar.shaka_year, calendar.vikram_year, calendar.kali_year) == (1948, 2083, 5127)
    assert (calendar.samvatsara, calendar.samvatsara_number) == ("Parabhava", 40)
    assert (calendar.tamil_month, calendar.tamil_day) == ("Purattasi", 14)
    assert calendar.tamil_samvatsara == "Parabhava"


def test_kshaya_and_vriddhi_tithis() -> None:
    # Delhi, October 2026: tithi 23 begins and ends between the sunrises of the 3rd
    # and 4th; Saptami (7) prevails at the sunrises of both the 17th and the 18th.
    third = compute_panchanga(date(2026, 10, 3), DELHI)
    assert third.calendar.kshaya_tithis == [23] and not third.calendar.vriddhi_tithi
    assert [t.number for t in third.tithis] == [22, 23, 24]
    eighteenth = compute_panchanga(date(2026, 10, 18), DELHI)
    assert eighteenth.calendar.vriddhi_tithi and eighteenth.calendar.kshaya_tithis == []
    assert eighteenth.tithis[0].number == 7
