"""KP analysis of a chart, natal or horary."""

from __future__ import annotations

from collections.abc import Sequence

from jyotish_engine.astro.bodies import GRAHAS, Body
from jyotish_engine.astro.houses import HouseSystem
from jyotish_engine.chart import compute_chart_at
from jyotish_engine.kp.significators import (
    bhava_of,
    horary_cusps,
    ruling_planets,
    significators,
)
from jyotish_engine.kp.subdivisions import KpLords, kp_lords
from jyotish_engine.models import (
    ChartResult,
    KpChartOut,
    KpCuspOut,
    KpOut,
    KpPlanetOut,
    PlaceInput,
)
from jyotish_engine.settings import Preset, Settings, preset


def _lords(lords: KpLords) -> KpOut:
    return KpOut(
        sign_lord=lords.sign_lord,
        star_lord=lords.star_lord,
        sub_lord=lords.sub_lord,
        sub_sub_lord=lords.sub_sub_lord,
    )


def _kp(chart: ChartResult, cusps: Sequence[float]) -> KpChartOut:
    if chart.day.weekday is None:
        raise ValueError("no sunrise at this place and date, so no day lord (polar latitude)")
    positions = {g.body: g.sidereal_longitude for g in chart.grahas if g.body in GRAHAS}
    found = significators(positions, cusps)
    rulers = ruling_planets(
        chart.day.weekday,
        positions[Body.MOON],
        chart.ascendant.sidereal_longitude,
        {node: positions[node] for node in (Body.RAHU, Body.KETU)},
    )
    return KpChartOut(
        cusps=[
            KpCuspOut(house=h + 1, longitude=c, lords=_lords(kp_lords(c)))
            for h, c in enumerate(cusps)
        ],
        planets=[
            KpPlanetOut(
                body=body,
                longitude=lon,
                house=bhava_of(lon, cusps),
                lords=_lords(kp_lords(lon)),
                signifies=[list(level) for level in found.by_planet[body]],
            )
            for body, lon in positions.items()
        ],
        house_significators=[
            [list(level) for level in found.by_house[house]] for house in range(1, 13)
        ],
        day_lord=rulers.day_lord,
        ruling_planets=list(rulers.planets),
    )


def compute_kp(chart: ChartResult) -> KpChartOut:
    """KP analysis of a chart computed with Placidus bhavas (the KP preset)."""
    if chart.houses.system is not HouseSystem.PLACIDUS or chart.houses.fallback:
        raise ValueError("KP needs Placidus cusps: compute the chart with the KP preset")
    return _kp(chart, chart.houses.cusps)


def compute_kp_horary(
    number: int, jd_ut: float, place: PlaceInput, settings: Settings | None = None
) -> KpChartOut:
    """KP horary: planets and ruling planets at the question (``jd_ut``), cusps from the
    KP number (1-249) the querent gives."""
    settings = settings or preset(Preset.KP)
    chart = compute_chart_at(jd_ut, place, settings)
    moment, cusps = horary_cusps(number, jd_ut, place.latitude, place.longitude, settings)
    result = _kp(chart, cusps)
    return result.model_copy(update={"horary_number": number, "horary_cusp_jd_ut": moment})
