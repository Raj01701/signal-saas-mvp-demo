"""When each panchanga limb begins and ends.

Limb boundaries are found with the same grid-and-bisection search as transits
(``transit.search.find_changes``), on vectorised sidereal longitudes of the Sun and
the Moon, to about 10 milliseconds. The shortest limb (a karana) lasts about ten
hours, so a grid of 0.1 day cannot miss one.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from jyotish_engine.astro.bodies import Body
from jyotish_engine.astro.series import jd_tt_to_ut, jd_ut_to_tt, sidereal_longitudes
from jyotish_engine.panchanga.elements import (
    FloatArray,
    IntArray,
    Limb,
    limb_indices,
    limb_name,
)
from jyotish_engine.settings import Settings
from jyotish_engine.transit.search import PRECISION_DAYS, find_changes

GRID_DAYS = 0.1
#: Longer than any limb lasts (a tithi can last about 26.8 hours).
MARGIN_DAYS = 1.3


@dataclass(frozen=True, slots=True)
class LimbSpan:
    limb: Limb
    #: 0-based index within the cycle (tithi 0-29, nakshatra and yoga 0-26, karana 0-59).
    index: int
    start_jd_ut: float
    end_jd_ut: float

    @property
    def name(self) -> str:
        return limb_name(self.limb, self.index)

    def contains(self, jd_ut: float) -> bool:
        return self.start_jd_ut <= jd_ut < self.end_jd_ut


def _sun_moon(jd_tt: FloatArray, settings: Settings) -> tuple[FloatArray, FloatArray]:
    def longitudes(body: Body) -> FloatArray:
        return sidereal_longitudes(
            body,
            jd_tt,
            ayanamsa=settings.ayanamsa,
            user_ayanamsa_j2000=settings.user_ayanamsa_j2000,
            position_type=settings.position_type,
            node_type=settings.node_type,
        )

    return longitudes(Body.SUN), longitudes(Body.MOON)


def limb_index_at(limb: Limb, jd_ut: float, settings: Settings | None = None) -> int:
    sun, moon = _sun_moon(jd_ut_to_tt([jd_ut]), settings or Settings())
    return int(limb_indices(limb, sun, moon)[0])


def _spans(
    limb: Limb, changes: list[tuple[float, int, int]], start_jd_ut: float, end_jd_ut: float
) -> list[LimbSpan]:
    if len(changes) < 2:
        raise ValueError("search window too short to bracket a limb")
    times = np.asarray(jd_tt_to_ut([t for t, _, _ in changes]), dtype=np.float64)
    spans = [
        LimbSpan(limb, changes[i][2], float(times[i]), float(times[i + 1]))
        for i in range(len(changes) - 1)
    ]
    return [s for s in spans if s.end_jd_ut > start_jd_ut and s.start_jd_ut < end_jd_ut]


def limb_spans(
    limb: Limb, start_jd_ut: float, end_jd_ut: float, settings: Settings | None = None
) -> list[LimbSpan]:
    """Every span of ``limb`` that overlaps ``[start_jd_ut, end_jd_ut)``, with its full
    start and end (so the first may begin before the window and the last end after it)."""
    settings = settings or Settings()

    def indices(jd_tt: FloatArray) -> IntArray:
        return limb_indices(limb, *_sun_moon(jd_tt, settings))

    low_tt, high_tt = jd_ut_to_tt([start_jd_ut - MARGIN_DAYS, end_jd_ut + MARGIN_DAYS])
    changes = find_changes(indices, float(low_tt), float(high_tt), GRID_DAYS)
    return _spans(limb, changes, start_jd_ut, end_jd_ut)


def all_limb_spans(
    start_jd_ut: float, end_jd_ut: float, settings: Settings | None = None
) -> dict[Limb, list[LimbSpan]]:
    """``limb_spans`` for all four limbs at once, sharing every Sun and Moon evaluation.

    One grid finds every bracket; the brackets of all limbs are then bisected
    together, so each step evaluates the two bodies once.
    """
    settings = settings or Settings()
    low_tt, high_tt = jd_ut_to_tt([start_jd_ut - MARGIN_DAYS, end_jd_ut + MARGIN_DAYS])
    count = int(np.ceil((high_tt - low_tt) / GRID_DAYS)) + 1
    grid = np.linspace(float(low_tt), float(high_tt), count)
    sun, moon = _sun_moon(grid, settings)
    owners: list[Limb] = []
    low_parts, high_parts, before_parts = [], [], []
    for limb in Limb:
        samples = limb_indices(limb, sun, moon)
        where = np.flatnonzero(samples[1:] != samples[:-1])
        owners += [limb] * where.size
        low_parts.append(grid[where])
        high_parts.append(grid[where + 1])
        before_parts.append(samples[where])
    low, high = np.concatenate(low_parts), np.concatenate(high_parts)
    before = np.concatenate(before_parts)
    kinds = np.array([list(Limb).index(limb) for limb in owners])

    def indices_at(jd_tt: FloatArray) -> IntArray:
        s, m = _sun_moon(jd_tt, settings)
        result = np.empty(jd_tt.size, dtype=np.int64)
        for k, limb in enumerate(Limb):
            mask = kinds == k
            result[mask] = limb_indices(limb, s[mask], m[mask])
        return result

    while float(np.max(high - low)) > PRECISION_DAYS:
        middle = 0.5 * (low + high)
        unchanged = indices_at(middle) == before
        low = np.where(unchanged, middle, low)
        high = np.where(unchanged, high, middle)
    after = indices_at(high)
    result: dict[Limb, list[LimbSpan]] = {}
    for k, limb in enumerate(Limb):
        mask = kinds == k
        changes = [
            (float(t), int(b), int(a))
            for t, b, a in zip(high[mask], before[mask], after[mask], strict=True)
        ]
        result[limb] = _spans(limb, changes, start_jd_ut, end_jd_ut)
    return result
