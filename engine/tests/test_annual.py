"""Tajika basics, Mudda dasha and the assembled Varshaphal and Tithi Pravesha."""

from __future__ import annotations

from datetime import datetime
from itertools import pairwise

import pytest

from jyotish_engine.annual.dashas import mudda_dashas, mudda_sub_periods
from jyotish_engine.annual.tajika import (
    SEVEN,
    TajikaAspect,
    TajikaYoga,
    ikkavala,
    induvara,
    muntha_sign,
    office_bearers,
    tajika_aspect,
    tajika_relation,
)
from jyotish_engine.annual.varshaphal import compute_tithi_pravesha, compute_varshaphal
from jyotish_engine.astro.bodies import GRAHAS, Body
from jyotish_engine.chart import compute_chart
from jyotish_engine.core.nakshatra import NAKSHATRA_SPAN
from jyotish_engine.models import BirthInput, PlaceInput

DELHI = PlaceInput(name="New Delhi", latitude=28.6139, longitude=77.2090)


def test_ikkavala_and_induvara() -> None:
    # Lagna Aries: houses 1, 2, 4, 5, 7, 8, 10, 11 are kendras and panapharas.
    good = dict(zip(SEVEN, [0.0, 35.0, 95.0, 125.0, 185.0, 215.0, 305.0], strict=True))
    assert ikkavala(0, good) and not induvara(0, good)
    bad = dict(zip(SEVEN, [65.0, 155.0, 245.0, 335.0, 65.0, 155.0, 245.0], strict=True))
    assert induvara(0, bad) and not ikkavala(0, bad)
    mixed = {**good, Body.SATURN: 65.0}  # Saturn in the 3rd
    assert not ikkavala(0, mixed) and not induvara(0, mixed)


def test_muntha_moves_one_sign_a_year() -> None:
    assert muntha_sign(4, 0) == 4
    assert muntha_sign(4, 1) == 5
    assert muntha_sign(11, 13) == 0


def test_tajika_aspects_by_sign_distance() -> None:
    assert tajika_aspect(0, 0) is TajikaAspect.CONJUNCTION
    assert tajika_aspect(0, 2) is TajikaAspect.SEXTILE
    assert tajika_aspect(0, 8) is TajikaAspect.TRINE
    assert tajika_aspect(0, 9) is TajikaAspect.SQUARE
    assert tajika_aspect(0, 6) is TajikaAspect.OPPOSITION
    assert tajika_aspect(0, 1) is None
    assert tajika_aspect(0, 5) is None


def test_ithasala_and_isarapha() -> None:
    # Moon (fast) at 10 deg Aries, Saturn (slow) at 14 deg Leo: trine, Moon behind by 4.
    applying = tajika_relation(Body.MOON, 10.0, Body.SATURN, 134.0)
    assert applying is not None and applying.yoga is TajikaYoga.ITHASALA
    assert applying.friendly and applying.orb == pytest.approx(10.5)
    # Moon past Saturn by 3 degrees: separating.
    separating = tajika_relation(Body.SATURN, 134.0, Body.MOON, 17.0)
    assert separating is not None and separating.yoga is TajikaYoga.ISARAPHA
    assert separating.faster is Body.MOON
    # Too far apart for the orbs: an aspect but no yoga.
    loose = tajika_relation(Body.MARS, 1.0, Body.SATURN, 140.0)
    assert loose is not None and loose.yoga is None
    assert tajika_relation(Body.SUN, 1.0, Body.MOON, 35.0) is None  # 2nd house: no aspect


def test_office_bearers_by_day_and_night() -> None:
    sidereal = {body: 0.0 for body in GRAHAS}
    sidereal[Body.SUN] = 45.0  # Taurus: Venus
    sidereal[Body.MOON] = 100.0  # Cancer: Moon
    day = office_bearers(4, 0, 3, sidereal, by_day=True)
    assert day.natal_lagna_lord is Body.SUN  # Leo
    assert day.varsha_lagna_lord is Body.MARS  # Aries
    assert day.muntha_lord is Body.MARS  # Leo + 3 = Scorpio
    assert day.tri_rashi_lord is Body.SUN  # Aries by day
    assert day.dina_ratri_lord is Body.VENUS
    night = office_bearers(4, 0, 3, sidereal, by_day=False)
    assert night.tri_rashi_lord is Body.JUPITER
    assert night.dina_ratri_lord is Body.MOON
    assert day.candidates() == [Body.SUN, Body.MARS, Body.VENUS]


def test_mudda_is_vimshottari_in_one_year() -> None:
    year_start, year_days = 2451545.0, 365.25
    # Moon at the start of Ashwini: Ketu's dasha, advanced 2 years -> Sun, nothing elapsed.
    periods = mudda_dashas(0.0, 2, year_start, year_days)
    assert periods[0].lord is Body.SUN and periods[0].start_jd == year_start
    assert sum(p.end_jd - p.start_jd for p in periods[:9]) == pytest.approx(year_days)
    # Halfway through a nakshatra: the first dasha began half its length earlier.
    half = mudda_dashas(NAKSHATRA_SPAN / 2, 0, year_start, year_days)
    ketu_days = 7 * year_days / 120
    assert half[0].start_jd == pytest.approx(year_start - ketu_days / 2)
    assert half[-1].end_jd >= year_start + year_days
    for a, b in pairwise(half):
        assert a.end_jd == b.start_jd
    subs = mudda_sub_periods(half[1])
    assert subs[0].lords == (half[1].lord, half[1].lord)
    assert subs[-1].end_jd == half[1].end_jd


@pytest.fixture(scope="module")
def natal() -> object:
    return compute_chart(BirthInput(local_datetime=datetime(1990, 5, 17, 12, 0), place=DELHI))


def test_varshaphal_for_a_year_of_life(natal: object) -> None:
    chart = natal  # type: ignore[assignment]
    result = compute_varshaphal(chart, 36)  # type: ignore[arg-type]
    natal_sun = next(g for g in chart.grahas if g.body is Body.SUN)  # type: ignore[attr-defined]
    annual_sun = next(g for g in result.chart.grahas if g.body is Body.SUN)
    assert annual_sun.sidereal_longitude == pytest.approx(natal_sun.sidereal_longitude, abs=1e-6)
    assert 365.2 < result.end_jd_ut - result.start_jd_ut < 365.3
    assert result.muntha == (chart.ascendant.sign + 36) % 12  # type: ignore[attr-defined]
    mahas = [p for p in result.mudda if len(p.lords) == 1]
    assert mahas[0].start_jd_ut <= result.start_jd_ut < mahas[0].end_jd_ut
    assert mahas[-1].end_jd_ut >= result.end_jd_ut
    patyayini = [p for p in result.patyayini if len(p.lords) == 1]
    assert len(patyayini) == 8 and "lagna" in {p.lords[0] for p in patyayini}
    assert patyayini[0].start_jd_ut == result.start_jd_ut
    assert patyayini[-1].end_jd_ut == pytest.approx(result.end_jd_ut)
    assert len(result.sahams) == 36
    punya = next(s for s in result.sahams if s.name == "punya")
    annual = {g.body: g.sidereal_longitude for g in result.chart.grahas}
    lagna = result.chart.ascendant.sidereal_longitude
    arc = (
        annual[Body.MOON] - annual[Body.SUN]
        if result.by_day
        else annual[Body.SUN] - annual[Body.MOON]
    )
    assert (punya.sidereal_longitude - lagna - arc) % 30.0 == pytest.approx(0.0, abs=1e-9)
    assert punya.sign == int(punya.sidereal_longitude // 30)
    first = compute_varshaphal(chart, 0)  # type: ignore[arg-type]
    assert first.start_jd_ut == chart.time.jd_ut  # type: ignore[attr-defined]
    with pytest.raises(ValueError, match="years_completed"):
        compute_varshaphal(chart, -1)  # type: ignore[arg-type]


def test_tithi_pravesha_repeats_the_birth_tithi(natal: object) -> None:
    chart = natal  # type: ignore[assignment]
    result = compute_tithi_pravesha(chart, 10)  # type: ignore[arg-type]
    by_body = {g.body: g for g in result.chart.grahas}
    elongation = (
        by_body[Body.MOON].sidereal_longitude - by_body[Body.SUN].sidereal_longitude
    ) % 360
    assert elongation == pytest.approx(result.elongation, abs=1e-5)
    natal_sun = next(g for g in chart.grahas if g.body is Body.SUN)  # type: ignore[attr-defined]
    assert by_body[Body.SUN].sign == natal_sun.sign
