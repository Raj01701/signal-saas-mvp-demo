"""Nutation, obliquity and sidereal time (IAU 2006 precession, IAU 2000A nutation)."""

from __future__ import annotations

import math
from typing import Any

from skyfield.nutationlib import iau2000a_radians, mean_obliquity

from jyotish_engine.astro.time import Instant, timescale

RAD2DEG = 180.0 / math.pi


def nutation_deg(instant: Instant) -> tuple[float, float]:
    """Nutation in longitude and in obliquity (degrees), IAU 2000A."""
    d_psi, d_eps = iau2000a_radians(instant.skyfield())
    return float(d_psi) * RAD2DEG, float(d_eps) * RAD2DEG


def mean_obliquity_deg(instant: Instant) -> float:
    """Mean obliquity of the ecliptic of date (IAU 2006, degrees)."""
    t: Any = instant.skyfield()
    return float(mean_obliquity(t.tdb)) / 3600.0


def true_obliquity_deg(instant: Instant) -> float:
    return mean_obliquity_deg(instant) + nutation_deg(instant)[1]


def greenwich_apparent_sidereal_deg(instant: Instant) -> float:
    """Greenwich apparent sidereal time in degrees.

    Sidereal time depends on UT1, so the Skyfield time is built from ``jd_ut`` here.
    """
    t: Any = timescale().ut1_jd(instant.jd_ut)
    return (float(t.gast) * 15.0) % 360.0
