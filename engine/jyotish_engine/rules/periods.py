"""Readings of a moment: the running Vimshottari periods and the transits."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime

from jyotish_engine.astro.bodies import GRAHAS, Body
from jyotish_engine.astro.time import datetime_to_jd, jd_to_datetime
from jyotish_engine.core.zodiac import Sign
from jyotish_engine.dasha.nakshatra import NakshatraDasha
from jyotish_engine.dasha.tables import running_periods
from jyotish_engine.models import ChartResult, PeriodReadingsOut, TransitPositionOut
from jyotish_engine.rules.catalogue import Catalogue, default_catalogue
from jyotish_engine.rules.facts import ChartFacts
from jyotish_engine.rules.schema import PERIOD_CATEGORIES, Category
from jyotish_engine.rules.yogas import rule_out
from jyotish_engine.settings import Settings
from jyotish_engine.transit.search import longitude_at


def transit_positions(jd_ut: float, settings: Settings) -> dict[Body, float]:
    """Sidereal longitudes of the nine grahas at ``jd_ut``, with the chart's settings."""
    return {body: longitude_at(body, jd_ut, settings) for body in GRAHAS}


def _transit_out(facts: ChartFacts, positions: Mapping[Body, float]) -> list[TransitPositionOut]:
    return [
        TransitPositionOut(
            body=body,
            longitude=longitude,
            sign=Sign(int(longitude // 30.0) % 12),
            house_from_lagna=facts.transit_house(body),
            house_from_moon=facts.transit_house(body, Body.MOON),
        )
        for body, longitude in positions.items()
    ]


def compute_period_readings(
    chart: ChartResult,
    moment: datetime | None = None,
    *,
    include_sensitive: bool = False,
    catalogue: Catalogue | None = None,
) -> PeriodReadingsOut:
    """Dasha and transit rules that hold at ``moment`` (default: now), with their inputs.

    Dasha rules see the running Vimshottari mahadasha and antardasha lords; transit
    rules see the grahas' sidereal positions at the moment, computed with the chart's
    settings. Rules marked sensitive are left out unless ``include_sensitive`` is set.
    """
    jd_ut = datetime_to_jd(moment or datetime.now(UTC))
    if jd_ut < chart.time.jd_ut:
        raise ValueError("the moment must not be before the birth")
    periods = running_periods(chart, NakshatraDasha.VIMSHOTTARI, jd_ut, depth=3)
    positions = transit_positions(jd_ut, chart.settings)
    facts = ChartFacts.from_chart(chart).with_period(tuple(periods[1].lords), positions)
    rules = catalogue or default_catalogue()
    results = rules.evaluate(facts, PERIOD_CATEGORIES)
    shown = [r for r in results if include_sensitive or not r.rule.sensitive]
    present = [r for r in shown if r.present]
    return PeriodReadingsOut(
        moment=jd_to_datetime(jd_ut),
        jd_ut=jd_ut,
        dasha=periods,
        transits=_transit_out(facts, positions),
        dasha_readings=[rule_out(r) for r in present if r.rule.category is Category.DASHA],
        transit_readings=[rule_out(r) for r in present if r.rule.category is Category.TRANSIT],
        cancelled=[rule_out(r) for r in shown if r.cancelled],
    )
