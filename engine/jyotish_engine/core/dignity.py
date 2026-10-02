"""Planetary dignity and relationships (BPHS chapters on grahas and their friendships).

* Exaltation, debilitation, moolatrikona and own signs.
* Natural (naisargika) friendship, temporary (tatkalika) friendship from mutual sign
  positions, and the five-fold compound (panchadha) relationship.

Rahu and Ketu follow the Jagannatha Hora convention: Rahu is exalted in Taurus and
Gemini and has its moolatrikona in Virgo; Ketu is exalted in Scorpio and Sagittarius
with moolatrikona in Pisces. Their co-lordship of Aquarius and Scorpio is used for
arudhas and Jaimini dashas (``co_lords``) but not for dignity. Schools differ, so
these conventions are kept in one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum

from jyotish_engine.astro.bodies import Body
from jyotish_engine.core.zodiac import SIGN_LORDS, Sign


class Relationship(IntEnum):
    GREAT_ENEMY = 0
    ENEMY = 1
    NEUTRAL = 2
    FRIEND = 3
    GREAT_FRIEND = 4


class Dignity(StrEnum):
    EXALTED = "exalted"
    MOOLATRIKONA = "moolatrikona"
    OWN = "own"
    GREAT_FRIEND = "great_friend"
    FRIEND = "friend"
    NEUTRAL = "neutral"
    ENEMY = "enemy"
    GREAT_ENEMY = "great_enemy"
    DEBILITATED = "debilitated"


@dataclass(frozen=True, slots=True)
class DignityRule:
    exaltation_signs: tuple[Sign, ...]
    #: Degree of deepest exaltation within the first exaltation sign (planets only).
    exaltation_degree: float
    moolatrikona_sign: Sign
    moolatrikona_from: float
    moolatrikona_to: float
    own_signs: tuple[Sign, ...]


DIGNITY_RULES: dict[Body, DignityRule] = {
    Body.SUN: DignityRule((Sign.ARIES,), 10.0, Sign.LEO, 0.0, 20.0, (Sign.LEO,)),
    Body.MOON: DignityRule((Sign.TAURUS,), 3.0, Sign.TAURUS, 3.0, 30.0, (Sign.CANCER,)),
    Body.MARS: DignityRule(
        (Sign.CAPRICORN,), 28.0, Sign.ARIES, 0.0, 12.0, (Sign.ARIES, Sign.SCORPIO)
    ),
    Body.MERCURY: DignityRule(
        (Sign.VIRGO,), 15.0, Sign.VIRGO, 15.0, 20.0, (Sign.GEMINI, Sign.VIRGO)
    ),
    Body.JUPITER: DignityRule(
        (Sign.CANCER,), 5.0, Sign.SAGITTARIUS, 0.0, 10.0, (Sign.SAGITTARIUS, Sign.PISCES)
    ),
    Body.VENUS: DignityRule((Sign.PISCES,), 27.0, Sign.LIBRA, 0.0, 15.0, (Sign.TAURUS, Sign.LIBRA)),
    Body.SATURN: DignityRule(
        (Sign.LIBRA,), 20.0, Sign.AQUARIUS, 0.0, 20.0, (Sign.CAPRICORN, Sign.AQUARIUS)
    ),
    Body.RAHU: DignityRule((Sign.TAURUS, Sign.GEMINI), 20.0, Sign.VIRGO, 0.0, 30.0, ()),
    Body.KETU: DignityRule((Sign.SCORPIO, Sign.SAGITTARIUS), 20.0, Sign.PISCES, 0.0, 30.0, ()),
}

#: Signs with two lords in Jaimini astrology: the planet and the node.
CO_LORDS: dict[Sign, tuple[Body, Body]] = {
    Sign.SCORPIO: (Body.MARS, Body.KETU),
    Sign.AQUARIUS: (Body.SATURN, Body.RAHU),
}

_F, _N, _E = Relationship.FRIEND, Relationship.NEUTRAL, Relationship.ENEMY
_SEVEN = (Body.SUN, Body.MOON, Body.MARS, Body.MERCURY, Body.JUPITER, Body.VENUS, Body.SATURN)

#: Natural friendships: BPHS for the seven planets, Jagannatha Hora for the nodes.
#: Rows are the planet, columns the other planet.
_NATURAL_TABLE: dict[Body, tuple[Relationship, ...]] = {
    #              Sun Moon Mars Merc Jup  Ven  Sat  Rahu Ketu
    Body.SUN: (_N, _F, _F, _N, _F, _E, _E, _E, _N),
    Body.MOON: (_F, _N, _N, _F, _N, _N, _N, _N, _N),
    Body.MARS: (_F, _F, _N, _E, _F, _N, _N, _N, _N),
    Body.MERCURY: (_F, _E, _N, _N, _N, _F, _N, _N, _E),
    Body.JUPITER: (_F, _F, _F, _E, _N, _E, _N, _E, _N),
    Body.VENUS: (_E, _E, _N, _F, _N, _N, _F, _F, _N),
    Body.SATURN: (_E, _E, _E, _F, _N, _F, _N, _F, _E),
    Body.RAHU: (_E, _E, _E, _N, _N, _F, _F, _N, _N),
    Body.KETU: (_F, _N, _F, _N, _N, _E, _E, _N, _N),
}
_ORDER = (*_SEVEN, Body.RAHU, Body.KETU)


def natural_relationship(planet: Body, other: Body) -> Relationship:
    if planet is other:
        return Relationship.NEUTRAL
    return _NATURAL_TABLE[planet][_ORDER.index(other)]


def temporary_friend(planet_sign: int, other_sign: int) -> bool:
    """Tatkalika friendship: the other planet is 2, 3, 4, 10, 11 or 12 signs from it."""
    distance = (other_sign - planet_sign) % 12 + 1
    return distance in (2, 3, 4, 10, 11, 12)


def compound_relationship(
    planet: Body, other: Body, planet_sign: int, other_sign: int
) -> Relationship:
    """Panchadha (five-fold) relationship combining natural and temporary friendship."""
    natural = natural_relationship(planet, other)
    temp = 1 if temporary_friend(planet_sign, other_sign) else -1
    score = {Relationship.FRIEND: 1, Relationship.NEUTRAL: 0, Relationship.ENEMY: -1}[
        natural
    ] + temp
    return {
        2: Relationship.GREAT_FRIEND,
        1: Relationship.FRIEND,
        0: Relationship.NEUTRAL,
        -1: Relationship.ENEMY,
        -2: Relationship.GREAT_ENEMY,
    }[score]


def is_exalted(body: Body, sign: Sign) -> bool:
    return sign in DIGNITY_RULES[body].exaltation_signs


def is_debilitated(body: Body, sign: Sign) -> bool:
    return (sign + 6) % 12 in DIGNITY_RULES[body].exaltation_signs


def deep_exaltation_longitude(body: Body) -> float:
    rule = DIGNITY_RULES[body]
    return 30.0 * rule.exaltation_signs[0] + rule.exaltation_degree


def in_moolatrikona(body: Body, sign: Sign, degrees_in_sign: float) -> bool:
    rule = DIGNITY_RULES[body]
    return (
        rule.moolatrikona_sign == sign
        and rule.moolatrikona_from <= degrees_in_sign < rule.moolatrikona_to
    )


def dignity(
    body: Body,
    sign: Sign,
    degrees_in_sign: float,
    sign_positions: dict[Body, int] | None = None,
) -> Dignity:
    """Dignity of a graha in a sign.

    Order of precedence: exaltation, debilitation, moolatrikona, own sign, then the
    compound relationship with the sign lord (natural only if ``sign_positions`` is
    not given).
    """
    if is_exalted(body, sign):
        return Dignity.EXALTED
    if is_debilitated(body, sign):
        return Dignity.DEBILITATED
    if in_moolatrikona(body, sign, degrees_in_sign):
        return Dignity.MOOLATRIKONA
    if sign in DIGNITY_RULES[body].own_signs:
        return Dignity.OWN
    lord = SIGN_LORDS[sign]
    if lord is body:
        return Dignity.OWN
    if sign_positions is None:
        relation = natural_relationship(body, lord)
    else:
        relation = compound_relationship(body, lord, sign_positions[body], sign_positions[lord])
    return {
        Relationship.GREAT_FRIEND: Dignity.GREAT_FRIEND,
        Relationship.FRIEND: Dignity.FRIEND,
        Relationship.NEUTRAL: Dignity.NEUTRAL,
        Relationship.ENEMY: Dignity.ENEMY,
        Relationship.GREAT_ENEMY: Dignity.GREAT_ENEMY,
    }[relation]
