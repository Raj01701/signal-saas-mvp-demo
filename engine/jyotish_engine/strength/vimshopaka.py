"""Vimshopaka bala: dignity across the divisional charts, out of 20 (BPHS, chapter 16).

In each varga a planet scores by the relationship between it and the lord of the
sign it occupies there (compound relationship from the rasi positions): 20 in its
own or exaltation sign, 18 with a great friend, 15 with a friend, 10 neutral, 7
with an enemy and 5 with a great enemy. Each scheme weights the vargas to a total
of 20:

* shadvarga: D1 6, D2 2, D3 4, D9 5, D12 2, D30 1;
* saptavarga: D1 5, D2 2, D3 3, D7 2.5, D9 4.5, D12 2, D30 1;
* dashavarga: D1 3, D60 5, and 1.5 each for D2, D3, D7, D9, D10, D12, D16, D30;
* shodashavarga: D1 3.5, D2 1, D3 1, D4 0.5, D7 0.5, D9 3, D10 0.5, D12 0.5,
  D16 2, D20 0.5, D24 0.5, D27 0.5, D30 1, D40 0.5, D45 0.5, D60 4.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum

from jyotish_engine.astro.bodies import Body
from jyotish_engine.core.dignity import DIGNITY_RULES, Relationship, compound_relationship
from jyotish_engine.core.varga import varga_sign
from jyotish_engine.core.zodiac import SIGN_LORDS

SEVEN = (Body.SUN, Body.MOON, Body.MARS, Body.MERCURY, Body.JUPITER, Body.VENUS, Body.SATURN)


class VargaScheme(StrEnum):
    SHADVARGA = "shadvarga"
    SAPTAVARGA = "saptavarga"
    DASHAVARGA = "dashavarga"
    SHODASHAVARGA = "shodashavarga"


WEIGHTS: dict[VargaScheme, dict[int, float]] = {
    VargaScheme.SHADVARGA: {1: 6, 2: 2, 3: 4, 9: 5, 12: 2, 30: 1},
    VargaScheme.SAPTAVARGA: {1: 5, 2: 2, 3: 3, 7: 2.5, 9: 4.5, 12: 2, 30: 1},
    VargaScheme.DASHAVARGA: {
        1: 3, 2: 1.5, 3: 1.5, 7: 1.5, 9: 1.5, 10: 1.5, 12: 1.5, 16: 1.5, 30: 1.5, 60: 5,
    },
    VargaScheme.SHODASHAVARGA: {
        1: 3.5, 2: 1, 3: 1, 4: 0.5, 7: 0.5, 9: 3, 10: 0.5, 12: 0.5, 16: 2, 20: 0.5,
        24: 0.5, 27: 0.5, 30: 1, 40: 0.5, 45: 0.5, 60: 4,
    },
}  # fmt: skip

POINTS: dict[Relationship, float] = {
    Relationship.GREAT_FRIEND: 18.0,
    Relationship.FRIEND: 15.0,
    Relationship.NEUTRAL: 10.0,
    Relationship.ENEMY: 7.0,
    Relationship.GREAT_ENEMY: 5.0,
}


def varga_points(
    body: Body, longitude: float, division: int, rasi_signs: Mapping[Body, int]
) -> float:
    sign = varga_sign(longitude, division)
    rule = DIGNITY_RULES[body]
    if sign in rule.own_signs or sign in rule.exaltation_signs:
        return 20.0
    lord = SIGN_LORDS[sign]
    relation = compound_relationship(body, lord, rasi_signs[body], rasi_signs[lord])
    return POINTS[relation]


def vimshopaka(sidereal: Mapping[Body, float], scheme: VargaScheme) -> dict[Body, float]:
    """Vimshopaka bala (0-20) of the seven planets under one scheme."""
    rasi_signs = {b: int(lon // 30.0) % 12 for b, lon in sidereal.items()}
    return {
        body: sum(
            weight * varga_points(body, sidereal[body], division, rasi_signs) / 20.0
            for division, weight in WEIGHTS[scheme].items()
        )
        for body in SEVEN
    }
