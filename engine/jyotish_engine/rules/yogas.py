"""Yogas and doshas of a chart, from the knowledge-base rule catalogue."""

from __future__ import annotations

from jyotish_engine.models import (
    ChartResult,
    CitationOut,
    UndecidedRuleOut,
    YogaOut,
    YogasOut,
)
from jyotish_engine.rules.catalogue import Catalogue, RuleResult, default_catalogue
from jyotish_engine.rules.facts import ChartFacts
from jyotish_engine.rules.schema import PERIOD_CATEGORIES, READING_CATEGORIES, Category

#: Yoga and dosha categories: everything but natal readings and period results.
YOGA_CATEGORIES = frozenset(Category) - READING_CATEGORIES - PERIOD_CATEGORIES


def rule_out(result: RuleResult) -> YogaOut:
    """A rule result as the public model."""
    rule = result.rule
    return YogaOut(
        id=rule.id,
        name=rule.name,
        category=rule.category,
        school=rule.school,
        provenance=rule.provenance,
        status=rule.status,
        description=rule.description,
        domains=list(rule.effects.domains),
        polarity=rule.effects.polarity,
        strength=rule.effects.strength,
        summary=rule.effects.summary,
        evidence=list(result.evidence),
        cancel_evidence=list(result.cancel_evidence),
        participants=list(result.participants),
        sources=[
            CitationOut(
                text=c.text,
                edition=c.edition,
                chapter=c.chapter,
                verses=c.verses,
                locator=c.locator,
                verified=c.verified,
            )
            for c in rule.sources
        ],
    )


def compute_yogas(
    chart: ChartResult,
    *,
    gender: str | None = None,
    include_sensitive: bool = False,
    catalogue: Catalogue | None = None,
) -> YogasOut:
    """Evaluate every catalogue rule against ``chart``.

    ``gender`` ("male" or "female") decides the few rules that depend on it; without
    it they are reported as undecided. Rules marked sensitive (health, longevity)
    are left out unless ``include_sensitive`` is set.
    """
    rules = catalogue or default_catalogue()
    results = rules.evaluate(ChartFacts.from_chart(chart, gender=gender), YOGA_CATEGORIES)
    shown = [r for r in results if include_sensitive or not r.rule.sensitive]
    return YogasOut(
        catalogue_size=len(results),
        present=[rule_out(r) for r in shown if r.present],
        cancelled=[rule_out(r) for r in shown if r.cancelled],
        undecided=[
            UndecidedRuleOut(id=r.rule.id, name=r.rule.name, missing=r.missing)
            for r in shown
            if r.missing is not None
        ],
    )
