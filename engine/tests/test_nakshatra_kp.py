from itertools import pairwise

import pytest

from jyotish_engine.astro.bodies import Body
from jyotish_engine.core.nakshatra import NAKSHATRAS, nakshatra_of
from jyotish_engine.kp.subdivisions import kp_249_table, kp_horary_ascendant, kp_lords


def test_nakshatra_boundaries_and_padas() -> None:
    start = nakshatra_of(0.0)
    assert start.nakshatra.name == "Ashwini" and start.pada == 1
    assert nakshatra_of(3.3334).pada == 2
    rohini = nakshatra_of(40.0 + 5.0)  # 15 deg Taurus
    assert rohini.nakshatra.name == "Rohini"
    assert rohini.nakshatra.lord is Body.MOON
    assert nakshatra_of(359.9999).nakshatra.name == "Revati"
    assert nakshatra_of(359.9999).pada == 4


def test_lords_follow_vimshottari_order() -> None:
    lords = [n.lord for n in NAKSHATRAS[:9]]
    assert lords == [
        Body.KETU,
        Body.VENUS,
        Body.SUN,
        Body.MOON,
        Body.MARS,
        Body.RAHU,
        Body.JUPITER,
        Body.SATURN,
        Body.MERCURY,
    ]
    assert NAKSHATRAS[9].lord is Body.KETU  # Magha


def test_fraction_elapsed() -> None:
    half = nakshatra_of(360.0 / 27.0 * 1.5)  # middle of Bharani
    assert half.fraction_elapsed == pytest.approx(0.5)


def test_kp_table_has_249_divisions_covering_the_zodiac() -> None:
    table = kp_249_table()
    assert len(table) == 249
    assert table[0].start == 0.0
    assert table[-1].end == pytest.approx(360.0)
    for a, b in pairwise(table):
        assert a.end == pytest.approx(b.start)
    # Divisions never straddle a sign boundary.
    for division in table:
        assert int(division.start // 30) == int((division.end - 1e-9) // 30)


def test_kp_lords_examples() -> None:
    # First sub of Ashwini belongs to Ketu itself; 0 deg 46 min 40 s later Venus starts.
    assert kp_lords(0.1).sub_lord is Body.KETU
    assert kp_lords(0.8).sub_lord is Body.VENUS
    # 5 deg Taurus lies in Krittika (Sun); 10 deg Taurus is exactly where Rohini (Moon) starts.
    lords = kp_lords(35.0)
    assert lords.sign_lord is Body.VENUS
    assert lords.star_lord is Body.SUN
    assert kp_lords(40.0).star_lord is Body.MOON
    assert kp_horary_ascendant(1) == 0.0
    with pytest.raises(ValueError, match="1 to 249"):
        kp_horary_ascendant(250)
