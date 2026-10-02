"""Life events used for rectification, and the houses and karakas that signify them."""

from __future__ import annotations

from enum import StrEnum

from jyotish_engine.astro.bodies import Body
from jyotish_engine.predict.domains import DomainSpec
from jyotish_engine.rules.schema import Domain


class EventKind(StrEnum):
    """The event kinds saved with a person (``api/jyotish_api/routers/account.py``)."""

    MARRIAGE = "marriage"
    DIVORCE = "divorce"
    CHILD_BIRTH = "child_birth"
    EDUCATION = "education"
    JOB = "job"
    PROMOTION = "promotion"
    JOB_LOSS = "job_loss"
    BUSINESS = "business"
    RELOCATION = "relocation"
    FOREIGN_TRAVEL = "foreign_travel"
    PROPERTY = "property"
    ILLNESS = "illness"
    SURGERY = "surgery"
    ACCIDENT = "accident"
    PARENT_DEATH = "parent_death"
    SPOUSE_DEATH = "spouse_death"
    OTHER = "other"


def _spec(
    domain: Domain,
    primary: tuple[int, ...],
    secondary: tuple[int, ...],
    karakas: tuple[Body, ...],
    varga: int | None,
) -> DomainSpec:
    return DomainSpec(domain, primary, secondary, karakas, varga)


#: Parashari significations of each event: main houses, supporting houses, karakas
#: and the divisional chart that confirms it. "other" events are not scored.
EVENT_SPECS: dict[EventKind, DomainSpec] = {
    EventKind.MARRIAGE: _spec(Domain.MARRIAGE, (7,), (2, 11), (Body.VENUS,), 9),
    EventKind.DIVORCE: _spec(Domain.MARRIAGE, (6,), (12, 8), (Body.VENUS,), 9),
    EventKind.CHILD_BIRTH: _spec(Domain.CHILDREN, (5,), (9, 11), (Body.JUPITER,), 7),
    EventKind.EDUCATION: _spec(Domain.EDUCATION, (4, 5), (9,), (Body.MERCURY, Body.JUPITER), 24),
    EventKind.JOB: _spec(Domain.CAREER, (10,), (6, 2, 11), (Body.SUN, Body.SATURN), 10),
    EventKind.PROMOTION: _spec(Domain.CAREER, (10,), (11, 2), (Body.SUN,), 10),
    EventKind.JOB_LOSS: _spec(Domain.CAREER, (12,), (8, 6), (Body.SATURN,), 10),
    EventKind.BUSINESS: _spec(Domain.CAREER, (7, 10), (11,), (Body.MERCURY,), 10),
    EventKind.RELOCATION: _spec(Domain.PROPERTY, (4, 12), (3,), (Body.MOON,), 4),
    EventKind.FOREIGN_TRAVEL: _spec(Domain.TRAVEL, (12, 9), (3,), (Body.RAHU,), None),
    EventKind.PROPERTY: _spec(Domain.PROPERTY, (4,), (11, 2), (Body.MARS, Body.VENUS), 4),
    EventKind.ILLNESS: _spec(Domain.HEALTH, (6,), (8, 1, 12), (Body.SUN,), 30),
    EventKind.SURGERY: _spec(Domain.HEALTH, (8,), (6, 1), (Body.MARS,), 30),
    EventKind.ACCIDENT: _spec(Domain.HEALTH, (8,), (6, 1), (Body.MARS,), None),
    EventKind.PARENT_DEATH: _spec(Domain.PARENTS, (9, 4), (3, 10, 12), (Body.SUN, Body.MOON), 12),
    EventKind.SPOUSE_DEATH: _spec(Domain.MARRIAGE, (7,), (2, 8, 12), (Body.VENUS,), 9),
}
