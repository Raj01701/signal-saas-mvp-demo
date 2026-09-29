"""The Vedic day: it runs from one sunrise to the next, and its weekday (vara) is
the weekday on which that sunrise falls."""

from __future__ import annotations

from dataclasses import dataclass

from jyotish_engine.astro.riseset import SunriseDefinition, next_sunrise, next_sunset
from jyotish_engine.astro.time import Instant
from jyotish_engine.special.upagraha import DayFrame

_SEARCH_WINDOW = 1.3  # days


@dataclass(frozen=True, slots=True)
class VedicDay:
    sunrise: Instant
    sunset: Instant
    next_sunrise: Instant
    #: 0 = Sunday ... 6 = Saturday, taken from the local date of the sunrise.
    weekday: int

    def is_day(self, instant: Instant) -> bool:
        return self.sunrise.jd_ut <= instant.jd_ut < self.sunset.jd_ut

    def minutes_since_sunrise(self, instant: Instant) -> float:
        return (instant.jd_ut - self.sunrise.jd_ut) * 1440.0

    def frame(self) -> DayFrame:
        return DayFrame(
            sunrise=self.sunrise.jd_ut,
            sunset=self.sunset.jd_ut,
            next_sunrise=self.next_sunrise.jd_ut,
            weekday=self.weekday,
        )


def weekday_of(jd_ut: float, longitude: float) -> int:
    """Weekday (0 = Sunday) of the local mean date at a longitude."""
    local_jd = jd_ut + longitude / 360.0
    return int((int(local_jd + 0.5) + 1) % 7)


def vedic_day(
    instant: Instant,
    latitude: float,
    longitude: float,
    elevation_m: float = 0.0,
    definition: SunriseDefinition = SunriseDefinition.HINDU,
) -> VedicDay | None:
    """The Vedic day containing ``instant``, or ``None`` during polar day or night."""
    args = (latitude, longitude, elevation_m, definition)
    candidate = next_sunrise(
        Instant.from_jd_ut(instant.jd_ut - 1.2), *args, max_days=_SEARCH_WINDOW
    )
    sunrise: Instant | None = None
    while candidate is not None and candidate.jd_ut <= instant.jd_ut:
        sunrise = candidate
        candidate = next_sunrise(
            Instant.from_jd_ut(candidate.jd_ut + 0.01), *args, max_days=_SEARCH_WINDOW
        )
    if sunrise is None or candidate is None:
        return None
    sunset = next_sunset(sunrise, *args, max_days=_SEARCH_WINDOW)
    if sunset is None or sunset.jd_ut > candidate.jd_ut:
        return None
    return VedicDay(
        sunrise=sunrise,
        sunset=sunset,
        next_sunrise=candidate,
        weekday=weekday_of(sunrise.jd_ut, longitude),
    )
