"""Dashas of the annual chart: Mudda (varsha Vimshottari) and Patyayini.

**Mudda dasha** is Vimshottari compressed into one year: the 120 years of the
cycle fill the Tajika year. The first dasha belongs to the lord of the natal
Moon's nakshatra advanced by the number of completed years, and it has run the
same fraction as the Vimshottari dasha had at birth. Antardashas are in
proportion, as in Vimshottari.

**Patyayini dasha** (P.V.R. Narasimha Rao, *Vedic Astrology: An Integrated
Approach*): take the degrees the lagna and the seven planets have covered in
their signs in the annual chart (krisamsas), in increasing order. The first
dasha's share is its own krisamsa, each following one's the difference from the
previous; the shares fill the year. Sub-periods run through the same order,
starting from the period's own lord, in the same proportions.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from jyotish_engine.astro.bodies import Body
from jyotish_engine.dasha.base import Period, subdivide
from jyotish_engine.dasha.nakshatra import DEFINITIONS, NakshatraDasha, birth_balance

LAGNA = "lagna"
SEVEN = (Body.SUN, Body.MOON, Body.MARS, Body.MERCURY, Body.JUPITER, Body.VENUS, Body.SATURN)


def mudda_dashas(
    natal_moon: float, years_completed: int, year_start_jd: float, year_days: float
) -> list[Period]:
    """Mudda dashas covering the Tajika year that starts at ``year_start_jd``."""
    definition = DEFINITIONS[NakshatraDasha.VIMSHOTTARI]
    lord_index, elapsed = birth_balance(definition, natal_moon)
    index = (lord_index + years_completed) % len(definition.sequence)
    unit = year_days / definition.total_years
    start = year_start_jd - elapsed * definition.sequence[index][1] * unit
    year_end = year_start_jd + year_days
    periods: list[Period] = []
    while start < year_end:
        lord, years = definition.sequence[index % len(definition.sequence)]
        end = start + years * unit
        periods.append(Period((lord,), start, end))
        start, index = end, index + 1
    return periods


def mudda_sub_periods(period: Period) -> list[Period]:
    return subdivide(period, DEFINITIONS[NakshatraDasha.VIMSHOTTARI].sequence)


@dataclass(frozen=True, slots=True)
class PatyayiniPeriod:
    lords: tuple[str, ...]  # "lagna" or a planet name, from the mahadasha down
    start_jd: float
    end_jd: float
    index: int  # position of this period's lord in the order


@dataclass(frozen=True, slots=True)
class PatyayiniScheme:
    lords: tuple[str, ...]
    shares: tuple[float, ...]  # sum to 1


def patyayini_scheme(ascendant: float, sidereal: Mapping[Body, float]) -> PatyayiniScheme:
    krisamsas = [(LAGNA, ascendant % 30.0)] + [(b.value, sidereal[b] % 30.0) for b in SEVEN]
    ordered = sorted(krisamsas, key=lambda item: item[1])
    arcs = [ordered[0][1]] + [ordered[i][1] - ordered[i - 1][1] for i in range(1, len(ordered))]
    total = sum(arcs)
    return PatyayiniScheme(tuple(name for name, _ in ordered), tuple(a / total for a in arcs))


def patyayini_dashas(
    scheme: PatyayiniScheme, year_start_jd: float, year_days: float
) -> list[PatyayiniPeriod]:
    periods = []
    start = year_start_jd
    for i, (lord, share) in enumerate(zip(scheme.lords, scheme.shares, strict=True)):
        end = year_start_jd + year_days if i == len(scheme.lords) - 1 else start + share * year_days
        periods.append(PatyayiniPeriod((lord,), start, end, i))
        start = end
    return periods


def patyayini_sub_periods(
    scheme: PatyayiniScheme, period: PatyayiniPeriod
) -> list[PatyayiniPeriod]:
    count = len(scheme.lords)
    length = period.end_jd - period.start_jd
    out = []
    start = period.start_jd
    for k in range(count):
        index = (period.index + k) % count
        end = period.end_jd if k == count - 1 else start + scheme.shares[index] * length
        out.append(PatyayiniPeriod((*period.lords, scheme.lords[index]), start, end, index))
        start = end
    return out
