"""Tajika annual-chart basics: Muntha, the five office-bearers and Tajika aspects.

* **Muntha** starts in the natal lagna sign and moves one sign per completed year.
* **Office-bearers** (panchadhikaris; Tajika Neelakanthi): the lords of the natal
  lagna, the annual (varsha) lagna and the Muntha sign; the tri-rashi lord of the
  annual lagna, taken for day or night; and the lord of the Sun's sign by day or
  of the Moon's sign by night. Tajika uses the seven planets as lords.
* **Tajika aspects** are counted between signs: the 1st (conjunction) and 7th, 4th
  and 10th houses are inimical; the 3rd and 11th, 5th and 9th are friendly; the
  2nd, 6th, 8th and 12th give no aspect. Two aspecting planets are within orbs when
  the degrees they have covered in their signs differ by less than the mean of
  their deeptamsas. The faster planet, still behind the slower, makes an
  **ithasala** (applying); once it has passed it, an **isarapha** (separating).

Choosing the lord of the year also needs the Tajika strengths (pancha-vargiya
bala), which arrive with the other strengths in M4.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from jyotish_engine.astro.bodies import Body
from jyotish_engine.core.zodiac import SIGN_LORDS, Sign

SEVEN = (Body.SUN, Body.MOON, Body.MARS, Body.MERCURY, Body.JUPITER, Body.VENUS, Body.SATURN)

#: Orbs (deeptamsa) in degrees.
DEEPTAMSA: dict[Body, float] = {
    Body.SUN: 15.0,
    Body.MOON: 12.0,
    Body.MARS: 8.0,
    Body.MERCURY: 7.0,
    Body.JUPITER: 9.0,
    Body.VENUS: 7.0,
    Body.SATURN: 9.0,
}

#: Fastest to slowest by mean daily motion.
SPEED_ORDER = (Body.MOON, Body.MERCURY, Body.VENUS, Body.SUN, Body.MARS, Body.JUPITER, Body.SATURN)

#: Tri-rashi lords of each sign (Aries to Pisces), by day and by night.
TRI_RASHI_DAY = (
    Body.SUN, Body.VENUS, Body.SATURN, Body.VENUS, Body.JUPITER, Body.MOON,
    Body.MERCURY, Body.MARS, Body.SATURN, Body.MARS, Body.JUPITER, Body.MOON,
)  # fmt: skip
TRI_RASHI_NIGHT = (
    Body.JUPITER, Body.MOON, Body.MERCURY, Body.MARS, Body.SUN, Body.VENUS,
    Body.SATURN, Body.VENUS, Body.SATURN, Body.MARS, Body.JUPITER, Body.MOON,
)  # fmt: skip


class TajikaAspect(StrEnum):
    CONJUNCTION = "conjunction"  # 1st
    SEXTILE = "sextile"  # 3rd / 11th
    SQUARE = "square"  # 4th / 10th
    TRINE = "trine"  # 5th / 9th
    OPPOSITION = "opposition"  # 7th


ASPECT_BY_HOUSE: dict[int, TajikaAspect] = {
    1: TajikaAspect.CONJUNCTION,
    3: TajikaAspect.SEXTILE,
    11: TajikaAspect.SEXTILE,
    4: TajikaAspect.SQUARE,
    10: TajikaAspect.SQUARE,
    5: TajikaAspect.TRINE,
    9: TajikaAspect.TRINE,
    7: TajikaAspect.OPPOSITION,
}
FRIENDLY = frozenset({TajikaAspect.SEXTILE, TajikaAspect.TRINE})


class TajikaYoga(StrEnum):
    ITHASALA = "ithasala"  # applying, within orbs
    ISARAPHA = "isarapha"  # separating, within orbs


@dataclass(frozen=True, slots=True)
class TajikaRelation:
    faster: Body
    slower: Body
    aspect: TajikaAspect
    friendly: bool
    #: Degrees the slower planet is ahead of the faster within their signs.
    gap: float
    orb: float
    yoga: TajikaYoga | None


def _sign(longitude: float) -> int:
    return int(longitude // 30.0) % 12


def muntha_sign(natal_lagna_sign: int, years_completed: int) -> int:
    return (natal_lagna_sign + years_completed) % 12


def tajika_aspect(sign_a: int, sign_b: int) -> TajikaAspect | None:
    return ASPECT_BY_HOUSE.get((sign_b - sign_a) % 12 + 1)


def tajika_relation(a: Body, lon_a: float, b: Body, lon_b: float) -> TajikaRelation | None:
    """How two of the seven planets relate in Tajika, or None without an aspect."""
    aspect = tajika_aspect(_sign(lon_a), _sign(lon_b))
    if aspect is None:
        return None
    if SPEED_ORDER.index(a) > SPEED_ORDER.index(b):
        a, lon_a, b, lon_b = b, lon_b, a, lon_a
    orb = (DEEPTAMSA[a] + DEEPTAMSA[b]) / 2.0
    gap = lon_b % 30.0 - lon_a % 30.0
    yoga = None
    if 0.0 <= gap <= orb:
        yoga = TajikaYoga.ITHASALA
    elif -orb <= gap < 0.0:
        yoga = TajikaYoga.ISARAPHA
    return TajikaRelation(a, b, aspect, aspect in FRIENDLY, gap, orb, yoga)


def tajika_relations(sidereal: Mapping[Body, float]) -> list[TajikaRelation]:
    """Relations between every pair of the seven planets that aspect each other."""
    out = []
    for i, a in enumerate(SEVEN):
        for b in SEVEN[i + 1 :]:
            relation = tajika_relation(a, sidereal[a], b, sidereal[b])
            if relation is not None:
                out.append(relation)
    return out


@dataclass(frozen=True, slots=True)
class OfficeBearers:
    natal_lagna_lord: Body
    varsha_lagna_lord: Body
    muntha_lord: Body
    tri_rashi_lord: Body
    dina_ratri_lord: Body

    def candidates(self) -> list[Body]:
        """The distinct office-bearers, in the order listed."""
        seen: list[Body] = []
        for body in (
            self.natal_lagna_lord,
            self.varsha_lagna_lord,
            self.muntha_lord,
            self.tri_rashi_lord,
            self.dina_ratri_lord,
        ):
            if body not in seen:
                seen.append(body)
        return seen


def office_bearers(
    natal_lagna_sign: int,
    varsha_lagna_sign: int,
    years_completed: int,
    sidereal: Mapping[Body, float],
    by_day: bool,
) -> OfficeBearers:
    """The five office-bearers of an annual chart (``sidereal``: annual positions)."""
    luminary = Body.SUN if by_day else Body.MOON
    tri_rashi = TRI_RASHI_DAY if by_day else TRI_RASHI_NIGHT
    return OfficeBearers(
        natal_lagna_lord=SIGN_LORDS[Sign(natal_lagna_sign)],
        varsha_lagna_lord=SIGN_LORDS[Sign(varsha_lagna_sign)],
        muntha_lord=SIGN_LORDS[Sign(muntha_sign(natal_lagna_sign, years_completed))],
        tri_rashi_lord=tri_rashi[varsha_lagna_sign],
        dina_ratri_lord=SIGN_LORDS[Sign(_sign(sidereal[luminary]))],
    )
