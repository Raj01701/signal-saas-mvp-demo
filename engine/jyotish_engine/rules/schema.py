"""The schema of knowledge-base rule files (``knowledge/**/*.yaml``).

A rule file holds shared ``defaults``, explicit ``rules`` and templated
``families``. A family is a rule template whose strings contain ``{name}``
placeholders (optionally with a filter: ``{house|ord}`` gives "7th",
``{planet|title}`` gives "Mars") and a list of instances, each with its own
parameters and tests. See ``knowledge/README.md`` for the authoring guide.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

RULE_ID = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)+$")


class Category(StrEnum):
    MAHAPURUSHA = "mahapurusha"
    CHANDRA = "chandra"
    SURYA = "surya"
    NABHASA = "nabhasa"
    RAJA = "raja"
    DHANA = "dhana"
    PARIVARTANA = "parivartana"
    VIPARITA = "viparita"
    NEECHA_BHANGA = "neecha_bhanga"
    BHAVA = "bhava"
    MALIKA = "malika"
    CONJUNCTION = "conjunction"
    NAMED = "named"
    DOSHA = "dosha"
    BIRTH = "birth"


class School(StrEnum):
    PARASHARI = "parashari"
    JAIMINI = "jaimini"
    TAJIKA = "tajika"


class Provenance(StrEnum):
    #: Found in the classical Sanskrit texts (BPHS, Brihat Jataka, Phaladeepika, ...).
    CLASSICAL = "classical"
    #: Widely used in Indian practice, but not traceable to a core classical text.
    TRADITIONAL = "traditional"
    #: Introduced by 20th-century and later authors.
    MODERN = "modern"


class Status(StrEnum):
    DRAFT = "draft"
    REVIEWED = "reviewed"


class Polarity(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    MIXED = "mixed"


class Strength(StrEnum):
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"


class Domain(StrEnum):
    SELF = "self"
    CHARACTER = "character"
    INTELLECT = "intellect"
    WEALTH = "wealth"
    CAREER = "career"
    STATUS = "status"
    FAME = "fame"
    MARRIAGE = "marriage"
    CHILDREN = "children"
    PARENTS = "parents"
    SIBLINGS = "siblings"
    PROPERTY = "property"
    EDUCATION = "education"
    HEALTH = "health"
    LONGEVITY = "longevity"
    FORTUNE = "fortune"
    SPIRITUALITY = "spirituality"
    TRAVEL = "travel"
    CONFLICT = "conflict"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Citation(_Strict):
    """Where a rule comes from. ``text`` and ``edition`` are ids in ``sources.yaml``."""

    text: str
    edition: str | None = None
    chapter: int | str | None = None
    verses: str | None = None
    #: A section or yoga name, for books without useful chapter and verse numbers.
    locator: str | None = None
    #: True once someone has checked this citation against the named edition.
    verified: bool = False
    note: str | None = None

    @model_validator(mode="after")
    def _has_location(self) -> Citation:
        if self.chapter is None and self.locator is None:
            raise ValueError(f"citation of {self.text!r} needs a chapter or a locator")
        return self


class Effect(_Strict):
    domains: list[Domain] = Field(min_length=1)
    polarity: Polarity
    strength: Strength
    #: The result in our own words (never a copied translation).
    summary: str = Field(min_length=10)


ChartSpec = dict[str, Any]


class RuleTests(_Strict):
    #: Charts where the rule must be present.
    positive: list[ChartSpec] = Field(min_length=1)
    #: Charts where the rule's condition must be false.
    negative: list[ChartSpec] = Field(min_length=1)
    #: Charts where the condition holds but a cancellation applies.
    cancelled: list[ChartSpec] = Field(default_factory=list)


class Rule(_Strict):
    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    category: Category
    school: School
    provenance: Provenance
    description: str = Field(min_length=10)
    when: str
    cancel_when: str | None = None
    #: An expression giving the planets that form the rule (for dasha activation).
    participants: str | None = None
    effects: Effect
    sources: list[Citation] = Field(min_length=1)
    status: Status = Status.DRAFT
    #: Health, longevity and similar topics: hidden unless explicitly requested.
    sensitive: bool = False
    notes: str | None = None
    tests: RuleTests

    @field_validator("id")
    @classmethod
    def _id_format(cls, value: str) -> str:
        if not RULE_ID.match(value):
            raise ValueError(f"rule id {value!r} must look like 'family.name' (a-z, 0-9, _)")
        return value

    @model_validator(mode="after")
    def _cancel_tests(self) -> Rule:
        if self.cancel_when is None and self.tests.cancelled:
            raise ValueError(f"{self.id}: 'cancelled' tests given but no cancel_when")
        if self.cancel_when is not None and not self.tests.cancelled:
            raise ValueError(f"{self.id}: cancel_when needs at least one 'cancelled' test")
        return self


class FamilyInstance(_Strict):
    params: dict[str, Any]
    tests: dict[str, list[ChartSpec]]
    #: Fields that replace the template's for this instance only.
    overrides: dict[str, Any] = Field(default_factory=dict)


class Family(_Strict):
    template: dict[str, Any]
    instances: list[FamilyInstance] = Field(min_length=1)


class RuleFile(_Strict):
    defaults: dict[str, Any] = Field(default_factory=dict)
    rules: list[dict[str, Any]] = Field(default_factory=list)
    families: list[Family] = Field(default_factory=list)


_PLACEHOLDER = re.compile(r"\{([a-z_][a-z0-9_]*)(?:\|([a-z]+))?\}")


def ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


_FILTERS = {
    "ord": lambda v: ordinal(int(v)),
    "title": lambda v: str(v).replace("_", " ").title(),
    "upper": lambda v: str(v).upper(),
}


def substitute(value: Any, params: dict[str, Any]) -> Any:
    """Fill ``{name}`` placeholders in every string inside ``value``."""
    if isinstance(value, str):

        def replace(match: re.Match[str]) -> str:
            name, filter_name = match.group(1), match.group(2)
            if name not in params:
                raise ValueError(f"template placeholder {{{name}}} has no parameter")
            if filter_name is not None and filter_name not in _FILTERS:
                raise ValueError(f"unknown template filter {filter_name!r}")
            raw = params[name]
            return _FILTERS[filter_name](raw) if filter_name else str(raw)

        return _PLACEHOLDER.sub(replace, value)
    if isinstance(value, list):
        return [substitute(v, params) for v in value]
    if isinstance(value, dict):
        return {substitute(k, params): substitute(v, params) for k, v in value.items()}
    return value
