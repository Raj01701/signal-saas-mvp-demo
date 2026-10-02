"""Ashtakavarga (BPHS, chapters 66-72), its reductions and pindas, and kakshya transits.

**Bhinna ashtakavarga (BAV).** Each of the seven planets gets a bindu (point) in
every sign that is one of its benefic places counted from each of eight
contributors: the seven planets and the lagna. The totals are fixed: Sun 48,
Moon 49, Mars 39, Mercury 54, Jupiter 56, Venus 52, Saturn 39. The sarva
ashtakavarga (SAV) adds the seven BAVs (337 bindus); the lagna's own
ashtakavarga (49) is given separately. The prastara records which contributor
gave each bindu.

Texts differ over three places in the Moon's table. The default follows P.V.R.
Narasimha Rao, *Vedic Astrology: An Integrated Approach* (and Jagannatha Hora):
from the Moon 1, 3, 6, 7, 9, 10, 11; from Mars 2, 3, 5, 6, 10, 11; from Jupiter
1, 2, 4, 7, 8, 10, 11. The alternative reading, found in several other books, has
1, 3, 6, 7, 10, 11; 2, 3, 5, 6, 9, 10, 11; and 1, 4, 7, 8, 10, 11, 12.

**Reductions**, applied to each planet's BAV in turn:

* *Trikona shodhana*, for each trine of signs: if one holds no bindu, nothing
  changes; if all three hold the same number, all become zero; otherwise the
  smallest is subtracted from each.
* *Ekadhipatya shodhana*, for each pair of signs with the same lord (Mars, Venus,
  Mercury, Jupiter, Saturn): nothing changes if either sign holds no bindu or both
  are occupied. If both are empty, equal values become zero and unequal ones both
  take the smaller. If one is occupied, the empty one becomes zero when it holds
  no more than the occupied one, and otherwise takes the occupied one's value. A
  sign is occupied if a graha (Rahu and Ketu included) or the lagna is in it.

**Pindas.** Rasi pinda: the reduced bindus times the sign multipliers (Aries 7,
Taurus 10, Gemini 8, Cancer 4, Leo 10, Virgo 5, Libra 7, Scorpio 8, Sagittarius 9,
Capricorn 5, Aquarius 11, Pisces 12). Graha pinda: for each planet, the reduced
bindus in its sign times the planet multiplier (Sun 5, Moon 5, Mars 8, Mercury 5,
Jupiter 10, Venus 7, Saturn 5). Their sum is the shodhya pinda. These rules
reproduce the worked example in Rao's book exactly (``tests/test_ashtakavarga.py``).

**Kakshya.** Each sign has eight kakshyas of 3 deg 45 min ruled in turn by
Saturn, Jupiter, Mars, the Sun, Venus, Mercury, the Moon and the lagna. A planet
transiting a kakshya does well if that kakshya's lord gave a bindu to the planet's
BAV in that sign.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from jyotish_engine.astro.bodies import Body

LAGNA = "lagna"
SEVEN = (Body.SUN, Body.MOON, Body.MARS, Body.MERCURY, Body.JUPITER, Body.VENUS, Body.SATURN)
#: Contributors in the order the tables list them.
CONTRIBUTORS: tuple[str, ...] = (*(b.value for b in SEVEN), LAGNA)


class MoonTable(StrEnum):
    PVR = "pvr"
    ALTERNATIVE = "alternative"


_Row = tuple[tuple[int, ...], ...]

#: Benefic places of each planet counted from (Sun, Moon, Mars, Mercury, Jupiter,
#: Venus, Saturn, lagna).
TABLES: dict[str, _Row] = {
    "sun": (
        (1, 2, 4, 7, 8, 9, 10, 11), (3, 6, 10, 11), (1, 2, 4, 7, 8, 9, 10, 11),
        (3, 5, 6, 9, 10, 11, 12), (5, 6, 9, 11), (6, 7, 12), (1, 2, 4, 7, 8, 9, 10, 11),
        (3, 4, 6, 10, 11, 12),
    ),
    "moon": (
        (3, 6, 7, 8, 10, 11), (1, 3, 6, 7, 9, 10, 11), (2, 3, 5, 6, 10, 11),
        (1, 3, 4, 5, 7, 8, 10, 11), (1, 2, 4, 7, 8, 10, 11), (3, 4, 5, 7, 9, 10, 11),
        (3, 5, 6, 11), (3, 6, 10, 11),
    ),
    "mars": (
        (3, 5, 6, 10, 11), (3, 6, 11), (1, 2, 4, 7, 8, 10, 11), (3, 5, 6, 11),
        (6, 10, 11, 12), (6, 8, 11, 12), (1, 4, 7, 8, 9, 10, 11), (1, 3, 6, 10, 11),
    ),
    "mercury": (
        (5, 6, 9, 11, 12), (2, 4, 6, 8, 10, 11), (1, 2, 4, 7, 8, 9, 10, 11),
        (1, 3, 5, 6, 9, 10, 11, 12), (6, 8, 11, 12), (1, 2, 3, 4, 5, 8, 9, 11),
        (1, 2, 4, 7, 8, 9, 10, 11), (1, 2, 4, 6, 8, 10, 11),
    ),
    "jupiter": (
        (1, 2, 3, 4, 7, 8, 9, 10, 11), (2, 5, 7, 9, 11), (1, 2, 4, 7, 8, 10, 11),
        (1, 2, 4, 5, 6, 9, 10, 11), (1, 2, 3, 4, 7, 8, 10, 11), (2, 5, 6, 9, 10, 11),
        (3, 5, 6, 12), (1, 2, 4, 5, 6, 7, 9, 10, 11),
    ),
    "venus": (
        (8, 11, 12), (1, 2, 3, 4, 5, 8, 9, 11, 12), (3, 4, 6, 9, 11, 12), (3, 5, 6, 9, 11),
        (5, 8, 9, 10, 11), (1, 2, 3, 4, 5, 8, 9, 10, 11), (3, 4, 5, 8, 9, 10, 11),
        (1, 2, 3, 4, 5, 8, 9, 11),
    ),
    "saturn": (
        (1, 2, 4, 7, 8, 10, 11), (3, 6, 11), (3, 5, 6, 10, 11, 12), (6, 8, 9, 10, 11, 12),
        (5, 6, 11, 12), (6, 11, 12), (3, 5, 6, 11), (1, 3, 4, 6, 10, 11),
    ),
    LAGNA: (
        (3, 4, 6, 10, 11, 12), (3, 6, 10, 11, 12), (1, 3, 6, 10, 11), (1, 2, 4, 6, 8, 10, 11),
        (1, 2, 4, 5, 6, 7, 9, 10, 11), (1, 2, 3, 4, 5, 8, 9), (1, 3, 4, 6, 10, 11),
        (3, 6, 10, 11),
    ),
}  # fmt: skip

#: The Moon's rows from the Moon, Mars and Jupiter under the alternative reading.
_MOON_ALTERNATIVE = {
    1: (1, 3, 6, 7, 10, 11),
    2: (2, 3, 5, 6, 9, 10, 11),
    4: (1, 4, 7, 8, 10, 11, 12),
}

RASI_MULTIPLIERS = (7, 10, 8, 4, 10, 5, 7, 8, 9, 5, 11, 12)
GRAHA_MULTIPLIERS: dict[Body, int] = {
    Body.SUN: 5, Body.MOON: 5, Body.MARS: 8, Body.MERCURY: 5,
    Body.JUPITER: 10, Body.VENUS: 7, Body.SATURN: 5,
}  # fmt: skip
#: Pairs of signs with one lord: Mars, Venus, Mercury, Jupiter, Saturn.
SAME_LORD_PAIRS = ((0, 7), (1, 6), (2, 5), (8, 11), (9, 10))
#: Kakshya lords, in order within every sign.
KAKSHYA_LORDS: tuple[str, ...] = (
    "saturn", "jupiter", "mars", "sun", "venus", "mercury", "moon", LAGNA,
)  # fmt: skip
KAKSHYA_SPAN = 30.0 / 8.0


def table(name: str, moon: MoonTable = MoonTable.PVR) -> _Row:
    rows = TABLES[name]
    if name == "moon" and moon is MoonTable.ALTERNATIVE:
        rows = tuple(_MOON_ALTERNATIVE.get(i, row) for i, row in enumerate(rows))
    return rows


@dataclass(frozen=True, slots=True)
class Ashtakavarga:
    #: Bindus per sign (Aries first) for each planet and "lagna".
    bav: dict[str, tuple[int, ...]]
    #: Sum of the seven planets' BAVs.
    sav: tuple[int, ...]
    #: prastara[planet][contributor] = 0/1 per sign.
    prastara: dict[str, dict[str, tuple[int, ...]]]


def ashtakavarga(
    ascendant_sign: int, signs: Mapping[Body, int], moon: MoonTable = MoonTable.PVR
) -> Ashtakavarga:
    """Ashtakavarga from the lagna sign and the planets' signs (0 = Aries)."""
    positions = {**{b.value: signs[b] for b in SEVEN}, LAGNA: ascendant_sign}
    bav: dict[str, tuple[int, ...]] = {}
    prastara: dict[str, dict[str, tuple[int, ...]]] = {}
    for name in (*(b.value for b in SEVEN), LAGNA):
        totals = [0] * 12
        grid: dict[str, tuple[int, ...]] = {}
        for contributor, places in zip(CONTRIBUTORS, table(name, moon), strict=True):
            row = [0] * 12
            for place in places:
                row[(positions[contributor] + place - 1) % 12] = 1
            grid[contributor] = tuple(row)
            totals = [t + r for t, r in zip(totals, row, strict=True)]
        bav[name] = tuple(totals)
        prastara[name] = grid
    sav = tuple(sum(bav[b.value][s] for b in SEVEN) for s in range(12))
    return Ashtakavarga(bav, sav, prastara)


def trikona_shodhana(bindus: tuple[int, ...]) -> tuple[int, ...]:
    out = list(bindus)
    for first in range(4):
        trine = (first, first + 4, first + 8)
        values = [out[s] for s in trine]
        if 0 in values:
            continue
        cut = values[0] if len(set(values)) == 1 else min(values)
        for s in trine:
            out[s] -= cut
    return tuple(out)


def ekadhipatya_shodhana(bindus: tuple[int, ...], occupied: set[int]) -> tuple[int, ...]:
    out = list(bindus)
    for a, b in SAME_LORD_PAIRS:
        in_a, in_b = a in occupied, b in occupied
        if out[a] == 0 or out[b] == 0 or (in_a and in_b):
            continue
        if not in_a and not in_b:
            value = 0 if out[a] == out[b] else min(out[a], out[b])
            out[a] = out[b] = value
            continue
        full, empty = (a, b) if in_a else (b, a)
        out[empty] = 0 if out[empty] <= out[full] else out[full]
    return tuple(out)


@dataclass(frozen=True, slots=True)
class Pindas:
    reduced: tuple[int, ...]
    rasi_pinda: int
    graha_pinda: int

    @property
    def shodhya_pinda(self) -> int:
        return self.rasi_pinda + self.graha_pinda


def pindas(bindus: tuple[int, ...], signs: Mapping[Body, int], occupied: set[int]) -> Pindas:
    """Reduce one planet's BAV and compute its rasi, graha and shodhya pindas.

    ``occupied``: signs holding a graha (Rahu and Ketu included) or the lagna.
    """
    reduced = ekadhipatya_shodhana(trikona_shodhana(bindus), occupied)
    rasi = sum(r * m for r, m in zip(reduced, RASI_MULTIPLIERS, strict=True))
    graha = sum(GRAHA_MULTIPLIERS[b] * reduced[signs[b]] for b in SEVEN)
    return Pindas(reduced, rasi, graha)


def kakshya(longitude: float) -> tuple[int, int, str]:
    """(sign, kakshya index 0-7, kakshya lord) of a sidereal longitude."""
    sign = int(longitude // 30.0) % 12
    index = min(int((longitude % 30.0) / KAKSHYA_SPAN), 7)
    return sign, index, KAKSHYA_LORDS[index]


def kakshya_bindu(av: Ashtakavarga, planet: Body, transit_longitude: float) -> bool:
    """Whether ``planet`` transiting ``transit_longitude`` sits in a kakshya whose lord
    gave it a bindu in that sign."""
    sign, _, lord = kakshya(transit_longitude)
    return av.prastara[planet.value][lord][sign] == 1
