"""Lookups for questions about a chart: planets, houses, periods, transits, areas, years."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from itertools import pairwise

import pytest

from jyotish_engine.ask import ChartLookup, area_of, planet_of
from jyotish_engine.ask.lookup import areas_in, planets_in, sign_name
from jyotish_engine.astro.bodies import GRAHAS, Body
from jyotish_engine.astro.time import datetime_to_jd
from jyotish_engine.chart import compute_chart
from jyotish_engine.core.zodiac import SIGN_LORDS, Sign
from jyotish_engine.dasha.nakshatra import NakshatraDasha
from jyotish_engine.dasha.tables import running_periods
from jyotish_engine.models import BirthInput, ChartResult, PlaceInput
from jyotish_engine.rules.schema import Domain
from jyotish_engine.strength.strengths import compute_strengths

TODAY = date(2026, 10, 2)


@pytest.fixture(scope="module")
def chart() -> ChartResult:
    place = PlaceInput(name="Varanasi", latitude=25.3176, longitude=82.9739)
    return compute_chart(BirthInput(local_datetime=datetime(1985, 3, 14, 6, 20), place=place))


@pytest.fixture(scope="module")
def lookup(chart: ChartResult) -> ChartLookup:
    return ChartLookup(chart, today=TODAY, gender="male")


def test_names() -> None:
    assert planet_of("Guru") is Body.JUPITER and planet_of("शनि") is Body.SATURN
    assert planet_of(" moon ") is Body.MOON
    with pytest.raises(LookupError):
        planet_of("Pluto")
    assert area_of("career") is Domain.CAREER and area_of("job") is Domain.CAREER
    assert area_of("shaadi") is Domain.MARRIAGE
    with pytest.raises(LookupError):
        area_of("weather")
    assert areas_in("When will I get married and buy a house?") == [
        Domain.MARRIAGE,
        Domain.PROPERTY,
    ]
    assert areas_in("नौकरी कब लगेगी") == [Domain.CAREER]
    # Whole words only: a career is not a car, Sunday is not the Sun, a house is a bhava.
    assert areas_in("my career") == [Domain.CAREER]
    assert areas_in("What does my 7th house show?") == []
    assert planets_in("Is Sunday good?") == []
    assert planets_in("Guru and Mangal") == [Body.MARS, Body.JUPITER]
    assert sign_name(3) == "Cancer (Karka)"


def test_planet(lookup: ChartLookup, chart: ChartResult) -> None:
    lagna = int(chart.ascendant.sign)
    for body in GRAHAS:
        facts = lookup.planet(body)
        graha = next(g for g in chart.grahas if g.body is body)
        assert facts.house == graha.house
        ruled = {(int(s) - lagna) % 12 + 1 for s, lord in SIGN_LORDS.items() if lord is body}
        assert set(facts.rules) == ruled
        assert ((graha.house + 6 - 1) % 12) + 1 in facts.aspects  # every graha aspects the 7th
        assert "D9" in facts.vargas and "D10" in facts.vargas
        assert facts.summary().startswith(f"{body.value.title()}: ")
    assert lookup.planet("rahu").co_rules and lookup.planet("rahu").strength is None
    assert lookup.planet("jupiter").strength is not None
    assert set(lookup.planet("mars").aspects) == {
        (lookup.planet("mars").house + n - 2) % 12 + 1 for n in (4, 7, 8)
    }


def test_house(lookup: ChartLookup, chart: ChartResult) -> None:
    sav = compute_strengths(chart).ashtakavarga.sav
    for number in range(1, 13):
        facts = lookup.house(number)
        sign = (int(chart.ascendant.sign) + number - 1) % 12
        assert facts.sign == sign_name(sign)
        assert facts.lord == SIGN_LORDS[Sign(sign)].value.title()
        held = {g.body.value.title() for g in chart.grahas if g.body in GRAHAS and g.sign == sign}
        assert set(facts.occupants) == held
        assert facts.bindus == sav[sign]
        assert facts.summary().startswith(f"House {number} (")
    with pytest.raises(ValueError, match="1 to 12"):
        lookup.house(13)


def test_moment(lookup: ChartLookup, chart: ChartResult) -> None:
    day = date(2027, 5, 1)
    facts = lookup.moment(day)
    assert facts.age == 42
    jd = datetime_to_jd(datetime(2027, 5, 1, 12, tzinfo=UTC))
    chain = running_periods(chart, NakshatraDasha.VIMSHOTTARI, jd, depth=3)
    assert [p.lords for p in facts.periods] == [[b.value.title() for b in p.lords] for p in chain]
    assert {p.planet.lower() for p in facts.positions} == {b.value for b in GRAHAS}
    assert facts.readings and "mahadasha" in facts.summary()


def test_periods(lookup: ChartLookup) -> None:
    year = lookup.periods(date(2027, 1, 1), date(2028, 1, 1))
    assert year and all(len(p.lords) == 3 for p in year)
    decade = lookup.periods(date(2026, 1, 1), date(2036, 1, 1))
    assert all(len(p.lords) == 2 for p in decade)
    for rows in (year, decade):
        assert rows[0].start <= date(2027, 1, 1) and rows[-1].end >= date(2028, 1, 1)
        assert all(a.end == b.start for a, b in pairwise(rows))
    with pytest.raises(ValueError, match="end after"):
        lookup.periods(date(2027, 1, 1), date(2027, 1, 1))


def test_transits(lookup: ChartLookup) -> None:
    start, end = date(2026, 10, 1), date(2029, 1, 1)
    stays = lookup.transits(start, end)
    assert {t.planet for t in stays} == {"Saturn", "Jupiter", "Rahu", "Ketu"}
    for t in stays:
        assert t.start < end and t.end > start and t.start < t.end
        sign = next(s for s in Sign if t.sign == sign_name(s))
        assert t.house_from_moon == (int(sign) - lookup.moon) % 12 + 1
        if t.planet == "Saturn" and t.house_from_moon in (12, 1, 2):
            assert t.note and "Sade Sati" in t.note
    # Stays show their real ingress and egress, not the edges of the range.
    saturn = [t for t in stays if t.planet == "Saturn"]
    assert saturn[0].start < start and saturn[-1].end > end
    # Rahu and Ketu are always opposite.
    for rahu in (t for t in stays if t.planet == "Rahu"):
        ketu = next(k for k in stays if k.planet == "Ketu" and k.start == rahu.start)
        assert (ketu.house_from_lagna - rahu.house_from_lagna) % 12 == 6
    assert lookup.transits(date(2100, 1, 1), date(2101, 1, 1)) == []


def test_area(lookup: ChartLookup) -> None:
    marriage = lookup.area("marriage")
    assert marriage.houses == [7, 2, 11] and marriage.karakas == ["Venus"]
    assert marriage.windows and 0.0 <= marriage.promise <= 1.0
    adult = lookup.born + timedelta(days=18 * 365)
    assert all(w.end > adult for w in marriage.windows)  # read from adulthood only
    ahead = lookup.area("job", TODAY, date(2036, 1, 1))
    assert all(w.end > TODAY and w.start < date(2036, 1, 1) for w in ahead.windows)
    health = lookup.area(Domain.HEALTH)
    assert health.windows == [] and health.note
    sensitive = ChartLookup(lookup.chart, today=TODAY, include_sensitive=True)
    assert sensitive.area(Domain.HEALTH).windows
    female = ChartLookup(lookup.chart, today=TODAY, gender="female")
    assert female.area("marriage").karakas == ["Venus", "Jupiter"]


def test_year(lookup: ChartLookup) -> None:
    facts = lookup.year(2027)
    assert facts.turns == 42
    assert facts.annual is not None and facts.annual.start.year == 2027
    assert 1 <= facts.annual.muntha_house <= 12
    assert {len(p.lords) for p in facts.periods} == {2, 3}
    assert all(p.end > date(2027, 1, 1) and p.start < date(2028, 1, 1) for p in facts.periods)
    for windows in facts.windows.values():
        assert all(w.end > date(2027, 1, 1) and w.start < date(2028, 1, 1) for w in windows)
    assert "health" not in facts.windows
    assert facts.summary().startswith("2027 (turns 42")
    assert lookup.year(1980).annual is None  # before the birth
