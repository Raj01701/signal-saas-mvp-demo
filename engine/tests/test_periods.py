"""Period readings: the rules see the running dasha and the transits of a moment."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from jyotish_engine.astro.time import datetime_to_jd, jd_to_datetime
from jyotish_engine.chart import compute_chart
from jyotish_engine.dasha.nakshatra import NakshatraDasha
from jyotish_engine.dasha.tables import running_periods
from jyotish_engine.models import BirthInput, ChartResult, PlaceInput
from jyotish_engine.rules.dsl import compile_expression
from jyotish_engine.rules.facts import ChartFacts, MissingFactError
from jyotish_engine.rules.periods import compute_period_readings

DELHI = PlaceInput(name="New Delhi", latitude=28.6139, longitude=77.2090)
MOMENT = datetime(2026, 9, 30, tzinfo=UTC)


@pytest.fixture(scope="module")
def chart() -> ChartResult:
    """Leo rising: Mercury and Saturn own the maraka houses (2nd and 7th)."""
    return compute_chart(BirthInput(local_datetime=datetime(1990, 5, 17, 12, 0), place=DELHI))


def test_readings_follow_the_running_dasha_and_transits(chart: ChartResult) -> None:
    out = compute_period_readings(chart, MOMENT)
    running = running_periods(chart, NakshatraDasha.VIMSHOTTARI, datetime_to_jd(MOMENT), depth=3)
    assert out.dasha == running
    md, ad = running[1].lords
    assert f"dasha.pair_{md.value}_{ad.value}" in {r.id for r in out.dasha_readings}
    gochara = {r.id for r in out.transit_readings + out.cancelled}
    for transit in out.transits:
        assert f"transit.{transit.body.value}_h{transit.house_from_moon}" in gochara
    assert all(r.cancel_evidence for r in out.cancelled)
    assert all(r.evidence and r.sources for r in out.dasha_readings + out.transit_readings)


def test_sensitive_rules_only_on_request(chart: ChartResult) -> None:
    moment = datetime(2035, 1, 1, tzinfo=UTC)  # Saturn mahadasha: a maraka lord here
    hidden = compute_period_readings(chart, moment)
    shown = compute_period_readings(chart, moment, include_sensitive=True)
    assert "dasha.maraka" not in {r.id for r in hidden.dasha_readings}
    assert "dasha.maraka" in {r.id for r in shown.dasha_readings}


def test_moment_before_birth_is_rejected(chart: ChartResult) -> None:
    with pytest.raises(ValueError, match="before the birth"):
        compute_period_readings(chart, datetime(1980, 1, 1, tzinfo=UTC))


def test_datetime_round_trip() -> None:
    assert jd_to_datetime(datetime_to_jd(MOMENT)) == MOMENT
    assert datetime_to_jd(datetime(2000, 1, 1, 12)) == 2451545.0


FACTS = ChartFacts.from_spec(
    {
        "lagna": "taurus",
        "moon": "aries",
        "rest": "leo",
        "dasha": ["saturn", "venus"],
        "transit": {"sun": "gemini", "mars": "sagittarius", "jupiter": "leo", "saturn": "aquarius"},
    }
)


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("md == lord(10) and ad == venus", True),
        ("house(md) == 4", True),
        ("yogakaraka(md)", True),  # Saturn owns the 9th and 10th from Taurus
        ("yogakaraka(ad)", False),
        ("natural_friend(md, ad) and natural_enemy(sun, md)", True),
        ("transit_house(jupiter, moon) == 5 and transit_house(jupiter) == 4", True),
        ("transit_sign(saturn) == aquarius", True),
        ("transit_influences(saturn, 4)", True),  # Saturn in the 10th aspects the 4th
        ("transit_influences(jupiter, 11)", False),
        ("vedha(sun)", True),  # Sun 3rd from the Moon, Mars in the vedha house (9th)
        ("vedha(jupiter)", False),  # 5th from the Moon, nothing in the 4th
        ("vedha(saturn)", True),  # 11th from the Moon, Jupiter in the vedha house (5th)
    ],
)
def test_period_functions(expression: str, expected: bool) -> None:
    value, evidence = compile_expression(expression).evaluate(FACTS)
    assert value is expected
    assert bool(evidence) is expected


def test_period_facts_are_required() -> None:
    natal = ChartFacts.from_spec({"lagna": "aries", "rest": "leo"})
    with pytest.raises(MissingFactError, match="dasha"):
        compile_expression("md == sun").evaluate(natal)
    with pytest.raises(MissingFactError, match="transits"):
        compile_expression("transit_house(saturn) == 1").evaluate(natal)
