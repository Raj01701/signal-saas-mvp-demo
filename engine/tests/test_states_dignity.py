import pytest

from jyotish_engine.astro.bodies import Body
from jyotish_engine.core.aspects import graha_aspected_signs, rashi_aspected_signs
from jyotish_engine.core.dignity import (
    Dignity,
    Relationship,
    compound_relationship,
    dignity,
    natural_relationship,
)
from jyotish_engine.core.states import (
    BaladiAvastha,
    JagradadiAvastha,
    baladi_avastha,
    is_combust,
    is_gandanta,
    jagradadi_avastha,
    planetary_wars,
)
from jyotish_engine.core.zodiac import Sign


def test_dignities() -> None:
    assert dignity(Body.SUN, Sign.ARIES, 10.0) is Dignity.EXALTED
    assert dignity(Body.SUN, Sign.LIBRA, 10.0) is Dignity.DEBILITATED
    assert dignity(Body.SUN, Sign.LEO, 5.0) is Dignity.MOOLATRIKONA
    assert dignity(Body.SUN, Sign.LEO, 25.0) is Dignity.OWN
    assert dignity(Body.MOON, Sign.TAURUS, 2.0) is Dignity.EXALTED
    assert dignity(Body.MERCURY, Sign.VIRGO, 17.0) is Dignity.EXALTED  # whole sign exalted
    assert dignity(Body.JUPITER, Sign.LEO, 3.0) is Dignity.FRIEND
    assert dignity(Body.RAHU, Sign.GEMINI, 3.0) is Dignity.EXALTED


def test_natural_and_compound_relationships() -> None:
    assert natural_relationship(Body.SUN, Body.SATURN) is Relationship.ENEMY
    assert natural_relationship(Body.MOON, Body.SATURN) is Relationship.NEUTRAL
    # Natural friend placed 2nd from it: temporary friend too, so great friend.
    assert compound_relationship(Body.SUN, Body.MOON, 0, 1) is Relationship.GREAT_FRIEND
    # Natural enemy in the 7th: temporary enemy too, so great enemy.
    assert compound_relationship(Body.SUN, Body.SATURN, 0, 6) is Relationship.GREAT_ENEMY
    # Neutral in the 10th (temporary friend): friend.
    assert compound_relationship(Body.SUN, Body.MERCURY, 0, 9) is Relationship.FRIEND


def test_aspects() -> None:
    assert graha_aspected_signs(Body.MARS, Sign.ARIES) == [3, 6, 7]
    assert graha_aspected_signs(Body.SATURN, Sign.ARIES) == [2, 6, 9]
    assert rashi_aspected_signs(Sign.ARIES) == [4, 7, 10]  # Leo, Scorpio, Aquarius
    assert rashi_aspected_signs(Sign.TAURUS) == [3, 6, 9]  # Cancer, Libra, Capricorn
    assert rashi_aspected_signs(Sign.GEMINI) == [5, 8, 11]


def test_combustion() -> None:
    assert is_combust(Body.VENUS, 100.0, 109.0, retrograde=False)
    assert not is_combust(Body.VENUS, 100.0, 109.0, retrograde=True)
    assert not is_combust(Body.RAHU, 100.0, 100.0, retrograde=True)


def test_planetary_war_winner_is_further_north() -> None:
    longitudes = dict.fromkeys(
        (Body.MARS, Body.MERCURY, Body.JUPITER, Body.VENUS, Body.SATURN), 0.0
    )
    longitudes.update(
        {
            Body.MARS: 10.0,
            Body.VENUS: 10.5,
            Body.JUPITER: 200.0,
            Body.SATURN: 300.0,
            Body.MERCURY: 50.0,
        }
    )
    latitudes = dict.fromkeys(longitudes, 0.0)
    latitudes[Body.VENUS] = 1.2
    wars = planetary_wars(longitudes, latitudes)
    assert len(wars) == 1
    assert wars[0].winner is Body.VENUS
    assert wars[0].separation_deg == pytest.approx(0.5)


def test_avasthas_and_gandanta() -> None:
    assert baladi_avastha(15.0) is BaladiAvastha.YUVA  # Aries 15 degrees
    assert baladi_avastha(31.0) is BaladiAvastha.MRITA  # Taurus 1 degree (reversed)
    assert jagradadi_avastha(Dignity.OWN) is JagradadiAvastha.JAGRAT
    assert jagradadi_avastha(Dignity.DEBILITATED) is JagradadiAvastha.SUSHUPTI
    assert is_gandanta(119.0) and is_gandanta(121.0) and is_gandanta(359.5)
    assert not is_gandanta(110.0)
