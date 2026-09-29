"""Krishnamurti Paddhati (KP) subdivisions of the zodiac.

Each nakshatra is divided among the nine Vimshottari lords in proportion to their
dasha years, starting from the nakshatra's own lord (the *sub*); each sub is divided
again the same way (the *sub-sub*). Splitting subs where they cross a sign boundary
gives the 249 divisions used for KP horary numbers.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache

from jyotish_engine.astro.bodies import Body
from jyotish_engine.core.nakshatra import (
    NAKSHATRA_SPAN,
    VIMSHOTTARI_SEQUENCE,
    VIMSHOTTARI_TOTAL_YEARS,
)
from jyotish_engine.core.zodiac import SIGN_LORDS, Sign

_EPSILON = 1e-9


def _sequence_from(lord: Body) -> list[tuple[Body, int]]:
    start = next(i for i, (body, _) in enumerate(VIMSHOTTARI_SEQUENCE) if body is lord)
    return [VIMSHOTTARI_SEQUENCE[(start + k) % 9] for k in range(9)]


def _divide(
    start: float, span: float, first_lord: Body, offset: float
) -> tuple[Body, float, float]:
    """Find which lord's portion of [start, start + span) contains ``offset``."""
    position = start
    for lord, years in _sequence_from(first_lord):
        width = span * years / VIMSHOTTARI_TOTAL_YEARS
        if offset < position + width - _EPSILON or lord is _sequence_from(first_lord)[-1][0]:
            return lord, position, width
        position += width
    raise AssertionError("unreachable")


@dataclass(frozen=True, slots=True)
class KpLords:
    sign_lord: Body
    star_lord: Body
    sub_lord: Body
    sub_sub_lord: Body


def kp_lords(longitude: float) -> KpLords:
    longitude %= 360.0
    nak_index = min(int(longitude / NAKSHATRA_SPAN), 26)
    nak_start = nak_index * NAKSHATRA_SPAN
    star_lord = VIMSHOTTARI_SEQUENCE[nak_index % 9][0]
    sub_lord, sub_start, sub_span = _divide(nak_start, NAKSHATRA_SPAN, star_lord, longitude)
    sub_sub_lord, _, _ = _divide(sub_start, sub_span, sub_lord, longitude)
    return KpLords(
        sign_lord=SIGN_LORDS[Sign(int(longitude // 30.0))],
        star_lord=star_lord,
        sub_lord=sub_lord,
        sub_sub_lord=sub_sub_lord,
    )


@dataclass(frozen=True, slots=True)
class KpDivision:
    number: int  # 1..249
    start: float
    end: float
    sign: Sign
    star_lord: Body
    sub_lord: Body


@cache
def kp_249_table() -> tuple[KpDivision, ...]:
    """The 249 KP divisions, as used for horary (prashna) numbers."""
    rows: list[KpDivision] = []
    for nak_index in range(27):
        nak_start = nak_index * NAKSHATRA_SPAN
        star_lord = VIMSHOTTARI_SEQUENCE[nak_index % 9][0]
        position = nak_start
        for lord, years in _sequence_from(star_lord):
            end = position + NAKSHATRA_SPAN * years / VIMSHOTTARI_TOTAL_YEARS
            boundary = (int(position // 30.0) + 1) * 30.0
            pieces = [(position, end)]
            if position < boundary - _EPSILON and end > boundary + _EPSILON:
                pieces = [(position, boundary), (boundary, end)]
            for lo, hi in pieces:
                rows.append(
                    KpDivision(
                        number=len(rows) + 1,
                        start=lo,
                        end=hi,
                        sign=Sign(int((lo + _EPSILON) // 30.0) % 12),
                        star_lord=star_lord,
                        sub_lord=lord,
                    )
                )
            position = end
    return tuple(rows)


def kp_horary_ascendant(number: int) -> float:
    """Ascendant longitude for a KP horary number (1..249): start of that division."""
    table = kp_249_table()
    if not 1 <= number <= len(table):
        raise ValueError(f"KP horary numbers run from 1 to {len(table)}")
    return table[number - 1].start
