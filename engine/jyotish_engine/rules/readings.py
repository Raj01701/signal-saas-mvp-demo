"""Natal readings: the classical result of each placement in a chart."""

from __future__ import annotations

from jyotish_engine.models import ChartResult, ReadingsOut
from jyotish_engine.rules.catalogue import Catalogue, default_catalogue
from jyotish_engine.rules.facts import ChartFacts
from jyotish_engine.rules.schema import READING_CATEGORIES, Category
from jyotish_engine.rules.yogas import rule_out

#: Display order: the rising sign and the Moon first, then planets, then house lords.
ORDER = (
    Category.LAGNA,
    Category.NAKSHATRA,
    Category.PLANET_IN_SIGN,
    Category.PLANET_IN_HOUSE,
    Category.LORD_IN_HOUSE,
)


def compute_readings(
    chart: ChartResult, *, include_sensitive: bool = False, catalogue: Catalogue | None = None
) -> ReadingsOut:
    """Every reading rule that holds for ``chart``: one per house lord, graha and so on.

    Rules marked sensitive are left out unless ``include_sensitive`` is set.
    """
    rules = catalogue or default_catalogue()
    results = rules.evaluate(ChartFacts.from_chart(chart), READING_CATEGORIES)
    shown = [r for r in results if r.present and (include_sensitive or not r.rule.sensitive)]
    shown.sort(key=lambda r: ORDER.index(r.rule.category))
    return ReadingsOut(catalogue_size=len(results), readings=[rule_out(r) for r in shown])
