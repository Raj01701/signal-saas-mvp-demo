"""Catalogue loading and validation, using small rule files written per test."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

from jyotish_engine.astro.bodies import Body
from jyotish_engine.rules.catalogue import (
    Catalogue,
    CatalogueError,
    RuleEvaluationError,
    default_knowledge_dir,
)
from jyotish_engine.rules.facts import ChartFacts
from jyotish_engine.rules.schema import ordinal, substitute

SOURCES = {
    "texts": [{"id": "bphs", "editions": [{"id": "santhanam"}]}],
    "modern_references": [{"id": "raman_300"}],
}
EXALTED_MARS = {"lagna": "aries", "mars": "capricorn", "rest": "leo"}
PLAIN = {"lagna": "aries", "rest": "leo"}

RULE: dict[str, Any] = {
    "id": "test.mars_exalted",
    "name": "Mars exalted",
    "category": "named",
    "school": "parashari",
    "provenance": "classical",
    "description": "Mars is in Capricorn (a test rule).",
    "when": "exalted(mars)",
    "participants": "[mars]",
    "effects": {
        "domains": ["status"],
        "polarity": "positive",
        "strength": "minor",
        "summary": "A test effect summary.",
    },
    "sources": [{"text": "bphs", "edition": "santhanam", "chapter": 1}],
    "tests": {"positive": [EXALTED_MARS], "negative": [PLAIN]},
}


def _rule(**changes: Any) -> dict[str, Any]:
    rule = copy.deepcopy(RULE)
    rule.update(changes)
    return rule


def _write(root: Path, files: dict[str, Any], sources: dict[str, Any] | None = None) -> Path:
    (root / "yogas").mkdir(parents=True, exist_ok=True)
    (root / "sources.yaml").write_text(yaml.safe_dump(sources or SOURCES), encoding="utf-8")
    for name, content in files.items():
        text = content if isinstance(content, str) else yaml.safe_dump(content, sort_keys=False)
        (root / "yogas" / name).write_text(text, encoding="utf-8")
    return root


def test_loads_and_evaluates(tmp_path: Path) -> None:
    catalogue = Catalogue.load(_write(tmp_path, {"a.yaml": {"rules": [RULE]}}))
    assert len(catalogue) == 1
    [result] = catalogue.evaluate(ChartFacts.from_spec(EXALTED_MARS))
    assert result.present and not result.cancelled
    assert result.evidence == ("exalted(mars)",)
    assert result.participants == (Body.MARS,)
    [absent] = catalogue.evaluate(ChartFacts.from_spec(PLAIN))
    assert not absent.present and absent.participants == ()


def test_defaults_apply_to_every_rule(tmp_path: Path) -> None:
    rule = _rule()
    del rule["school"]
    catalogue = Catalogue.load(
        _write(tmp_path, {"a.yaml": {"defaults": {"school": "jaimini"}, "rules": [rule]}})
    )
    assert catalogue["test.mars_exalted"].rule.school.value == "jaimini"


@pytest.mark.parametrize(
    ("rule", "message"),
    [
        (
            _rule(sources=[{"text": "saravali", "edition": "santhanam", "chapter": 1}]),
            "unknown source",
        ),
        (_rule(sources=[{"text": "bphs", "edition": "sharma", "chapter": 1}]), "has no edition"),
        (_rule(sources=[{"text": "bphs", "chapter": 1}]), "needs an edition"),
        (_rule(sources=[{"text": "raman_300"}]), "chapter or a locator"),
        (_rule(sources=[]), "at least 1"),
        (_rule(when="exalted(mars) and foo()"), "unknown function"),
        (_rule(id="MarsExalted"), "must look like"),
        (_rule(cancel_when="retrograde(mars)"), "needs at least one 'cancelled' test"),
        (
            _rule(tests={"positive": [EXALTED_MARS], "negative": [PLAIN], "cancelled": [PLAIN]}),
            "no cancel_when",
        ),
        (_rule(tests={"positive": [EXALTED_MARS], "negative": []}), "at least 1"),
        (_rule(colour="red"), "Extra inputs"),
        (_rule(when="fires('nothing.*')"), "matches no rule"),
    ],
)
def test_invalid_rules_are_rejected(tmp_path: Path, rule: dict[str, Any], message: str) -> None:
    with pytest.raises(CatalogueError, match=message):
        Catalogue.load(_write(tmp_path, {"a.yaml": {"rules": [rule]}}))


def test_duplicate_ids_across_files(tmp_path: Path) -> None:
    root = _write(tmp_path, {"a.yaml": {"rules": [RULE]}, "b.yaml": {"rules": [RULE]}})
    with pytest.raises(CatalogueError, match="duplicate id"):
        Catalogue.load(root)


def test_yaml_errors_name_the_file(tmp_path: Path) -> None:
    with pytest.raises(CatalogueError, match=r"bad\.yaml"):
        Catalogue.load(_write(tmp_path, {"bad.yaml": "rules: [\n  - id: x: y\n"}))


def test_fires_orders_rules_and_detects_cycles(tmp_path: Path) -> None:
    later = _rule(id="test.after", when="fires('test.mars_exalted') and in_kendra(mars)")
    catalogue = Catalogue.load(_write(tmp_path, {"a.yaml": {"rules": [later, RULE]}}))
    assert [r.rule.id for r in catalogue] == ["test.mars_exalted", "test.after"]
    assert catalogue["test.after"].depends_on == ("test.mars_exalted",)
    results = {r.rule.id: r.present for r in catalogue.evaluate(ChartFacts.from_spec(EXALTED_MARS))}
    assert results == {"test.mars_exalted": True, "test.after": True}
    # Evaluating one rule alone evaluates what it depends on first.
    facts = ChartFacts.from_spec(EXALTED_MARS)
    assert catalogue.evaluate_rule(catalogue["test.after"], facts).present

    one = _rule(id="test.one", when="fires('test.two')")
    two = _rule(id="test.two", when="fires('test.one')")
    with pytest.raises(CatalogueError, match="circular"):
        Catalogue.load(_write(tmp_path / "cycle", {"a.yaml": {"rules": [one, two]}}))


def test_families_expand_with_filters(tmp_path: Path) -> None:
    template = _rule(
        id="test.lord_{house}_kendra",
        name="{house|ord} lord in a kendra ({planet|title})",
        when="in_kendra(lord({house}))",
    )
    del template["tests"]
    family = {
        "template": template,
        "instances": [
            {
                "params": {"house": 10, "planet": "saturn"},
                "tests": {
                    "positive": [{"lagna": "aries", "saturn": "cancer", "rest": "leo"}],
                    "negative": [PLAIN],
                },
            },
            {
                "params": {"house": 2, "planet": "venus"},
                "tests": {
                    "positive": [{"lagna": "aries", "venus": "aries", "rest": "leo"}],
                    "negative": [PLAIN],
                },
                "overrides": {"provenance": "modern"},
            },
        ],
    }
    catalogue = Catalogue.load(_write(tmp_path, {"f.yaml": {"families": [family]}}))
    rules = {r.rule.id: r.rule for r in catalogue}
    assert rules["test.lord_10_kendra"].name == "10th lord in a kendra (Saturn)"
    assert rules["test.lord_10_kendra"].when == "in_kendra(lord(10))"
    assert rules["test.lord_2_kendra"].provenance.value == "modern"

    broken = copy.deepcopy(family)
    broken["template"]["name"] = "{missing} lord"
    with pytest.raises(CatalogueError, match="has no parameter"):
        Catalogue.load(_write(tmp_path / "broken", {"f.yaml": {"families": [broken]}}))


def test_missing_birth_fact_leaves_the_rule_undecided(tmp_path: Path) -> None:
    rule = _rule(when="exalted(mars) and day_birth()")
    catalogue = Catalogue.load(_write(tmp_path, {"a.yaml": {"rules": [rule]}}))
    facts = ChartFacts.from_spec(EXALTED_MARS)
    [result] = catalogue.evaluate(facts)
    assert result.missing == "day_birth"
    assert not result.present and facts.results["test.mars_exalted"] is False


def test_evaluation_errors_name_the_rule(tmp_path: Path) -> None:
    rule = _rule(when="house(1) == 1")
    catalogue = Catalogue.load(_write(tmp_path, {"a.yaml": {"rules": [rule]}}))
    with pytest.raises(RuleEvaluationError, match=r"test\.mars_exalted"):
        catalogue.evaluate(ChartFacts.from_spec(PLAIN))


def test_knowledge_dir_can_be_configured(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("JYOTISH_KNOWLEDGE_DIR", str(tmp_path))
    assert default_knowledge_dir() == tmp_path
    monkeypatch.delenv("JYOTISH_KNOWLEDGE_DIR")
    assert (default_knowledge_dir() / "sources.yaml").exists()


def test_substitute_and_ordinal() -> None:
    assert [ordinal(n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 22)] == [
        "1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "22nd",
    ]  # fmt: skip
    assert substitute({"a": ["{x|upper}", 3]}, {"x": "yes"}) == {"a": ["YES", 3]}
    with pytest.raises(ValueError, match="unknown template filter"):
        substitute("{x|shout}", {"x": 1})
