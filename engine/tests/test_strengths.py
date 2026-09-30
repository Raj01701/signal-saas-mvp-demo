"""Bhava bala, ishta and kashta, vimshopaka, Tajika strength and the strengths API."""

from __future__ import annotations

from datetime import datetime

import pytest

from jyotish_engine.annual.tajika_strength import hadda_lord, pancha_vargiya_bala, year_lord
from jyotish_engine.astro.bodies import GRAHAS, Body
from jyotish_engine.chart import compute_chart
from jyotish_engine.models import BirthInput, PlaceInput
from jyotish_engine.settings import Settings
from jyotish_engine.strength.ashtakavarga import MoonTable
from jyotish_engine.strength.bhava import bhava_dig_bala, bhava_madhyas, sign_class
from jyotish_engine.strength.strengths import compute_strengths
from jyotish_engine.strength.vimshopaka import WEIGHTS, VargaScheme, vimshopaka

DELHI = PlaceInput(name="New Delhi", latitude=28.6139, longitude=77.2090)


@pytest.fixture(scope="module")
def chart() -> object:
    return compute_chart(BirthInput(local_datetime=datetime(1990, 5, 17, 12, 0), place=DELHI))


def test_sign_classes() -> None:
    assert sign_class(65.0) == "human"  # Gemini
    assert sign_class(245.0) == "human"  # Sagittarius, first half
    assert sign_class(255.0) == "quadruped"  # Sagittarius, second half
    assert sign_class(275.0) == "quadruped"  # Capricorn, first half
    assert sign_class(290.0) == "water"  # Capricorn, second half
    assert sign_class(215.0) == "insect"  # Scorpio
    assert sign_class(100.0) == "water"  # Cancer


def test_bhava_dig_bala_peaks_at_the_signs_angle() -> None:
    assert bhava_dig_bala(1, 65.0) == 60.0  # human sign in the 1st
    assert bhava_dig_bala(7, 65.0) == 0.0  # and nothing opposite
    assert bhava_dig_bala(4, 100.0) == 60.0  # water sign in the 4th
    assert bhava_dig_bala(10, 5.0) == 60.0  # quadruped in the 10th
    assert bhava_dig_bala(1, 5.0) == 30.0


def test_bhava_madhyas_start_at_the_ascendant() -> None:
    madhyas = bhava_madhyas(100.0, 10.0)
    assert madhyas[0] == pytest.approx(100.0)
    assert madhyas[9] == pytest.approx(10.0)
    assert madhyas[6] == pytest.approx(280.0)


def test_vimshopaka_weights_and_range() -> None:
    for weights in WEIGHTS.values():
        assert sum(weights.values()) == pytest.approx(20.0)
    sidereal = {body: 17.0 * i + 3.0 for i, body in enumerate(GRAHAS)}
    for scheme in VargaScheme:
        for value in vimshopaka(sidereal, scheme).values():
            assert 5.0 <= value <= 20.0


def test_vimshopaka_rewards_own_signs() -> None:
    """Mars early in Aries sits in its own sign in the rasi and in several vargas."""
    sidereal = {body: 200.0 for body in GRAHAS}
    sidereal[Body.MARS] = 0.5
    scores = vimshopaka(sidereal, VargaScheme.SHADVARGA)
    assert scores[Body.MARS] > 10.0


def test_hadda_terms() -> None:
    assert hadda_lord(3.0) is Body.JUPITER  # Aries 0-6
    assert hadda_lord(29.0) is Body.SATURN  # Aries 25-30
    assert hadda_lord(240.0 + 13.0) is Body.VENUS  # Sagittarius 12-17


def test_pancha_vargiya_bala_bounds() -> None:
    exalted = pancha_vargiya_bala(Body.SUN, 10.0)  # deep exaltation, Aries, own-ish D9
    assert exalted.uchcha == pytest.approx(20.0)
    assert exalted.kshetra == pytest.approx(30.0)
    assert 0.0 < exalted.total <= 20.0
    debilitated = pancha_vargiya_bala(Body.SUN, 190.0)
    assert debilitated.uchcha == pytest.approx(0.0)
    assert debilitated.total < exalted.total


def test_year_lord_prefers_an_aspecting_office_bearer() -> None:
    sidereal = {body: 100.0 for body in GRAHAS}  # all in Cancer
    sidereal[Body.JUPITER] = 95.0  # exalted, Cancer
    sidereal[Body.SATURN] = 5.0  # debilitated, Aries: square to a Cancer lagna
    lord, aspects = year_lord([Body.SATURN, Body.JUPITER], 3, sidereal)
    assert lord is Body.JUPITER and aspects
    # Only Saturn aspects a Libra lagna (Aries-Libra opposition; Cancer-Libra square too).
    lord, _ = year_lord([Body.SATURN], 6, sidereal)
    assert lord is Body.SATURN


def test_compute_strengths(chart: object) -> None:
    result = compute_strengths(chart)  # type: ignore[arg-type]
    assert len(result.shadbala) == 7 and len(result.bhava_bala) == 12
    for planet in result.shadbala:
        assert planet.total == pytest.approx(
            planet.sthana
            + planet.dig
            + planet.kala
            + planet.cheshta
            + planet.naisargika
            + planet.drik
        )
        assert planet.rupas == pytest.approx(planet.total / 60.0)
        assert 0.0 <= planet.ishta_phala <= 60.0 and 0.0 <= planet.kashta_phala <= 60.0
    assert sum(result.ashtakavarga.sav) == 337
    assert result.ashtakavarga.moon_table == "pvr"
    for house in result.bhava_bala:
        lord_total = next(p.total for p in result.shadbala if p.body is house.lord)
        assert house.adhipati == pytest.approx(lord_total)
    assert set(result.vimshopaka) == {s.value for s in VargaScheme}


def test_alternative_moon_table_setting() -> None:
    birth = BirthInput(local_datetime=datetime(1990, 5, 17, 12, 0), place=DELHI)
    default = compute_strengths(compute_chart(birth))
    other = compute_strengths(
        compute_chart(birth, Settings(ashtakavarga_moon=MoonTable.ALTERNATIVE))
    )
    assert other.ashtakavarga.moon_table == "alternative"
    assert sum(other.ashtakavarga.bav["moon"]) == sum(default.ashtakavarga.bav["moon"]) == 49
