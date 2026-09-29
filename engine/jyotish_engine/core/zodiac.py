"""The sidereal zodiac: signs (rashis) and their lords."""

from __future__ import annotations

from enum import IntEnum

from jyotish_engine.astro.bodies import Body


class Sign(IntEnum):
    ARIES = 0
    TAURUS = 1
    GEMINI = 2
    CANCER = 3
    LEO = 4
    VIRGO = 5
    LIBRA = 6
    SCORPIO = 7
    SAGITTARIUS = 8
    CAPRICORN = 9
    AQUARIUS = 10
    PISCES = 11

    @property
    def sanskrit(self) -> str:
        return SANSKRIT_NAMES[self]

    @property
    def lord(self) -> Body:
        return SIGN_LORDS[self]

    @property
    def is_odd(self) -> bool:
        """Odd (masculine) signs: Aries, Gemini, Leo, Libra, Sagittarius, Aquarius."""
        return self.value % 2 == 0

    @property
    def modality(self) -> str:
        return ("movable", "fixed", "dual")[self.value % 3]

    @property
    def element(self) -> str:
        return ("fire", "earth", "air", "water")[self.value % 4]


SANSKRIT_NAMES: dict[Sign, str] = {
    Sign.ARIES: "Mesha",
    Sign.TAURUS: "Vrishabha",
    Sign.GEMINI: "Mithuna",
    Sign.CANCER: "Karka",
    Sign.LEO: "Simha",
    Sign.VIRGO: "Kanya",
    Sign.LIBRA: "Tula",
    Sign.SCORPIO: "Vrishchika",
    Sign.SAGITTARIUS: "Dhanu",
    Sign.CAPRICORN: "Makara",
    Sign.AQUARIUS: "Kumbha",
    Sign.PISCES: "Meena",
}

SIGN_LORDS: dict[Sign, Body] = {
    Sign.ARIES: Body.MARS,
    Sign.TAURUS: Body.VENUS,
    Sign.GEMINI: Body.MERCURY,
    Sign.CANCER: Body.MOON,
    Sign.LEO: Body.SUN,
    Sign.VIRGO: Body.MERCURY,
    Sign.LIBRA: Body.VENUS,
    Sign.SCORPIO: Body.MARS,
    Sign.SAGITTARIUS: Body.JUPITER,
    Sign.CAPRICORN: Body.SATURN,
    Sign.AQUARIUS: Body.SATURN,
    Sign.PISCES: Body.JUPITER,
}


def sign_of(longitude: float) -> Sign:
    """Sign containing a sidereal longitude."""
    return Sign(int((longitude % 360.0) // 30.0))


def degrees_in_sign(longitude: float) -> float:
    return (longitude % 360.0) % 30.0
