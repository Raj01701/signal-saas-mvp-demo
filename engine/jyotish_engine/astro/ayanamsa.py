"""Ayanamsa: the offset between the tropical and sidereal zodiacs.

Two families are supported.

**Epoch-defined** systems (Lahiri, Raman, KP and others) fix the ayanamsa at one
epoch and carry it forward with precession. The *mean* ayanamsa at J1900.0 (TT) is
stored for each system and carried to the date with IAU 2006 precession, measured
as the longitude of the epoch's mean equinox in the mean ecliptic of date.

**Star-anchored** ("true") systems pin a star to a fixed sidereal longitude: Spica
at 180 degrees for True Chitra, zeta Piscium at 359 degrees 50 minutes for True
Revati, delta Cancri at 106 degrees for True Pushya.

Sidereal longitude = tropical apparent longitude (true equinox of date) minus the
*true* ayanamsa (mean ayanamsa plus nutation in longitude). Nutation therefore
cancels, and sidereal positions do not wobble with it.

The epoch constants were calibrated numerically against Swiss Ephemeris 2.10.03's
modes of the same names, so that charts match the tools most astrologers use. Only
output values were compared; no Swiss Ephemeris code is used. See
``engine/tests/test_astro_golden.py`` for the tolerances verified. Lahiri follows the
Indian Calendar Reform Committee definition (23 deg 15 min 00.658 sec on
1956-03-21) to within 0.14 arcseconds.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from jyotish_engine.astro.frames import nutation_deg
from jyotish_engine.astro.precession import PrecessionModel, equinox_longitude_shift
from jyotish_engine.astro.stars import AnchorStar, star_longitude
from jyotish_engine.astro.time import Instant

J1900_TT = 2415020.0


class Ayanamsa(StrEnum):
    LAHIRI = "lahiri"
    LAHIRI_ICRC = "lahiri_icrc"
    LAHIRI_1940 = "lahiri_1940"
    LAHIRI_VP285 = "lahiri_vp285"
    TRUE_CHITRA = "true_chitra"
    TRUE_REVATI = "true_revati"
    TRUE_PUSHYA = "true_pushya"
    RAMAN = "raman"
    KRISHNAMURTI = "krishnamurti"
    KRISHNAMURTI_VP291 = "krishnamurti_vp291"
    YUKTESHWAR = "yukteshwar"
    JN_BHASIN = "jn_bhasin"
    FAGAN_BRADLEY = "fagan_bradley"
    USER = "user"


@dataclass(frozen=True, slots=True)
class EpochDefinition:
    label: str
    mean_value_j1900: float  # degrees, mean ayanamsa at J1900.0 TT


@dataclass(frozen=True, slots=True)
class StarDefinition:
    label: str
    star: AnchorStar
    sidereal_longitude: float


EPOCH_SYSTEMS: dict[Ayanamsa, EpochDefinition] = {
    Ayanamsa.LAHIRI: EpochDefinition("Lahiri (Chitrapaksha)", 22.460511632),
    Ayanamsa.LAHIRI_ICRC: EpochDefinition("Lahiri (ICRC 1956 original)", 22.460208295),
    Ayanamsa.LAHIRI_1940: EpochDefinition("Lahiri (1940)", 22.445742497),
    Ayanamsa.LAHIRI_VP285: EpochDefinition("Lahiri (vernal point 285 CE)", 22.466901970),
    Ayanamsa.RAMAN: EpochDefinition("B.V. Raman", 21.014210277),
    Ayanamsa.KRISHNAMURTI: EpochDefinition("Krishnamurti (KP)", 22.363659277),
    Ayanamsa.KRISHNAMURTI_VP291: EpochDefinition("Krishnamurti (KP, VP 291 CE)", 22.383785709),
    Ayanamsa.YUKTESHWAR: EpochDefinition("Sri Yukteshwar", 21.082222265),
    Ayanamsa.JN_BHASIN: EpochDefinition("J.N. Bhasin", 21.365556265),
    Ayanamsa.FAGAN_BRADLEY: EpochDefinition("Fagan-Bradley (Western sidereal)", 23.343719268),
}

STAR_SYSTEMS: dict[Ayanamsa, StarDefinition] = {
    Ayanamsa.TRUE_CHITRA: StarDefinition("True Chitra (Spica at 180°)", AnchorStar.SPICA, 180.0),
    Ayanamsa.TRUE_REVATI: StarDefinition(
        "True Revati (zeta Psc at 359°50′)", AnchorStar.REVATI, 359.0 + 50.0 / 60.0
    ),
    Ayanamsa.TRUE_PUSHYA: StarDefinition(
        "True Pushya (delta Cnc at 106°)", AnchorStar.PUSHYA, 106.0
    ),
}


def label(system: Ayanamsa) -> str:
    if system in EPOCH_SYSTEMS:
        return EPOCH_SYSTEMS[system].label
    if system in STAR_SYSTEMS:
        return STAR_SYSTEMS[system].label
    return "User-defined"


def mean_ayanamsa(
    instant: Instant, system: Ayanamsa, user_value_j2000: float | None = None
) -> float:
    """Mean ayanamsa (without nutation), degrees.

    ``user_value_j2000`` is the mean ayanamsa at J2000.0 for ``Ayanamsa.USER``.
    """
    if system is Ayanamsa.USER:
        if user_value_j2000 is None:
            raise ValueError("a user-defined ayanamsa needs its J2000.0 value")
        return user_value_j2000 + equinox_longitude_shift(
            2451545.0, instant.jd_tt, PrecessionModel.IAU2006
        )
    if system in STAR_SYSTEMS:
        return true_ayanamsa(instant, system) - nutation_deg(instant)[0]
    definition = EPOCH_SYSTEMS[system]
    return definition.mean_value_j1900 + equinox_longitude_shift(
        J1900_TT, instant.jd_tt, PrecessionModel.IAU2006
    )


def true_ayanamsa(
    instant: Instant, system: Ayanamsa, user_value_j2000: float | None = None
) -> float:
    """Ayanamsa including nutation in longitude: subtract it from apparent longitudes."""
    if system in STAR_SYSTEMS:
        definition = STAR_SYSTEMS[system]
        star = star_longitude(definition.star, instant, apparent=True)
        return (star - definition.sidereal_longitude) % 360.0
    return mean_ayanamsa(instant, system, user_value_j2000) + nutation_deg(instant)[0]


def to_sidereal(tropical_longitude: float, true_ayanamsa_value: float) -> float:
    return (tropical_longitude - true_ayanamsa_value) % 360.0
