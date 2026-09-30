"""Shadbala: the six-fold strength of the seven planets (BPHS, chapter 27).

Following B.V. Raman, *Graha and Bhava Balas*, whose worked example (the
"standard horoscope" of 16 October 1918) the tests reproduce to within a virupa
or two. Strengths are in virupas (shashtiamsas); 60 virupas make one rupa.

1. **Sthana bala** (positional): uchcha (exaltation), saptavargaja (dignity in D1,
   D2, D3, D7, D9, D12 and D30), ojayugma (odd or even sign in the rasi and
   navamsa), kendradi (angular, succedent or cadent house) and drekkana bala.
2. **Dig bala** (directional): distance from the house where the planet has no
   directional strength (Sun and Mars: 4th; Moon and Venus: 10th; Mercury and
   Jupiter: 7th; Saturn: 1st), measured from that house's cusp (the angles).
3. **Kala bala** (temporal): nathonnata (day or night), paksha (lunar phase),
   tribhaga (third of day or night), the lords of the year, month, weekday and
   hour, ayana (declination) and yuddha (planetary war) bala.
4. **Cheshta bala** (motional), from the cheshta kendra: the difference between
   the planet's seeghrochcha and the mean of its mean and true longitudes. Mean
   longitudes come from modern mean orbital elements (Meeus, *Astronomical
   Algorithms*, ch. 31) rather than the epoch tables of the books, which moves
   results by a fraction of a virupa. The Sun and Moon have none of their own:
   their motion is already counted in ayana and paksha bala.
5. **Naisargika bala** (natural): fixed.
6. **Drik bala** (aspectual): a quarter of the benefic minus the malefic aspect
   strength received, from BPHS's sphuta drishti values with the extra strength of
   Mars's, Jupiter's and Saturn's special aspects.

Where the books' own numbers depart from these rules, the engine keeps the rule:
Raman's example gives Mars a dig bala above the 60-virupa maximum (the arc was not
folded at 180 degrees), and V.P. Jain's example gives the full moolatrikona value
to planets past the moolatrikona degrees of their sign (BPHS gives degree ranges).

Benefics and malefics follow P.V.R. Narasimha Rao: Jupiter and Venus are
benefics, the waxing Moon too, and Mercury when alone or with more benefics than
malefics in its sign; the Sun, Mars, Saturn, the waning Moon and Mercury in worse
company are malefics.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from jyotish_engine.astro.bodies import Body
from jyotish_engine.astro.frames import greenwich_apparent_sidereal_deg, true_obliquity_deg
from jyotish_engine.astro.time import Instant, jd_to_datetime
from jyotish_engine.core.dignity import (
    DIGNITY_RULES,
    Relationship,
    compound_relationship,
    deep_exaltation_longitude,
)
from jyotish_engine.core.dignity import in_moolatrikona as _in_moolatrikona
from jyotish_engine.core.varga import varga_sign
from jyotish_engine.core.zodiac import SIGN_LORDS, Sign
from jyotish_engine.models import ChartResult

SEVEN = (Body.SUN, Body.MOON, Body.MARS, Body.MERCURY, Body.JUPITER, Body.VENUS, Body.SATURN)
NODES = (Body.RAHU, Body.KETU)

SAPTAVARGA = (1, 2, 3, 7, 9, 12, 30)
MOOLATRIKONA_VIRUPAS = 45.0
OWN_VIRUPAS = 30.0
RELATION_VIRUPAS: dict[Relationship, float] = {
    Relationship.GREAT_FRIEND: 22.5,
    Relationship.FRIEND: 15.0,
    Relationship.NEUTRAL: 7.5,
    Relationship.ENEMY: 3.75,
    Relationship.GREAT_ENEMY: 1.875,
}

#: House (1-based) where each planet has no directional strength.
DIG_ZERO_HOUSE: dict[Body, int] = {
    Body.SUN: 4,
    Body.MARS: 4,
    Body.MOON: 10,
    Body.VENUS: 10,
    Body.MERCURY: 7,
    Body.JUPITER: 7,
    Body.SATURN: 1,
}

NAISARGIKA: dict[Body, float] = {
    Body.SUN: 60.0,
    Body.MOON: 360.0 / 7.0,
    Body.VENUS: 300.0 / 7.0,
    Body.JUPITER: 240.0 / 7.0,
    Body.MERCURY: 180.0 / 7.0,
    Body.MARS: 120.0 / 7.0,
    Body.SATURN: 60.0 / 7.0,
}

#: Chaldean order of the planetary hours.
HORA_ORDER = (Body.SUN, Body.VENUS, Body.MERCURY, Body.MOON, Body.SATURN, Body.JUPITER, Body.MARS)
WEEKDAY_LORDS = (
    Body.SUN, Body.MOON, Body.MARS, Body.MERCURY, Body.JUPITER, Body.VENUS, Body.SATURN,
)  # fmt: skip

#: Diameters of the planets' discs used for yuddha bala (BPHS).
DISC_DIAMETER: dict[Body, float] = {
    Body.MARS: 9.4,
    Body.MERCURY: 6.6,
    Body.JUPITER: 190.4,
    Body.VENUS: 16.6,
    Body.SATURN: 158.0,
}

#: Required strength (rupas) for a planet to be called strong (BPHS 27).
REQUIRED_RUPAS: dict[Body, float] = {
    Body.SUN: 6.5,
    Body.MOON: 6.0,
    Body.MARS: 5.0,
    Body.MERCURY: 7.0,
    Body.JUPITER: 6.5,
    Body.VENUS: 5.5,
    Body.SATURN: 5.0,
}


def _sign(longitude: float) -> int:
    return int(longitude // 30.0) % 12


def _arc(a: float, b: float) -> float:
    """Separation of two longitudes, 0 to 180 degrees."""
    return abs((a - b + 180.0) % 360.0 - 180.0)


# --- Sthana bala -------------------------------------------------------------


def uchcha_bala(body: Body, longitude: float) -> float:
    return (180.0 - _arc(longitude, deep_exaltation_longitude(body))) / 3.0


def in_moolatrikona(body: Body, longitude: float) -> bool:
    return _in_moolatrikona(body, Sign(_sign(longitude)), longitude % 30.0)


def saptavargaja_bala(body: Body, sidereal: Mapping[Body, float]) -> float:
    """Dignity in the seven vargas; the compound relationship uses rasi positions."""
    longitude = sidereal[body]
    rasi_signs = {b: _sign(lon) for b, lon in sidereal.items()}
    total = 0.0
    for division in SAPTAVARGA:
        sign = varga_sign(longitude, division)
        if division == 1 and in_moolatrikona(body, longitude):
            total += MOOLATRIKONA_VIRUPAS
        elif sign in DIGNITY_RULES[body].own_signs:
            total += OWN_VIRUPAS
        else:
            lord = SIGN_LORDS[sign]
            relation = compound_relationship(body, lord, rasi_signs[body], rasi_signs[lord])
            total += RELATION_VIRUPAS[relation]
    return total


def ojayugma_bala(body: Body, longitude: float) -> float:
    wants_even = body in (Body.MOON, Body.VENUS)
    total = 0.0
    for sign in (_sign(longitude), varga_sign(longitude, 9)):
        if (sign % 2 == 1) == wants_even:
            total += 15.0
    return total


def kendradi_bala(longitude: float, lagna_sign: int) -> float:
    house = (_sign(longitude) - lagna_sign) % 12
    return 60.0 if house % 3 == 0 else 30.0 if house % 3 == 1 else 15.0


def drekkana_bala(body: Body, longitude: float) -> float:
    part = min(int((longitude % 30.0) // 10.0), 2)
    wanted = {
        Body.SUN: 0, Body.MARS: 0, Body.JUPITER: 0,
        Body.MERCURY: 1, Body.SATURN: 1,
        Body.MOON: 2, Body.VENUS: 2,
    }[body]  # fmt: skip
    return 15.0 if part == wanted else 0.0


# --- Dig bala ----------------------------------------------------------------


def dig_bala(body: Body, longitude: float, ascendant: float, midheaven: float) -> float:
    zero_point = {
        1: ascendant,
        4: (midheaven + 180.0) % 360.0,
        7: (ascendant + 180.0) % 360.0,
        10: midheaven,
    }[DIG_ZERO_HOUSE[body]]
    return _arc(longitude, zero_point) / 3.0


# --- Kala bala ---------------------------------------------------------------


def nathonnata_bala(body: Body, hours_from_midnight: float) -> float:
    """``hours_from_midnight``: 0 at apparent midnight, 12 at apparent noon."""
    day_strength = 5.0 * hours_from_midnight
    if body is Body.MERCURY:
        return 60.0
    if body in (Body.SUN, Body.JUPITER, Body.VENUS):
        return day_strength
    return 60.0 - day_strength


def benefics(sidereal: Mapping[Body, float]) -> set[Body]:
    """Natural benefics of the chart (see the module docstring)."""
    signs = {b: _sign(lon) for b, lon in sidereal.items()}
    waxing = (sidereal[Body.MOON] - sidereal[Body.SUN]) % 360.0 < 180.0
    good = {Body.JUPITER, Body.VENUS} | ({Body.MOON} if waxing else set())
    bad = {Body.SUN, Body.MARS, Body.SATURN, *NODES} | (set() if waxing else {Body.MOON})
    company = [b for b, s in signs.items() if s == signs[Body.MERCURY] and b is not Body.MERCURY]
    if sum(b in good for b in company) >= sum(b in bad for b in company):
        good.add(Body.MERCURY)
    return good


def paksha_bala(body: Body, sidereal: Mapping[Body, float], benefic: set[Body]) -> float:
    """The Moon's is doubled, and taken as a benefic's (strongest at full Moon)."""
    phase = _arc(sidereal[Body.MOON], sidereal[Body.SUN]) / 3.0
    if body is Body.MOON:
        return 2.0 * phase
    return phase if body in benefic else 60.0 - phase


def tribhaga_lord(fraction_of_day: float | None, fraction_of_night: float | None) -> Body:
    """Lord of the third of the day (or night) in which the birth falls."""
    if fraction_of_day is not None:
        return (Body.MERCURY, Body.SUN, Body.SATURN)[min(int(fraction_of_day * 3), 2)]
    assert fraction_of_night is not None
    return (Body.MOON, Body.VENUS, Body.MARS)[min(int(fraction_of_night * 3), 2)]


#: Kali Yuga epoch: 18 February 3102 BCE (Julian), a Friday.
KALI_EPOCH_JD = 588465.5
_KALI_WEEKDAY = 5  # Friday, with 0 = Sunday


def ahargana(civil_day_jd: float) -> int:
    """Ahargana of a civil day: the first day of Kali Yuga counts as day 1.

    ``civil_day_jd`` is the Julian day at the start (0h) of the local civil date.
    """
    return math.floor(civil_day_jd - KALI_EPOCH_JD + 1e-9) + 1


def year_and_month_lords(days: int) -> tuple[Body, Body]:
    """Lords of the weekdays that began the current 360-day year and 30-day month.

    Counting from the first day of Kali Yuga (a Friday) as day 1 reproduces the
    year and month lords of the worked examples of both B.V. Raman and V.P. Jain.
    """
    year_start = days - days % 360
    month_start = days - days % 30
    return (
        WEEKDAY_LORDS[(_KALI_WEEKDAY - 1 + year_start) % 7],
        WEEKDAY_LORDS[(_KALI_WEEKDAY - 1 + month_start) % 7],
    )


def hora_lord(weekday: int, hours_since_sunrise: float) -> Body:
    """Lord of the equal (one-hour) hora from sunrise, starting with the day's lord."""
    first = HORA_ORDER.index(WEEKDAY_LORDS[weekday])
    return HORA_ORDER[(first + int(hours_since_sunrise)) % 7]


def ayana_bala(body: Body, declination: float) -> float:
    """From the kranti (declination, degrees, north positive; see ``kranti``).

    The Sun, Mars, Jupiter and Venus gain with northern declination, the Moon and
    Saturn with southern, Mercury with either. The Sun's is doubled.
    """
    if body in (Body.MOON, Body.SATURN):
        value = 24.0 - declination
    elif body is Body.MERCURY:
        value = 24.0 + abs(declination)
    else:
        value = 24.0 + declination
    bala = value * 60.0 / 48.0
    return 2.0 * bala if body is Body.SUN else bala


# --- Cheshta bala ------------------------------------------------------------

#: Mean longitude polynomials (degrees, mean equinox of date, T in Julian centuries
#: from J2000 TT): Meeus, *Astronomical Algorithms*, table 31.A.
_MEAN_LONGITUDE: dict[Body, tuple[float, float, float, float]] = {
    Body.MERCURY: (252.250906, 149474.0722491, 0.00030350, 0.000000018),
    Body.VENUS: (181.979801, 58519.2130302, 0.00031014, 0.000000015),
    Body.MARS: (355.433000, 19141.6964471, 0.00031052, 0.000000016),
    Body.JUPITER: (34.351519, 3036.3027748, 0.00022330, 0.000000037),
    Body.SATURN: (50.077444, 1223.5110686, 0.00051908, -0.000000030),
}
_EARTH_MEAN_LONGITUDE = (100.466457, 36000.7698278, 0.00030322, 0.000000020)


def _poly(coefficients: tuple[float, float, float, float], t: float) -> float:
    a0, a1, a2, a3 = coefficients
    return (a0 + a1 * t + a2 * t * t + a3 * t * t * t) % 360.0


def mean_longitudes(jd_tt: float, ayanamsa: float) -> dict[str, float]:
    """Sidereal mean longitudes: heliocentric for the planets, geocentric for the Sun."""
    t = (jd_tt - 2451545.0) / 36525.0
    out = {b.value: (_poly(c, t) - ayanamsa) % 360.0 for b, c in _MEAN_LONGITUDE.items()}
    out["sun"] = (_poly(_EARTH_MEAN_LONGITUDE, t) + 180.0 - ayanamsa) % 360.0
    return out


def cheshta_bala(body: Body, true_longitude: float, means: Mapping[str, float]) -> float:
    if body in (Body.SUN, Body.MOON):
        return 0.0
    if body in (Body.MERCURY, Body.VENUS):
        seeghrochcha, mean = means[body.value], means["sun"]
    else:
        seeghrochcha, mean = means["sun"], means[body.value]
    average = (mean + true_longitude) / 2.0
    if abs(mean - true_longitude) > 180.0:
        average = (average + 180.0) % 360.0
    return _arc(seeghrochcha, average) / 3.0


# --- Drik bala ---------------------------------------------------------------


def drishti_value(aspecting: Body, angle: float) -> float:
    """Aspect strength (virupas) of ``aspecting`` on a point ``angle`` degrees ahead."""
    a = angle % 360.0
    if 30.0 <= a < 60.0:
        value = (a - 30.0) / 2.0
    elif 60.0 <= a < 90.0:
        value = a - 45.0
        if aspecting is Body.SATURN:
            value += 45.0
    elif 90.0 <= a < 120.0:
        value = (120.0 - a) / 2.0 + 30.0
        if aspecting is Body.MARS:
            value += 15.0
    elif 120.0 <= a < 150.0:
        value = 150.0 - a
        if aspecting is Body.JUPITER:
            value += 30.0
    elif 150.0 <= a < 180.0:
        value = 2.0 * (a - 150.0)
    elif 180.0 <= a < 300.0:
        value = (300.0 - a) / 2.0
        if aspecting is Body.MARS and 210.0 <= a < 240.0:
            value += 15.0
        elif aspecting is Body.JUPITER and 240.0 <= a < 270.0:
            value += 30.0
        elif aspecting is Body.SATURN and 270.0 <= a < 300.0:
            value += 45.0
    else:
        value = 0.0
    return value


def drik_bala(body: Body, sidereal: Mapping[Body, float], benefic: set[Body]) -> float:
    total = 0.0
    for other in SEVEN:
        if other is body:
            continue
        value = drishti_value(other, sidereal[body] - sidereal[other])
        total += value if other in benefic else -value
    return total / 4.0


# --- Yuddha bala -------------------------------------------------------------


def yuddha_adjustments(
    sidereal: Mapping[Body, float], before_war: Mapping[Body, float]
) -> dict[Body, float]:
    """Gains and losses from planetary war (Mars to Saturn within one degree).

    The winner, the planet further north (here: with the larger strength before
    the war, as BPHS applies it), gains the difference of the two strengths divided
    by the difference of their disc diameters; the loser loses as much.
    """
    out = {b: 0.0 for b in SEVEN}
    fighters = [b for b in SEVEN if b in DISC_DIAMETER]
    for i, a in enumerate(fighters):
        for b in fighters[i + 1 :]:
            if _arc(sidereal[a], sidereal[b]) >= 1.0:
                continue
            winner, loser = (a, b) if before_war[a] >= before_war[b] else (b, a)
            diameter = abs(DISC_DIAMETER[a] - DISC_DIAMETER[b])
            gain = abs(before_war[a] - before_war[b]) / diameter if diameter else 0.0
            out[winner] += gain
            out[loser] -= gain
    return out


# --- Assembly ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ShadbalaInputs:
    """Everything shadbala needs about a moment and place."""

    sidereal: Mapping[Body, float]  # the seven planets (and optionally the nodes)
    ascendant: float  # sidereal
    midheaven: float  # sidereal
    declinations: Mapping[Body, float]  # degrees, north positive
    jd_tt: float
    ayanamsa: float
    hours_from_midnight: float  # 0-12
    fraction_of_day: float | None  # birth by day: 0-1 through the day
    fraction_of_night: float | None  # birth by night: 0-1 through the night
    weekday: int  # of the Vedic day, 0 = Sunday
    hours_since_sunrise: float
    ahargana: int


@dataclass(frozen=True, slots=True)
class PlanetShadbala:
    uchcha: float
    saptavargaja: float
    ojayugma: float
    kendradi: float
    drekkana: float
    dig: float
    nathonnata: float
    paksha: float
    tribhaga: float
    abda: float
    masa: float
    vara: float
    hora: float
    ayana: float
    yuddha: float
    cheshta: float
    naisargika: float
    drik: float

    @property
    def sthana(self) -> float:
        return self.uchcha + self.saptavargaja + self.ojayugma + self.kendradi + self.drekkana

    @property
    def kala(self) -> float:
        return (
            self.nathonnata + self.paksha + self.tribhaga + self.abda + self.masa
            + self.vara + self.hora + self.ayana + self.yuddha
        )  # fmt: skip

    @property
    def total(self) -> float:
        return self.sthana + self.dig + self.kala + self.cheshta + self.naisargika + self.drik

    @property
    def rupas(self) -> float:
        return self.total / 60.0


def shadbala(inputs: ShadbalaInputs) -> dict[Body, PlanetShadbala]:
    sidereal = inputs.sidereal
    lagna_sign = _sign(inputs.ascendant)
    good = benefics(sidereal)
    year_lord, month_lord = year_and_month_lords(inputs.ahargana)
    day_lord = WEEKDAY_LORDS[inputs.weekday]
    hour_lord = hora_lord(inputs.weekday, inputs.hours_since_sunrise)
    third_lord = tribhaga_lord(inputs.fraction_of_day, inputs.fraction_of_night)
    means = mean_longitudes(inputs.jd_tt, inputs.ayanamsa)

    parts: dict[Body, dict[str, float]] = {}
    for body in SEVEN:
        lon = sidereal[body]
        parts[body] = {
            "uchcha": uchcha_bala(body, lon),
            "saptavargaja": saptavargaja_bala(body, sidereal),
            "ojayugma": ojayugma_bala(body, lon),
            "kendradi": kendradi_bala(lon, lagna_sign),
            "drekkana": drekkana_bala(body, lon),
            "dig": dig_bala(body, lon, inputs.ascendant, inputs.midheaven),
            "nathonnata": nathonnata_bala(body, inputs.hours_from_midnight),
            "paksha": paksha_bala(body, sidereal, good),
            "tribhaga": 60.0 if body in (third_lord, Body.JUPITER) else 0.0,
            "abda": 15.0 if body is year_lord else 0.0,
            "masa": 30.0 if body is month_lord else 0.0,
            "vara": 45.0 if body is day_lord else 0.0,
            "hora": 60.0 if body is hour_lord else 0.0,
            "ayana": ayana_bala(body, inputs.declinations[body]),
            "cheshta": cheshta_bala(body, lon, means),
            "naisargika": NAISARGIKA[body],
            "drik": drik_bala(body, sidereal, good),
        }
    before_war = {
        b: sum(p[k] for k in ("uchcha", "saptavargaja", "ojayugma", "kendradi", "drekkana",
                              "dig", "nathonnata", "paksha", "tribhaga", "hora"))
        for b, p in parts.items()
    }  # fmt: skip
    war = yuddha_adjustments(sidereal, before_war)
    return {body: PlanetShadbala(yuddha=war[body], **parts[body]) for body in SEVEN}


# --- From a chart ---------------------------------------------------------------


#: The kranti tables of BPHS and the Surya Siddhanta take the obliquity as 24 degrees.
KRANTI_OBLIQUITY = 24.0


def kranti(tropical_longitude: float) -> float:
    """Declination of the ecliptic point at ``tropical_longitude`` (the planet's
    latitude ignored), with the classical 24-degree obliquity."""
    return math.degrees(
        math.asin(
            math.sin(math.radians(KRANTI_OBLIQUITY)) * math.sin(math.radians(tropical_longitude))
        )
    )


def _local_apparent_hours(
    sun_tropical: float, obliquity: float, gast_deg: float, lon: float
) -> float:
    lam, eps = math.radians(sun_tropical), math.radians(obliquity)
    right_ascension = math.degrees(math.atan2(math.cos(eps) * math.sin(lam), math.cos(lam)))
    hour_angle = (gast_deg + lon - right_ascension) % 360.0
    return (12.0 + hour_angle / 15.0) % 24.0


def inputs_from_chart(chart: ChartResult) -> ShadbalaInputs:
    """Build shadbala inputs from a computed chart."""
    instant = Instant(jd_ut=chart.time.jd_ut, jd_tt=chart.time.jd_tt)
    by_body = {g.body: g for g in chart.grahas}
    obliquity = true_obliquity_deg(instant)
    sidereal = {b: by_body[b].sidereal_longitude for b in (*SEVEN, *NODES)}
    declinations = {b: kranti(by_body[b].tropical_longitude) for b in SEVEN}
    solar_time = _local_apparent_hours(
        by_body[Body.SUN].tropical_longitude,
        obliquity,
        greenwich_apparent_sidereal_deg(instant),
        chart.birth.place.longitude,
    )
    day = chart.day
    if day.sunrise is None or day.sunset is None or day.next_sunrise is None or day.weekday is None:
        raise ValueError("shadbala needs sunrise and sunset, which do not occur at this latitude")
    birth = jd_to_datetime(chart.time.jd_ut)

    def hours(start: datetime, end: datetime) -> float:
        return (end - start).total_seconds() / 3600.0

    by_day = bool(day.born_during_day)
    offset = timedelta(seconds=chart.time.interpretation.utc_offset_seconds)
    local_date = (day.sunrise + offset).date()
    civil_jd = 2440587.5 + (local_date - date(1970, 1, 1)).days
    return ShadbalaInputs(
        sidereal=sidereal,
        ascendant=chart.ascendant.sidereal_longitude,
        midheaven=chart.midheaven.sidereal_longitude,
        declinations=declinations,
        jd_tt=chart.time.jd_tt,
        ayanamsa=chart.ayanamsa.true,
        hours_from_midnight=min(solar_time, 24.0 - solar_time),
        fraction_of_day=hours(day.sunrise, birth) / hours(day.sunrise, day.sunset)
        if by_day
        else None,
        fraction_of_night=None
        if by_day
        else hours(day.sunset, birth) / hours(day.sunset, day.next_sunrise),
        weekday=day.weekday,
        hours_since_sunrise=hours(day.sunrise, birth),
        ahargana=ahargana(civil_jd),
    )


def compute_shadbala(chart: ChartResult) -> dict[Body, PlanetShadbala]:
    return shadbala(inputs_from_chart(chart))
