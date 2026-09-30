"""Event search: when a graha changes sign or nakshatra, reaches a longitude, or stations.

The sidereal longitude is sampled on a regular grid (vectorised, see
``astro.series``); wherever the quantity of interest differs between neighbouring
samples, the change is narrowed down by bisection to ``PRECISION_DAYS``. The grid
step keeps every body well under one division per step, so ingresses cannot be
skipped. The one blind spot is a pair of crossings closer together than one step,
which only happens when a planet stations within a few arcseconds of a boundary;
the pair then cancels and neither is reported.

Times are Julian days (UT). Sidereal positions follow the chart settings
(ayanamsa, apparent or true positions, mean or true nodes).
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

import numpy as np
from numpy.typing import NDArray

from jyotish_engine.astro.bodies import Body
from jyotish_engine.astro.positions import NodeType
from jyotish_engine.astro.series import (
    FloatArray,
    as_jd_array,
    jd_tt_to_ut,
    jd_ut_to_tt,
    sidereal_longitudes,
)
from jyotish_engine.settings import Settings

#: Bisection stops when an event is bracketed this tightly (about 9 milliseconds).
PRECISION_DAYS = 1e-7

#: Fastest sidereal motion of each body (degrees per day, either direction), with margin.
MAX_SPEED: dict[Body, float] = {
    Body.SUN: 1.1,
    Body.MOON: 16.0,
    Body.MARS: 0.9,
    Body.MERCURY: 2.5,
    Body.JUPITER: 0.35,
    Body.VENUS: 1.4,
    Body.SATURN: 0.15,
    Body.RAHU: 0.5,
    Body.KETU: 0.5,
    Body.URANUS: 0.08,
    Body.NEPTUNE: 0.05,
    Body.PLUTO: 0.05,
}

#: Longest grid step used for each body (days); shorter when divisions are narrow.
MAX_STEP_DAYS: dict[Body, float] = {
    Body.SUN: 1.0,
    Body.MOON: 0.25,
    Body.MARS: 1.0,
    Body.MERCURY: 0.5,
    Body.JUPITER: 2.0,
    Body.VENUS: 1.0,
    Body.SATURN: 2.0,
    Body.RAHU: 0.25,
    Body.KETU: 0.25,
    Body.URANUS: 4.0,
    Body.NEPTUNE: 4.0,
    Body.PLUTO: 4.0,
}

#: Half-width of the finite difference used for speeds in the station search (days).
SPEED_STEP_DAYS = 0.01

NAKSHATRA_WIDTH = 360.0 / 27.0


class Motion(StrEnum):
    DIRECT = "direct"
    RETROGRADE = "retrograde"


@dataclass(frozen=True, slots=True)
class Ingress:
    """``body`` leaves division ``from_index`` for ``to_index`` (0-based, width-sized)."""

    body: Body
    jd_ut: float
    from_index: int
    to_index: int
    motion: Motion


@dataclass(frozen=True, slots=True)
class Crossing:
    body: Body
    jd_ut: float
    longitude: float
    motion: Motion


@dataclass(frozen=True, slots=True)
class Station:
    """The body stops and turns: ``motion`` is the direction it takes afterwards."""

    body: Body
    jd_ut: float
    longitude: float
    motion: Motion


def _longitude_function(body: Body, settings: Settings) -> Callable[[FloatArray], FloatArray]:
    def evaluate(jd_tt: FloatArray) -> FloatArray:
        return sidereal_longitudes(
            body,
            jd_tt,
            ayanamsa=settings.ayanamsa,
            user_ayanamsa_j2000=settings.user_ayanamsa_j2000,
            position_type=settings.position_type,
            node_type=settings.node_type,
        )

    return evaluate


def longitude_at(body: Body, jd_ut: float, settings: Settings | None = None) -> float:
    """Sidereal longitude of ``body`` at one instant (degrees)."""
    evaluate = _longitude_function(body, settings or Settings())
    return float(evaluate(jd_ut_to_tt([jd_ut]))[0])


def _grid_step(body: Body, width: float, settings: Settings) -> float:
    step = MAX_STEP_DAYS[body]
    if body in (Body.RAHU, Body.KETU) and settings.node_type is NodeType.MEAN:
        step = 2.0
    return min(step, 0.4 * width / MAX_SPEED[body])


def find_changes(
    values: Callable[[FloatArray], NDArray[np.int64]],
    start_tt: float,
    end_tt: float,
    step: float,
    precision: float = PRECISION_DAYS,
) -> list[tuple[float, int, int]]:
    """Instants (TT) where an integer-valued function of time changes.

    Returns ``(jd_tt, value_before, value_after)`` for each change, in time order.
    """
    count = max(2, math.ceil((end_tt - start_tt) / step) + 1)
    grid = np.linspace(start_tt, end_tt, count)
    samples = values(grid)
    index = np.flatnonzero(samples[1:] != samples[:-1])
    if index.size == 0:
        return []
    low, high = grid[index], grid[index + 1]
    before = samples[index]
    while float(np.max(high - low)) > precision:
        middle = 0.5 * (low + high)
        unchanged = values(middle) == before
        low = np.where(unchanged, middle, low)
        high = np.where(unchanged, high, middle)
    after = values(high)
    return [(float(t), int(a), int(b)) for t, a, b in zip(high, before, after, strict=True)]


def ingresses(
    body: Body,
    start_jd_ut: float,
    end_jd_ut: float,
    settings: Settings | None = None,
    width: float = 30.0,
) -> list[Ingress]:
    """Every entry of ``body`` into a new division of ``width`` degrees (30 = signs)."""
    settings = settings or Settings()
    longitude = _longitude_function(body, settings)
    divisions = round(360.0 / width)

    def division(jd_tt: FloatArray) -> NDArray[np.int64]:
        return np.minimum(np.floor(longitude(jd_tt) / width), divisions - 1).astype(np.int64)

    start_tt, end_tt = jd_ut_to_tt([start_jd_ut, end_jd_ut])
    changes = find_changes(
        division, float(start_tt), float(end_tt), _grid_step(body, width, settings)
    )
    if not changes:
        return []
    times_ut = jd_tt_to_ut([t for t, _, _ in changes])
    events = []
    for jd_ut, (_, before, after) in zip(times_ut, changes, strict=True):
        forward = (after - before) % divisions == 1
        events.append(
            Ingress(
                body, float(jd_ut), before, after, Motion.DIRECT if forward else Motion.RETROGRADE
            )
        )
    return events


def sign_ingresses(
    body: Body, start_jd_ut: float, end_jd_ut: float, settings: Settings | None = None
) -> list[Ingress]:
    return ingresses(body, start_jd_ut, end_jd_ut, settings, 30.0)


def nakshatra_ingresses(
    body: Body, start_jd_ut: float, end_jd_ut: float, settings: Settings | None = None
) -> list[Ingress]:
    return ingresses(body, start_jd_ut, end_jd_ut, settings, NAKSHATRA_WIDTH)


def longitude_crossings(
    body: Body,
    target: float,
    start_jd_ut: float,
    end_jd_ut: float,
    settings: Settings | None = None,
) -> list[Crossing]:
    """Every time ``body`` passes the sidereal longitude ``target`` (either direction)."""
    settings = settings or Settings()
    longitude = _longitude_function(body, settings)

    def half(jd_tt: FloatArray) -> NDArray[np.int64]:
        return np.floor(((longitude(jd_tt) - target) % 360.0) / 180.0).astype(np.int64)

    start_tt, end_tt = jd_ut_to_tt([start_jd_ut, end_jd_ut])
    changes = find_changes(half, float(start_tt), float(end_tt), _grid_step(body, 180.0, settings))
    # Half-circle changes also happen at the opposite point; keep those at the target.
    kept = [
        (t, before)
        for t, before, _ in changes
        if abs((longitude(as_jd_array(t))[0] - target + 180.0) % 360.0 - 180.0) < 90.0
    ]
    if not kept:
        return []
    times_ut = jd_tt_to_ut([t for t, _ in kept])
    return [
        Crossing(
            body, float(jd_ut), target % 360.0, Motion.DIRECT if before == 1 else Motion.RETROGRADE
        )
        for jd_ut, (_, before) in zip(times_ut, kept, strict=True)
    ]


def stations(
    body: Body, start_jd_ut: float, end_jd_ut: float, settings: Settings | None = None
) -> list[Station]:
    """Retrograde and direct stations (sidereal speed changes sign).

    Only the five planets (and the outer planets) station. Rahu and Ketu are
    treated as always retrograde: the true node's brief reversals, a few times a
    month, are not reported. Stations are measured against the fixed stars
    (sidereal speed); against the moving equinox they fall slightly earlier or
    later, by up to a few hours for Saturn, because the tropical frame precesses
    by about 50 arcseconds a year.
    """
    if body in (Body.SUN, Body.MOON, Body.RAHU, Body.KETU):
        return []
    settings = settings or Settings()
    longitude = _longitude_function(body, settings)
    h = SPEED_STEP_DAYS

    def direction(jd_tt: FloatArray) -> NDArray[np.int64]:
        both = longitude(np.concatenate([jd_tt - h, jd_tt + h]))
        delta = (both[jd_tt.size :] - both[: jd_tt.size] + 180.0) % 360.0 - 180.0
        return (delta >= 0.0).astype(np.int64)

    start_tt, end_tt = jd_ut_to_tt([start_jd_ut, end_jd_ut])
    changes = find_changes(
        direction, float(start_tt), float(end_tt), MAX_STEP_DAYS[body], precision=1e-6
    )
    if not changes:
        return []
    times_tt = np.array([t for t, _, _ in changes])
    lons = longitude(times_tt)
    times_ut = jd_tt_to_ut(times_tt)
    return [
        Station(body, float(jd_ut), float(lon), Motion.DIRECT if after == 1 else Motion.RETROGRADE)
        for jd_ut, lon, (_, _, after) in zip(times_ut, lons, changes, strict=True)
    ]


def mesha_sankrantis(
    start_jd_ut: float, end_jd_ut: float, settings: Settings | None = None
) -> list[float]:
    """Times the Sun enters sidereal Aries (Mesha sankranti) in the interval (UT)."""
    return [
        event.jd_ut
        for event in sign_ingresses(Body.SUN, start_jd_ut, end_jd_ut, settings)
        if event.to_index == 0
    ]
