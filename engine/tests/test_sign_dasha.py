"""Sign dasha rules: orders, lengths, exceptions and sub-periods."""

from __future__ import annotations

from datetime import datetime

import pytest

from jyotish_engine.astro.bodies import GRAHAS, Body
from jyotish_engine.chart import compute_chart
from jyotish_engine.core.jaimini import count_signs, dasha_years, stronger_sign
from jyotish_engine.dasha.sign import (
    SignDasha,
    chara_antardasha_order,
    chara_order,
    narayana_order,
    sign_mahadashas,
    sign_sub_periods,
)
from jyotish_engine.dasha.tables import chart_sign_dasha_table, running_sign_periods
from jyotish_engine.models import BirthInput, PlaceInput


def _positions(**signs: float) -> dict[Body, float]:
    """All grahas at 10 degrees of Aries unless given (as longitudes)."""
    base = {body: 10.0 for body in GRAHAS}
    base.update({Body(name): lon for name, lon in signs.items()})
    return base


def test_count_signs_is_inclusive_in_both_directions() -> None:
    assert count_signs(0, 0) == 1
    assert count_signs(0, 3) == 4
    assert count_signs(0, 3, forward=False) == 10
    assert count_signs(11, 0) == 2


def test_dasha_years_counting_and_exceptions() -> None:
    # Aries (odd-footed) with Mars in Cancer: count Aries..Cancer = 4, minus 1 = 3,
    # and Mars is debilitated in Cancer: 2 years.
    assert dasha_years(0, _positions(mars=100.0)) == 2
    # Cancer (even-footed) with the Moon in Aries: count backwards Cancer..Aries = 4.
    assert dasha_years(3, _positions(moon=5.0)) == 3
    # Lord in the sign itself: 12 years; exalted lord adds one (Sun in Aries for Leo).
    assert dasha_years(4, _positions(sun=125.0)) == 12
    # Leo is even-footed: Leo..Aries backwards = 5, so 4 years, plus 1 (Sun exalted).
    assert dasha_years(4, _positions(sun=5.0)) == 5
    # Both co-lords of Scorpio in Scorpio: 12 years, whatever their dignity.
    assert dasha_years(7, _positions(mars=215.0, ketu=225.0, rahu=45.0)) == 12


def test_chara_order_direction_follows_the_ninth_house() -> None:
    # Aries lagna: the 9th is Sagittarius, odd-footed, so the dashas run zodiacally.
    assert chara_order(0) == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    # Cancer lagna: the 9th is Pisces, even-footed, so they run backwards.
    assert chara_order(3) == [3, 2, 1, 0, 11, 10, 9, 8, 7, 6, 5, 4]


def test_chara_antardashas_end_with_the_dasha_sign() -> None:
    sidereal = _positions()
    assert chara_antardasha_order(0, sidereal)[0] == 1
    assert chara_antardasha_order(0, sidereal)[-1] == 0
    assert chara_antardasha_order(3, sidereal)[:2] == [2, 1]  # Cancer is even-footed
    assert chara_antardasha_order(3, sidereal)[-1] == 3


@pytest.mark.parametrize("seed", range(12))
def test_narayana_orders_visit_every_sign_once(seed: int) -> None:
    sidereal = _positions(saturn=200.0, ketu=300.0)
    order = narayana_order(seed, sidereal)
    assert order[0] == seed
    assert sorted(order) == list(range(12))


def test_narayana_progressions_by_nature_and_exceptions() -> None:
    far = _positions(saturn=200.0, ketu=300.0, rahu=120.0)
    assert narayana_order(0, far)[:3] == [0, 1, 2]  # movable, odd: sign by sign
    assert narayana_order(3, far)[:3] == [3, 2, 1]  # movable, even: backwards
    assert narayana_order(4, far)[:3] == [4, 9, 2]  # fixed, odd: every sixth sign
    assert narayana_order(1, far)[:3] == [1, 8, 3]  # fixed, even: every sixth backwards
    assert narayana_order(2, far)[:6] == [2, 10, 6, 5, 1, 9]  # dual: kendras and trines
    with_saturn = _positions(saturn=40.0, ketu=300.0, rahu=120.0)  # Saturn in Taurus
    assert narayana_order(1, with_saturn)[:3] == [1, 2, 3]
    with_ketu = _positions(saturn=200.0, ketu=40.0, rahu=220.0)  # Ketu in Taurus
    assert narayana_order(1, with_ketu)[:3] == [1, 6, 11]


def test_stronger_sign_prefers_more_planets_then_rules() -> None:
    sidereal = _positions(sun=40.0, moon=45.0, rahu=200.0, ketu=20.0)
    assert stronger_sign(1, 7, sidereal) == 1  # two grahas in Taurus, none in Scorpio


def test_second_round_complements_the_first() -> None:
    sidereal = _positions(
        sun=40.0,
        moon=100.0,
        mars=200.0,
        mercury=250.0,
        jupiter=300.0,
        venus=330.0,
        saturn=15.0,
        rahu=70.0,
        ketu=250.0,
    )
    mahas = sign_mahadashas(SignDasha.NARAYANA, 5.0, sidereal, 2451545.0, 365.25)
    assert len(mahas) == 24
    for first, second in zip(mahas[:12], mahas[12:], strict=True):
        assert first.sign == second.sign
        years_1 = (first.end_jd - first.start_jd) / 365.25
        years_2 = (second.end_jd - second.start_jd) / 365.25
        assert years_1 + years_2 == pytest.approx(max(12.0, years_1))
    subs = sign_sub_periods(SignDasha.NARAYANA, mahas[0], sidereal)
    assert len(subs) == 12 and subs[-1].end_jd == mahas[0].end_jd
    assert sorted(s.sign for s in subs) == list(range(12))


def test_chart_level_sign_dasha_tables() -> None:
    chart = compute_chart(
        BirthInput(
            local_datetime=datetime(1990, 5, 17, 12, 0),
            place=PlaceInput(name="New Delhi", latitude=28.6139, longitude=77.2090),
        )
    )
    table = chart_sign_dasha_table(chart, SignDasha.CHARA)
    assert table.first_sign == chart.ascendant.sign
    assert table.periods[0].start_jd_ut == chart.time.jd_ut
    assert len([p for p in table.periods if len(p.signs) == 1]) == 24
    narayana = chart_sign_dasha_table(chart, SignDasha.NARAYANA, depth=1)
    assert narayana.first_sign in (chart.ascendant.sign, (chart.ascendant.sign + 6) % 12)
    chain = running_sign_periods(chart, SignDasha.NARAYANA, chart.time.jd_ut + 9000.0, 3)
    assert [len(p.signs) for p in chain] == [1, 2, 3]
