"""The lunisolar calendar: lunar months, era years, samvatsara, ritu and ayana, and the
Tamil solar month and day.

**Lunar months.** An amanta month runs from one new moon to the next. It is named
after the sign the Sun enters during it: entering Mesha names Chaitra, entering
Vrishabha names Vaishakha, and so on. Equivalently, the name is one past the Sun's
sign at the opening new moon, which is how the modern (drik) almanacs compute it.

* A month in which the Sun enters no sign is *adhika* (intercalary). It takes the
  name of the month that follows, which is then *nija*.
* A month in which the Sun enters two signs is *kshaya*. It carries both names, and
  the second name has no month of its own that year. Kshaya months occur only near
  perihelion, and rarely.

In the purnimanta reckoning of North India, the dark half of each month belongs to
the next month. The bright half of amanta Chaitra is also the bright half of
purnimanta Chaitra, but its dark half is the dark half of purnimanta Vaishakha. An
adhika month keeps both halves.

**Years.** The Kali, Shaka and Vikram (Chaitradi) years are elapsed years. They turn
at the start of Chaitra, or of adhika Chaitra when there is one. The Gujarati Vikram
year (Kartikadi) turns at the start of Kartika. The samvatsara is the 60-year cycle
counted continuously with the Shaka year, as in the Ugadi almanacs of the Deccan and
the south: (Shaka + 11) mod 60, with 0 for Prabhava. North Indian almanacs instead
name the year from Jupiter's mean motion, which drops one name about every 85
years; that count is not computed yet.

**Tamil solar calendar.** The month is the Sun's sidereal sign (Mesha gives
Chittirai). A sankranti before sunset makes that civil day the first of the new
month; a later one makes the next day the first.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

import numpy as np

from jyotish_engine.astro.bodies import Body
from jyotish_engine.astro.riseset import SunriseDefinition, next_sunset
from jyotish_engine.astro.series import FloatArray, jd_tt_to_ut, jd_ut_to_tt, sidereal_longitudes
from jyotish_engine.astro.time import Instant, jd_to_datetime
from jyotish_engine.settings import Settings
from jyotish_engine.transit.search import elongation_crossings

MASAS = (
    "Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana", "Bhadrapada",
    "Ashvina", "Kartika", "Margashirsha", "Pausha", "Magha", "Phalguna",
)  # fmt: skip
RITUS = ("Vasanta", "Grishma", "Varsha", "Sharad", "Hemanta", "Shishira")
SAMVATSARAS = (
    "Prabhava", "Vibhava", "Shukla", "Pramoda", "Prajapati", "Angirasa", "Shrimukha",
    "Bhava", "Yuva", "Dhatri", "Ishvara", "Bahudhanya", "Pramathi", "Vikrama", "Vrisha",
    "Chitrabhanu", "Svabhanu", "Tarana", "Parthiva", "Vyaya", "Sarvajit", "Sarvadhari",
    "Virodhi", "Vikriti", "Khara", "Nandana", "Vijaya", "Jaya", "Manmatha", "Durmukhi",
    "Hevilambi", "Vilambi", "Vikari", "Sharvari", "Plava", "Shubhakrit", "Shobhakrit",
    "Krodhi", "Vishvavasu", "Parabhava", "Plavanga", "Kilaka", "Saumya", "Sadharana",
    "Virodhikrit", "Paridhavi", "Pramadi", "Ananda", "Rakshasa", "Nala", "Pingala",
    "Kalayukta", "Siddharthi", "Raudra", "Durmati", "Dundubhi", "Rudhirodgari",
    "Raktakshi", "Krodhana", "Akshaya",
)  # fmt: skip
TAMIL_MONTHS = (
    "Chittirai", "Vaikasi", "Ani", "Adi", "Avani", "Purattasi",
    "Aippasi", "Karthigai", "Margazhi", "Thai", "Masi", "Panguni",
)  # fmt: skip

KARTIKA = 7
#: Elapsed years: Kali = Shaka + 3179, Vikram = Shaka + 135, Shaka = Gregorian - 78
#: from the start of Chaitra to the end of December.
KALI_MINUS_SHAKA = 3179
VIKRAM_MINUS_SHAKA = 135
GREGORIAN_MINUS_SHAKA = 78
#: Samvatsara index = (Shaka + 11) mod 60; Shaka 1909 (1987-88) was Prabhava.
SAMVATSARA_SHIFT = 11

#: Mean motions, used only to seed the solver (days; degrees per day).
SYNODIC_MONTH = 29.530588853
MEAN_ELONGATION_RATE = 360.0 / SYNODIC_MONTH
MEAN_SOLAR_RATE = 0.9856
_RATE_STEP_DAYS = 1e-3
_NEWTON_ITERATIONS = 12


@dataclass(frozen=True, slots=True)
class LunarMonth:
    """An amanta month, from the new moon at ``start_jd_ut`` to the one at ``end_jd_ut``."""

    #: 0 = Chaitra ... 11 = Phalguna.
    index: int
    start_jd_ut: float
    end_jd_ut: float
    adhika: bool = False
    #: The regular month that follows an adhika month of the same name.
    nija: bool = False
    #: For a kshaya month: the second month whose sankranti also falls within it.
    kshaya_index: int | None = None

    @property
    def name(self) -> str:
        return MASAS[self.index]

    @property
    def kshaya(self) -> bool:
        return self.kshaya_index is not None


@dataclass(frozen=True, slots=True)
class LunarYear:
    """Elapsed era years, and the samvatsara, of a lunar month."""

    kali: int
    shaka: int
    #: Chaitradi Vikram year (North India), turning with the Shaka year.
    vikram: int
    #: Kartikadi Vikram year (Gujarat), one less from Chaitra to Ashvina.
    vikram_kartikadi: int
    #: 0 = Prabhava ... 59 = Akshaya.
    samvatsara: int

    @property
    def samvatsara_name(self) -> str:
        return SAMVATSARAS[self.samvatsara]


@dataclass(frozen=True, slots=True)
class SolarDate:
    """A date of the Tamil solar calendar."""

    #: 0 = Chittirai (the Sun in Mesha) ... 11 = Panguni.
    month: int
    #: 1-based day of the month.
    day: int
    #: The sankranti that began the month.
    sankranti_jd_ut: float
    #: Gregorian year in which the solar year began (at Chittirai 1).
    year: int

    @property
    def month_name(self) -> str:
        return TAMIL_MONTHS[self.month]

    @property
    def samvatsara(self) -> int:
        return (self.year - GREGORIAN_MINUS_SHAKA + SAMVATSARA_SHIFT) % 60


def _longitudes(body: Body, jd_tt: FloatArray, settings: Settings) -> FloatArray:
    return sidereal_longitudes(
        body,
        jd_tt,
        ayanamsa=settings.ayanamsa,
        user_ayanamsa_j2000=settings.user_ayanamsa_j2000,
        position_type=settings.position_type,
        node_type=settings.node_type,
    )


def _elongation(jd_tt: FloatArray, settings: Settings) -> FloatArray:
    moon = _longitudes(Body.MOON, jd_tt, settings)
    return (moon - _longitudes(Body.SUN, jd_tt, settings)) % 360.0


def _solve(
    angle: Callable[[FloatArray], FloatArray], target: float, guesses_tt: FloatArray
) -> FloatArray:
    """Times (TT) near ``guesses_tt`` at which a steadily increasing angle equals
    ``target`` degrees, by Newton's method with a numerical rate (to about 1 ms)."""
    t = np.asarray(guesses_tt, dtype=np.float64)
    for _ in range(_NEWTON_ITERATIONS):
        values = angle(np.concatenate([t, t + _RATE_STEP_DAYS]))
        now, later = values[: t.size], values[t.size :]
        offset = (now - target + 180.0) % 360.0 - 180.0
        rate = ((later - now + 180.0) % 360.0 - 180.0) / _RATE_STEP_DAYS
        step = offset / rate
        t = t - step
        if float(np.max(np.abs(step))) < 1e-8:
            return t
    raise RuntimeError("no convergence")


def _sign(longitude: float) -> int:
    return min(int(longitude // 30.0), 11)


def new_moons(
    start_jd_ut: float, end_jd_ut: float, settings: Settings | None = None
) -> list[float]:
    """Every new moon (Moon and Sun at the same longitude) in the interval, UT."""
    return elongation_crossings(0.0, start_jd_ut, end_jd_ut, settings)


def _new_moons_around(jd_ut: float, settings: Settings) -> tuple[list[float], list[int]]:
    """Five consecutive new moons (UT), at least two of them before ``jd_ut`` and two
    after, with the Sun's sign at each. The solver starts from mean new moons around
    the last one, which it reaches from well within a day."""
    jd_tt = jd_ut_to_tt([jd_ut])
    since = float(_elongation(jd_tt, settings)[0]) / MEAN_ELONGATION_RATE
    guesses = jd_tt[0] - since + SYNODIC_MONTH * np.arange(-2.0, 3.0)
    times_tt = _solve(lambda t: _elongation(t, settings), 0.0, guesses)
    signs = [_sign(value) for value in _longitudes(Body.SUN, times_tt, settings)]
    return [float(t) for t in jd_tt_to_ut(times_tt)], signs


def lunar_month(jd_ut: float, settings: Settings | None = None) -> LunarMonth:
    """The amanta month in progress at ``jd_ut``. For a civil day, pass its sunrise."""
    settings = settings or Settings()
    moons, signs = _new_moons_around(jd_ut, settings)
    current = max(i for i, t in enumerate(moons) if t <= jd_ut)
    before, first, last = signs[current - 1], signs[current], signs[current + 1]
    index = (first + 1) % 12
    signs_entered = (last - first) % 12
    return LunarMonth(
        index=index,
        start_jd_ut=moons[current],
        end_jd_ut=moons[current + 1],
        adhika=signs_entered == 0,
        nija=signs_entered != 0 and before == first,
        kshaya_index=(index + 1) % 12 if signs_entered == 2 else None,
    )


def lunar_year(month: LunarMonth) -> LunarYear:
    """Era years of an amanta month.

    The year is the solar year of the latest Mesha sankranti before the month opens,
    except for Chaitra, which opens before the Mesha sankranti that starts its year.
    Mesha sankranti falls in April throughout the supported ephemeris range, so the
    Gregorian month of the opening new moon settles which sankranti came last.
    """
    opening = jd_to_datetime(month.start_jd_ut)
    year = opening.year if month.index == 0 or opening.month >= 4 else opening.year - 1
    shaka = year - GREGORIAN_MINUS_SHAKA
    vikram = shaka + VIKRAM_MINUS_SHAKA
    return LunarYear(
        kali=shaka + KALI_MINUS_SHAKA,
        shaka=shaka,
        vikram=vikram,
        vikram_kartikadi=vikram if month.index >= KARTIKA else vikram - 1,
        samvatsara=(shaka + SAMVATSARA_SHIFT) % 60,
    )


def purnimanta_month(month: LunarMonth, tithi_index: int) -> tuple[int, bool]:
    """Purnimanta month index, and whether it is adhika, for a tithi (0-29) of ``month``."""
    if month.adhika or tithi_index < 15:
        return month.index, month.adhika
    return (month.index + 1) % 12, False


def ritu(month: LunarMonth) -> int:
    """Season by lunar month: 0 = Vasanta (Chaitra and Vaishakha) ... 5 = Shishira."""
    return month.index // 2


def ayana(sun_longitude: float) -> str:
    """Uttarayana while the Sun goes from 270 to 90 degrees, else dakshinayana.

    With the tropical longitude this is the solstice definition; with the sidereal
    one it runs from Makara sankranti to Karka sankranti.
    """
    northward = sun_longitude % 360.0 >= 270.0 or sun_longitude % 360.0 < 90.0
    return "uttarayana" if northward else "dakshinayana"


def tamil_solar_date(
    civil_date: date,
    sunset_jd_ut: float,
    latitude: float,
    longitude: float,
    elevation_m: float = 0.0,
    rule: SunriseDefinition = SunriseDefinition.HINDU,
    settings: Settings | None = None,
) -> SolarDate:
    """Tamil solar month and day of ``civil_date``, whose sunset is ``sunset_jd_ut``."""
    sankranti, month = last_sankranti(sunset_jd_ut, settings)
    first = next_sunset(Instant.from_jd_ut(sankranti), latitude, longitude, elevation_m, rule)
    if first is None:
        raise ValueError("the Sun does not set here (polar day)")
    # Chittirai begins in April throughout the supported ephemeris range.
    new_year = civil_date.month > 4 or (civil_date.month == 4 and month == 0)
    return SolarDate(
        month=month,
        day=round(sunset_jd_ut - first.jd_ut) + 1,
        sankranti_jd_ut=sankranti,
        year=civil_date.year if new_year else civil_date.year - 1,
    )


def last_sankranti(jd_ut: float, settings: Settings | None = None) -> tuple[float, int]:
    """The latest time (UT) at or before ``jd_ut`` that the Sun entered a sidereal
    sign, and that sign (0 = Mesha)."""
    settings = settings or Settings()
    jd_tt = jd_ut_to_tt([jd_ut])
    longitude = float(_longitudes(Body.SUN, jd_tt, settings)[0])
    sign = _sign(longitude)
    guess = jd_tt - (longitude - 30.0 * sign) / MEAN_SOLAR_RATE
    solved = _solve(lambda t: _longitudes(Body.SUN, t, settings), 30.0 * sign, guess)
    return float(jd_tt_to_ut(solved)[0]), sign
