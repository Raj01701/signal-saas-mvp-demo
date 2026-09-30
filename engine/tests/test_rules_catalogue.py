"""The knowledge-base catalogue: loads cleanly, and every rule passes its own tests."""

from __future__ import annotations

from collections import Counter
from typing import Any

import pytest

from jyotish_engine.rules.catalogue import Catalogue, CompiledRule, default_catalogue
from jyotish_engine.rules.facts import ChartFacts
from jyotish_engine.rules.schema import Provenance, Status

CATALOGUE = default_catalogue()
RULES = list(CATALOGUE)


def _run(compiled: CompiledRule, spec: dict[str, Any]) -> tuple[bool, bool, list[str]]:
    facts = ChartFacts.from_spec(spec)
    result = CATALOGUE.evaluate_rule(compiled, facts)
    assert result.missing is None, f"{compiled.rule.id}: spec lacks {result.missing}: {spec}"
    return result.present, result.cancelled, list(result.evidence)


def test_catalogue_size() -> None:
    """Milestone M4 ships at least 300 yogas and doshas."""
    assert len(CATALOGUE) >= 300, Counter(r.rule.category.value for r in CATALOGUE)


def test_every_rule_is_draft_and_cited() -> None:
    for compiled in CATALOGUE:
        rule = compiled.rule
        assert rule.status is Status.DRAFT, "only a qualified reviewer may mark rules reviewed"
        assert all(not c.verified for c in rule.sources), rule.id
        if rule.provenance is Provenance.CLASSICAL:
            assert any(c.edition for c in rule.sources), f"{rule.id}: classical, no classical text"


@pytest.mark.parametrize("compiled", RULES, ids=[r.rule.id for r in RULES])
def test_rule_fixtures(compiled: CompiledRule) -> None:
    tests = compiled.rule.tests
    for spec in tests.positive:
        present, _, evidence = _run(compiled, spec)
        assert present, f"{compiled.rule.id} should be present in {spec}"
        assert evidence, f"{compiled.rule.id} gave no evidence for {spec}"
    for spec in tests.negative:
        present, cancelled, _ = _run(compiled, spec)
        assert not present and not cancelled, f"{compiled.rule.id} should be absent in {spec}"
    for spec in tests.cancelled:
        present, cancelled, _ = _run(compiled, spec)
        assert cancelled and not present, f"{compiled.rule.id} should be cancelled in {spec}"


def test_evaluate_whole_catalogue_on_a_spec() -> None:
    facts = ChartFacts.from_spec({"lagna": "aries", "mars": "capricorn", "rest": "gemini"})
    results = CATALOGUE.evaluate(facts)
    assert len(results) == len(CATALOGUE)
    present = {r.rule.id for r in results if r.present}
    assert "mahapurusha.ruchaka" in present


def test_reload_gives_same_rules() -> None:
    again = Catalogue.load()
    assert [r.rule.id for r in again] == [r.rule.id for r in CATALOGUE]
