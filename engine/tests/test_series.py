"""The vectorised series agree with the scalar position and ayanamsa functions."""

from __future__ import annotations

import numpy as np
import pytest

from jyotish_engine.astro import series
from jyotish_engine.astro.ayanamsa import Ayanamsa, true_ayanamsa
from jyotish_engine.astro.bodies import GRAHAS
from jyotish_engine.astro.positions import NodeType, PositionType, tropical_positions
from jyotish_engine.astro.precession import (
    PrecessionModel,
    equinox_longitude_shift,
    equinox_longitude_shifts,
)
from jyotish_engine.astro.time import Instant

DATES_TT = np.array([2415100.3, 2433591.2243, 2451545.0, 2460000.7, 2470000.1])
MICRO_ARCSEC = 1e-6 / 3600.0


def _sep(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.max(np.abs((a - b + 180.0) % 360.0 - 180.0)))


def test_equinox_shifts_match_scalar() -> None:
    ours = equinox_longitude_shifts(2415020.0, DATES_TT)
    scalar = [equinox_longitude_shift(2415020.0, d, PrecessionModel.IAU2006) for d in DATES_TT]
    assert np.max(np.abs(ours - np.array(scalar))) < MICRO_ARCSEC


@pytest.mark.parametrize("node_type", list(NodeType))
@pytest.mark.parametrize("position_type", list(PositionType))
def test_tropical_longitudes_match_scalar(node_type: NodeType, position_type: PositionType) -> None:
    for body in GRAHAS:
        ours = series.tropical_longitudes(body, DATES_TT, position_type, node_type)
        scalar = [
            tropical_positions(Instant.from_jd_tt(d), [body], node_type, position_type)[
                body
            ].longitude
            for d in DATES_TT
        ]
        assert _sep(ours, np.array(scalar)) < MICRO_ARCSEC, body


@pytest.mark.parametrize("system", [a for a in Ayanamsa if a is not Ayanamsa.USER])
def test_sidereal_longitudes_match_scalar(system: Ayanamsa) -> None:
    """Computed without nutation, yet equal to tropical minus the true ayanamsa."""
    for body in GRAHAS:
        ours = series.sidereal_longitudes(body, DATES_TT, ayanamsa=system)
        scalar = []
        for d in DATES_TT:
            instant = Instant.from_jd_tt(d)
            tropical = tropical_positions(instant, [body])[body].longitude
            scalar.append((tropical - true_ayanamsa(instant, system)) % 360.0)
        assert _sep(ours, np.array(scalar)) < MICRO_ARCSEC, (system, body)


def test_user_ayanamsa() -> None:
    value = 23.85
    ours = series.sidereal_longitudes(
        GRAHAS[0], DATES_TT, ayanamsa=Ayanamsa.USER, user_ayanamsa_j2000=value
    )
    for d, lon in zip(DATES_TT, ours, strict=True):
        instant = Instant.from_jd_tt(d)
        tropical = tropical_positions(instant, [GRAHAS[0]])[GRAHAS[0]].longitude
        expected = (tropical - true_ayanamsa(instant, Ayanamsa.USER, value)) % 360.0
        assert abs((lon - expected + 180.0) % 360.0 - 180.0) < MICRO_ARCSEC
    with pytest.raises(ValueError, match="J2000"):
        series.mean_ayanamsas(DATES_TT, Ayanamsa.USER)


def test_time_scale_round_trip() -> None:
    jd_ut = np.array([2433591.2243, 2460000.5])
    back = series.jd_tt_to_ut(series.jd_ut_to_tt(jd_ut))
    assert np.max(np.abs(back - jd_ut)) < 1e-9
