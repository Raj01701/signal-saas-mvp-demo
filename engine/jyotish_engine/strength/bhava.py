"""Bhava bala (house strength) and ishta and kashta phala (BPHS, chapter 27).

Following B.V. Raman, *Graha and Bhava Balas*:

* **Bhavadhipati bala**: the shadbala of the house's lord.
* **Bhava dig bala**: the sign on the bhava madhya (middle of the house) is
  strongest in one angle: human signs (Gemini, Virgo, Libra, Aquarius and the first
  half of Sagittarius) in the 1st; water signs (Cancer, Pisces and the second half
  of Capricorn) in the 4th; Scorpio in the 7th; four-footed signs (Aries, Taurus,
  Leo, the second half of Sagittarius and the first half of Capricorn) in the
  10th. The bhava gets 10 virupas for every house it is closer to that angle than
  the opposite one, up to 60.
* **Bhava drishti bala**: the aspects the bhava madhya receives, benefics adding and
  malefics subtracting, each a quarter of its strength; Jupiter's and Mercury's
  aspects count in full.

Bhava madhyas are the Porphyry cusps (Sripati's bhava middles), so the ascendant
is the middle of the first house.

**Ishta and kashta phala**: the good and bad a planet can give, from its uchcha and
cheshta bala: ishta = sqrt(uchcha x cheshta), kashta = sqrt((60 - uchcha) x
(60 - cheshta)). The Sun's cheshta is taken as its (undoubled) ayana bala and the
Moon's as its (undoubled) paksha bala.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from jyotish_engine.astro.bodies import Body
from jyotish_engine.astro.houses import Angles, porphyry_cusps
from jyotish_engine.core.zodiac import SIGN_LORDS, Sign
from jyotish_engine.strength.shadbala import SEVEN, PlanetShadbala, drishti_value

HUMAN, WATER, INSECT, QUADRUPED = "human", "water", "insect", "quadruped"
STRONG_HOUSE = {HUMAN: 1, WATER: 4, INSECT: 7, QUADRUPED: 10}


def sign_class(longitude: float) -> str:
    sign, degrees = int(longitude // 30.0) % 12, longitude % 30.0
    if sign in (2, 5, 6, 10) or (sign == 8 and degrees < 15.0):
        return HUMAN
    if sign in (3, 11) or (sign == 9 and degrees >= 15.0):
        return WATER
    if sign == 7:
        return INSECT
    return QUADRUPED


def bhava_madhyas(ascendant: float, midheaven: float) -> list[float]:
    """Middles of the twelve houses (sidereal), first house first."""
    angles = Angles(armc=0.0, ascendant=ascendant, mc=midheaven, obliquity=0.0, latitude=0.0)
    return porphyry_cusps(angles)


def bhava_dig_bala(house: int, madhya: float) -> float:
    """``house`` 1-12; the madhya's sign class decides the angle where it is strong."""
    strong = STRONG_HOUSE[sign_class(madhya)]
    distance = abs(house - strong) % 12
    distance = min(distance, 12 - distance)
    return (6 - distance) * 10.0


def bhava_drishti_bala(madhya: float, sidereal: Mapping[Body, float], benefic: set[Body]) -> float:
    total = 0.0
    for body in SEVEN:
        value = drishti_value(body, madhya - sidereal[body])
        sign = 1.0 if body in benefic else -1.0
        total += sign * value if body in (Body.JUPITER, Body.MERCURY) else sign * value / 4.0
    return total


@dataclass(frozen=True, slots=True)
class BhavaBala:
    house: int
    madhya: float
    lord: Body
    adhipati: float
    dig: float
    drishti: float

    @property
    def total(self) -> float:
        return self.adhipati + self.dig + self.drishti

    @property
    def rupas(self) -> float:
        return self.total / 60.0


def bhava_bala(
    ascendant: float,
    midheaven: float,
    sidereal: Mapping[Body, float],
    benefic: set[Body],
    shadbala: Mapping[Body, PlanetShadbala],
) -> list[BhavaBala]:
    out = []
    for index, madhya in enumerate(bhava_madhyas(ascendant, midheaven)):
        lord = SIGN_LORDS[Sign(int(madhya // 30.0) % 12)]
        out.append(
            BhavaBala(
                house=index + 1,
                madhya=madhya,
                lord=lord,
                adhipati=shadbala[lord].total,
                dig=bhava_dig_bala(index + 1, madhya),
                drishti=bhava_drishti_bala(madhya, sidereal, benefic),
            )
        )
    return out


def ishta_kashta(body: Body, strength: PlanetShadbala) -> tuple[float, float]:
    if body is Body.SUN:
        motion = strength.ayana / 2.0
    elif body is Body.MOON:
        motion = strength.paksha / 2.0
    else:
        motion = strength.cheshta
    motion = min(max(motion, 0.0), 60.0)
    uchcha = min(max(strength.uchcha, 0.0), 60.0)
    return math.sqrt(uchcha * motion), math.sqrt((60.0 - uchcha) * (60.0 - motion))
