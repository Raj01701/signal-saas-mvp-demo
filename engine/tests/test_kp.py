"""KP significators, ruling planets, horary cusps and the chart-level analysis."""

from __future__ import annotations

from datetime import datetime

import pytest

from jyotish_engine.astro.bodies import Body
from jyotish_engine.chart import compute_chart
from jyotish_engine.kp.chart import compute_kp, compute_kp_horary
from jyotish_engine.kp.significators import bhava_of, horary_cusps, ruling_planets, significators
from jyotish_engine.kp.subdivisions import kp_horary_ascendant, kp_lords
from jyotish_engine.models import BirthInput, PlaceInput
from jyotish_engine.settings import Preset, preset

DELHI = PlaceInput(name="New Delhi", latitude=28.6139, longitude=77.2090, elevation_m=216)
#: Equal 30-degree cusps from 0 Aries: house n is the nth sign, owned by its lord.
SIGN_CUSPS = [30.0 * i for i in range(12)]
POSITIONS = {
    Body.SUN: 100.0,  # Cancer (4), Pushya: Saturn's star
    Body.MOON: 10.0,  # Aries (1), Ashwini: Ketu's star
    Body.MARS: 250.0,  # Sagittarius (9), Purva Ashadha: Venus's star
    Body.MERCURY: 80.0,  # Gemini (3), Punarvasu: Jupiter's star
    Body.JUPITER: 125.0,  # Leo (5), Magha: Ketu's star
    Body.VENUS: 160.0,  # Virgo (6), Hasta: Moon's star
    Body.SATURN: 195.0,  # Libra (7), Swati: Rahu's star
    Body.RAHU: 50.0,  # Taurus (2), Rohini: Moon's star
    Body.KETU: 230.0,  # Scorpio (8), Jyeshtha: Mercury's star
}


def test_bhava_of_wraps_around() -> None:
    cusps = [(345.0 + 30.0 * i) % 360.0 for i in range(12)]
    assert bhava_of(350.0, cusps) == 1 and bhava_of(10.0, cusps) == 1
    assert bhava_of(15.0, cusps) == 2 and bhava_of(344.9, cusps) == 12


def test_four_levels() -> None:
    found = significators(POSITIONS, SIGN_CUSPS)
    # Sun: its star lord Saturn occupies 7; it occupies 4; Saturn owns 10 and 11;
    # the Sun owns 5.
    assert found.by_planet[Body.SUN] == ((7,), (4,), (10, 11), (5,))
    assert found.houses_of(Body.SUN) == (7, 4, 10, 11, 5)
    # Rahu in Taurus is Venus's agent: it adds Venus's house (6) and Venus's signs (2, 7).
    assert found.by_planet[Body.RAHU] == ((1,), (2, 6), (4,), (2, 7))
    # House 4 (Cancer): the Sun occupies it; its owner the Moon.
    by_house = found.by_house[4]
    assert Body.SUN in by_house[1] and by_house[3] == (Body.MOON,)
    assert set(by_house[0]) == {
        b for b, lon in POSITIONS.items() if kp_lords(lon).star_lord is Body.SUN
    }


def test_ruling_planets() -> None:
    nodes = {Body.RAHU: 50.0, Body.KETU: 230.0}
    rulers = ruling_planets(0, moon_longitude=10.0, lagna_longitude=100.0, node_longitudes=nodes)
    assert rulers.day_lord is Body.SUN
    assert rulers.moon.sign_lord is Body.MARS and rulers.moon.star_lord is Body.KETU
    assert rulers.lagna.sign_lord is Body.MOON and rulers.lagna.star_lord is Body.SATURN
    # The lagna's sub lord is Venus, so Rahu (in Taurus) joins, as does Ketu (in
    # Scorpio, Mars's sign); with the lagna at 95 degrees (sub lord Saturn) Rahu does not.
    assert (rulers.lagna.sub_lord, rulers.nodes) == (Body.VENUS, (Body.RAHU, Body.KETU))
    other = ruling_planets(0, moon_longitude=10.0, lagna_longitude=95.0, node_longitudes=nodes)
    assert (other.lagna.sub_lord, other.nodes) == (Body.SATURN, (Body.KETU,))
    assert rulers.planets[0] is Body.SUN and len(set(rulers.planets)) == len(rulers.planets)


@pytest.mark.parametrize("number", [1, 57, 125, 249])
def test_horary_cusps_start_the_division(number: int) -> None:
    jd = 2461313.9
    moment, cusps = horary_cusps(number, jd, DELHI.latitude, DELHI.longitude, preset(Preset.KP))
    assert abs(moment - jd) <= 0.55
    assert abs((cusps[0] - kp_horary_ascendant(number) + 180.0) % 360.0 - 180.0) < 1e-5
    assert len(cusps) == 12


def test_kp_chart_and_horary() -> None:
    kp = preset(Preset.KP)
    chart = compute_chart(BirthInput(local_datetime=datetime(1990, 5, 17, 12, 0), place=DELHI), kp)
    result = compute_kp(chart)
    assert len(result.cusps) == 12 and len(result.planets) == 9
    for planet in result.planets:
        assert planet.house == bhava_of(planet.longitude, [c.longitude for c in result.cusps])
        assert planet.house in planet.signifies[1]
    assert result.ruling_planets[0] is result.day_lord
    assert all(len(levels) == 4 for levels in result.house_significators)
    with pytest.raises(ValueError, match="Placidus"):
        compute_kp(
            compute_chart(BirthInput(local_datetime=datetime(1990, 5, 17, 12, 0), place=DELHI))
        )
    horary = compute_kp_horary(111, 2461313.9, DELHI)
    assert horary.horary_number == 111 and horary.horary_cusp_jd_ut is not None
    assert horary.cusps[0].longitude == pytest.approx(kp_horary_ascendant(111), abs=1e-5)
