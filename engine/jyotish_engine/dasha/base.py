"""Generic dasha period tree.

A dasha system assigns a sequence of ruling lords with fixed lengths. Each period
subdivides into sub-periods of the same lords, starting from the period's own
lord, either in proportion to their lengths (the classical rule) or equally.
Levels: 1 Mahadasha, 2 Antardasha, 3 Pratyantardasha, 4 Sookshma, 5 Prana, 6 Deha.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from jyotish_engine.astro.bodies import Body

LEVEL_NAMES = ("mahadasha", "antardasha", "pratyantardasha", "sookshma", "prana", "deha")


class SubPeriodRule(StrEnum):
    PROPORTIONAL = "proportional"
    EQUAL = "equal"


@dataclass(frozen=True, slots=True)
class Period:
    """A dasha period. ``lords`` is the path from the mahadasha lord down."""

    lords: tuple[Body, ...]
    start_jd: float  # UT
    end_jd: float  # UT

    @property
    def lord(self) -> Body:
        return self.lords[-1]

    @property
    def level(self) -> int:
        return len(self.lords)

    def contains(self, jd: float) -> bool:
        return self.start_jd <= jd < self.end_jd

    def years(self, year_days: float) -> float:
        return (self.end_jd - self.start_jd) / year_days


def rotate_from(sequence: Sequence[tuple[Body, float]], lord: Body) -> list[tuple[Body, float]]:
    """The sequence starting at ``lord`` and wrapping around."""
    index = next(i for i, (body, _) in enumerate(sequence) if body is lord)
    return [sequence[(index + k) % len(sequence)] for k in range(len(sequence))]


def subdivide(
    period: Period,
    sequence: Sequence[tuple[Body, float]],
    rule: SubPeriodRule = SubPeriodRule.PROPORTIONAL,
) -> list[Period]:
    """Split a period among the lords, starting from its own lord."""
    ordered = rotate_from(sequence, period.lord)
    total = sum(years for _, years in ordered)
    length = period.end_jd - period.start_jd
    out: list[Period] = []
    start = period.start_jd
    for i, (lord, years) in enumerate(ordered):
        share = years / total if rule is SubPeriodRule.PROPORTIONAL else 1.0 / len(ordered)
        end = period.end_jd if i == len(ordered) - 1 else start + length * share
        out.append(Period((*period.lords, lord), start, end))
        start = end
    return out


def active_chain(
    periods: Sequence[Period],
    jd: float,
    sequence: Sequence[tuple[Body, float]],
    depth: int,
    rule: SubPeriodRule = SubPeriodRule.PROPORTIONAL,
) -> list[Period]:
    """Periods at each level (1..depth) running at ``jd``; empty if outside the range."""
    chain: list[Period] = []
    level = list(periods)
    for _ in range(depth):
        current = next((p for p in level if p.contains(jd)), None)
        if current is None:
            break
        chain.append(current)
        level = subdivide(current, sequence, rule)
    return chain
