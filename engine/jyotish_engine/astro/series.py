"""Positions over many instants at once, for event search and time series.

These are vectorised versions of the functions in ``positions`` and ``ayanamsa``:
they take an array of Julian days (TT) and compute every instant in one pass,
which makes scanning years of motion fast.

Sidereal longitudes are computed in the *mean* ecliptic and equinox of date. The
true-equinox longitude of any body is its mean-equinox longitude plus the nutation
in longitude, exactly, and the true ayanamsa carries the same nutation term, so it
cancels: the result equals the scalar ``tropical - true ayanamsa`` (to about
1e-9 arcsecond, see ``tests/test_series.py``) while skipping the costly IAU 2000A
nutation series.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray
from skyfield.framelib import ICRS_to_J2000, ecliptic_frame
from skyfield.functions import mxmxm, rot_x

from jyotish_engine.astro.ayanamsa import EPOCH_SYSTEMS, J1900_TT, STAR_SYSTEMS, Ayanamsa
from jyotish_engine.astro.bodies import EPHEMERIS_BODIES, Body
from jyotish_engine.astro.ephemeris import get_ephemeris
from jyotish_engine.astro.positions import (
    NodeType,
    PositionType,
    mean_node_polynomial,
    osculating_node_longitudes,
)
from jyotish_engine.astro.precession import equinox_longitude_shifts
from jyotish_engine.astro.stars import skyfield_star
from jyotish_engine.astro.time import J2000_JD, timescale

FloatArray = NDArray[np.float64]


class _MeanEclipticOfDate:
    """Mean ecliptic and equinox of date (IAU 2006 precession, no nutation)."""

    @staticmethod
    def rotation_at(t: Any) -> Any:
        return mxmxm(rot_x(-t._mean_obliquity_radians), t.precession_matrix(), ICRS_to_J2000)


mean_ecliptic_frame = _MeanEclipticOfDate()


def as_jd_array(jd: ArrayLike) -> FloatArray:
    return np.atleast_1d(np.asarray(jd, dtype=np.float64))


def _times(jd_tt: FloatArray) -> Any:
    eph = get_ephemeris()
    eph.check_range(float(jd_tt.min()))
    eph.check_range(float(jd_tt.max()))
    return timescale().tt_jd(jd_tt)


def _longitudes(
    body: Body,
    dates: FloatArray,
    frame: Any,
    position_type: PositionType,
    node_type: NodeType,
) -> FloatArray:
    t = _times(dates)
    if body in EPHEMERIS_BODIES:
        eph = get_ephemeris()
        if position_type is PositionType.APPARENT:
            position = eph.earth.at(t).observe(eph.target(body)).apparent()
        else:
            position = (eph.target(body) - eph.earth).at(t)
        _, lon, _ = position.frame_latlon(frame)
        return np.asarray(lon.degrees % 360.0, dtype=np.float64)
    if body in (Body.RAHU, Body.KETU):
        if node_type is NodeType.TRUE:
            rahu = np.asarray(osculating_node_longitudes(t, frame), dtype=np.float64)
        else:
            rahu = np.asarray(mean_node_polynomial((dates - J2000_JD) / 36525.0), dtype=np.float64)
            if frame is ecliptic_frame:
                d_psi, _ = t._nutation_angles_radians
                rahu = rahu + np.degrees(d_psi)
            rahu %= 360.0
        return rahu if body is Body.RAHU else (rahu + 180.0) % 360.0
    raise ValueError(f"no positions for {body}")


def tropical_longitudes(
    body: Body,
    jd_tt: ArrayLike,
    position_type: PositionType = PositionType.APPARENT,
    node_type: NodeType = NodeType.TRUE,
) -> FloatArray:
    """Tropical longitudes (true ecliptic and equinox of date, degrees)."""
    return _longitudes(body, as_jd_array(jd_tt), ecliptic_frame, position_type, node_type)


def mean_ayanamsas(
    jd_tt: ArrayLike, system: Ayanamsa, user_value_j2000: float | None = None
) -> FloatArray:
    """Ayanamsa measured from the mean equinox of date (no nutation), degrees."""
    dates = as_jd_array(jd_tt)
    if system in STAR_SYSTEMS:
        definition = STAR_SYSTEMS[system]
        eph = get_ephemeris()
        star = eph.earth.at(_times(dates)).observe(skyfield_star(definition.star)).apparent()
        _, lon, _ = star.frame_latlon(mean_ecliptic_frame)
        return np.asarray((lon.degrees - definition.sidereal_longitude) % 360.0, dtype=np.float64)
    if system is Ayanamsa.USER:
        if user_value_j2000 is None:
            raise ValueError("a user-defined ayanamsa needs its J2000.0 value")
        shift = equinox_longitude_shifts(J2000_JD, dates)
        return np.asarray(user_value_j2000 + shift, dtype=np.float64)
    shift = equinox_longitude_shifts(J1900_TT, dates)
    return np.asarray(EPOCH_SYSTEMS[system].mean_value_j1900 + shift, dtype=np.float64)


def sidereal_longitudes(
    body: Body,
    jd_tt: ArrayLike,
    *,
    ayanamsa: Ayanamsa = Ayanamsa.LAHIRI,
    user_ayanamsa_j2000: float | None = None,
    position_type: PositionType = PositionType.APPARENT,
    node_type: NodeType = NodeType.TRUE,
) -> FloatArray:
    """Sidereal longitudes (degrees) of ``body`` at each date."""
    dates = as_jd_array(jd_tt)
    mean_lon = _longitudes(body, dates, mean_ecliptic_frame, position_type, node_type)
    return (mean_lon - mean_ayanamsas(dates, ayanamsa, user_ayanamsa_j2000)) % 360.0


def jd_ut_to_tt(jd_ut: ArrayLike) -> FloatArray:
    return np.asarray(timescale().ut1_jd(as_jd_array(jd_ut)).tt, dtype=np.float64)


def jd_tt_to_ut(jd_tt: ArrayLike) -> FloatArray:
    return np.asarray(timescale().tt_jd(as_jd_array(jd_tt)).ut1, dtype=np.float64)
