"""Sunrise and sunset under the definitions used by Indian almanacs.

* ``HINDU``: the centre of the Sun's disc on the true horizon, with no refraction and
  a geocentric Sun. This is the traditional Jyotish definition, used for vara, hora
  and Gulika.
* ``UPPER_LIMB_REFRACTION``: the upper edge of the disc on the apparent horizon, the
  civil definition and Drik Panchang's default.
* ``DISC_CENTRE_REFRACTION``: the centre of the disc on the apparent horizon.

The last two model standard atmospheric refraction (1013.25 hPa, 15 C) at the
horizon, and use the Sun's apparent semi-diameter from its distance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import numpy as np
from skyfield.api import wgs84

from jyotish_engine.astro.bodies import Body
from jyotish_engine.astro.ephemeris import get_ephemeris
from jyotish_engine.astro.frames import greenwich_apparent_sidereal_deg
from jyotish_engine.astro.time import Instant, timescale

#: Horizontal refraction at 1013.25 hPa and 15 C (arcminutes). The value reproduces
#: the rise and set times of Swiss Ephemeris, which almanacs such as Drik Panchang use.
HORIZON_REFRACTION_ARCMIN = 33.593
#: Solar semi-diameter at 1 AU (arcseconds), IAU value.
SOLAR_SEMIDIAMETER_1AU_ARCSEC = 959.63

_SCAN_STEP_DAYS = 1.0 / 48.0  # 30 minutes
_BISECTION_TOLERANCE_DAYS = 1e-8  # about 1 ms


class SunriseDefinition(StrEnum):
    HINDU = "hindu"
    UPPER_LIMB_REFRACTION = "upper_limb_refraction"
    DISC_CENTRE_REFRACTION = "disc_centre_refraction"


@dataclass(frozen=True, slots=True)
class RiseSet:
    rise: Instant | None
    set: Instant | None


def _geocentric_altitudes(jd_ut: Any, latitude: float, longitude: float) -> Any:
    """Altitude of the Sun's geocentric apparent centre (no refraction), degrees."""
    ts = timescale()
    eph = get_ephemeris()
    times = ts.ut1_jd(jd_ut)
    apparent = eph.earth.at(times).observe(eph.target(Body.SUN)).apparent()
    ra, dec, _ = apparent.radec(epoch=times)
    gast = np.asarray(times.gast) * 15.0
    hour_angle = np.radians(gast + longitude - np.asarray(ra.hours) * 15.0)
    phi = math.radians(latitude)
    delta = np.radians(np.asarray(dec.degrees))
    sin_alt = math.sin(phi) * np.sin(delta) + math.cos(phi) * np.cos(delta) * np.cos(hour_angle)
    return np.degrees(np.arcsin(np.clip(sin_alt, -1.0, 1.0)))


def _topocentric_altitudes(
    jd_ut: Any, latitude: float, longitude: float, elevation_m: float
) -> tuple[Any, Any]:
    """Altitude of the Sun's topocentric apparent centre (no refraction), degrees."""
    ts = timescale()
    eph = get_ephemeris()
    times = ts.ut1_jd(jd_ut)
    observer = eph.earth + wgs84.latlon(latitude, longitude, elevation_m=elevation_m)
    alt, _, distance = observer.at(times).observe(eph.target(Body.SUN)).apparent().altaz()
    return np.asarray(alt.degrees), np.asarray(distance.au)


def _event_function(
    definition: SunriseDefinition, latitude: float, longitude: float, elevation_m: float
) -> Any:
    """Return f(jd_ut) that is zero at the event and positive when the Sun is up."""
    if definition is SunriseDefinition.HINDU:

        def hindu(jd_ut: Any) -> Any:
            return _geocentric_altitudes(jd_ut, latitude, longitude)

        return hindu

    refraction = HORIZON_REFRACTION_ARCMIN / 60.0

    def refracted(jd_ut: Any) -> Any:
        altitude, distance_au = _topocentric_altitudes(jd_ut, latitude, longitude, elevation_m)
        horizon = -refraction
        if definition is SunriseDefinition.UPPER_LIMB_REFRACTION:
            horizon -= SOLAR_SEMIDIAMETER_1AU_ARCSEC / distance_au / 3600.0
        return altitude - horizon

    return refracted


def _refine(f: Any, lo: float, hi: float) -> float:
    """Locate the sign change of ``f`` in [lo, hi] using a few vectorised zooms.

    Each pass samples 33 points, so three passes shrink a 30-minute bracket to about
    0.05 s; linear interpolation over that tiny bracket is then exact to the
    millisecond. This needs 4 calls into the ephemeris instead of about 25 for
    bisection.
    """
    samples = 33
    for _ in range(3):
        grid = np.linspace(lo, hi, samples)
        values = f(grid)
        positive = values > 0.0
        change = np.nonzero(positive[:-1] != positive[1:])[0]
        if change.size == 0:
            break
        i = int(change[0])
        lo, hi = float(grid[i]), float(grid[i + 1])
        if hi - lo < _BISECTION_TOLERANCE_DAYS:
            break
    f_lo, f_hi = f(np.array([lo, hi]))
    if f_hi == f_lo:
        return 0.5 * (lo + hi)
    return lo + (hi - lo) * float(-f_lo / (f_hi - f_lo))


def _scan(f: Any, start_jd: float, max_days: float, rising: bool) -> float | None:
    steps = math.ceil(max_days / _SCAN_STEP_DAYS) + 1
    grid = start_jd + _SCAN_STEP_DAYS * np.arange(steps)
    values = f(grid)
    for i in range(steps - 1):
        a, b = values[i], values[i + 1]
        if (rising and a <= 0.0 < b) or (not rising and a > 0.0 >= b):
            return _refine(f, float(grid[i]), float(grid[i + 1]))
    return None


def next_sunrise(
    start: Instant,
    latitude: float,
    longitude: float,
    elevation_m: float = 0.0,
    definition: SunriseDefinition = SunriseDefinition.HINDU,
    max_days: float = 2.0,
) -> Instant | None:
    """First sunrise after ``start``, or ``None`` if the Sun stays down (polar night)."""
    f = _event_function(definition, latitude, longitude, elevation_m)
    jd = _scan(f, start.jd_ut, max_days, rising=True)
    return Instant.from_jd_ut(jd) if jd is not None else None


def next_sunset(
    start: Instant,
    latitude: float,
    longitude: float,
    elevation_m: float = 0.0,
    definition: SunriseDefinition = SunriseDefinition.HINDU,
    max_days: float = 2.0,
) -> Instant | None:
    """First sunset after ``start``, or ``None`` if the Sun stays up (polar day)."""
    f = _event_function(definition, latitude, longitude, elevation_m)
    jd = _scan(f, start.jd_ut, max_days, rising=False)
    return Instant.from_jd_ut(jd) if jd is not None else None


def next_rise_and_set(
    start: Instant,
    latitude: float,
    longitude: float,
    elevation_m: float = 0.0,
    definition: SunriseDefinition = SunriseDefinition.HINDU,
    max_days: float = 2.0,
) -> RiseSet:
    """First sunrise and first sunset after ``start`` (each independently)."""
    return RiseSet(
        rise=next_sunrise(start, latitude, longitude, elevation_m, definition, max_days),
        set=next_sunset(start, latitude, longitude, elevation_m, definition, max_days),
    )


def local_sidereal_degrees(instant: Instant, longitude: float) -> float:
    """Local apparent sidereal time (degrees)."""
    return (greenwich_apparent_sidereal_deg(instant) + longitude) % 360.0
