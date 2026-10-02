"""Chart facts: test-chart specs, derived states, lunar day and chart conversion."""

from __future__ import annotations

from datetime import datetime

import pytest

from jyotish_engine.astro.bodies import GRAHAS, Body
from jyotish_engine.chart import compute_chart
from jyotish_engine.models import BirthInput, BirthTimeSource, PlaceInput
from jyotish_engine.rules.facts import ChartFacts, MissingFactError, parse_position

DELHI = PlaceInput(name="New Delhi", latitude=28.6139, longitude=77.2090, elevation_m=216)


def _facts(**spec: object) -> ChartFacts:
    return ChartFacts.from_spec({"lagna": "aries", "rest": "leo", **spec})


def test_parse_position() -> None:
    assert parse_position("aries") == 15.0
    assert parse_position("Leo 3.5") == 123.5
    assert parse_position(370) == 10.0
    assert parse_position(12.25) == 12.25
    for bad in ["", "ophiuchus", "leo 30", "leo -1", "leo 1 2", True]:
        with pytest.raises(ValueError, match="bad position"):
            parse_position(bad)


def test_rest_fills_unplaced_grahas() -> None:
    facts = _facts(mars="capricorn 12")
    assert facts.positions[Body.MARS] == 282.0
    assert facts.positions[Body.SUN] == facts.positions[Body.SATURN] == 135.0
    assert set(facts.positions) == set(GRAHAS)


def test_nodes_are_kept_opposite() -> None:
    assert _facts().positions[Body.KETU] == 315.0
    assert _facts(rahu="gemini 10").positions[Body.KETU] == 250.0
    assert _facts(ketu="gemini 10").positions[Body.RAHU] == 250.0
    both = _facts(rahu="aries 1", ketu="libra 1")
    assert both.positions[Body.RAHU] == 1.0 and both.positions[Body.KETU] == 181.0
    with pytest.raises(ValueError, match="not opposite"):
        _facts(rahu="aries 1", ketu="libra 2")


@pytest.mark.parametrize(
    ("spec", "message"),
    [
        ({"rest": "leo"}, "no lagna"),
        ({"lagna": "aries", "sun": "leo"}, "places no moon"),
        ({"lagna": "aries", "rest": "leo", "pluto": "leo"}, "unknown keys"),
        ({"lagna": "aries", "rest": "leo", "day_birth": "yes"}, "day_birth"),
        ({"lagna": "aries", "rest": "leo", "gender": "other"}, "gender"),
    ],
)
def test_bad_specs(spec: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        ChartFacts.from_spec(spec)


def test_spec_without_nodes_or_rest_is_rejected() -> None:
    placed = {b.value: "leo" for b in GRAHAS if b not in (Body.RAHU, Body.KETU)}
    with pytest.raises(ValueError, match="places no rahu"):
        ChartFacts.from_spec({"lagna": "aries", **placed})


def test_houses_lords_and_occupants() -> None:
    facts = _facts(mars="capricorn", moon="cancer")
    assert facts.house(Body.MARS) == 10
    assert facts.house(Body.MARS, Body.MOON) == 7
    assert facts.lord(10) is Body.SATURN
    assert facts.lord(1, Body.MOON) is Body.MOON
    assert facts.dispositor(Body.MARS) is Body.SATURN
    assert facts.occupants(5) == [
        Body.SUN,
        Body.MERCURY,
        Body.JUPITER,
        Body.VENUS,
        Body.SATURN,
        Body.RAHU,
    ]


def test_retrograde_from_spec() -> None:
    facts = _facts(retrograde=["saturn"])
    assert facts.retrograde == frozenset({Body.SATURN})
    with pytest.raises(ValueError):
        _facts(retrograde=["comet"])


def test_natural_benefics() -> None:
    waxing = _facts(sun="aries 0", moon="taurus 15")
    assert Body.MOON in waxing.benefics and waxing.waxing
    waning = _facts(sun="aries 0", moon="scorpio 15")
    assert Body.MOON not in waning.benefics and not waning.waxing
    alone = _facts(mercury="virgo")
    assert Body.MERCURY in alone.benefics
    with_saturn = _facts(mercury="virgo", saturn="virgo")
    assert Body.MERCURY not in with_saturn.benefics
    balanced = _facts(mercury="virgo", saturn="virgo", jupiter="virgo")
    assert Body.MERCURY in balanced.benefics
    assert {Body.JUPITER, Body.VENUS} <= alone.benefics
    assert not {Body.SUN, Body.MARS, Body.SATURN, Body.RAHU, Body.KETU} & alone.benefics


def test_working_strength() -> None:
    # Exalted Mars stays strong although its dispositor is a compound enemy.
    exalted = ChartFacts.from_spec(
        {"lagna": "aries", "moon": "aries", "mars": "capricorn", "rest": "gemini"}
    )
    assert exalted.enemy_sign(Body.MARS) and exalted.strong(Body.MARS)
    assert not _facts(mars="cancer").strong(Body.MARS)  # debilitated
    assert not _facts(mercury="leo").strong(Body.MERCURY)  # combust with the Sun
    assert _facts(sun="leo", venus="cancer", rest="gemini").strong(Body.VENUS)  # kendra
    assert not _facts(sun="aries", venus="leo", rest="gemini").strong(Body.VENUS)  # enemy sign
    assert not _facts(venus="gemini", sun="leo").strong(Body.VENUS)  # 3rd house, no dignity


@pytest.mark.parametrize(
    ("moon", "tithi", "karana"),
    [
        ("aries 0", 1, "kimstughna"),
        ("aries 6", 1, "bava"),
        ("aries 20", 2, "kaulava"),
        ("taurus 15", 4, "vishti"),
        ("pisces 12", 29, "shakuni"),
        ("pisces 18", 30, "chatushpada"),
        ("pisces 24", 30, "naga"),
    ],
)
def test_tithi_and_karana(moon: str, tithi: int, karana: str) -> None:
    facts = _facts(sun="aries 0", moon=moon)
    assert facts.tithi == tithi
    assert facts.karana == karana


def test_nakshatra_pada_and_gandanta() -> None:
    facts = ChartFacts.from_spec({"lagna": "aries 0", "moon": "cancer 11", "rest": "leo"})
    assert (facts.nakshatra("lagna"), facts.pada("lagna")) == (1, 1)
    assert (facts.nakshatra(Body.MOON), facts.pada(Body.MOON)) == (8, 3)
    assert _facts(moon="pisces 28").gandanta(Body.MOON)
    assert _facts(moon="leo 1").gandanta(Body.MOON)
    assert _facts(moon="aries 3").gandanta(Body.MOON)
    assert not _facts(moon="aries 4").gandanta(Body.MOON)


def test_birth_facts_are_required_only_when_used() -> None:
    facts = _facts()
    with pytest.raises(MissingFactError, match="day_birth"):
        facts.require_day_birth()
    with pytest.raises(MissingFactError, match="gender"):
        facts.require_gender()
    known = _facts(day_birth=True, gender="male")
    assert known.require_day_birth() is True and known.require_gender() == "male"


def test_from_chart_matches_the_chart() -> None:
    chart = compute_chart(
        BirthInput(
            local_datetime=datetime(1990, 5, 17, 12, 0),
            place=DELHI,
            time_source=BirthTimeSource.BIRTH_CERTIFICATE,
        )
    )
    facts = ChartFacts.from_chart(chart, gender="female")
    assert facts.lagna == chart.ascendant.sidereal_longitude
    for graha in chart.grahas:
        if graha.body in GRAHAS:
            assert facts.positions[graha.body] == graha.sidereal_longitude
    assert facts.retrograde == frozenset(g.body for g in chart.grahas if g.retrograde)
    assert facts.day_birth is True
    assert facts.gender == "female"
    assert facts.lagna_sign == int(chart.ascendant.sign)
