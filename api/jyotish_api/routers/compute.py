"""Stateless calculation routes: no account needed, nothing stored."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from fastapi import APIRouter, Query, Request

from jyotish_api.charts import ChartCache, resolve_settings
from jyotish_api.schemas import (
    AnnualRequest,
    ChartRequest,
    DashaRequest,
    HoraryRequest,
    MatchRequest,
    PanchangaRequest,
    PeriodRequest,
    PredictionsRequest,
    ReadingsRequest,
    RectifyRequest,
    TransitRequest,
    YogasRequest,
)
from jyotish_engine.annual.varshaphal import compute_tithi_pravesha, compute_varshaphal
from jyotish_engine.astro.bodies import Body
from jyotish_engine.astro.time import Instant
from jyotish_engine.dasha.kalachakra import KalachakraPeriod, kalachakra_mahadashas
from jyotish_engine.dasha.nakshatra import NakshatraDasha
from jyotish_engine.dasha.sign import SignDasha, SignPeriod, sign_mahadashas
from jyotish_engine.dasha.tables import nakshatra_dasha_table
from jyotish_engine.kp.chart import compute_kp, compute_kp_horary
from jyotish_engine.match.compute import compute_match
from jyotish_engine.models import (
    ChartResult,
    DashaTableOut,
    KpChartOut,
    MatchOut,
    PanchangaOut,
    PeriodReadingsOut,
    PredictionsOut,
    ReadingsOut,
    RectificationOut,
    SensitivityOut,
    StrengthsOut,
    TithiPraveshaOut,
    VarshaphalOut,
    YogasOut,
)
from jyotish_engine.panchanga.day import compute_panchanga
from jyotish_engine.place.geocode import Place, search_places
from jyotish_engine.predict import compute_predictions
from jyotish_engine.rectify import LifeEvent, rectify
from jyotish_engine.rules.periods import compute_period_readings
from jyotish_engine.rules.readings import compute_readings
from jyotish_engine.rules.yogas import compute_yogas
from jyotish_engine.sensitivity import compute_sensitivity
from jyotish_engine.settings import Preset, preset
from jyotish_engine.strength.strengths import compute_strengths
from jyotish_engine.transit.gochara import DoubleTransit, double_transits
from jyotish_engine.transit.saturn import SaturnTransit, TransitEpisode, saturn_transits

router = APIRouter(prefix="/v1")
MAX_TRANSIT_YEARS = 100


def _chart(request: Request, body: ChartRequest) -> ChartResult:
    cache: ChartCache = request.app.state.charts
    return cache.chart(body.birth, resolve_settings(body.settings, body.preset))


def _jd(day: date) -> float:
    return Instant.from_utc(datetime(day.year, day.month, day.day, tzinfo=UTC)).jd_ut


def _sidereal(chart: ChartResult) -> dict[Body, float]:
    return {g.body: g.sidereal_longitude for g in chart.grahas}


@router.get("/geo/search")
def geo_search(
    request: Request,
    q: str = Query(min_length=2, max_length=100),
    country: str | None = Query(default=None, min_length=2, max_length=2),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[Place]:
    """Places by name (GeoNames), most populous first."""
    warmup = getattr(request.app.state, "warmup", None)
    if warmup is not None:
        warmup.join(timeout=60.0)  # rather than loading a second copy
    return search_places(q, country_code=country, limit=limit)


@router.post("/charts")
def chart(request: Request, body: ChartRequest) -> ChartResult:
    """The birth chart: positions, houses, divisional charts, special points, Vimshottari."""
    return _chart(request, body)


@router.post("/charts/sensitivity")
def sensitivity(request: Request, body: ChartRequest) -> SensitivityOut:
    """How many minutes each time-sensitive factor holds before and after the birth time."""
    return compute_sensitivity(_chart(request, body))


@router.post("/charts/yogas")
def yogas(request: Request, body: YogasRequest) -> YogasOut:
    return compute_yogas(
        _chart(request, body), gender=body.gender, include_sensitive=body.include_sensitive
    )


@router.post("/charts/readings")
def readings(request: Request, body: ReadingsRequest) -> ReadingsOut:
    """The classical result of each placement: rising sign, Moon's nakshatra, grahas, lords."""
    return compute_readings(_chart(request, body), include_sensitive=body.include_sensitive)


@router.post("/charts/period")
def period(request: Request, body: PeriodRequest) -> PeriodReadingsOut:
    """Dasha and transit readings at a moment (default now), with the running periods."""
    return compute_period_readings(
        _chart(request, body), body.moment, include_sensitive=body.include_sensitive
    )


@router.post("/charts/predictions")
def predictions(request: Request, body: PredictionsRequest) -> PredictionsOut:
    """Promise × period × trigger for each life domain, month by month, with windows."""
    return compute_predictions(_chart(request, body), body.start, body.end, gender=body.gender)


@router.post("/rectify")
def rectify_birth_time(request: Request, body: RectifyRequest) -> RectificationOut:
    """Rank candidate birth times near the recorded one by how their dashas fit the events."""
    return rectify(
        _chart(request, body),
        [LifeEvent(e.kind, e.date) for e in body.events],
        uncertainty_minutes=body.uncertainty_minutes,
        step_seconds=body.step_seconds,
        gender=body.gender,
        priors=body.priors,
    )


@router.post("/charts/strengths")
def strengths(request: Request, body: ChartRequest) -> StrengthsOut:
    return compute_strengths(_chart(request, body))


@dataclass(frozen=True)
class DashaOut:
    system: str
    #: Nakshatra dashas.
    table: DashaTableOut | None = None
    #: Sign dashas (Jaimini).
    sign_periods: list[SignPeriod] | None = None
    #: Kalachakra.
    kalachakra_periods: list[KalachakraPeriod] | None = None


@router.post("/charts/dashas")
def dashas(request: Request, body: DashaRequest) -> DashaOut:
    """Any supported dasha system: a nakshatra dasha to ``depth`` levels, a sign dasha,
    or Kalachakra."""
    chart = _chart(request, body)
    sidereal, jd, year_days = _sidereal(chart), chart.time.jd_ut, chart.dashas.year_days
    if body.system in NakshatraDasha.__members__.values():
        table = nakshatra_dasha_table(
            NakshatraDasha(body.system), jd, sidereal[Body.MOON], year_days, depth=body.depth
        )
        return DashaOut(body.system, table=table)
    if body.system in SignDasha.__members__.values():
        periods = sign_mahadashas(
            SignDasha(body.system), chart.ascendant.sidereal_longitude, sidereal, jd, year_days
        )
        return DashaOut(body.system, sign_periods=periods)
    if body.system == "kalachakra":
        return DashaOut(
            body.system,
            kalachakra_periods=kalachakra_mahadashas(sidereal[Body.MOON], jd, year_days),
        )
    raise ValueError(f"unknown dasha system {body.system!r}")


@dataclass(frozen=True)
class TransitsOut:
    #: Saturn's transits counted from the natal Moon (Sade Sati, Ashtama, ...).
    saturn: dict[SaturnTransit, list[TransitEpisode]]
    #: Jupiter and Saturn both influencing a house, from the lagna and from the Moon.
    double_from_lagna: list[DoubleTransit]
    double_from_moon: list[DoubleTransit]


@router.post("/charts/transits")
def transits(request: Request, body: TransitRequest) -> TransitsOut:
    if not body.start < body.end or (body.end - body.start).days > 366 * MAX_TRANSIT_YEARS:
        raise ValueError(f"the window must run forwards and span at most {MAX_TRANSIT_YEARS} years")
    chart = _chart(request, body)
    settings, start, end = chart.settings, _jd(body.start), _jd(body.end)
    moon_sign = int(_sidereal(chart)[Body.MOON] // 30.0)
    lagna_sign = int(chart.ascendant.sidereal_longitude // 30.0)
    return TransitsOut(
        saturn=saturn_transits(moon_sign, start, end, settings),
        double_from_lagna=double_transits(lagna_sign, start, end, settings),
        double_from_moon=double_transits(moon_sign, start, end, settings),
    )


@dataclass(frozen=True)
class AnnualOut:
    varshaphal: VarshaphalOut
    tithi_pravesha: TithiPraveshaOut


@router.post("/charts/annual")
def annual(request: Request, body: AnnualRequest) -> AnnualOut:
    """The Tajika annual chart and Tithi Pravesha for the year after ``years_completed``."""
    natal = _chart(request, body)
    return AnnualOut(
        varshaphal=compute_varshaphal(natal, body.years_completed, body.place),
        tithi_pravesha=compute_tithi_pravesha(natal, body.years_completed, body.place),
    )


@router.post("/charts/kp")
def kp(request: Request, body: ChartRequest) -> KpChartOut:
    """KP analysis; uses the KP preset unless settings or a preset are given."""
    if body.settings is None and body.preset is None:
        body = body.model_copy(update={"preset": Preset.KP})
    return compute_kp(_chart(request, body))


@router.post("/kp/horary")
def kp_horary(body: HoraryRequest) -> KpChartOut:
    moment = body.moment if body.moment.tzinfo else body.moment.replace(tzinfo=UTC)
    settings = body.settings or preset(Preset.KP)
    return compute_kp_horary(body.number, Instant.from_utc(moment).jd_ut, body.place, settings)


@router.post("/panchanga")
def panchanga(body: PanchangaRequest) -> PanchangaOut:
    return compute_panchanga(
        body.date, body.place, resolve_settings(body.settings, body.preset), zone=body.zone
    )


@router.post("/match")
def match(request: Request, body: MatchRequest) -> MatchOut:
    cache: ChartCache = request.app.state.charts
    settings = resolve_settings(body.settings, body.preset)
    return compute_match(
        cache.chart(body.groom, settings), cache.chart(body.bride, settings), body.profile
    )
