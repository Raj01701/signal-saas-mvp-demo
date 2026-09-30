"""Tajika strength (pancha-vargiya bala) and the lord of the year.

Pending review by a qualified Jyotishi: sources differ on details, and the rules
here are the common reading, stated so they can be checked.

**Pancha-vargiya bala** (Tajika Neelakanthi): five strengths, each at full value in
the planet's own or exaltation sign, three quarters in a friend's, half in a
neutral's and a quarter in an enemy's (natural relationships):

* kshetra (the sign): 30;
* uchcha: 20 at the deep exaltation point, falling evenly to 0 at debilitation;
* hadda (terms): 15, by the Egyptian terms (Ptolemy, *Tetrabiblos* I.20) that
  Tajika inherited; some Indian editions swap the lords of two terms in Gemini and
  Sagittarius;
* drekkana (D3): 10;
* navamsa (D9): 5.

The sum, divided by 4, is out of 20.

**Lord of the year**: of the office-bearers, those whose sign has a Tajika aspect
on the annual lagna are eligible, and the one with the highest pancha-vargiya
bala is the lord. When none aspects the lagna, the strongest office-bearer is
taken. Ties go to the earlier office-bearer in the list.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from jyotish_engine.annual.tajika import SEVEN, tajika_aspect
from jyotish_engine.astro.bodies import Body
from jyotish_engine.core.dignity import (
    DIGNITY_RULES,
    Relationship,
    deep_exaltation_longitude,
    natural_relationship,
)
from jyotish_engine.core.varga import varga_sign
from jyotish_engine.core.zodiac import SIGN_LORDS, Sign

_JU, _VE, _ME, _MA, _SA = Body.JUPITER, Body.VENUS, Body.MERCURY, Body.MARS, Body.SATURN

#: Egyptian terms: (lord, end degree) for each sign, Aries to Pisces.
HADDA: tuple[tuple[tuple[Body, float], ...], ...] = (
    ((_JU, 6), (_VE, 12), (_ME, 20), (_MA, 25), (_SA, 30)),
    ((_VE, 8), (_ME, 14), (_JU, 22), (_SA, 27), (_MA, 30)),
    ((_ME, 6), (_JU, 12), (_VE, 17), (_MA, 24), (_SA, 30)),
    ((_MA, 7), (_VE, 13), (_ME, 19), (_JU, 26), (_SA, 30)),
    ((_JU, 6), (_VE, 11), (_SA, 18), (_ME, 24), (_MA, 30)),
    ((_ME, 7), (_VE, 17), (_JU, 21), (_MA, 28), (_SA, 30)),
    ((_SA, 6), (_ME, 14), (_JU, 21), (_VE, 28), (_MA, 30)),
    ((_MA, 7), (_VE, 11), (_ME, 19), (_JU, 24), (_SA, 30)),
    ((_JU, 12), (_VE, 17), (_ME, 21), (_SA, 26), (_MA, 30)),
    ((_ME, 7), (_JU, 14), (_VE, 22), (_SA, 26), (_MA, 30)),
    ((_ME, 7), (_VE, 13), (_JU, 20), (_MA, 25), (_SA, 30)),
    ((_VE, 12), (_JU, 16), (_ME, 19), (_MA, 28), (_SA, 30)),
)

_FRACTION: dict[Relationship, float] = {
    Relationship.FRIEND: 0.75,
    Relationship.NEUTRAL: 0.5,
    Relationship.ENEMY: 0.25,
}


def hadda_lord(longitude: float) -> Body:
    sign, degrees = int(longitude // 30.0) % 12, longitude % 30.0
    return next(lord for lord, end in HADDA[sign] if degrees < end)


def _dignity_fraction(body: Body, sign: Sign, lord: Body) -> float:
    rule = DIGNITY_RULES[body]
    if body is lord or sign in rule.own_signs or sign in rule.exaltation_signs:
        return 1.0
    return _FRACTION[natural_relationship(body, lord)]


@dataclass(frozen=True, slots=True)
class PanchaVargiya:
    kshetra: float
    uchcha: float
    hadda: float
    drekkana: float
    navamsa: float

    @property
    def total(self) -> float:
        return (self.kshetra + self.uchcha + self.hadda + self.drekkana + self.navamsa) / 4.0


def pancha_vargiya_bala(body: Body, longitude: float) -> PanchaVargiya:
    rasi = Sign(int(longitude // 30.0) % 12)
    d3, d9 = varga_sign(longitude, 3), varga_sign(longitude, 9)
    distance = abs((longitude - deep_exaltation_longitude(body) + 180.0) % 360.0 - 180.0)
    hadda = hadda_lord(longitude)
    return PanchaVargiya(
        kshetra=30.0 * _dignity_fraction(body, rasi, SIGN_LORDS[rasi]),
        uchcha=20.0 * (180.0 - distance) / 180.0,
        hadda=15.0 * _dignity_fraction(body, rasi, hadda),
        drekkana=10.0 * _dignity_fraction(body, d3, SIGN_LORDS[d3]),
        navamsa=5.0 * _dignity_fraction(body, d9, SIGN_LORDS[d9]),
    )


def year_lord(
    candidates: Sequence[Body], varsha_lagna_sign: int, sidereal: Mapping[Body, float]
) -> tuple[Body, bool]:
    """The lord of the year, and whether it aspects the annual lagna."""
    strength = {b: pancha_vargiya_bala(b, sidereal[b]).total for b in SEVEN}
    aspecting = [
        c for c in candidates
        if tajika_aspect(int(sidereal[c] // 30.0) % 12, varsha_lagna_sign) is not None
    ]  # fmt: skip
    pool = aspecting or list(candidates)
    best = max(pool, key=lambda c: (strength[c], -pool.index(c)))
    return best, bool(aspecting)
