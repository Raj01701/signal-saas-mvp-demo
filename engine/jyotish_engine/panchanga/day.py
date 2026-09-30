"""The panchanga of a civil date at a place: one Hindu day, sunrise to sunrise."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from jyotish_engine.astro.bodies import Body
from jyotish_engine.astro.positions import tropical_positions
from jyotish_engine.astro.riseset import (
    SunriseDefinition,
    next_moonrise,
    next_moonset,
    next_sunrise,
    next_sunset,
)
from jyotish_engine.astro.time import Instant, jd_to_datetime
from jyotish_engine.models import (
    CalendarOut,
    LimbSpanOut,
    LunarMonthOut,
    PanchangaOut,
    PeriodOut,
    PlaceInput,
)
from jyotish_engine.panchanga import muhurta
from jyotish_engine.panchanga.calendar import (
    MASAS,
    RITUS,
    SAMVATSARAS,
    ayana,
    lunar_month,
    lunar_year,
    purnimanta_month,
    ritu,
    tamil_solar_date,
)
from jyotish_engine.panchanga.elements import VARA_LORDS, VARAS, Limb, paksha
from jyotish_engine.panchanga.muhurta import Period
from jyotish_engine.panchanga.timing import LimbSpan, all_limb_spans
from jyotish_engine.place.timezone import resolve_local_time
from jyotish_engine.settings import Settings
from jyotish_engine.transit.search import longitude_at


def _limb(span: LimbSpan) -> LimbSpanOut:
    return LimbSpanOut(
        limb=span.limb.value,
        number=span.index + 1,
        name=span.name,
        paksha=paksha(span.index) if span.limb is Limb.TITHI else None,
        start=jd_to_datetime(span.start_jd_ut),
        end=jd_to_datetime(span.end_jd_ut),
        start_jd_ut=span.start_jd_ut,
        end_jd_ut=span.end_jd_ut,
    )


def _period(period: Period) -> PeriodOut:
    return PeriodOut(
        name=period.name,
        start=jd_to_datetime(period.start_jd_ut),
        end=jd_to_datetime(period.end_jd_ut),
        start_jd_ut=period.start_jd_ut,
        end_jd_ut=period.end_jd_ut,
        lord=period.lord,
        quality=period.quality,
    )


def _calendar(
    day: date,
    place: PlaceInput,
    settings: Settings,
    sunrises: tuple[float, float, float],
    sunset_jd: float,
    tithis: list[LimbSpan],
) -> CalendarOut:
    """``sunrises``: the previous, this and the next sunrise (UT)."""
    previous_jd, sunrise_jd, next_jd = sunrises
    month = lunar_month(sunrise_jd, settings)
    year = lunar_year(month)
    tithi = tithis[0].index
    purnimanta, purnimanta_adhika = purnimanta_month(month, tithi)
    tamil = tamil_solar_date(
        day,
        sunset_jd,
        place.latitude,
        place.longitude,
        place.elevation_m,
        settings.sunrise,
        settings,
    )
    tropical_sun = tropical_positions(
        Instant.from_jd_ut(sunrise_jd), [Body.SUN], settings.node_type, settings.position_type
    )[Body.SUN].longitude
    kshaya_name = None if month.kshaya_index is None else MASAS[month.kshaya_index]
    return CalendarOut(
        amanta=LunarMonthOut(
            number=month.index + 1,
            name=month.name,
            adhika=month.adhika,
            nija=month.nija,
            kshaya_name=kshaya_name,
            start=jd_to_datetime(month.start_jd_ut),
            end=jd_to_datetime(month.end_jd_ut),
            start_jd_ut=month.start_jd_ut,
            end_jd_ut=month.end_jd_ut,
        ),
        purnimanta_number=purnimanta + 1,
        purnimanta_name=MASAS[purnimanta],
        purnimanta_adhika=purnimanta_adhika,
        paksha=paksha(tithi),
        paksha_day=tithi % 15 + 1,
        ritu=RITUS[ritu(month)],
        ayana_sidereal=ayana(longitude_at(Body.SUN, sunrise_jd, settings)),
        ayana_tropical=ayana(tropical_sun),
        kali_year=year.kali,
        shaka_year=year.shaka,
        vikram_year=year.vikram,
        vikram_year_kartikadi=year.vikram_kartikadi,
        samvatsara_number=year.samvatsara + 1,
        samvatsara=year.samvatsara_name,
        tamil_month_number=tamil.month + 1,
        tamil_month=tamil.month_name,
        tamil_day=tamil.day,
        tamil_samvatsara=SAMVATSARAS[tamil.samvatsara],
        kshaya_tithis=[s.index + 1 for s in tithis[1:] if s.end_jd_ut <= next_jd],
        vriddhi_tithi=tithis[0].start_jd_ut <= previous_jd,
    )


def _local_midnight(
    day: date, place: PlaceInput, zone: str | None
) -> tuple[float, float, str | None]:
    resolution = resolve_local_time(
        datetime(day.year, day.month, day.day), place.latitude, place.longitude, zone=zone
    )
    chosen = resolution.chosen
    return Instant.from_utc(chosen.utc).jd_ut, chosen.utc_offset_seconds, resolution.zone


def compute_panchanga(
    day: date,
    place: PlaceInput,
    settings: Settings | None = None,
    zone: str | None = None,
) -> PanchangaOut:
    """Panchanga for the Hindu day that begins at sunrise on the civil date ``day``.

    The time zone comes from the coordinates unless ``zone`` is given; it only
    decides where the civil date starts. Sunrise follows ``settings.sunrise``.
    """
    settings = settings or Settings()
    midnight, offset, zone_name = _local_midnight(day, place, zone)
    next_midnight, _, _ = _local_midnight(day + timedelta(days=1), place, zone)
    lat, lon, elevation = place.latitude, place.longitude, place.elevation_m
    rule: SunriseDefinition = settings.sunrise

    rise = next_sunrise(Instant.from_jd_ut(midnight), lat, lon, elevation, rule)
    if rise is None:
        raise ValueError("the Sun does not rise on this date here (polar night)")
    sunset = next_sunset(rise, lat, lon, elevation, rule)
    following = next_sunrise(sunset, lat, lon, elevation, rule) if sunset else None
    previous_sunset = next_sunset(Instant.from_jd_ut(rise.jd_ut - 1.0), lat, lon, elevation, rule)
    previous_rise = next_sunrise(Instant.from_jd_ut(rise.jd_ut - 1.1), lat, lon, elevation, rule)
    if sunset is None or following is None or previous_sunset is None or previous_rise is None:
        raise ValueError("the Sun does not set on this date here (polar day)")
    sunrise_jd, sunset_jd, next_jd = rise.jd_ut, sunset.jd_ut, following.jd_ut
    weekday = (day.weekday() + 1) % 7

    moonrise = next_moonrise(Instant.from_jd_ut(midnight), lat, lon, elevation)
    moonset = next_moonset(Instant.from_jd_ut(midnight), lat, lon, elevation)
    limbs = all_limb_spans(sunrise_jd, next_jd, settings)

    return PanchangaOut(
        civil_date=day,
        place=place,
        settings=settings,
        zone=zone_name,
        utc_offset_seconds=offset,
        weekday=weekday,
        vara=VARAS[weekday],
        vara_lord=VARA_LORDS[weekday],
        sunrise=jd_to_datetime(sunrise_jd),
        sunrise_jd_ut=sunrise_jd,
        sunset=jd_to_datetime(sunset_jd),
        sunset_jd_ut=sunset_jd,
        next_sunrise=jd_to_datetime(next_jd),
        next_sunrise_jd_ut=next_jd,
        moonrise=jd_to_datetime(moonrise.jd_ut)
        if moonrise and moonrise.jd_ut < next_midnight
        else None,
        moonset=jd_to_datetime(moonset.jd_ut)
        if moonset and moonset.jd_ut < next_midnight
        else None,
        calendar=_calendar(
            day,
            place,
            settings,
            (previous_rise.jd_ut, sunrise_jd, next_jd),
            sunset_jd,
            limbs[Limb.TITHI],
        ),
        tithis=[_limb(s) for s in limbs[Limb.TITHI]],
        nakshatras=[_limb(s) for s in limbs[Limb.NAKSHATRA]],
        yogas=[_limb(s) for s in limbs[Limb.YOGA]],
        karanas=[_limb(s) for s in limbs[Limb.KARANA]],
        kalams=[_period(p) for p in muhurta.kalams(sunrise_jd, sunset_jd, weekday)],
        abhijit=_period(muhurta.abhijit(sunrise_jd, sunset_jd)),
        brahma_muhurta=_period(muhurta.brahma_muhurta(previous_sunset.jd_ut, sunrise_jd)),
        durmuhurtas=[
            _period(p) for p in muhurta.durmuhurtas(sunrise_jd, sunset_jd, next_jd, weekday)
        ],
        horas=[_period(p) for p in muhurta.horas(sunrise_jd, sunset_jd, next_jd, weekday)],
        choghadiyas=[
            _period(p) for p in muhurta.choghadiyas(sunrise_jd, sunset_jd, next_jd, weekday)
        ],
    )
