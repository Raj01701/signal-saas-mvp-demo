"""Shadbala versus the worked examples of B.V. Raman and V.P. Jain.

The engine computes its own positions (Raman's within 3.5 arcminutes of the
book's; Jain's about 17 arcminutes lower, so that example is checked more
loosely). Every component is compared; the known differences are listed and
explained, and each must stay as small as described:

* Raman, Mars dig bala: the book leaves the arc unfolded past 180 degrees and
  exceeds the 60-virupa maximum (64.30); the rule gives 55.45.
* Mercury cheshta bala (both books): the books' mean longitudes come from epoch
  tables, the engine's from modern mean elements (about 4 virupas apart).
* Jain, Sun and Mercury saptavargaja: the book gives moolatrikona value to the
  whole moolatrikona sign; BPHS limits it to the moolatrikona degrees.
* Jain, Mercury and Jupiter yuddha bala: they are 8 arcminutes apart, a planetary
  war by BPHS, which the book does not apply.
"""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache

import pytest

from jyotish_engine.astro.ayanamsa import Ayanamsa
from jyotish_engine.astro.bodies import Body
from jyotish_engine.chart import compute_chart
from jyotish_engine.models import BirthInput, PlaceInput
from jyotish_engine.place.timezone import TimeStandard
from jyotish_engine.settings import Settings
from jyotish_engine.strength.shadbala import (
    SEVEN,
    PlanetShadbala,
    ahargana,
    compute_shadbala,
    drishti_value,
    kranti,
    uchcha_bala,
    year_and_month_lords,
)

S, MO, MA, ME, JU, VE, SA = SEVEN

RAMAN = {
    "uchcha": (3.0, 32.75, 37.06, 54.5, 56.33, 1.95, 34.80),  # book sthana implies 34.80
    "saptavargaja": (90, 48.75, 90, 135, 71.25, 116.25, 97.5),
    "ojayugma": (30, 15, 15, 30, 15, 30, 15),
    "kendradi": (60, 30, 30, 60, 15, 15, 30),
    "drekkana": (15, 0, 0, 0, 0, 15, 0),
    "dig": (48.10, 31.56, 64.30, 21.09, 11.50, 15.15, 58.02),
    "nathonnata": (48.32, 11.68, 11.68, 60, 48.32, 48.32, 11.68),
    "paksha": (16.54, 86.92, 16.54, 16.54, 43.46, 43.46, 16.54),
    "tribhaga": (0, 0, 0, 0, 60, 0, 60),
    "abda": (0, 0, 0, 0, 0, 0, 15),
    "masa": (0, 0, 0, 30, 0, 0, 0),
    "vara": (0, 0, 0, 45, 0, 0, 0),
    "hora": (0, 60, 0, 0, 0, 0, 0),
    "ayana": (38.12, 43.44, 1.84, 41.25, 59.4, 23.75, 13.75),
    "cheshta": (0, 0, 22.23, 2.3, 35.26, 5.95, 21.14),
    "drik": (15.86, -21.73, 0.95, 15.64, -16.04, 18.47, 7.21),
}
RAMAN_TOTAL = (424.24, 389.80, 306.20, 537.02, 433.71, 376.15, 389.21)
RAMAN_EXCEPTIONS = {("dig", MA): 9.0, ("cheshta", ME): 4.5}

JAIN = {
    "uchcha": (14.54, 32.17, 4.94, 58.16, 34.85, 3.09, 48.81),
    "saptavargaja": (127.5, 30, 135, 120, 58.13, 150, 82.5),
    "ojayugma": (15, 0, 15, 0, 0, 15, 0),
    "dig": (6.59, 12.22, 20.99, 31.97, 31.99, 53.29, 26.67),
    "nathonnata": (6.1, 53.9, 53.9, 60.0, 6.1, 6.1, 53.9),
    "paksha": (5.62, 108.76, 5.62, 54.38, 54.38, 54.38, 5.62),
    "tribhaga": (0, 0, 0, 0, 60, 60, 0),
    "abda": (0, 0, 15, 0, 0, 0, 0),
    "masa": (0, 0, 30, 0, 0, 0, 0),
    "vara": (0, 0, 0, 0, 0, 0, 45),
    "hora": (0, 0, 0, 60, 0, 0, 0),
    "ayana": (70.08, 43.19, 53.56, 37.10, 22.94, 15.41, 35.04),
    "cheshta": (0, 0, 20.93, 28.76, 8.43, 28.18, 5.05),
    "drik": (11.24, -0.32, -5.10, 4.29, 4.32, -2.86, 5.82),
}
JAIN_EXCEPTIONS = {
    ("saptavargaja", S): 15.0,
    ("saptavargaja", ME): 15.0,
    ("yuddha", ME): 2.0,
    ("yuddha", JU): 2.0,
    ("cheshta", ME): 4.5,
    ("cheshta", VE): 1.5,
}


@lru_cache(maxsize=2)
def _book_chart(name: str) -> dict[Body, PlanetShadbala]:
    if name == "raman":
        moment, lat, lon, ayanamsa = (
            datetime(1918, 10, 16, 14, 22, 16),
            13.0,
            77 + 35 / 60,
            (Ayanamsa.RAMAN),
        )
    else:
        moment, lat, lon, ayanamsa = (
            datetime(1981, 9, 13, 1, 30),
            28 + 39 / 60,
            77 + 13 / 60,
            (Ayanamsa.LAHIRI),
        )
    birth = BirthInput(
        local_datetime=moment,
        place=PlaceInput(latitude=lat, longitude=lon),
        time_standard=TimeStandard.FIXED_OFFSET,
        utc_offset_seconds=19800,
    )
    return compute_shadbala(compute_chart(birth, Settings(ayanamsa=ayanamsa)))


def _compare(
    name: str,
    book: dict[str, tuple[float, ...]],
    exceptions: dict[tuple[str, Body], float],
    tolerance: float,
) -> None:
    ours = _book_chart(name)
    for component, values in book.items():
        for body, expected in zip(SEVEN, values, strict=True):
            limit = exceptions.get((component, body), tolerance)
            actual = getattr(ours[body], component)
            assert abs(actual - expected) <= limit, (name, component, body, actual, expected)
    for (component, body), limit in exceptions.items():
        if component == "yuddha":
            assert abs(getattr(ours[body], component)) <= limit


def test_raman_components() -> None:
    _compare("raman", RAMAN, RAMAN_EXCEPTIONS, tolerance=1.0)


def test_raman_totals_within_one_percent() -> None:
    ours = _book_chart("raman")
    for body, expected in zip(SEVEN, RAMAN_TOTAL, strict=True):
        allowance = 9.0 if body is MA else 4.5 if body is ME else 0.0
        assert abs(ours[body].total - expected) <= 0.01 * expected + allowance, body


def test_jain_components() -> None:
    _compare("jain", JAIN, JAIN_EXCEPTIONS, tolerance=1.0)


def test_kranti_and_uchcha_basics() -> None:
    assert kranti(90.0) == pytest.approx(24.0)
    assert kranti(0.0) == pytest.approx(0.0)
    assert uchcha_bala(Body.SUN, 10.0) == pytest.approx(60.0)
    assert uchcha_bala(Body.SUN, 190.0) == pytest.approx(0.0)


def test_year_and_month_lords_from_the_kali_epoch() -> None:
    # 16 October 1918 (a Wednesday): Raman's year lord Saturn, month lord Mercury.
    days = ahargana(2421882.5)
    assert (days + 4) % 7 == 3  # weekday of the day itself: Wednesday
    assert year_and_month_lords(days) == (Body.SATURN, Body.MERCURY)


def test_drishti_values() -> None:
    assert drishti_value(Body.SUN, 180.0) == pytest.approx(60.0)
    assert drishti_value(Body.SUN, 20.0) == 0.0
    assert drishti_value(Body.MARS, 90.0) == pytest.approx(60.0)  # 4th aspect full
    assert drishti_value(Body.JUPITER, 120.0) == pytest.approx(60.0)  # 5th aspect full
    assert drishti_value(Body.SATURN, 270.0) == pytest.approx(60.0)  # 10th aspect full
    assert drishti_value(Body.VENUS, 90.0) == pytest.approx(45.0)
