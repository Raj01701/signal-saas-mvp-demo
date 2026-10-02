"""Kalachakra dasha (BPHS, chapter 46), from the Moon's nakshatra pada.

The nakshatras fall into four groups, each with its own table of nine dasha signs
for every pada:

* savya (direct), Ashwini type: Ashwini, Krittika, Punarvasu, Ashlesha, Hasta,
  Swati, Mula, Uttarashadha, Purvabhadra;
* savya, Bharani type: Bharani, Pushya, Chitra, Purvashadha, Uttarabhadra, Revati;
* apasavya (reverse), Rohini type: Rohini, Magha, Vishakha, Shravana;
* apasavya, Mrigashira type: Mrigashira, Ardra, Purva and Uttara Phalguni,
  Anuradha, Jyeshtha, Dhanishta, Shatabhisha.

Each sign has fixed years (Aries 7, Taurus 16, Gemini 9, Cancer 21, Leo 5, Virgo 9,
Libra 16, Scorpio 7, Sagittarius 10, Capricorn 4, Aquarius 4, Pisces 10). A pada's
nine signs add up to its span of life (paramayus: 100, 85, 83 or 86 years). The
first sign of a pada is its deha (body), the last its jeeva (life).

At birth, the part of the Moon's pada already traversed, times the paramayus,
gives the years already run through the pada's signs; the dasha of the sign
reached is running. After the pada's ninth sign, the signs of the following padas
(in zodiacal order) follow. Antardashas: the nine signs of the same pada, starting
from the dasha sign's place in it, each for (dasha years x sign years /
paramayus); deeper levels repeat the rule. The first dasha's sub-periods run from
its true start, before birth.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from jyotish_engine.core.nakshatra import NAKSHATRA_SPAN

PADA_SPAN = NAKSHATRA_SPAN / 4.0

AR, TA, GE, CN, LE, VI, LI, SC, SG, CP, AQ, PI = range(12)

#: Years of each sign's dasha, Aries to Pisces.
SIGN_YEARS = (7, 16, 9, 21, 5, 9, 16, 7, 10, 4, 4, 10)


class KalachakraGroup(StrEnum):
    SAVYA_ASHWINI = "savya_ashwini"
    SAVYA_BHARANI = "savya_bharani"
    APASAVYA_ROHINI = "apasavya_rohini"
    APASAVYA_MRIGASHIRA = "apasavya_mrigashira"


_S1, _S2 = KalachakraGroup.SAVYA_ASHWINI, KalachakraGroup.SAVYA_BHARANI
_A1, _A2 = KalachakraGroup.APASAVYA_ROHINI, KalachakraGroup.APASAVYA_MRIGASHIRA

#: Group of each nakshatra, Ashwini to Revati.
NAKSHATRA_GROUP: tuple[KalachakraGroup, ...] = (
    _S1, _S2, _S1, _A1, _A2, _A2, _S1, _S2, _S1,
    _A1, _A2, _A2, _S1, _S2, _S1, _A1, _A2, _A2,
    _S1, _S2, _S1, _A1, _A2, _A2, _S1, _S2, _S2,
)  # fmt: skip

#: The nine dasha signs of each pada (BPHS 46), deha first and jeeva last.
PADA_SIGNS: dict[KalachakraGroup, tuple[tuple[int, ...], ...]] = {
    _S1: (
        (AR, TA, GE, CN, LE, VI, LI, SC, SG),
        (CP, AQ, PI, SC, LI, VI, CN, LE, GE),
        (TA, AR, PI, AQ, CP, SG, AR, TA, GE),
        (CN, LE, VI, LI, SC, SG, CP, AQ, PI),
    ),
    _S2: (
        (SC, LI, VI, CN, LE, GE, TA, AR, PI),
        (AQ, CP, SG, AR, TA, GE, CN, LE, VI),
        (LI, SC, SG, CP, AQ, PI, SC, LI, VI),
        (CN, LE, GE, TA, AR, PI, AQ, CP, SG),
    ),
    _A1: (
        (SG, CP, AQ, PI, AR, TA, GE, LE, CN),
        (VI, LI, SC, PI, AQ, CP, SG, SC, LI),
        (VI, LE, CN, GE, TA, AR, SG, CP, AQ),
        (PI, AR, TA, GE, LE, CN, VI, LI, SC),
    ),
    _A2: (
        (PI, AQ, CP, SG, SC, LI, VI, LE, CN),
        (GE, TA, AR, SG, CP, AQ, PI, AR, TA),
        (GE, LE, CN, VI, LI, SC, PI, AQ, CP),
        (SG, SC, LI, VI, LE, CN, GE, TA, AR),
    ),
}


def pada_signs(pada: int) -> tuple[int, ...]:
    """Dasha signs of a pada numbered 0 (Ashwini 1) to 107 (Revati 4)."""
    pada %= 108
    return PADA_SIGNS[NAKSHATRA_GROUP[pada // 4]][pada % 4]


def paramayus(pada: int) -> int:
    return sum(SIGN_YEARS[s] for s in pada_signs(pada))


def deha_jeeva(pada: int) -> tuple[int, int]:
    signs = pada_signs(pada)
    return signs[0], signs[-1]


@dataclass(frozen=True, slots=True)
class KalachakraPeriod:
    """A Kalachakra period: ``signs`` from the mahadasha sign down (0 = Aries).

    ``pada`` and ``position`` locate the period's sign in its pada's sequence, which
    decides the order of its sub-periods.
    """

    signs: tuple[int, ...]
    start_jd: float
    end_jd: float
    pada: int
    position: int

    @property
    def sign(self) -> int:
        return self.signs[-1]

    def contains(self, jd: float) -> bool:
        return self.start_jd <= jd < self.end_jd


def birth_position(moon_sidereal: float) -> tuple[int, int, float]:
    """(pada 0..107, index of the running sign in its sequence, years already run in it)."""
    moon = moon_sidereal % 360.0
    pada = min(int(moon / PADA_SPAN), 107)
    fraction = (moon - pada * PADA_SPAN) / PADA_SPAN
    elapsed = fraction * paramayus(pada)
    for index, sign in enumerate(pada_signs(pada)):
        years = SIGN_YEARS[sign]
        if elapsed < years or index == 8:
            return pada, index, min(elapsed, years)
        elapsed -= years
    raise AssertionError("unreachable")


def kalachakra_mahadashas(
    moon_sidereal: float, birth_jd_ut: float, year_days: float, span_years: float = 120.0
) -> list[KalachakraPeriod]:
    """Mahadashas from the one running at birth until ``span_years`` after birth."""
    pada, index, elapsed = birth_position(moon_sidereal)
    start = birth_jd_ut - elapsed * year_days
    horizon = birth_jd_ut + span_years * year_days
    periods: list[KalachakraPeriod] = []
    while start < horizon:
        sign = pada_signs(pada)[index]
        end = start + SIGN_YEARS[sign] * year_days
        periods.append(KalachakraPeriod((sign,), start, end, pada, index))
        start = end
        index += 1
        if index == 9:
            pada, index = (pada + 1) % 108, 0
    return periods


def kalachakra_sub_periods(period: KalachakraPeriod) -> list[KalachakraPeriod]:
    """Nine sub-periods: the pada's signs from the period's own place, proportionally."""
    signs = pada_signs(period.pada)
    total = paramayus(period.pada)
    length = period.end_jd - period.start_jd
    out: list[KalachakraPeriod] = []
    start = period.start_jd
    for k in range(9):
        position = (period.position + k) % 9
        sign = signs[position]
        end = period.end_jd if k == 8 else start + length * SIGN_YEARS[sign] / total
        out.append(KalachakraPeriod((*period.signs, sign), start, end, period.pada, position))
        start = end
    return out


def kalachakra_running(
    moon_sidereal: float, birth_jd_ut: float, year_days: float, jd_ut: float, depth: int = 3
) -> list[KalachakraPeriod]:
    span = max(120.0, (jd_ut - birth_jd_ut) / year_days + 1.0)
    level = kalachakra_mahadashas(moon_sidereal, birth_jd_ut, year_days, span)
    chain: list[KalachakraPeriod] = []
    for _ in range(depth):
        current = next((p for p in level if p.contains(jd_ut)), None)
        if current is None:
            break
        chain.append(current)
        level = kalachakra_sub_periods(current)
    return chain
