"""Periods of the day used to choose or avoid times.

All are fractions of the actual day (sunrise to sunset) or night (sunset to the
next sunrise), so they follow the season and the place.

* **Rahu kalam, Yamaganda and Gulika kalam**: one of the eight equal parts of the
  day, by weekday (the standard tables; Sunday first).
* **Muhurtas**: day and night each have fifteen. **Abhijit** is the 8th muhurta of
  the day, around local noon. **Brahma muhurta** is the 14th muhurta of the night,
  ending one muhurta before sunrise.
* **Durmuhurtas**, by weekday, after Karanam Ramakumar's *Panchangam Calculations*:
  Sunday the 14th day muhurta; Monday the 9th and 12th; Tuesday the 4th, and the
  7th of the night; Wednesday the 8th; Thursday the 6th and 12th; Friday the 4th
  and 9th; Saturday the 3rd.
* **Horas**: twelve unequal planetary hours by day and twelve by night. The first
  belongs to the lord of the weekday, and the lords follow the hora order Sun,
  Venus, Mercury, Moon, Saturn, Jupiter, Mars.
* **Choghadiyas**: eight parts of the day and eight of the night. The day starts
  with the weekday lord's choghadiya and the night with that of the lord of the
  fifth weekday from it; both then follow the hora order. Amrit, Shubh and Labh are
  good, Chal neutral, and Udveg, Rog and Kaal to be avoided.
"""

from __future__ import annotations

from dataclasses import dataclass

from jyotish_engine.astro.bodies import Body
from jyotish_engine.panchanga.elements import VARA_LORDS

#: Which eighth of the day (0-based), Sunday first.
RAHU_PART = (7, 1, 6, 4, 5, 3, 2)
YAMAGANDA_PART = (4, 3, 2, 1, 0, 6, 5)
GULIKA_PART = (6, 5, 4, 3, 2, 1, 0)
#: Durmuhurtas by weekday: (day or night, 1-based muhurta).
DURMUHURTAS: tuple[tuple[tuple[str, int], ...], ...] = (
    (("day", 14),),
    (("day", 9), ("day", 12)),
    (("day", 4), ("night", 7)),
    (("day", 8),),
    (("day", 6), ("day", 12)),
    (("day", 4), ("day", 9)),
    (("day", 3),),
)
HORA_ORDER = (Body.SUN, Body.VENUS, Body.MERCURY, Body.MOON, Body.SATURN, Body.JUPITER, Body.MARS)
CHOGHADIYA = {
    Body.SUN: ("Udveg", "bad"),
    Body.MOON: ("Amrit", "good"),
    Body.MARS: ("Rog", "bad"),
    Body.MERCURY: ("Labh", "good"),
    Body.JUPITER: ("Shubh", "good"),
    Body.VENUS: ("Chal", "neutral"),
    Body.SATURN: ("Kaal", "bad"),
}


@dataclass(frozen=True, slots=True)
class Period:
    name: str
    start_jd_ut: float
    end_jd_ut: float
    lord: Body | None = None
    quality: str | None = None


def _part(name: str, start: float, end: float, parts: int, index: int) -> Period:
    length = (end - start) / parts
    return Period(name, start + index * length, start + (index + 1) * length)


def kalams(sunrise: float, sunset: float, weekday: int) -> list[Period]:
    """Rahu kalam, Yamaganda and Gulika kalam (``weekday`` 0 = Sunday)."""
    return [
        _part("Rahu kalam", sunrise, sunset, 8, RAHU_PART[weekday]),
        _part("Yamaganda", sunrise, sunset, 8, YAMAGANDA_PART[weekday]),
        _part("Gulika kalam", sunrise, sunset, 8, GULIKA_PART[weekday]),
    ]


def abhijit(sunrise: float, sunset: float) -> Period:
    return _part("Abhijit muhurta", sunrise, sunset, 15, 7)


def brahma_muhurta(previous_sunset: float, sunrise: float) -> Period:
    return _part("Brahma muhurta", previous_sunset, sunrise, 15, 13)


def durmuhurtas(sunrise: float, sunset: float, next_sunrise: float, weekday: int) -> list[Period]:
    periods = []
    for part, number in DURMUHURTAS[weekday]:
        start, end = (sunrise, sunset) if part == "day" else (sunset, next_sunrise)
        periods.append(_part("Durmuhurta", start, end, 15, number - 1))
    return periods


def _lords_from(first: Body, count: int) -> list[Body]:
    offset = HORA_ORDER.index(first)
    return [HORA_ORDER[(offset + i) % 7] for i in range(count)]


def horas(sunrise: float, sunset: float, next_sunrise: float, weekday: int) -> list[Period]:
    """The 24 planetary hours from sunrise to the next sunrise."""
    lords = _lords_from(VARA_LORDS[weekday], 24)
    periods = []
    for i, lord in enumerate(lords):
        start, end, index = (sunrise, sunset, i) if i < 12 else (sunset, next_sunrise, i - 12)
        part = _part(f"Hora of {lord.value.title()}", start, end, 12, index)
        periods.append(Period(part.name, part.start_jd_ut, part.end_jd_ut, lord))
    return periods


def choghadiyas(sunrise: float, sunset: float, next_sunrise: float, weekday: int) -> list[Period]:
    """Eight choghadiyas of the day, then eight of the night."""
    periods = []
    for start, end, first in (
        (sunrise, sunset, VARA_LORDS[weekday]),
        (sunset, next_sunrise, VARA_LORDS[(weekday + 4) % 7]),
    ):
        for i, lord in enumerate(_lords_from(first, 8)):
            name, quality = CHOGHADIYA[lord]
            part = _part(name, start, end, 8, i)
            periods.append(Period(name, part.start_jd_ut, part.end_jd_ut, lord, quality))
    return periods
