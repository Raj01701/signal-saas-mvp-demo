"""Transits scored by the natal Ashtakavarga (sign bindus and kakshyas)."""

from __future__ import annotations

from datetime import datetime
from itertools import pairwise

import pytest

from jyotish_engine.astro.bodies import Body
from jyotish_engine.astro.time import Instant
from jyotish_engine.chart import compute_chart
from jyotish_engine.models import BirthInput, BirthTimeSource, PlaceInput
from jyotish_engine.strength.ashtakavarga import (
    KAKSHYA_LORDS,
    KAKSHYA_SPAN,
    SEVEN,
    Ashtakavarga,
    ashtakavarga,
    kakshya_bindu,
)
from jyotish_engine.transit.ashtakavarga import ashtakavarga_transits, kakshya_transits
from jyotish_engine.transit.search import longitude_at

DELHI = PlaceInput(name="New Delhi", latitude=28.6139, longitude=77.2090, elevation_m=216)
START = Instant.from_utc(datetime(2020, 1, 1)).jd_ut
END = Instant.from_utc(datetime(2030, 1, 1)).jd_ut


@pytest.fixture(scope="module")
def natal() -> Ashtakavarga:
    chart = compute_chart(
        BirthInput(
            local_datetime=datetime(1990, 5, 17, 12, 0),
            place=DELHI,
            time_source=BirthTimeSource.BIRTH_CERTIFICATE,
        )
    )
    signs = {g.body: int(g.sign) for g in chart.grahas if g.body in SEVEN}
    return ashtakavarga(int(chart.ascendant.sign), signs)


def test_sign_transits_carry_bav_and_sav(natal: Ashtakavarga) -> None:
    stays = ashtakavarga_transits(natal, Body.SATURN, START, END)
    assert stays[0].start_jd_ut == START and stays[-1].end_jd_ut == END
    for before, after in pairwise(stays):
        assert before.end_jd_ut == after.start_jd_ut
    for stay in stays:
        middle = 0.5 * (stay.start_jd_ut + stay.end_jd_ut)
        assert int(longitude_at(Body.SATURN, middle) // 30) == stay.sign
        assert stay.bav_bindus == natal.bav["saturn"][stay.sign]
        assert stay.sav_bindus == natal.sav[stay.sign]
        assert 0 <= stay.bav_bindus <= 8 and 0 <= stay.sav_bindus <= 56
    # The same signs as a plain 5-day sampling, entered one sign at a time (with
    # retrograde returns into the previous sign).
    sampled = {
        int(longitude_at(Body.SATURN, START + d) // 30) for d in range(0, int(END - START), 5)
    }
    assert {s.sign for s in stays} == sampled
    assert all((b.sign - a.sign) % 12 in (1, 11) for a, b in pairwise(stays))


def test_kakshya_passages_cover_the_window(natal: Ashtakavarga) -> None:
    start, end = START, START + 27.4  # about one sidereal month of the Moon
    passages = kakshya_transits(natal, Body.MOON, start, end)
    assert passages[0].start_jd_ut == start and passages[-1].end_jd_ut == end
    assert 96 <= len(passages) <= 98  # all 96 kakshyas, cut at both ends
    for before, after in pairwise(passages):
        assert before.end_jd_ut == after.start_jd_ut
        assert (after.sign * 8 + after.kakshya - before.sign * 8 - before.kakshya) % 96 == 1
    for passage in passages:
        middle = 0.5 * (passage.start_jd_ut + passage.end_jd_ut)
        longitude = longitude_at(Body.MOON, middle)
        assert int(longitude // 30) == passage.sign
        assert int(longitude % 30 // KAKSHYA_SPAN) == passage.kakshya
        assert passage.lord == KAKSHYA_LORDS[passage.kakshya]
        assert passage.bindu == kakshya_bindu(natal, Body.MOON, longitude)


def test_bindus_in_a_sign_match_its_kakshya_count(natal: Ashtakavarga) -> None:
    passages = kakshya_transits(natal, Body.MOON, START, START + 27.4)
    for sign in range(12):
        lords = {p.lord for p in passages if p.sign == sign and p.bindu}
        in_sign = {p.lord for p in passages if p.sign == sign}
        if len(in_sign) == 8:  # a complete passage through the sign
            assert len(lords) == natal.bav["moon"][sign]


def test_retrograde_kakshya_steps_go_backwards(natal: Ashtakavarga) -> None:
    passages = kakshya_transits(natal, Body.JUPITER, START, END)
    steps = {
        (after.sign * 8 + after.kakshya - before.sign * 8 - before.kakshya) % 96
        for before, after in pairwise(passages)
    }
    assert steps == {1, 95}  # forward, and backward while retrograde


def test_nodes_are_not_scored(natal: Ashtakavarga) -> None:
    with pytest.raises(ValueError, match="no ashtakavarga"):
        ashtakavarga_transits(natal, Body.RAHU, START, END)
    with pytest.raises(ValueError, match="no ashtakavarga"):
        kakshya_transits(natal, Body.KETU, START, END)
