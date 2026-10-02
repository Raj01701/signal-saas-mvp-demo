"""Precession of the equinoxes, used to carry an ayanamsa from its defining epoch.

Two models are provided because ayanamsa definitions were published against
different precession theories:

* IAU 1976 (Lieske et al. 1977), used by the Indian Calendar Reform Committee era
  definitions such as Lahiri.
* IAU 2006 (Capitaine et al. 2003), the current standard, via Skyfield.

The quantity needed for an ayanamsa is the ecliptic longitude, measured in the mean
ecliptic and equinox of date, of the mean equinox of the defining epoch. Near the
present it grows by about 50.3 arcseconds per year.
"""

from __future__ import annotations

import math
from enum import StrEnum
from typing import Any

import numpy as np
from skyfield.nutationlib import mean_obliquity
from skyfield.precessionlib import compute_precession

ARCSEC = math.pi / (180.0 * 3600.0)
J2000 = 2451545.0


class PrecessionModel(StrEnum):
    IAU1976 = "iau1976"
    IAU2006 = "iau2006"


def _rot1(angle: float) -> Any:
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, s], [0.0, -s, c]])


def _rot2(angle: float) -> Any:
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[c, 0.0, -s], [0.0, 1.0, 0.0], [s, 0.0, c]])


def _rot3(angle: float) -> Any:
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[c, s, 0.0], [-s, c, 0.0], [0.0, 0.0, 1.0]])


def _iau1976_matrix(jd_tt: float) -> Any:
    """Rotation from the mean equator/equinox of J2000 to that of date (Lieske 1977)."""
    t = (jd_tt - J2000) / 36525.0
    zeta = (2306.2181 * t + 0.30188 * t**2 + 0.017998 * t**3) * ARCSEC
    z = (2306.2181 * t + 1.09468 * t**2 + 0.018203 * t**3) * ARCSEC
    theta = (2004.3109 * t - 0.42665 * t**2 - 0.041833 * t**3) * ARCSEC
    return _rot3(-z) @ _rot2(theta) @ _rot3(-zeta)


def _iau1976_obliquity(jd_tt: float) -> float:
    t = (jd_tt - J2000) / 36525.0
    return (84381.448 - 46.8150 * t - 0.00059 * t**2 + 0.001813 * t**3) * ARCSEC


def _iau2006_matrix(jd_tt: float) -> Any:
    return np.asarray(compute_precession(jd_tt))


def _iau2006_obliquity(jd_tt: float) -> float:
    return float(mean_obliquity(jd_tt)) * ARCSEC


def equinox_longitude_shift(jd_tt_epoch: float, jd_tt: float, model: PrecessionModel) -> float:
    """Longitude (degrees) of the epoch's mean equinox in the mean ecliptic of ``jd_tt``.

    Positive when ``jd_tt`` is later than the epoch.
    """
    if model is PrecessionModel.IAU1976:
        p_epoch, p_date = _iau1976_matrix(jd_tt_epoch), _iau1976_matrix(jd_tt)
        eps_date = _iau1976_obliquity(jd_tt)
    else:
        p_epoch, p_date = _iau2006_matrix(jd_tt_epoch), _iau2006_matrix(jd_tt)
        eps_date = _iau2006_obliquity(jd_tt)
    equinox_epoch = np.array([1.0, 0.0, 0.0])
    in_j2000 = p_epoch.T @ equinox_epoch
    in_date_equatorial = p_date @ in_j2000
    in_date_ecliptic = _rot1(eps_date) @ in_date_equatorial
    return math.degrees(math.atan2(in_date_ecliptic[1], in_date_ecliptic[0]))


def equinox_longitude_shifts(jd_tt_epoch: float, jd_tt: Any) -> Any:
    """Vectorised :func:`equinox_longitude_shift` for an array of dates (IAU 2006)."""
    dates = np.atleast_1d(np.asarray(jd_tt, dtype=float))
    in_j2000 = _iau2006_matrix(jd_tt_epoch).T @ np.array([1.0, 0.0, 0.0])
    x, y, z = np.einsum("ijn,j->in", np.asarray(compute_precession(dates)), in_j2000)
    eps = np.asarray(mean_obliquity(dates)) * ARCSEC
    return np.degrees(np.arctan2(np.cos(eps) * y + np.sin(eps) * z, x))
