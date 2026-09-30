"""Kalachakra dasha: tables, balance at birth, sub-periods and chart output."""

from __future__ import annotations

from datetime import datetime
from itertools import pairwise

import pytest

from jyotish_engine.chart import compute_chart
from jyotish_engine.dasha.kalachakra import (
    NAKSHATRA_GROUP,
    PADA_SPAN,
    SIGN_YEARS,
    KalachakraGroup,
    birth_position,
    kalachakra_mahadashas,
    kalachakra_running,
    kalachakra_sub_periods,
    pada_signs,
    paramayus,
)
from jyotish_engine.dasha.tables import chart_kalachakra_table, running_kalachakra
from jyotish_engine.models import BirthInput, PlaceInput

YEAR = 365.25


def test_spans_of_life_follow_the_classical_pattern() -> None:
    savya = [paramayus(p) for p in range(4)]  # Ashwini
    apasavya = [paramayus(3 * 4 + p) for p in range(4)]  # Rohini
    assert savya == [100, 85, 83, 86]
    assert apasavya == [86, 83, 85, 100]
    for pada in range(108):
        assert len(pada_signs(pada)) == 9
        assert paramayus(pada) in (83, 85, 86, 100)


def test_groups_cover_every_nakshatra() -> None:
    counts = {group: NAKSHATRA_GROUP.count(group) for group in KalachakraGroup}
    assert counts == {
        KalachakraGroup.SAVYA_ASHWINI: 9,
        KalachakraGroup.SAVYA_BHARANI: 6,
        KalachakraGroup.APASAVYA_ROHINI: 4,
        KalachakraGroup.APASAVYA_MRIGASHIRA: 8,
    }


def test_birth_position_at_pada_boundaries() -> None:
    assert birth_position(0.0) == (0, 0, 0.0)
    pada, index, elapsed = birth_position(PADA_SPAN * 0.5)  # halfway through Ashwini 1
    assert pada == 0
    # 50 of 100 years: Aries 7 + Taurus 16 + Gemini 9 = 32, Cancer (21) runs, 18 in.
    assert (index, elapsed) == (3, pytest.approx(18.0))


def test_mahadashas_continue_into_the_next_pada() -> None:
    periods = kalachakra_mahadashas(PADA_SPAN * 0.99, 2451545.0, YEAR)
    assert periods[0].pada == 0
    later = [p for p in periods if p.pada == 1]
    assert later and [p.sign for p in later[:3]] == list(pada_signs(1)[:3])
    for a, b in pairwise(periods):
        assert a.end_jd == b.start_jd


def test_sub_periods_are_proportional_and_start_from_the_dasha_place() -> None:
    periods = kalachakra_mahadashas(PADA_SPAN * 2.5, 2451545.0, YEAR)  # Ashwini 3
    period = periods[1]
    subs = kalachakra_sub_periods(period)
    signs = pada_signs(period.pada)
    assert subs[0].sign == signs[period.position]
    assert subs[-1].end_jd == period.end_jd
    length = period.end_jd - period.start_jd
    first = subs[0].end_jd - subs[0].start_jd
    assert first == pytest.approx(length * SIGN_YEARS[subs[0].sign] / paramayus(period.pada))


def test_running_chain_nests() -> None:
    chain = kalachakra_running(123.4, 2451545.0, YEAR, 2451545.0 + 5000.0, depth=3)
    assert [len(p.signs) for p in chain] == [1, 2, 3]
    assert chain[1].signs[:1] == chain[0].signs


def test_chart_kalachakra_table() -> None:
    chart = compute_chart(
        BirthInput(
            local_datetime=datetime(1990, 5, 17, 12, 0),
            place=PlaceInput(name="New Delhi", latitude=28.6139, longitude=77.2090),
        )
    )
    table = chart_kalachakra_table(chart)
    assert table.periods[0].start_jd_ut <= chart.time.jd_ut < table.periods[0].end_jd_ut
    assert table.paramayus in (83, 85, 86, 100)
    assert table.deha == pada_signs(table.pada)[0]
    assert table.jeeva == pada_signs(table.pada)[-1]
    chain = running_kalachakra(chart, chart.time.jd_ut + 4000.0, 2)
    assert [len(p.signs) for p in chain] == [1, 2]
