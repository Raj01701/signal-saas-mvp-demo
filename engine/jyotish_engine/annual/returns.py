"""Annual return moments: Varsha Pravesha (solar return) and Tithi Pravesha.

* **Varsha Pravesha** is the moment the Sun returns to its sidereal longitude at
  birth; ``years_completed`` = 0 is the birth itself.
* **Tithi Pravesha** is the moment the Moon's elongation from the Sun (the tithi
  angle) returns to its value at birth while the Sun is in its birth sign. Should
  it recur twice in that solar month, the first is taken; should the month pass
  without it (rare, as a solar month can be shorter than a lunar one), the
  occurrence nearest the solar return is used.

Both use the chart settings (ayanamsa, apparent or true positions).
"""

from __future__ import annotations

from jyotish_engine.astro.bodies import Body
from jyotish_engine.settings import Settings
from jyotish_engine.transit.search import elongation_crossings, longitude_crossings
from jyotish_engine.transit.timeline import sign_timeline

#: Mean sidereal year, used only to place the search windows.
_YEAR = 365.256363


def varsha_pravesha(
    birth_jd_ut: float,
    natal_sun: float,
    years_completed: int,
    settings: Settings | None = None,
) -> float:
    """Julian day (UT) at which the year ``years_completed`` + 1 of life begins."""
    if years_completed == 0:
        return birth_jd_ut
    guess = birth_jd_ut + years_completed * _YEAR
    crossings = longitude_crossings(Body.SUN, natal_sun, guess - 4.0, guess + 4.0, settings)
    return min(crossings, key=lambda c: abs(c.jd_ut - guess)).jd_ut


def tithi_pravesha(
    birth_jd_ut: float,
    natal_sun: float,
    natal_moon: float,
    years_completed: int,
    settings: Settings | None = None,
) -> float:
    """Julian day (UT) of the Tithi Pravesha for the given year of life."""
    target = (natal_moon - natal_sun) % 360.0
    solar_return = varsha_pravesha(birth_jd_ut, natal_sun, years_completed, settings)
    sign = int(natal_sun // 30.0) % 12
    stay = next(
        s
        for s in sign_timeline(Body.SUN, solar_return - 35.0, solar_return + 35.0, settings)
        if s.sign == sign and s.start_jd_ut <= solar_return <= s.end_jd_ut
    )
    found = elongation_crossings(target, stay.start_jd_ut, stay.end_jd_ut, settings)
    if found:
        return found[0]
    nearby = elongation_crossings(target, solar_return - 20.0, solar_return + 20.0, settings)
    return min(nearby, key=lambda jd: abs(jd - solar_return))
