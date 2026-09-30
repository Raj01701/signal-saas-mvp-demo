"""Sign timelines, Saturn transits (Sade Sati), gochara with vedha, double transit."""

from __future__ import annotations

import json
from datetime import date
from itertools import pairwise
from pathlib import Path

import numpy as np
import pytest

from jyotish_engine.astro import series
from jyotish_engine.astro.bodies import GRAHAS, Body
from jyotish_engine.astro.time import jd_to_datetime
from jyotish_engine.transit.gochara import (
    VEDHA,
    double_transits,
    gochara,
    influenced_signs,
)
from jyotish_engine.transit.saturn import SaturnTransit, sade_sati, saturn_transits
from jyotish_engine.transit.timeline import house_from, sign_timeline

FIXTURE = Path(__file__).parent / "fixtures" / "transits_swisseph.json"
START_2010 = 2455197.5  # 2010-01-01
END_2030 = 2462502.5  # 2030-01-01
CAPRICORN = 9


def test_house_from_counts_the_reference_as_first() -> None:
    assert house_from(9, 9) == 1
    assert house_from(9, 8) == 12
    assert house_from(0, 11) == 12
    assert house_from(11, 0) == 2


def test_sign_timeline_is_contiguous_and_complete() -> None:
    stays = sign_timeline(Body.MERCURY, START_2010, START_2010 + 800.0)
    assert stays[0].start_jd_ut == START_2010
    assert stays[-1].end_jd_ut == START_2010 + 800.0
    assert stays[0].entered_retrograde is None
    for a, b in pairwise(stays):
        assert a.end_jd_ut == b.start_jd_ut
        assert a.sign != b.sign
    # Mercury backs into the previous sign during some of its retrograde periods.
    assert any(s.entered_retrograde for s in stays)


def test_sade_sati_for_a_capricorn_moon() -> None:
    """Saturn: Sagittarius 26 Jan 2017 (back to Scorpio Jun-Oct 2017), Capricorn
    24 Jan 2020, Aquarius 29 Apr 2022 (back Jul 2022 - Jan 2023), Pisces 29 Mar 2025."""
    episodes = sade_sati(CAPRICORN, START_2010, END_2030)
    assert len(episodes) == 1
    episode = episodes[0]
    assert jd_to_datetime(episode.start_jd_ut).date() == date(2017, 1, 26)
    assert jd_to_datetime(episode.end_jd_ut).date() == date(2025, 3, 29)
    assert [s.house for s in episode.spans] == [12, 12, 1, 2, 1, 2]
    assert not episode.open_start and not episode.open_end

    # Every boundary inside the fixture's range (to 2025-01-01) is one of Swiss
    # Ephemeris' Saturn ingresses, to the second.
    saturn = json.loads(FIXTURE.read_text("utf-8"))["bodies"]["saturn"]
    reference = [e[0] for e in saturn["ingresses"]]
    boundaries = [b for s in episode.spans for b in (s.start_jd_ut, s.end_jd_ut)]
    checked = [b for b in boundaries if b < saturn["end"]]
    assert len(checked) == len(boundaries) - 1
    for boundary in checked:
        assert min(abs(boundary - r) for r in reference) * 86400.0 < 1.0


def test_other_saturn_transits_use_their_houses() -> None:
    found = saturn_transits(CAPRICORN, START_2010, END_2030)
    assert set(found) == set(SaturnTransit)
    for span in (s for e in found[SaturnTransit.ASHTAMA] for s in e.spans):
        assert span.house == 8
    for span in (s for e in found[SaturnTransit.KANTAKA] for s in e.spans):
        assert span.house in (4, 7, 10)
    # Saturn in Libra (10th from Capricorn): 15 Nov 2011, back in Virgo May-Aug 2012,
    # then Libra from 4 Aug 2012 to 2 Nov 2014.
    libra = found[SaturnTransit.KANTAKA][0]
    assert [s.house for s in libra.spans] == [10, 10]
    assert jd_to_datetime(libra.start_jd_ut).date() == date(2011, 11, 15)
    assert jd_to_datetime(libra.spans[1].start_jd_ut).date() == date(2012, 8, 4)
    assert jd_to_datetime(libra.end_jd_ut).date() == date(2014, 11, 2)
    # It reaches Aries (the 4th) in 2027 and is still there when the window closes.
    ardha = found[SaturnTransit.ARDHASHTAMA]
    assert len(ardha) == 1
    assert jd_to_datetime(ardha[0].start_jd_ut).year == 2027
    assert ardha[0].open_end and not ardha[0].open_start


def test_gochara_vedha_and_exceptions() -> None:
    moon_sign = 0
    # Sun in the 3rd (favourable), Mars in the 9th (its vedha house): obstructed.
    placements = {p.body: p for p in gochara({Body.SUN: 2, Body.MARS: 8}, moon_sign)}
    assert placements[Body.SUN].favourable
    assert placements[Body.SUN].obstructed_by == (Body.MARS,)
    # Saturn in the 9th does not obstruct the Sun (father and son).
    placements = {p.body: p for p in gochara({Body.SUN: 2, Body.SATURN: 8}, moon_sign)}
    assert placements[Body.SUN].obstructed_by == ()
    # Vipareeta vedha: Sun in the 9th (unfavourable) relieved by Jupiter in the 3rd.
    placements = {p.body: p for p in gochara({Body.SUN: 8, Body.JUPITER: 2}, moon_sign)}
    assert not placements[Body.SUN].favourable
    assert placements[Body.SUN].relieved_by == (Body.JUPITER,)
    # Moon and Mercury never obstruct each other.
    placements = {p.body: p for p in gochara({Body.MOON: 0, Body.MERCURY: 4}, moon_sign)}
    assert placements[Body.MOON].favourable
    assert placements[Body.MOON].obstructed_by == ()


def test_vedha_table_is_consistent() -> None:
    for body, pairs in VEDHA.items():
        assert body in GRAHAS
        assert all(1 <= h <= 12 and 1 <= v <= 12 and h != v for h, v in pairs.items())
        assert len(set(pairs.values())) == len(pairs)  # each vedha house used once


def test_double_transits_match_a_brute_force_scan() -> None:
    start, end = START_2010, START_2010 + 4 * 365.25
    intervals = double_transits(3, start, end)
    samples = np.arange(start + 0.5, end, 7.0)
    jupiter = series.sidereal_longitudes(Body.JUPITER, series.jd_ut_to_tt(samples))
    saturn = series.sidereal_longitudes(Body.SATURN, series.jd_ut_to_tt(samples))
    for t, j_lon, s_lon in zip(samples, jupiter, saturn, strict=True):
        expected = influenced_signs(Body.JUPITER, int(j_lon // 30)) & influenced_signs(
            Body.SATURN, int(s_lon // 30)
        )
        active = {d.sign for d in intervals if d.start_jd_ut <= t < d.end_jd_ut}
        assert active == expected, jd_to_datetime(float(t))
    for d in intervals:
        assert d.house == house_from(3, d.sign)
        assert d.start_jd_ut < d.end_jd_ut


@pytest.mark.parametrize("body", [Body.SUN, Body.SATURN])
def test_timeline_signs_agree_with_positions(body: Body) -> None:
    stays = sign_timeline(body, START_2010, START_2010 + 3000.0)
    for stay in stays:
        middle = 0.5 * (stay.start_jd_ut + stay.end_jd_ut)
        lon = series.sidereal_longitudes(body, series.jd_ut_to_tt([middle]))[0]
        assert int(lon // 30) == stay.sign
