"""Nakshatra-based dasha systems (BPHS, chapters on dashas).

Each system is defined by its lords with their years, the nakshatra where the
cycle starts (seed), the counting direction, and how the balance at birth is
measured:

* ``nakshatra``: the fraction of the Moon's nakshatra still to run (Vimshottari and
  most systems);
* ``group``: the fraction of the lord's whole group of nakshatras still to run
  (Ashtottari, whose lords rule three or four consecutive nakshatras).

Conditional systems (Ashtottari, Shodashottari, Dwadashottari and the rest) are
meant for specific birth conditions described in BPHS; ``applicability`` helpers
live in ``conditions.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from jyotish_engine.astro.bodies import Body
from jyotish_engine.core.nakshatra import NAKSHATRA_SPAN
from jyotish_engine.dasha.base import Period, SubPeriodRule, active_chain, subdivide

S, MO, MA, ME, JU, VE, SA, RA, KE = (
    Body.SUN,
    Body.MOON,
    Body.MARS,
    Body.MERCURY,
    Body.JUPITER,
    Body.VENUS,
    Body.SATURN,
    Body.RAHU,
    Body.KETU,
)


class NakshatraDasha(StrEnum):
    VIMSHOTTARI = "vimshottari"
    ASHTOTTARI = "ashtottari"
    YOGINI = "yogini"
    SHODASHOTTARI = "shodashottari"
    DWADASHOTTARI = "dwadashottari"
    PANCHOTTARI = "panchottari"
    SHATABDIKA = "shatabdika"
    CHATURASHITI_SAMA = "chaturashiti_sama"
    DWISAPTATI_SAMA = "dwisaptati_sama"
    SHASHTIHAYANI = "shashtihayani"
    SHATTRIMSHA_SAMA = "shattrimsha_sama"


@dataclass(frozen=True, slots=True)
class DashaDefinition:
    name: str
    sequence: tuple[tuple[Body, float], ...]
    #: For each nakshatra (0 = Ashwini), the index into ``sequence`` of its lord.
    nakshatra_lord: tuple[int, ...]
    balance_by_group: bool = False
    #: Classical rule for sub-periods.
    sub_period_rule: SubPeriodRule = SubPeriodRule.PROPORTIONAL

    @property
    def total_years(self) -> float:
        return sum(years for _, years in self.sequence)


def _cyclic(seed_nakshatra: int, lords: int, direction: int = 1) -> tuple[int, ...]:
    """Nakshatras assigned to lords in rotation starting at a 1-based seed nakshatra."""
    mapping = [0] * 27
    for k in range(27):
        nak = (seed_nakshatra - 1 + direction * k) % 27
        mapping[nak] = k % lords
    return tuple(mapping)


def _groups(first_nakshatra: int, sizes: tuple[int, ...]) -> tuple[int, ...]:
    """Consecutive groups of nakshatras, starting at a 1-based nakshatra."""
    mapping = [0] * 27
    nak = first_nakshatra - 1
    for lord_index, size in enumerate(sizes):
        for _ in range(size):
            mapping[nak % 27] = lord_index
            nak += 1
    return tuple(mapping)


DEFINITIONS: dict[NakshatraDasha, DashaDefinition] = {
    NakshatraDasha.VIMSHOTTARI: DashaDefinition(
        "Vimshottari",
        ((KE, 7), (VE, 20), (S, 6), (MO, 10), (MA, 7), (RA, 18), (JU, 16), (SA, 19), (ME, 17)),
        _cyclic(1, 9),
    ),
    NakshatraDasha.ASHTOTTARI: DashaDefinition(
        "Ashtottari",
        ((S, 6), (MO, 15), (MA, 8), (ME, 17), (SA, 10), (JU, 19), (RA, 12), (VE, 21)),
        _groups(6, (4, 3, 4, 3, 3, 3, 4, 3)),  # from Ardra
        balance_by_group=True,
    ),
    NakshatraDasha.YOGINI: DashaDefinition(
        "Yogini",
        ((MO, 1), (S, 2), (JU, 3), (MA, 4), (ME, 5), (SA, 6), (VE, 7), (RA, 8)),
        # BPHS: the remainder of (birth nakshatra + 3) / 8 names the yogini, 1 = Mangala.
        # 27 is not a multiple of 8, so this is not a cyclic count from Ardra.
        tuple((n + 3) % 8 for n in range(27)),
    ),
    NakshatraDasha.SHODASHOTTARI: DashaDefinition(
        "Shodashottari",
        ((S, 11), (MA, 12), (JU, 13), (SA, 14), (KE, 15), (MO, 16), (ME, 17), (VE, 18)),
        _cyclic(8, 8),  # from Pushya
    ),
    NakshatraDasha.DWADASHOTTARI: DashaDefinition(
        "Dwadashottari",
        ((S, 7), (JU, 9), (KE, 11), (ME, 13), (RA, 15), (MA, 17), (SA, 19), (MO, 21)),
        _cyclic(27, 8, direction=-1),  # backwards from Revati
    ),
    NakshatraDasha.PANCHOTTARI: DashaDefinition(
        "Panchottari",
        ((S, 12), (ME, 13), (SA, 14), (MA, 15), (VE, 16), (MO, 17), (JU, 18)),
        _cyclic(17, 7),  # from Anuradha
    ),
    NakshatraDasha.SHATABDIKA: DashaDefinition(
        "Shatabdika",
        ((S, 5), (MO, 5), (VE, 10), (ME, 10), (JU, 20), (MA, 20), (SA, 30)),
        _cyclic(27, 7),  # from Revati
    ),
    NakshatraDasha.CHATURASHITI_SAMA: DashaDefinition(
        "Chaturashiti Sama",
        ((S, 12), (MO, 12), (MA, 12), (ME, 12), (JU, 12), (VE, 12), (SA, 12)),
        _cyclic(15, 7),  # from Swati
    ),
    NakshatraDasha.DWISAPTATI_SAMA: DashaDefinition(
        "Dwisaptati Sama",
        ((S, 9), (MO, 9), (MA, 9), (ME, 9), (JU, 9), (VE, 9), (SA, 9), (RA, 9)),
        _cyclic(19, 8),  # from Mula
    ),
    NakshatraDasha.SHASHTIHAYANI: DashaDefinition(
        "Shashtihayani",
        ((JU, 10), (S, 10), (MA, 10), (MO, 6), (ME, 6), (VE, 6), (SA, 6), (RA, 6)),
        _groups(1, (3, 4, 3, 4, 3, 4, 3, 3)),  # from Ashwini
    ),
    NakshatraDasha.SHATTRIMSHA_SAMA: DashaDefinition(
        "Shattrimsha Sama",
        ((MO, 1), (S, 2), (JU, 3), (MA, 4), (ME, 5), (SA, 6), (VE, 7), (RA, 8)),
        _cyclic(22, 8),  # from Shravana
    ),
}


def birth_balance(definition: DashaDefinition, moon: float) -> tuple[int, float]:
    """Index of the running lord at birth and the fraction of its period elapsed."""
    moon %= 360.0
    nak = min(int(moon / NAKSHATRA_SPAN), 26)
    lord_index = definition.nakshatra_lord[nak]
    within = (moon - nak * NAKSHATRA_SPAN) / NAKSHATRA_SPAN
    if not definition.balance_by_group:
        return lord_index, within
    group = [n for n in range(27) if definition.nakshatra_lord[n] == lord_index]
    # Order the group as it runs around the zodiac, starting from its first nakshatra.
    first = next(n for n in group if definition.nakshatra_lord[(n - 1) % 27] != lord_index)
    position = (nak - first) % 27
    return lord_index, (position + within) / len(group)


def mahadashas(
    system: NakshatraDasha,
    birth_jd_ut: float,
    moon_sidereal: float,
    year_days: float,
    cycles: int = 1,
) -> list[Period]:
    """Mahadashas from the one running at birth, for ``cycles`` full rounds."""
    definition = DEFINITIONS[system]
    lord_index, elapsed = birth_balance(definition, moon_sidereal)
    sequence = definition.sequence
    lord, years = sequence[lord_index]
    start = birth_jd_ut - elapsed * years * year_days
    periods = []
    for k in range(len(sequence) * cycles):
        lord, years = sequence[(lord_index + k) % len(sequence)]
        end = start + years * year_days
        periods.append(Period((lord,), start, end))
        start = end
    return periods


def sub_periods(
    system: NakshatraDasha, period: Period, rule: SubPeriodRule | None = None
) -> list[Period]:
    definition = DEFINITIONS[system]
    return subdivide(period, definition.sequence, rule or definition.sub_period_rule)


def running_periods(
    system: NakshatraDasha,
    birth_jd_ut: float,
    moon_sidereal: float,
    year_days: float,
    jd_ut: float,
    depth: int = 3,
    rule: SubPeriodRule | None = None,
) -> list[Period]:
    """The chain of periods (mahadasha down to ``depth``) running at ``jd_ut``."""
    definition = DEFINITIONS[system]
    cycles = 1 + int((jd_ut - birth_jd_ut) / (definition.total_years * year_days)) + 1
    periods = mahadashas(system, birth_jd_ut, moon_sidereal, year_days, cycles)
    return active_chain(
        periods, jd_ut, definition.sequence, depth, rule or definition.sub_period_rule
    )
