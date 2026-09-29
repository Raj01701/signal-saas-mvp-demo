"""Celestial bodies (grahas) used by the engine."""

from enum import StrEnum


class Body(StrEnum):
    """Bodies in the traditional weekday order, followed by the modern outer planets."""

    SUN = "sun"
    MOON = "moon"
    MARS = "mars"
    MERCURY = "mercury"
    JUPITER = "jupiter"
    VENUS = "venus"
    SATURN = "saturn"
    RAHU = "rahu"
    KETU = "ketu"
    URANUS = "uranus"
    NEPTUNE = "neptune"
    PLUTO = "pluto"


#: The nine grahas of classical Jyotish.
GRAHAS: tuple[Body, ...] = (
    Body.SUN,
    Body.MOON,
    Body.MARS,
    Body.MERCURY,
    Body.JUPITER,
    Body.VENUS,
    Body.SATURN,
    Body.RAHU,
    Body.KETU,
)

#: Non-classical outer planets, available as an option.
OUTER_PLANETS: tuple[Body, ...] = (Body.URANUS, Body.NEPTUNE, Body.PLUTO)

#: Bodies whose positions come straight from the JPL ephemeris.
EPHEMERIS_BODIES: tuple[Body, ...] = (
    Body.SUN,
    Body.MOON,
    Body.MARS,
    Body.MERCURY,
    Body.JUPITER,
    Body.VENUS,
    Body.SATURN,
    Body.URANUS,
    Body.NEPTUNE,
    Body.PLUTO,
)
