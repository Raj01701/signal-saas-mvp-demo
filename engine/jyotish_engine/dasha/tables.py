"""Dasha tables with dates, for charts and the API."""

from __future__ import annotations

import math

from jyotish_engine.astro.bodies import GRAHAS, Body
from jyotish_engine.astro.time import jd_to_datetime
from jyotish_engine.core.zodiac import Sign
from jyotish_engine.dasha.base import Period, SubPeriodRule, active_chain, subdivide
from jyotish_engine.dasha.nakshatra import DEFINITIONS, NakshatraDasha, mahadashas
from jyotish_engine.dasha.sign import (
    LABELS,
    SignDasha,
    SignPeriod,
    sign_mahadashas,
    sign_running_periods,
    sign_sub_periods,
)
from jyotish_engine.models import (
    ChartResult,
    DashaPeriodOut,
    DashaTableOut,
    SignDashaPeriodOut,
    SignDashaTableOut,
)

#: Tables list the mahadashas that start within this many years of birth.
SPAN_YEARS = 120.0
#: Deepest level listed in full; deeper levels are available through ``running``.
MAX_TABLE_DEPTH = 3
MAX_DEPTH = 6


def period_out(period: Period) -> DashaPeriodOut:
    return DashaPeriodOut(
        lords=list(period.lords),
        start=jd_to_datetime(period.start_jd),
        end=jd_to_datetime(period.end_jd),
        start_jd_ut=period.start_jd,
        end_jd_ut=period.end_jd,
    )


def _cycles(system: NakshatraDasha, birth_jd_ut: float, moon: float, year_days: float) -> int:
    first = mahadashas(system, birth_jd_ut, moon, year_days, cycles=1)
    total_days = first[-1].end_jd - first[0].start_jd
    needed = birth_jd_ut + SPAN_YEARS * year_days - first[0].start_jd
    return max(1, math.ceil(needed / total_days))


def _expand(
    periods: list[Period], system: NakshatraDasha, rule: SubPeriodRule, depth: int
) -> list[Period]:
    sequence = DEFINITIONS[system].sequence
    out: list[Period] = []
    for period in periods:
        out.append(period)
        if depth > 1:
            out += _expand(subdivide(period, sequence, rule), system, rule, depth - 1)
    return out


def nakshatra_dasha_table(
    system: NakshatraDasha,
    birth_jd_ut: float,
    moon_sidereal: float,
    year_days: float,
    depth: int = 2,
    rule: SubPeriodRule | None = None,
) -> DashaTableOut:
    """Every mahadasha from the one running at birth to the last one starting within
    ``SPAN_YEARS`` of birth, each followed by its sub-periods down to ``depth``."""
    if not 1 <= depth <= MAX_TABLE_DEPTH:
        raise ValueError(f"table depth must be 1 to {MAX_TABLE_DEPTH}")
    definition = DEFINITIONS[system]
    cycles = _cycles(system, birth_jd_ut, moon_sidereal, year_days)
    horizon = birth_jd_ut + SPAN_YEARS * year_days
    periods = [
        p
        for p in mahadashas(system, birth_jd_ut, moon_sidereal, year_days, cycles)
        if p.start_jd < horizon
    ]
    rows = _expand(periods, system, rule or definition.sub_period_rule, depth)
    return DashaTableOut(
        system=system.value,
        label=definition.name,
        year_days=year_days,
        birth_lord=periods[0].lord,
        balance_years=(periods[0].end_jd - birth_jd_ut) / year_days,
        periods=[period_out(p) for p in rows],
    )


def _moon(chart: ChartResult) -> float:
    return next(g.sidereal_longitude for g in chart.grahas if g.body is Body.MOON)


def chart_dasha_table(
    chart: ChartResult,
    system: NakshatraDasha,
    depth: int = 2,
    rule: SubPeriodRule | None = None,
) -> DashaTableOut:
    return nakshatra_dasha_table(
        system, chart.time.jd_ut, _moon(chart), chart.dashas.year_days, depth, rule
    )


def running_periods(
    chart: ChartResult,
    system: NakshatraDasha,
    jd_ut: float,
    depth: int = 5,
    rule: SubPeriodRule | None = None,
) -> list[DashaPeriodOut]:
    """The periods running at ``jd_ut``, from the mahadasha down to ``depth``."""
    if not 1 <= depth <= MAX_DEPTH:
        raise ValueError(f"depth must be 1 to {MAX_DEPTH}")
    definition = DEFINITIONS[system]
    birth = chart.time.jd_ut
    year_days = chart.dashas.year_days
    total_days = definition.total_years * year_days
    cycles = max(1, math.ceil((jd_ut - birth) / total_days) + 1)
    periods = mahadashas(system, birth, _moon(chart), year_days, cycles)
    chain = active_chain(
        periods, jd_ut, definition.sequence, depth, rule or definition.sub_period_rule
    )
    return [period_out(p) for p in chain]


def sign_period_out(period: SignPeriod) -> SignDashaPeriodOut:
    return SignDashaPeriodOut(
        signs=[Sign(s) for s in period.signs],
        start=jd_to_datetime(period.start_jd),
        end=jd_to_datetime(period.end_jd),
        start_jd_ut=period.start_jd,
        end_jd_ut=period.end_jd,
    )


def _chart_positions(chart: ChartResult) -> dict[Body, float]:
    return {g.body: g.sidereal_longitude for g in chart.grahas if g.body in GRAHAS}


def chart_sign_dasha_table(
    chart: ChartResult, system: SignDasha, depth: int = 2
) -> SignDashaTableOut:
    """Both rounds of a sign dasha, each period followed by its sub-periods."""
    if not 1 <= depth <= MAX_TABLE_DEPTH:
        raise ValueError(f"table depth must be 1 to {MAX_TABLE_DEPTH}")
    sidereal = _chart_positions(chart)
    periods = sign_mahadashas(
        system,
        chart.ascendant.sidereal_longitude,
        sidereal,
        chart.time.jd_ut,
        chart.dashas.year_days,
    )

    def expand(level: list[SignPeriod], remaining: int) -> list[SignPeriod]:
        out: list[SignPeriod] = []
        for period in level:
            out.append(period)
            if remaining > 1:
                out += expand(sign_sub_periods(system, period, sidereal), remaining - 1)
        return out

    return SignDashaTableOut(
        system=system.value,
        label=LABELS[system],
        year_days=chart.dashas.year_days,
        first_sign=Sign(periods[0].sign),
        periods=[sign_period_out(p) for p in expand(periods, depth)],
    )


def running_sign_periods(
    chart: ChartResult, system: SignDasha, jd_ut: float, depth: int = 3
) -> list[SignDashaPeriodOut]:
    if not 1 <= depth <= MAX_DEPTH:
        raise ValueError(f"depth must be 1 to {MAX_DEPTH}")
    chain = sign_running_periods(
        system,
        chart.ascendant.sidereal_longitude,
        _chart_positions(chart),
        chart.time.jd_ut,
        chart.dashas.year_days,
        jd_ut,
        depth,
    )
    return [sign_period_out(p) for p in chain]
