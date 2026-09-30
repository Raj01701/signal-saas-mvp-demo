"""Jaimini sign (rashi) dashas: Chara (K.N. Rao) and Narayana (P.V.R. Narasimha Rao).

Each period belongs to a sign, and its length comes from the position of that
sign's lord (``core.jaimini.dasha_years``). A period divides into twelve equal
sub-periods, one per sign, in an order that depends on the system. Both systems
start at birth and run two rounds of twelve dashas; in the second round each sign
gets 12 minus its first-round years.

**Chara dasha** (K.N. Rao, *Predicting through Jaimini's Chara Dasha*). The first
dasha is the lagna's. Dashas run zodiacally when the 9th sign from the lagna is
odd-footed and backwards otherwise. Antardashas begin with the sign after the dasha
sign and end with the dasha sign itself, zodiacally for an odd-footed dasha sign
and backwards for an even-footed one.

**Narayana dasha** (P.V.R. Narasimha Rao, *Vedic Astrology: An Integrated
Approach*, following Jaimini's Upadesa Sutras). The first dasha is that of the
stronger of the lagna and the 7th. From a movable sign the dashas go sign by sign,
from a fixed sign to every sixth sign, and from a dual sign through the kendras,
each kendra followed by its trines: zodiacally from an odd sign, backwards from an
even one. Saturn in the first sign makes them go sign by sign zodiacally; Ketu
there reverses the direction. Antardashas start from the stronger of the signs
holding the dasha sign's lord and the 7th lord, zodiacally from an odd sign and
backwards from an even one; Saturn in that sign makes them zodiacal, and Ketu in
the dasha sign reverses them.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from jyotish_engine.astro.bodies import Body
from jyotish_engine.core.jaimini import (
    ODD_FOOTED,
    dasha_lord,
    dasha_years,
    is_odd_sign,
    sign_index,
    stronger_sign,
)

ROUNDS = 2


class SignDasha(StrEnum):
    CHARA = "chara"
    NARAYANA = "narayana"


LABELS = {SignDasha.CHARA: "Chara (K.N. Rao)", SignDasha.NARAYANA: "Narayana"}


@dataclass(frozen=True, slots=True)
class SignPeriod:
    """A sign dasha period; ``signs`` runs from the mahadasha sign down (0 = Aries)."""

    signs: tuple[int, ...]
    start_jd: float  # UT
    end_jd: float  # UT

    @property
    def sign(self) -> int:
        return self.signs[-1]

    @property
    def level(self) -> int:
        return len(self.signs)

    def contains(self, jd: float) -> bool:
        return self.start_jd <= jd < self.end_jd


def _run(start: int, step: int) -> list[int]:
    return [(start + step * i) % 12 for i in range(12)]


def chara_order(lagna: int) -> list[int]:
    return _run(lagna, 1 if (lagna + 8) % 12 in ODD_FOOTED else -1)


def narayana_order(seed: int, sidereal: Mapping[Body, float]) -> list[int]:
    ketu, saturn = sign_index(sidereal[Body.KETU]), sign_index(sidereal[Body.SATURN])
    if saturn == seed and ketu != seed:
        return _run(seed, 1)
    forward = is_odd_sign(seed) != (ketu == seed)
    step = 1 if forward else -1
    nature = seed % 3  # 0 movable, 1 fixed, 2 dual
    if nature == 0:
        return _run(seed, step)
    if nature == 1:
        return _run(seed, 5 * step)
    order: list[int] = []
    for k in range(4):
        kendra = (seed + 3 * k * step) % 12
        trines = (8, 4) if forward else (4, 8)
        order += [kendra, (kendra + trines[0]) % 12, (kendra + trines[1]) % 12]
    return order


def chara_antardasha_order(sign: int, sidereal: Mapping[Body, float]) -> list[int]:
    step = 1 if sign in ODD_FOOTED else -1
    return [(sign + step * i) % 12 for i in range(1, 13)]


def narayana_antardasha_order(sign: int, sidereal: Mapping[Body, float]) -> list[int]:
    lord_sign = sign_index(sidereal[dasha_lord(sign, sidereal)])
    seventh_lord_sign = sign_index(sidereal[dasha_lord((sign + 6) % 12, sidereal)])
    seed = stronger_sign(lord_sign, seventh_lord_sign, sidereal)
    forward = is_odd_sign(seed) or sign_index(sidereal[Body.SATURN]) == seed
    if sign_index(sidereal[Body.KETU]) == sign:
        forward = not forward
    return _run(seed, 1 if forward else -1)


_SUB_ORDER: dict[SignDasha, Callable[[int, Mapping[Body, float]], list[int]]] = {
    SignDasha.CHARA: chara_antardasha_order,
    SignDasha.NARAYANA: narayana_antardasha_order,
}


def first_sign(system: SignDasha, ascendant: float, sidereal: Mapping[Body, float]) -> int:
    lagna = sign_index(ascendant)
    if system is SignDasha.CHARA:
        return lagna
    return stronger_sign(lagna, (lagna + 6) % 12, sidereal)


def mahadasha_order(
    system: SignDasha, ascendant: float, sidereal: Mapping[Body, float]
) -> list[int]:
    seed = first_sign(system, ascendant, sidereal)
    if system is SignDasha.CHARA:
        return chara_order(seed)
    return narayana_order(seed, sidereal)


def sign_mahadashas(
    system: SignDasha,
    ascendant: float,
    sidereal: Mapping[Body, float],
    birth_jd_ut: float,
    year_days: float,
    rounds: int = ROUNDS,
) -> list[SignPeriod]:
    """Mahadashas from birth: ``rounds`` rounds of twelve signs."""
    order = mahadasha_order(system, ascendant, sidereal)
    first_round = [dasha_years(sign, sidereal) for sign in order]
    periods: list[SignPeriod] = []
    start = birth_jd_ut
    for round_index in range(rounds):
        for sign, years in zip(order, first_round, strict=True):
            length = years if round_index % 2 == 0 else max(0, 12 - years)
            end = start + length * year_days
            periods.append(SignPeriod((sign,), start, end))
            start = end
    return periods


def sign_sub_periods(
    system: SignDasha, period: SignPeriod, sidereal: Mapping[Body, float]
) -> list[SignPeriod]:
    """Twelve equal sub-periods of ``period``; the last one ends exactly with it."""
    order = _SUB_ORDER[system](period.sign, sidereal)
    step = (period.end_jd - period.start_jd) / 12.0
    return [
        SignPeriod(
            (*period.signs, sign),
            period.start_jd + i * step,
            period.end_jd if i == 11 else period.start_jd + (i + 1) * step,
        )
        for i, sign in enumerate(order)
    ]


def sign_running_periods(
    system: SignDasha,
    ascendant: float,
    sidereal: Mapping[Body, float],
    birth_jd_ut: float,
    year_days: float,
    jd_ut: float,
    depth: int = 3,
) -> list[SignPeriod]:
    """The chain of periods running at ``jd_ut``, from the mahadasha down to ``depth``."""
    level = sign_mahadashas(system, ascendant, sidereal, birth_jd_ut, year_days)
    chain: list[SignPeriod] = []
    for _ in range(depth):
        current = next((p for p in level if p.contains(jd_ut)), None)
        if current is None:
            break
        chain.append(current)
        level = sign_sub_periods(system, current, sidereal)
    return chain
