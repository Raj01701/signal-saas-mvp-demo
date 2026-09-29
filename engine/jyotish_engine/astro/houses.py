"""Ascendant, midheaven and house (bhava) cusps.

All quadrant computations are tropical, against the true equinox of date: local
apparent sidereal time plus true obliquity. Callers subtract the ayanamsa to get
sidereal cusps. Whole-sign houses depend only on the sidereal ascendant, so they are
built in the chart layer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from jyotish_engine.astro.frames import greenwich_apparent_sidereal_deg, true_obliquity_deg
from jyotish_engine.astro.time import Instant

_TOLERANCE_DEG = 1e-10
_MAX_ITERATIONS = 100


class HouseSystem(StrEnum):
    WHOLE_SIGN = "whole_sign"
    EQUAL = "equal"
    PORPHYRY = "porphyry"
    SRIPATI = "sripati"
    PLACIDUS = "placidus"


class HouseComputationError(ValueError):
    """Raised when a quadrant system has no solution (e.g. Placidus near the poles)."""


@dataclass(frozen=True, slots=True)
class Angles:
    """Tropical sensitive points of the chart (degrees)."""

    armc: float
    ascendant: float
    mc: float
    obliquity: float
    latitude: float


def _wrap(angle: float) -> float:
    return angle % 360.0


def _mid(a: float, b: float) -> float:
    """Midpoint of the arc running forward (increasing longitude) from ``a`` to ``b``."""
    return _wrap(a + ((b - a) % 360.0) / 2.0)


def mc_from_armc(armc: float, obliquity: float) -> float:
    ramc = math.radians(armc)
    eps = math.radians(obliquity)
    return _wrap(math.degrees(math.atan2(math.sin(ramc), math.cos(ramc) * math.cos(eps))))


def ascendant_from_armc(armc: float, obliquity: float, latitude: float) -> float:
    """Ecliptic longitude rising on the eastern horizon."""
    ramc = math.radians(armc)
    eps = math.radians(obliquity)
    phi = math.radians(latitude)
    y = math.cos(ramc)
    x = -(math.sin(ramc) * math.cos(eps) + math.tan(phi) * math.sin(eps))
    asc = _wrap(math.degrees(math.atan2(y, x)))
    # Beyond the polar circles the formula can return the descendant; the ascendant
    # always lies within 180 degrees ahead of the MC.
    mc = mc_from_armc(armc, obliquity)
    if (asc - mc) % 360.0 > 180.0:
        asc = _wrap(asc + 180.0)
    return asc


def chart_angles(instant: Instant, latitude: float, longitude: float) -> Angles:
    armc = _wrap(greenwich_apparent_sidereal_deg(instant) + longitude)
    eps = true_obliquity_deg(instant)
    return Angles(
        armc=armc,
        ascendant=ascendant_from_armc(armc, eps, latitude),
        mc=mc_from_armc(armc, eps),
        obliquity=eps,
        latitude=latitude,
    )


def equal_cusps(angles: Angles) -> list[float]:
    return [_wrap(angles.ascendant + 30.0 * i) for i in range(12)]


def porphyry_cusps(angles: Angles) -> list[float]:
    asc, mc = angles.ascendant, angles.mc
    ic = _wrap(mc + 180.0)
    east_upper = (asc - mc) % 360.0  # MC to ascendant: houses 10, 11, 12
    east_lower = (ic - asc) % 360.0  # ascendant to IC: houses 1, 2, 3
    cusps = [0.0] * 12
    cusps[0] = asc
    cusps[1] = _wrap(asc + east_lower / 3.0)
    cusps[2] = _wrap(asc + 2.0 * east_lower / 3.0)
    cusps[3] = ic
    cusps[9] = mc
    cusps[10] = _wrap(mc + east_upper / 3.0)
    cusps[11] = _wrap(mc + 2.0 * east_upper / 3.0)
    for i in (4, 5, 6, 7, 8):
        cusps[i] = _wrap(cusps[i - 6] + 180.0)
    return cusps


def sripati_cusps(angles: Angles) -> list[float]:
    """Sripati bhava sandhis: midpoints between consecutive Porphyry cusps.

    The Porphyry cusps themselves are the bhava madhyas (house middles), so the
    ascendant falls in the middle of the first house.
    """
    madhya = porphyry_cusps(angles)
    return [_mid(madhya[i - 1], madhya[i]) for i in range(12)]


def _ecliptic_longitude_for_ra(ra: float, obliquity: float) -> float:
    """Ecliptic longitude (zero latitude) whose right ascension is ``ra``."""
    ra_r = math.radians(ra)
    eps = math.radians(obliquity)
    return _wrap(math.degrees(math.atan2(math.sin(ra_r), math.cos(ra_r) * math.cos(eps))))


def _declination(longitude: float, obliquity: float) -> float:
    return math.degrees(
        math.asin(math.sin(math.radians(obliquity)) * math.sin(math.radians(longitude)))
    )


def _ascensional_difference(declination: float, latitude: float) -> float:
    value = math.tan(math.radians(latitude)) * math.tan(math.radians(declination))
    if abs(value) > 1.0:
        raise HouseComputationError("point is circumpolar; Placidus undefined here")
    return math.degrees(math.asin(value))


def _placidus_cusp(angles: Angles, fraction: float, above_horizon: bool) -> float:
    armc, eps, lat = angles.armc, angles.obliquity, angles.latitude
    ra = armc + 90.0 * fraction if above_horizon else armc + 180.0 - 90.0 * fraction
    for _ in range(_MAX_ITERATIONS):
        lon = _ecliptic_longitude_for_ra(ra, eps)
        ad = _ascensional_difference(_declination(lon, eps), lat)
        if above_horizon:
            new_ra = armc + fraction * (90.0 + ad)
        else:
            new_ra = armc + 180.0 - fraction * (90.0 - ad)
        if abs(((new_ra - ra) + 180.0) % 360.0 - 180.0) < _TOLERANCE_DEG:
            return _ecliptic_longitude_for_ra(new_ra, eps)
        ra = new_ra
    raise HouseComputationError("Placidus iteration did not converge")


def placidus_cusps(angles: Angles) -> list[float]:
    if abs(angles.latitude) >= 90.0 - angles.obliquity:
        raise HouseComputationError("Placidus is undefined inside the polar circles")
    cusps = [0.0] * 12
    cusps[0] = angles.ascendant
    cusps[9] = angles.mc
    cusps[3] = _wrap(angles.mc + 180.0)
    cusps[10] = _placidus_cusp(angles, 1.0 / 3.0, above_horizon=True)
    cusps[11] = _placidus_cusp(angles, 2.0 / 3.0, above_horizon=True)
    cusps[1] = _placidus_cusp(angles, 2.0 / 3.0, above_horizon=False)
    cusps[2] = _placidus_cusp(angles, 1.0 / 3.0, above_horizon=False)
    for i in (4, 5, 6, 7, 8):
        cusps[i] = _wrap(cusps[i - 6] + 180.0)
    return cusps


@dataclass(frozen=True, slots=True)
class HouseCusps:
    system: HouseSystem
    cusps: list[float]
    #: True when the requested system failed and Porphyry was used instead.
    fallback: bool = False


def quadrant_cusps(system: HouseSystem, angles: Angles) -> HouseCusps:
    """Tropical cusps for a quadrant or equal system (not whole-sign)."""
    if system is HouseSystem.EQUAL:
        return HouseCusps(system, equal_cusps(angles))
    if system is HouseSystem.PORPHYRY:
        return HouseCusps(system, porphyry_cusps(angles))
    if system is HouseSystem.SRIPATI:
        return HouseCusps(system, sripati_cusps(angles))
    if system is HouseSystem.PLACIDUS:
        try:
            return HouseCusps(system, placidus_cusps(angles))
        except HouseComputationError:
            return HouseCusps(HouseSystem.PORPHYRY, porphyry_cusps(angles), fallback=True)
    raise ValueError(f"{system} cusps are built from the sidereal ascendant, not here")
