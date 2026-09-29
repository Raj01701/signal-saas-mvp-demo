"""Geocentric positions of the grahas.

Longitudes are tropical, referred to the true ecliptic and equinox of date (they
include nutation). Two conventions are supported:

* ``APPARENT`` (default): corrected for light-time, annual aberration and
  gravitational deflection, i.e. where the planet is seen. Swiss Ephemeris, Drik
  Panchang and most almanacs use this.
* ``TRUE``: the instantaneous geometric position, without those corrections. PyJHora
  (and tools that follow Jagannatha Hora's defaults) use this. The Sun and planets
  then differ by up to about 20 arcseconds (the aberration constant), the Moon by
  about 1 arcsecond.

Speeds come from a symmetric finite difference.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import numpy as np
from skyfield.framelib import ecliptic_frame

from jyotish_engine.astro.bodies import EPHEMERIS_BODIES, Body
from jyotish_engine.astro.ephemeris import get_ephemeris
from jyotish_engine.astro.frames import nutation_deg
from jyotish_engine.astro.time import Instant, timescale

#: Half-width of the finite-difference window used for speeds (days).
SPEED_STEP_DAYS = 1.0 / 24.0


class NodeType(StrEnum):
    MEAN = "mean"
    TRUE = "true"


class PositionType(StrEnum):
    APPARENT = "apparent"
    TRUE = "true"


@dataclass(frozen=True, slots=True)
class EclipticPosition:
    """Tropical ecliptic coordinates of date (degrees, AU, degrees per day)."""

    longitude: float
    latitude: float
    distance_au: float
    speed: float

    @property
    def retrograde(self) -> bool:
        return self.speed < 0.0


def wrap360(angle: float) -> float:
    return angle % 360.0


def angular_distance(a: float, b: float) -> float:
    """Smallest separation between two longitudes (degrees, 0 to 180)."""
    return abs((a - b + 180.0) % 360.0 - 180.0)


def _times_around(instant: Instant) -> Any:
    jd = instant.jd_tt
    return timescale().tt_jd(np.array([jd - SPEED_STEP_DAYS, jd, jd + SPEED_STEP_DAYS]))


def _speed(lons: Any) -> float:
    delta = (float(lons[2]) - float(lons[0]) + 540.0) % 360.0 - 180.0
    return delta / (2.0 * SPEED_STEP_DAYS)


def ephemeris_body_position(
    body: Body, instant: Instant, position_type: PositionType = PositionType.APPARENT
) -> EclipticPosition:
    """Position of a body read straight from the JPL kernel."""
    eph = get_ephemeris()
    eph.check_range(instant.jd_tt)
    times = _times_around(instant)
    if position_type is PositionType.APPARENT:
        position = eph.earth.at(times).observe(eph.target(body)).apparent()
    else:
        position = (eph.target(body) - eph.earth).at(times)
    lat, lon, dist = position.frame_latlon(ecliptic_frame)
    return EclipticPosition(
        longitude=wrap360(float(lon.degrees[1])),
        latitude=float(lat.degrees[1]),
        distance_au=float(dist.au[1]),
        speed=_speed(lon.degrees),
    )


def mean_node_longitude(jd_tt: float) -> float:
    """Mean longitude of the Moon's ascending node, mean equinox of date (degrees).

    Chapront ELP-2000/82 polynomial as given in Meeus, *Astronomical Algorithms*
    (2nd ed.), eq. 47.7.
    """
    t = (jd_tt - 2451545.0) / 36525.0
    omega = 125.0445479 - 1934.1362891 * t + 0.0020754 * t**2 + t**3 / 467441.0 - t**4 / 60616000.0
    return wrap360(omega)


def mean_node_position(instant: Instant) -> EclipticPosition:
    """Mean Rahu, expressed against the true equinox of date like the planets."""
    d_psi, _ = nutation_deg(instant)
    step = SPEED_STEP_DAYS
    before = mean_node_longitude(instant.jd_tt - step)
    after = mean_node_longitude(instant.jd_tt + step)
    speed = ((after - before + 540.0) % 360.0 - 180.0) / (2.0 * step)
    return EclipticPosition(
        longitude=wrap360(mean_node_longitude(instant.jd_tt) + d_psi),
        latitude=0.0,
        distance_au=0.0,
        speed=speed,
    )


def _osculating_node_longitudes(times: Any) -> Any:
    eph = get_ephemeris()
    geometric = (eph.target(Body.MOON) - eph.earth).at(times)
    position, velocity = geometric.frame_xyz_and_velocity(ecliptic_frame)
    h = np.cross(position.au, velocity.au_per_d, axis=0)
    return np.degrees(np.arctan2(h[0], -h[1])) % 360.0


def true_node_position(instant: Instant) -> EclipticPosition:
    """Osculating (true) Rahu: where the Moon's instantaneous orbit crosses the ecliptic."""
    get_ephemeris().check_range(instant.jd_tt)
    lons = _osculating_node_longitudes(_times_around(instant))
    return EclipticPosition(
        longitude=float(lons[1]),
        latitude=0.0,
        distance_au=0.0,
        speed=_speed(lons),
    )


def tropical_positions(
    instant: Instant,
    bodies: Iterable[Body],
    node_type: NodeType = NodeType.TRUE,
    position_type: PositionType = PositionType.APPARENT,
) -> dict[Body, EclipticPosition]:
    """Tropical positions for the requested bodies (Ketu = Rahu + 180 degrees)."""
    wanted = list(bodies)
    result: dict[Body, EclipticPosition] = {}
    for body in wanted:
        if body in EPHEMERIS_BODIES:
            result[body] = ephemeris_body_position(body, instant, position_type)
    if Body.RAHU in wanted or Body.KETU in wanted:
        rahu = (
            true_node_position(instant)
            if node_type is NodeType.TRUE
            else mean_node_position(instant)
        )
        if Body.RAHU in wanted:
            result[Body.RAHU] = rahu
        if Body.KETU in wanted:
            result[Body.KETU] = EclipticPosition(
                longitude=wrap360(rahu.longitude + 180.0),
                latitude=0.0,
                distance_au=0.0,
                speed=rahu.speed,
            )
    return result
