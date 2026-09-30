"""Varshaphal (Tajika annual chart) and Tithi Pravesha chart for a year of life."""

from __future__ import annotations

from jyotish_engine.annual.dashas import (
    mudda_dashas,
    mudda_sub_periods,
    patyayini_dashas,
    patyayini_scheme,
    patyayini_sub_periods,
)
from jyotish_engine.annual.returns import tithi_pravesha, varsha_pravesha
from jyotish_engine.annual.sahams import compute_sahams
from jyotish_engine.annual.tajika import SEVEN, muntha_sign, office_bearers, tajika_relations
from jyotish_engine.annual.tajika_strength import pancha_vargiya_bala, year_lord
from jyotish_engine.astro.bodies import GRAHAS, Body
from jyotish_engine.astro.time import jd_to_datetime
from jyotish_engine.chart import compute_chart_at
from jyotish_engine.core.zodiac import SIGN_LORDS, Sign
from jyotish_engine.models import (
    AnnualPeriodOut,
    ChartResult,
    OfficeBearersOut,
    PlaceInput,
    SahamOut,
    TajikaRelationOut,
    TithiPraveshaOut,
    VarshaphalOut,
)


def _positions(chart: ChartResult) -> dict[Body, float]:
    return {g.body: g.sidereal_longitude for g in chart.grahas if g.body in GRAHAS}


def _period(lords: tuple[str, ...], start: float, end: float) -> AnnualPeriodOut:
    return AnnualPeriodOut(
        lords=list(lords),
        start=jd_to_datetime(start),
        end=jd_to_datetime(end),
        start_jd_ut=start,
        end_jd_ut=end,
    )


def compute_varshaphal(
    natal: ChartResult, years_completed: int, place: PlaceInput | None = None
) -> VarshaphalOut:
    """Annual chart for the year beginning after ``years_completed`` years of life.

    The chart is cast for the birth place unless another ``place`` (such as the
    current residence) is given.
    """
    if years_completed < 0:
        raise ValueError("years_completed must be zero or more")
    settings = natal.settings
    natal_positions = _positions(natal)
    sun = natal_positions[Body.SUN]
    start = varsha_pravesha(natal.time.jd_ut, sun, years_completed, settings)
    end = varsha_pravesha(natal.time.jd_ut, sun, years_completed + 1, settings)
    year_days = end - start
    annual = compute_chart_at(start, place or natal.birth.place, settings)
    positions = _positions(annual)
    by_day = annual.day.born_during_day
    bearers = office_bearers(
        natal.ascendant.sign,
        annual.ascendant.sign,
        years_completed,
        positions,
        by_day if by_day is not None else True,
    )
    muntha = muntha_sign(natal.ascendant.sign, years_completed)
    lord, aspects_lagna = year_lord(bearers.candidates(), annual.ascendant.sign, positions)

    mudda = []
    for maha in mudda_dashas(natal_positions[Body.MOON], years_completed, start, year_days):
        mudda.append(_period(tuple(b.value for b in maha.lords), maha.start_jd, maha.end_jd))
        mudda += [
            _period(tuple(b.value for b in sub.lords), sub.start_jd, sub.end_jd)
            for sub in mudda_sub_periods(maha)
        ]
    scheme = patyayini_scheme(annual.ascendant.sidereal_longitude, positions)
    patyayini = []
    for period in patyayini_dashas(scheme, start, year_days):
        patyayini.append(_period(period.lords, period.start_jd, period.end_jd))
        patyayini += [
            _period(sub.lords, sub.start_jd, sub.end_jd)
            for sub in patyayini_sub_periods(scheme, period)
        ]

    return VarshaphalOut(
        years_completed=years_completed,
        start=jd_to_datetime(start),
        start_jd_ut=start,
        end=jd_to_datetime(end),
        end_jd_ut=end,
        chart=annual,
        muntha=Sign(muntha),
        muntha_lord=SIGN_LORDS[Sign(muntha)],
        by_day=by_day,
        office_bearers=OfficeBearersOut(
            natal_lagna_lord=bearers.natal_lagna_lord,
            varsha_lagna_lord=bearers.varsha_lagna_lord,
            muntha_lord=bearers.muntha_lord,
            tri_rashi_lord=bearers.tri_rashi_lord,
            dina_ratri_lord=bearers.dina_ratri_lord,
            candidates=bearers.candidates(),
        ),
        year_lord=lord,
        year_lord_aspects_lagna=aspects_lagna,
        pancha_vargiya={b: pancha_vargiya_bala(b, positions[b]).total for b in SEVEN},
        tajika=[
            TajikaRelationOut(
                faster=r.faster,
                slower=r.slower,
                aspect=r.aspect.value,
                friendly=r.friendly,
                gap=r.gap,
                orb=r.orb,
                yoga=r.yoga.value if r.yoga else None,
            )
            for r in tajika_relations(positions)
        ],
        sahams=[
            SahamOut(
                name=s.name,
                meaning=s.meaning,
                sidereal_longitude=s.longitude,
                sign=Sign(int(s.longitude // 30.0)),
                sensitive=s.sensitive,
            )
            for s in compute_sahams(
                annual.ascendant.sidereal_longitude,
                positions,
                by_day if by_day is not None else True,
            )
        ],
        mudda=mudda,
        patyayini=patyayini,
    )


def compute_tithi_pravesha(
    natal: ChartResult, years_completed: int, place: PlaceInput | None = None
) -> TithiPraveshaOut:
    natal_positions = _positions(natal)
    sun, moon = natal_positions[Body.SUN], natal_positions[Body.MOON]
    moment = tithi_pravesha(natal.time.jd_ut, sun, moon, years_completed, natal.settings)
    return TithiPraveshaOut(
        years_completed=years_completed,
        moment=jd_to_datetime(moment),
        jd_ut=moment,
        elongation=(moon - sun) % 360.0,
        chart=compute_chart_at(moment, place or natal.birth.place, natal.settings),
    )
