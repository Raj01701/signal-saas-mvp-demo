"""Load, check and run the knowledge-base rule catalogue.

Rules live in YAML files under ``knowledge/`` (see ``rules/schema.py``). Loading
expands families, validates every rule, checks each citation against
``knowledge/sources.yaml``, compiles the expressions and orders the rules so that
a rule referring to others with ``fires(...)`` runs after them.
"""

from __future__ import annotations

import fnmatch
import os
from collections.abc import Collection, Iterator, Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from jyotish_engine.astro.bodies import Body
from jyotish_engine.rules.dsl import Expression, RuleSyntaxError, compile_expression
from jyotish_engine.rules.facts import ChartFacts, MissingFactError
from jyotish_engine.rules.schema import Category, Citation, Rule, RuleFile, substitute

KNOWLEDGE_ENV = "JYOTISH_KNOWLEDGE_DIR"
RULE_DIRECTORIES = ("yogas", "natal", "dasha", "transit")


class CatalogueError(ValueError):
    """A rule file that is malformed, inconsistent or cites an unknown source."""


class RuleEvaluationError(RuntimeError):
    """A rule failed while being evaluated (a bug in the rule or the engine)."""


def default_knowledge_dir() -> Path:
    configured = os.environ.get(KNOWLEDGE_ENV)
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[3] / "knowledge"


@dataclass(frozen=True, slots=True)
class Sources:
    """Known text ids, their editions, and which texts are classical."""

    editions: Mapping[str, frozenset[str]]
    classical: frozenset[str]

    @classmethod
    def load(cls, path: Path) -> Sources:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        editions: dict[str, frozenset[str]] = {}
        classical = set()
        for section in ("texts", "modern_references"):
            for entry in data.get(section, []):
                editions[entry["id"]] = frozenset(e["id"] for e in entry.get("editions", []))
                if section == "texts":
                    classical.add(entry["id"])
        return cls(editions, frozenset(classical))

    def check(self, citation: Citation, where: str) -> None:
        if citation.text not in self.editions:
            raise CatalogueError(f"{where}: unknown source text {citation.text!r}")
        if citation.edition is None:
            if citation.text in self.classical:
                raise CatalogueError(f"{where}: citation of {citation.text!r} needs an edition")
            return
        if citation.edition not in self.editions[citation.text]:
            raise CatalogueError(
                f"{where}: {citation.text!r} has no edition {citation.edition!r} in sources.yaml"
            )


@dataclass(frozen=True)
class CompiledRule:
    rule: Rule
    when: Expression
    cancel_when: Expression | None
    participants: Expression | None
    path: str
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuleResult:
    rule: Rule
    #: The rule's condition holds and no cancellation applies.
    present: bool
    #: The condition holds, but a cancellation applies.
    cancelled: bool
    evidence: tuple[str, ...] = ()
    cancel_evidence: tuple[str, ...] = ()
    participants: tuple[Body, ...] = ()
    #: A birth fact the rule needed but the chart lacks (the rule was not decided).
    missing: str | None = None


def _merge(defaults: Mapping[str, Any], entry: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(defaults)
    merged.update(entry)
    return merged


def _expand(document: RuleFile) -> Iterator[dict[str, Any]]:
    for entry in document.rules:
        yield _merge(document.defaults, entry)
    for family in document.families:
        template = _merge(document.defaults, family.template)
        for instance in family.instances:
            rule = substitute(template, instance.params)
            rule.update(instance.overrides)
            rule["tests"] = instance.tests
            yield rule


def _compile(rule: Rule, path: str) -> CompiledRule:
    try:
        return CompiledRule(
            rule=rule,
            when=compile_expression(rule.when),
            cancel_when=compile_expression(rule.cancel_when) if rule.cancel_when else None,
            participants=compile_expression(rule.participants) if rule.participants else None,
            path=path,
        )
    except RuleSyntaxError as error:
        raise CatalogueError(f"{path}: {rule.id}: {error}") from error


def _references(compiled: CompiledRule) -> list[str]:
    expressions = [compiled.when, compiled.cancel_when, compiled.participants]
    return [ref for e in expressions if e is not None for ref in e.references()]


def _order(rules: list[CompiledRule]) -> list[CompiledRule]:
    """Resolve ``fires`` references and sort the rules so dependencies come first."""
    ids = [r.rule.id for r in rules]
    resolved: dict[str, CompiledRule] = {}
    for compiled in rules:
        depends: list[str] = []
        for pattern in _references(compiled):
            matches = [i for i in ids if fnmatch.fnmatchcase(i, pattern) and i != compiled.rule.id]
            if not matches:
                raise CatalogueError(f"{compiled.rule.id}: fires({pattern!r}) matches no rule")
            depends.extend(m for m in matches if m not in depends)
        resolved[compiled.rule.id] = CompiledRule(
            compiled.rule,
            compiled.when,
            compiled.cancel_when,
            compiled.participants,
            compiled.path,
            tuple(depends),
        )
    ordered: list[CompiledRule] = []
    state: dict[str, int] = {}  # 1 = visiting, 2 = done

    def visit(rule_id: str, chain: tuple[str, ...]) -> None:
        if state.get(rule_id) == 2:
            return
        if state.get(rule_id) == 1:
            raise CatalogueError(f"circular fires() references: {' -> '.join((*chain, rule_id))}")
        state[rule_id] = 1
        for dependency in resolved[rule_id].depends_on:
            visit(dependency, (*chain, rule_id))
        state[rule_id] = 2
        ordered.append(resolved[rule_id])

    for rule_id in ids:
        visit(rule_id, ())
    return ordered


def _flatten_bodies(value: Any) -> tuple[Body, ...]:
    found: list[Body] = []

    def walk(item: Any) -> None:
        if isinstance(item, list):
            for x in item:
                walk(x)
        elif isinstance(item, Body) and item not in found:
            found.append(item)

    walk(value)
    return tuple(found)


class Catalogue:
    """An ordered, validated set of compiled rules."""

    def __init__(self, rules: Sequence[CompiledRule]) -> None:
        self.rules = tuple(rules)
        self._by_id = {r.rule.id: r for r in self.rules}

    @classmethod
    def load(cls, directory: Path | None = None) -> Catalogue:
        root = directory or default_knowledge_dir()
        sources = Sources.load(root / "sources.yaml")
        compiled: list[CompiledRule] = []
        seen: dict[str, str] = {}
        for sub in RULE_DIRECTORIES:
            for path in sorted((root / sub).glob("**/*.yaml")):
                relative = str(path.relative_to(root))
                try:
                    document = RuleFile.model_validate(yaml.safe_load(path.read_text("utf-8")))
                    expanded = list(_expand(document))
                except (ValidationError, ValueError, yaml.YAMLError) as error:
                    raise CatalogueError(f"{relative}: {error}") from error
                for raw in expanded:
                    try:
                        rule = Rule.model_validate(raw)
                    except ValidationError as error:
                        name = raw.get("id", "?")
                        raise CatalogueError(f"{relative}: {name}: {error}") from error
                    if rule.id in seen:
                        raise CatalogueError(
                            f"{relative}: duplicate id {rule.id} ({seen[rule.id]})"
                        )
                    seen[rule.id] = relative
                    for citation in rule.sources:
                        sources.check(citation, f"{relative}: {rule.id}")
                    compiled.append(_compile(rule, relative))
        return cls(_order(compiled))

    def __len__(self) -> int:
        return len(self.rules)

    def __iter__(self) -> Iterator[CompiledRule]:
        return iter(self.rules)

    def __getitem__(self, rule_id: str) -> CompiledRule:
        return self._by_id[rule_id]

    def evaluate(
        self, facts: ChartFacts, categories: Collection[Category] | None = None
    ) -> list[RuleResult]:
        """Evaluate every rule (or those of ``categories``), in dependency order, on one chart."""
        facts.results.clear()
        return [
            self.evaluate_rule(compiled, facts)
            for compiled in self.rules
            if categories is None or compiled.rule.category in categories
        ]

    def evaluate_rule(self, compiled: CompiledRule, facts: ChartFacts) -> RuleResult:
        rule = compiled.rule
        for dependency in compiled.depends_on:
            if dependency not in facts.results:
                self.evaluate_rule(self._by_id[dependency], facts)
        try:
            condition, evidence = compiled.when.evaluate(facts)
            cancelled: bool = False
            cancel_evidence: list[str] = []
            if condition and compiled.cancel_when is not None:
                cancelled, cancel_evidence = compiled.cancel_when.evaluate(facts)
            participants: tuple[Body, ...] = ()
            if condition and compiled.participants is not None:
                participants = _flatten_bodies(compiled.participants.value(facts))
        except MissingFactError as missing:
            facts.results[rule.id] = False
            return RuleResult(rule, present=False, cancelled=False, missing=str(missing))
        except Exception as error:
            raise RuleEvaluationError(f"{rule.id} ({compiled.path}): {error}") from error
        present = condition and not cancelled
        facts.results[rule.id] = present
        return RuleResult(
            rule,
            present=present,
            cancelled=condition and cancelled,
            evidence=tuple(evidence),
            cancel_evidence=tuple(cancel_evidence),
            participants=participants,
        )


@cache
def default_catalogue() -> Catalogue:
    """The catalogue under ``knowledge/`` (or ``$JYOTISH_KNOWLEDGE_DIR``), loaded once."""
    return Catalogue.load()
