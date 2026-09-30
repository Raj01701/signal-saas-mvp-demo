"""How long each time-sensitive chart factor stays unchanged around the birth moment.

The lagna moves through a sign in about two hours, a navamsha in about 13 minutes
and a D60 part in about two; the Moon changes pada every six hours or so. A factor
that would change within the birth time's uncertainty is flagged as fragile, so a
reading does not lean on it until the time is rectified.
"""

from __future__ import annotations

from collections.abc import Callable

from jyotish_engine.astro.ayanamsa import true_ayanamsa
from jyotish_engine.astro.bodies import Body
from jyotish_engine.astro.houses import chart_angles
from jyotish_engine.astro.time import Instant
from jyotish_engine.core.nakshatra import NAKSHATRAS, PADA_SPAN
from jyotish_engine.core.varga import VargaMethod, varga_sign_index
from jyotish_engine.models import ChartResult, SensitiveFactorOut, SensitivityOut
from jyotish_engine.transit.search import longitude_at

#: Uncertainty assumed when the birth record gives none (minutes).
DEFAULT_UNCERTAINTY_MINUTES = 5.0
#: Divisional-chart lagnas checked, with the search step and span (minutes).
LAGNA_DIVISIONS: tuple[tuple[int, float, float], ...] = (
    (1, 5.0, 240.0),
    (9, 1.0, 60.0),
    (10, 1.0, 60.0),
    (60, 0.25, 15.0),
)
_MINUTE = 1.0 / 1440.0


def _window(
    value: Callable[[float], int], jd_ut: float, step: float, span: float
) -> tuple[float | None, float | None]:
    """Minutes before and after ``jd_ut`` until ``value`` changes (None beyond ``span``)."""
    here = value(jd_ut)

    def edge(direction: int) -> float | None:
        previous = jd_ut
        for k in range(1, int(span / step) + 1):
            t = jd_ut + direction * k * step * _MINUTE
            if value(t) != here:
                inside, outside = previous, t
                while abs(outside - inside) > _MINUTE / 60.0:
                    middle = 0.5 * (inside + outside)
                    inside, outside = (
                        (middle, outside) if value(middle) == here else (inside, middle)
                    )
                return abs(inside - jd_ut) / _MINUTE
            previous = t
        return None

    return edge(-1), edge(+1)


def compute_sensitivity(chart: ChartResult) -> SensitivityOut:
    """Stability windows of the lagnas (D1, D9, D10, D60) and the Moon's nakshatra pada."""
    settings, place, jd = chart.settings, chart.birth.place, chart.time.jd_ut
    uncertainty = chart.birth.uncertainty_minutes or DEFAULT_UNCERTAINTY_MINUTES
    methods = {v.division: v.method for v in chart.vargas}

    def sidereal_ascendant(t: float) -> float:
        instant = Instant.from_jd_ut(t)
        tropical = chart_angles(instant, place.latitude, place.longitude).ascendant
        shift = true_ayanamsa(instant, settings.ayanamsa, settings.user_ayanamsa_j2000)
        return (tropical - shift) % 360.0

    factors: list[SensitiveFactorOut] = []
    for division, step, span in LAGNA_DIVISIONS:
        method = methods.get(division, VargaMethod.PARASHARA)

        def lagna_sign(t: float, division: int = division, method: VargaMethod = method) -> int:
            asc = sidereal_ascendant(t)
            return varga_sign_index(int(asc // 30.0), asc % 30.0, division, method)

        before, after = _window(lagna_sign, jd, step, span)
        name = "Lagna" if division == 1 else f"D{division} lagna"
        factors.append(_factor(name, f"sign {lagna_sign(jd) + 1}", before, after, uncertainty))

    def moon_pada(t: float) -> int:
        return int(longitude_at(Body.MOON, t, settings) // PADA_SPAN) % 108

    before, after = _window(moon_pada, jd, 20.0, 720.0)
    pada = moon_pada(jd)
    label = f"{NAKSHATRAS[pada // 4].name} pada {pada % 4 + 1}"
    factors.append(_factor("Moon nakshatra pada", label, before, after, uncertainty))
    return SensitivityOut(uncertainty_minutes=uncertainty, factors=factors)


def _factor(
    name: str, value: str, before: float | None, after: float | None, uncertainty: float
) -> SensitiveFactorOut:
    nearest = min(m for m in (before, after, float("inf")) if m is not None)
    return SensitiveFactorOut(
        name=name,
        value=value,
        minutes_before=before,
        minutes_after=after,
        fragile=nearest < uncertainty,
    )
