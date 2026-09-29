"""Special lagnas (ascendants) of Parashari and Jaimini astrology.

Time-based lagnas start from the Sun's longitude at sunrise and advance at a fixed
rate with the time elapsed since sunrise:

* Bhava Lagna: one sign every 2 hours (5 ghatis).
* Hora Lagna: one sign every hour (2.5 ghatis).
* Ghati Lagna: one sign every ghati (24 minutes).

Pranapada advances four signs per ghati from the Sun's longitude at birth, then
shifts by the modality of the Sun's sign (movable 0, fixed 240, dual 120 degrees),
following P.V.R. Narasimha Rao's reading of BPHS.

Indu Lagna (wealth) combines the kalas of the 9th lords from the Lagna and the Moon
(B.V. Raman's method). Sree Lagna adds twelve signs times the fraction of the
Moon's nakshatra already traversed to the Lagna.
"""

from __future__ import annotations

from jyotish_engine.astro.bodies import Body
from jyotish_engine.core.nakshatra import nakshatra_of
from jyotish_engine.core.zodiac import SIGN_LORDS, Sign

BHAVA_LAGNA_DEG_PER_MIN = 30.0 / 120.0
HORA_LAGNA_DEG_PER_MIN = 30.0 / 60.0
GHATI_LAGNA_DEG_PER_MIN = 30.0 / 24.0

#: Kalas used by the Indu Lagna, Sun to Saturn.
INDU_KALAS: dict[Body, int] = {
    Body.SUN: 30,
    Body.MOON: 16,
    Body.MARS: 6,
    Body.MERCURY: 8,
    Body.JUPITER: 10,
    Body.VENUS: 12,
    Body.SATURN: 1,
}


def time_lagna(
    sun_at_sunrise: float, minutes_since_sunrise: float, degrees_per_minute: float
) -> float:
    return (sun_at_sunrise + minutes_since_sunrise * degrees_per_minute) % 360.0


def bhava_lagna(sun_at_sunrise: float, minutes_since_sunrise: float) -> float:
    return time_lagna(sun_at_sunrise, minutes_since_sunrise, BHAVA_LAGNA_DEG_PER_MIN)


def hora_lagna(sun_at_sunrise: float, minutes_since_sunrise: float) -> float:
    return time_lagna(sun_at_sunrise, minutes_since_sunrise, HORA_LAGNA_DEG_PER_MIN)


def ghati_lagna(sun_at_sunrise: float, minutes_since_sunrise: float) -> float:
    return time_lagna(sun_at_sunrise, minutes_since_sunrise, GHATI_LAGNA_DEG_PER_MIN)


def pranapada(sun_at_birth: float, minutes_since_sunrise: float) -> float:
    ghatis = minutes_since_sunrise / 24.0
    offset = (0.0, 240.0, 120.0)[int(sun_at_birth // 30.0) % 3]
    return (sun_at_birth + ghatis * 120.0 + offset) % 360.0


def indu_lagna(ascendant: float, moon: float) -> float:
    """Indu Lagna longitude (its sign, with the Moon's degrees within the sign)."""
    asc_sign = int(ascendant // 30.0) % 12
    moon_sign = int(moon // 30.0) % 12
    ninth_from_lagna = SIGN_LORDS[Sign((asc_sign + 8) % 12)]
    ninth_from_moon = SIGN_LORDS[Sign((moon_sign + 8) % 12)]
    count = (INDU_KALAS[ninth_from_lagna] + INDU_KALAS[ninth_from_moon]) % 12 or 12
    sign = (moon_sign + count - 1) % 12
    return 30.0 * sign + moon % 30.0


def sree_lagna(ascendant: float, moon: float) -> float:
    fraction = nakshatra_of(moon).fraction_elapsed
    return (ascendant + fraction * 360.0) % 360.0
