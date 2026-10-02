"""Ashtakavarga: totals, reductions, pindas and kakshyas.

The worked example is Chart 7 (exercise 22) of P.V.R. Narasimha Rao, *Vedic
Astrology: An Integrated Approach*: the book's BAVs, SAV and pindas are
reproduced exactly.
"""

from __future__ import annotations

import random

import pytest

from jyotish_engine.astro.bodies import Body
from jyotish_engine.strength.ashtakavarga import (
    LAGNA,
    SEVEN,
    MoonTable,
    ashtakavarga,
    ekadhipatya_shodhana,
    kakshya,
    kakshya_bindu,
    pindas,
    trikona_shodhana,
)

TOTALS = {
    "sun": 48,
    "moon": 49,
    "mars": 39,
    "mercury": 54,
    "jupiter": 56,
    "venus": 52,
    "saturn": 39,
    LAGNA: 49,
}

# Chart 7: Saturn, Moon, Rahu in Aries; Ketu, Jupiter in Libra; lagna in Scorpio;
# Mercury, Mars in Sagittarius; Sun in Capricorn; Venus in Aquarius.
CHART_7 = {
    Body.SUN: 9,
    Body.MOON: 0,
    Body.MARS: 8,
    Body.MERCURY: 8,
    Body.JUPITER: 6,
    Body.VENUS: 10,
    Body.SATURN: 0,
    Body.RAHU: 0,
    Body.KETU: 6,
}
CHART_7_LAGNA = 7
BOOK_BAV = {
    "sun": (4, 2, 3, 4, 6, 5, 5, 3, 2, 6, 6, 2),
    "moon": (6, 3, 5, 3, 5, 5, 6, 3, 3, 4, 4, 2),
    "mars": (3, 2, 3, 4, 2, 5, 4, 3, 3, 4, 3, 3),
    "mercury": (4, 6, 4, 3, 4, 7, 4, 5, 6, 3, 5, 3),
    "jupiter": (4, 4, 3, 5, 6, 5, 6, 4, 6, 4, 3, 6),
    "venus": (3, 5, 5, 4, 6, 2, 3, 6, 5, 2, 7, 4),
    "saturn": (3, 2, 2, 3, 5, 6, 3, 4, 1, 3, 6, 1),
}
BOOK_SAV = (27, 24, 25, 26, 34, 35, 31, 28, 26, 26, 34, 21)
BOOK_RASI_PINDA = (152, 85, 52, 95, 68, 154, 162)
BOOK_GRAHA_PINDA = (81, 55, 43, 33, 56, 54, 63)
BOOK_SHODHYA_PINDA = (233, 140, 95, 128, 124, 208, 225)


@pytest.mark.parametrize("moon", list(MoonTable))
def test_totals_do_not_depend_on_positions(moon: MoonTable) -> None:
    rng = random.Random(7)
    for _ in range(20):
        signs = {body: rng.randrange(12) for body in SEVEN}
        av = ashtakavarga(rng.randrange(12), signs, moon)
        assert {name: sum(values) for name, values in av.bav.items()} == TOTALS
        assert sum(av.sav) == 337
        for name, grid in av.prastara.items():
            summed = [sum(row[s] for row in grid.values()) for s in range(12)]
            assert tuple(summed) == av.bav[name]


def test_book_chart_7_bav_and_sav() -> None:
    av = ashtakavarga(CHART_7_LAGNA, CHART_7)
    for name, expected in BOOK_BAV.items():
        assert av.bav[name] == expected, name
    assert av.sav == BOOK_SAV


def test_book_chart_7_pindas() -> None:
    av = ashtakavarga(CHART_7_LAGNA, CHART_7)
    occupied = set(CHART_7.values()) | {CHART_7_LAGNA}
    results = [pindas(av.bav[b.value], CHART_7, occupied) for b in SEVEN]
    assert tuple(r.rasi_pinda for r in results) == BOOK_RASI_PINDA
    assert tuple(r.graha_pinda for r in results) == BOOK_GRAHA_PINDA
    assert tuple(r.shodhya_pinda for r in results) == BOOK_SHODHYA_PINDA


def test_trikona_shodhana_rules() -> None:
    # Aries/Leo/Sagittarius hold 4, 6, 6: subtract 4. Taurus/Virgo/Capricorn equal: zero.
    # Gemini/Libra/Aquarius contain a zero: unchanged.
    before = (4, 3, 0, 5, 6, 3, 2, 1, 6, 3, 5, 2)
    after = trikona_shodhana(before)
    assert (after[0], after[4], after[8]) == (0, 2, 2)
    assert (after[1], after[5], after[9]) == (0, 0, 0)
    assert (after[2], after[6], after[10]) == (0, 2, 5)
    assert (after[3], after[7], after[11]) == (4, 0, 1)


def test_ekadhipatya_shodhana_rules() -> None:
    base = [1] * 12
    # Mars's signs Aries (0) and Scorpio (7), both empty and unequal: both take 2.
    values = base.copy()
    values[0], values[7] = 5, 2
    assert ekadhipatya_shodhana(tuple(values), set())[0:8:7] == (2, 2)
    # Both empty and equal: both zero.
    values[0], values[7] = 3, 3
    assert ekadhipatya_shodhana(tuple(values), set())[0:8:7] == (0, 0)
    # Aries occupied, Scorpio empty with no more bindus: Scorpio becomes zero.
    values[0], values[7] = 4, 4
    assert ekadhipatya_shodhana(tuple(values), {0})[0:8:7] == (4, 0)
    # Scorpio empty with more bindus: it takes Aries's value.
    values[0], values[7] = 2, 5
    assert ekadhipatya_shodhana(tuple(values), {0})[0:8:7] == (2, 2)
    # Both occupied: unchanged.
    assert ekadhipatya_shodhana(tuple(values), {0, 7})[0:8:7] == (2, 5)


def test_alternative_moon_table_moves_three_places() -> None:
    pvr = ashtakavarga(CHART_7_LAGNA, CHART_7, MoonTable.PVR)
    alternative = ashtakavarga(CHART_7_LAGNA, CHART_7, MoonTable.ALTERNATIVE)
    assert pvr.bav["moon"] != alternative.bav["moon"]
    assert sum(alternative.bav["moon"]) == 49
    for body in SEVEN[2:]:
        assert pvr.bav[body.value] == alternative.bav[body.value]


def test_kakshyas() -> None:
    assert kakshya(3.0) == (0, 0, "saturn")
    assert kakshya(33.75 + 0.1) == (1, 1, "jupiter")
    assert kakshya(59.99) == (1, 7, LAGNA)
    av = ashtakavarga(CHART_7_LAGNA, CHART_7)
    for longitude in (1.0, 100.0, 215.5, 359.0):
        sign, _, lord = kakshya(longitude)
        assert kakshya_bindu(av, Body.SATURN, longitude) == bool(av.prastara["saturn"][lord][sign])
