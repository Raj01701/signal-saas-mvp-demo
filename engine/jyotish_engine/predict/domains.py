"""Life domains for predictions: their houses, karakas and divisional charts."""

from __future__ import annotations

from dataclasses import dataclass

from jyotish_engine.astro.bodies import Body
from jyotish_engine.rules.schema import Domain


@dataclass(frozen=True, slots=True)
class DomainSpec:
    domain: Domain
    #: Houses (from the lagna) that carry the domain, then supporting houses.
    primary: tuple[int, ...]
    secondary: tuple[int, ...]
    #: Natural significators (karakas).
    karakas: tuple[Body, ...]
    #: Division of the domain's divisional chart (D10 for career, ...).
    varga: int | None
    #: Ages at which the domain's events are read (desha-kala-patra): from, until.
    ages: tuple[float, float | None] = (0.0, None)

    def plausible(self, age: float) -> bool:
        low, high = self.ages
        return age >= low and (high is None or age < high)

    @property
    def houses(self) -> tuple[int, ...]:
        return self.primary + self.secondary


#: The domains of the plan's prediction model (Parashari house significations).
DOMAIN_SPECS: tuple[DomainSpec, ...] = (
    DomainSpec(Domain.CAREER, (10,), (6, 2, 11), (Body.SUN, Body.SATURN), 10, (16.0, None)),
    DomainSpec(Domain.MARRIAGE, (7,), (2, 11), (Body.VENUS,), 9, (18.0, None)),
    DomainSpec(Domain.CHILDREN, (5,), (9,), (Body.JUPITER,), 7, (18.0, None)),
    DomainSpec(Domain.WEALTH, (2, 11), (9,), (Body.JUPITER,), 2, (16.0, None)),
    DomainSpec(Domain.PROPERTY, (4,), (11,), (Body.MARS,), 4, (18.0, None)),
    DomainSpec(Domain.EDUCATION, (4, 5), (9,), (Body.MERCURY, Body.JUPITER), 24, (4.0, 35.0)),
    DomainSpec(Domain.PARENTS, (4, 9), (), (Body.MOON, Body.SUN), 12),
    DomainSpec(Domain.SPIRITUALITY, (9, 12), (5,), (Body.JUPITER, Body.KETU), 20),
    DomainSpec(Domain.HEALTH, (1,), (6, 8), (Body.SUN,), 30),
    DomainSpec(Domain.TRAVEL, (12, 9), (3,), (), None),
)


def karakas(spec: DomainSpec, gender: str | None) -> tuple[Body, ...]:
    """Karakas of ``spec``; for a woman's marriage Jupiter joins Venus."""
    if spec.domain is Domain.MARRIAGE and gender == "female":
        return (*spec.karakas, Body.JUPITER)
    return spec.karakas
