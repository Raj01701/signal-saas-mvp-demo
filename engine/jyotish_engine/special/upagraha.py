"""Upagrahas (sub-planets).

**Sun-based** (BPHS): Dhuma = Sun + 133 deg 20 min; Vyatipata = 360 - Dhuma;
Parivesha = Vyatipata + 180; Indrachapa = 360 - Parivesha;
Upakethu = Indrachapa + 16 deg 40 min (always Sun - 30 degrees).

**Time-based**: the day (sunrise to sunset) and the night (sunset to next sunrise)
are each split into eight equal parts. Day parts are ruled in weekday order starting
with the weekday's lord; night parts start with the lord five weekdays on. The
eighth part has no lord (this matches the Yamaganda and Gulika kalam timings printed
in panchangs). An upagraha's longitude is the ascendant rising at a set moment of
its ruler's part:

* Kala: Sun's part, middle.
* Mrityu: Mars's part, middle.
* Ardhaprahara: Mercury's part, middle.
* Yamaghantaka: Jupiter's part, middle.
* Gulika: Saturn's part, beginning (the start of Gulika kalam, as most software and
  PyJHora use).
* Mandi: Saturn's part, middle.

P.V.R. Narasimha Rao's book gives Gulika at the middle and Mandi at the beginning;
pass ``positions`` to ``time_based_upagrahas`` to use that convention.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from jyotish_engine.astro.bodies import Body

WEEKDAY_LORDS: tuple[Body, ...] = (
    Body.SUN,
    Body.MOON,
    Body.MARS,
    Body.MERCURY,
    Body.JUPITER,
    Body.VENUS,
    Body.SATURN,
)


class Upagraha(StrEnum):
    DHUMA = "dhuma"
    VYATIPATA = "vyatipata"
    PARIVESHA = "parivesha"
    INDRACHAPA = "indrachapa"
    UPAKETU = "upaketu"
    KALA = "kala"
    MRITYU = "mrityu"
    ARDHAPRAHARA = "ardhaprahara"
    YAMAGHANTAKA = "yamaghantaka"
    GULIKA = "gulika"
    MANDI = "mandi"


TIME_UPAGRAHAS: dict[Upagraha, tuple[Body, float]] = {
    # upagraha: (ruler of its part, position within the part from 0 to 1)
    Upagraha.KALA: (Body.SUN, 0.5),
    Upagraha.MRITYU: (Body.MARS, 0.5),
    Upagraha.ARDHAPRAHARA: (Body.MERCURY, 0.5),
    Upagraha.YAMAGHANTAKA: (Body.JUPITER, 0.5),
    Upagraha.GULIKA: (Body.SATURN, 0.0),
    Upagraha.MANDI: (Body.SATURN, 0.5),
}

#: PVR's book convention: Gulika at the middle and Mandi at the start of Saturn's part.
PVR_BOOK_POSITIONS: dict[Upagraha, float] = {Upagraha.GULIKA: 0.5, Upagraha.MANDI: 0.0}


def sun_based_upagrahas(sun: float) -> dict[Upagraha, float]:
    dhuma = (sun + 133.0 + 20.0 / 60.0) % 360.0
    vyatipata = (360.0 - dhuma) % 360.0
    parivesha = (vyatipata + 180.0) % 360.0
    indrachapa = (360.0 - parivesha) % 360.0
    upaketu = (indrachapa + 16.0 + 40.0 / 60.0) % 360.0
    return {
        Upagraha.DHUMA: dhuma,
        Upagraha.VYATIPATA: vyatipata,
        Upagraha.PARIVESHA: parivesha,
        Upagraha.INDRACHAPA: indrachapa,
        Upagraha.UPAKETU: upaketu,
    }


@dataclass(frozen=True, slots=True)
class DayFrame:
    """Sunrise, sunset and next sunrise (Julian days, UT) around a birth."""

    sunrise: float
    sunset: float
    next_sunrise: float
    weekday: int  # 0 = Sunday, weekday of the sunrise

    def is_day(self, jd_ut: float) -> bool:
        return self.sunrise <= jd_ut < self.sunset


def part_lords(weekday: int, night: bool) -> list[Body | None]:
    """Rulers of the eight parts of the day (or night)."""
    first = (weekday + 4) % 7 if night else weekday
    return [WEEKDAY_LORDS[(first + k) % 7] for k in range(7)] + [None]


def upagraha_time(
    frame: DayFrame,
    jd_ut: float,
    upagraha: Upagraha,
    positions: dict[Upagraha, float] | None = None,
) -> float:
    """The moment (JD UT) whose rising degree gives a time-based upagraha."""
    ruler, position = TIME_UPAGRAHAS[upagraha]
    if positions and upagraha in positions:
        position = positions[upagraha]
    night = not frame.is_day(jd_ut)
    start, end = (frame.sunset, frame.next_sunrise) if night else (frame.sunrise, frame.sunset)
    width = (end - start) / 8.0
    index = part_lords(frame.weekday, night).index(ruler)
    return start + width * (index + position)


def time_based_upagrahas(
    frame: DayFrame,
    jd_ut: float,
    ascendant_at: Callable[[float], float],
    positions: dict[Upagraha, float] | None = None,
) -> dict[Upagraha, float]:
    """Longitudes of the time-based upagrahas; ``ascendant_at`` maps JD UT to a longitude."""
    return {u: ascendant_at(upagraha_time(frame, jd_ut, u, positions)) for u in TIME_UPAGRAHAS}
