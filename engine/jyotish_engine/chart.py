"""Top-level entry point: birth data in, fully described chart out."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from jyotish_engine import ENGINE_VERSION
from jyotish_engine.astro.ayanamsa import label as ayanamsa_label
from jyotish_engine.astro.ayanamsa import mean_ayanamsa, true_ayanamsa
from jyotish_engine.astro.bodies import GRAHAS, OUTER_PLANETS, Body
from jyotish_engine.astro.ephemeris import get_ephemeris
from jyotish_engine.astro.houses import HouseSystem, chart_angles, quadrant_cusps
from jyotish_engine.astro.positions import tropical_positions
from jyotish_engine.astro.riseset import next_sunrise, next_sunset
from jyotish_engine.astro.time import Instant
from jyotish_engine.core.zodiac import Sign, degrees_in_sign, sign_of
from jyotish_engine.place.timezone import (
    Confidence,
    TimeInterpretation,
    TimeStandard,
    resolve_local_time,
)
from jyotish_engine.settings import Settings


class BirthTimeSource(StrEnum):
    """Where the birth time came from; drives the Rodden-style rating."""

    BIRTH_CERTIFICATE = "birth_certificate"  # AA
    HOSPITAL_RECORD = "hospital_record"  # AA
    FAMILY_RECORD = "family_record"  # A (written at the time, e.g. a janma patrika)
    MEMORY = "memory"  # A
    ESTIMATE = "estimate"  # C
    RECTIFIED = "rectified"  # time derived by rectification
    UNKNOWN = "unknown"  # X


RODDEN_RATING: dict[BirthTimeSource, str] = {
    BirthTimeSource.BIRTH_CERTIFICATE: "AA",
    BirthTimeSource.HOSPITAL_RECORD: "AA",
    BirthTimeSource.FAMILY_RECORD: "A",
    BirthTimeSource.MEMORY: "A",
    BirthTimeSource.ESTIMATE: "C",
    BirthTimeSource.RECTIFIED: "R",
    BirthTimeSource.UNKNOWN: "X",
}


class PlaceInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str | None = None
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    elevation_m: float = 0.0
    country_code: str | None = None
    geonames_id: int | None = None


class BirthInput(BaseModel):
    """A birth record exactly as written, before any time-zone interpretation."""

    model_config = ConfigDict(frozen=True)

    local_datetime: datetime
    place: PlaceInput
    time_standard: TimeStandard = TimeStandard.AUTO
    utc_offset_seconds: float | None = None
    zone: str | None = None
    time_source: BirthTimeSource = BirthTimeSource.UNKNOWN
    uncertainty_minutes: float | None = Field(default=None, ge=0.0)


class TimeInterpretationOut(BaseModel):
    standard: TimeStandard
    label: str
    utc: datetime
    utc_offset_seconds: float
    note: str | None = None

    @classmethod
    def of(cls, value: TimeInterpretation) -> TimeInterpretationOut:
        return cls(
            standard=value.standard,
            label=value.label,
            utc=value.utc,
            utc_offset_seconds=value.utc_offset_seconds,
            note=value.note,
        )


class TimeOut(BaseModel):
    local: datetime
    zone: str | None
    interpretation: TimeInterpretationOut
    alternatives: list[TimeInterpretationOut]
    ambiguous: bool
    confidence: Confidence
    warnings: list[str]
    jd_ut: float
    jd_tt: float
    delta_t_seconds: float


class PointOut(BaseModel):
    """A sidereal point with its tropical source value."""

    tropical_longitude: float
    sidereal_longitude: float
    sign: Sign
    sign_name: str
    degrees_in_sign: float

    @classmethod
    def of(cls, tropical: float, ayanamsa_true: float) -> PointOut:
        sidereal = (tropical - ayanamsa_true) % 360.0
        sign = sign_of(sidereal)
        return cls(
            tropical_longitude=tropical % 360.0,
            sidereal_longitude=sidereal,
            sign=sign,
            sign_name=sign.sanskrit,
            degrees_in_sign=degrees_in_sign(sidereal),
        )


class GrahaOut(PointOut):
    body: Body
    latitude: float
    speed: float
    retrograde: bool
    distance_au: float


class HousesOut(BaseModel):
    system: HouseSystem
    fallback: bool
    #: Sidereal start of each bhava (sandhi) for Sripati, or cusp for other systems.
    cusps: list[float]
    #: Whole-sign houses: house number to sign (house 1 is the ascendant's sign).
    whole_sign: list[Sign]


class AyanamsaOut(BaseModel):
    system: str
    label: str
    mean: float
    true: float


class EphemerisOut(BaseModel):
    name: str
    jd_start: float
    jd_end: float


class DayOut(BaseModel):
    sunrise_before_birth: datetime | None
    sunset: datetime | None
    next_sunrise: datetime | None
    born_during_day: bool | None


class ChartResult(BaseModel):
    engine_version: str
    ephemeris: EphemerisOut
    settings: Settings
    settings_hash: str
    birth: BirthInput
    rodden_rating: str
    time: TimeOut
    ayanamsa: AyanamsaOut
    ascendant: PointOut
    midheaven: PointOut
    grahas: list[GrahaOut]
    houses: HousesOut
    day: DayOut


def _day(instant: Instant, place: PlaceInput, settings: Settings) -> DayOut:
    args = (place.latitude, place.longitude, place.elevation_m, settings.sunrise)
    first = next_sunrise(Instant.from_jd_ut(instant.jd_ut - 1.2), *args, max_days=1.3)
    sunrise_before: Instant | None = None
    while first is not None and first.jd_ut <= instant.jd_ut:
        sunrise_before = first
        first = next_sunrise(Instant.from_jd_ut(first.jd_ut + 0.01), *args, max_days=1.3)
    upcoming = next_sunrise(instant, *args, max_days=1.3)
    sunset = (
        next_sunset(sunrise_before, *args, max_days=1.3) if sunrise_before is not None else None
    )
    born_during_day = None if sunset is None else sunset.jd_ut > instant.jd_ut
    return DayOut(
        sunrise_before_birth=sunrise_before.utc_datetime() if sunrise_before else None,
        sunset=sunset.utc_datetime() if sunset else None,
        next_sunrise=upcoming.utc_datetime() if upcoming else None,
        born_during_day=born_during_day,
    )


def compute_chart(birth: BirthInput, settings: Settings | None = None) -> ChartResult:
    """Compute a complete sidereal chart for a birth record."""
    settings = settings or Settings()
    place = birth.place
    resolution = resolve_local_time(
        birth.local_datetime.replace(tzinfo=None),
        place.latitude,
        place.longitude,
        standard=birth.time_standard,
        utc_offset_seconds=birth.utc_offset_seconds,
        zone=birth.zone,
    )
    instant = Instant.from_utc(resolution.chosen.utc)
    eph = get_ephemeris()
    eph.check_range(instant.jd_tt)

    ayan_true = true_ayanamsa(instant, settings.ayanamsa, settings.user_ayanamsa_j2000)
    ayan_mean = mean_ayanamsa(instant, settings.ayanamsa, settings.user_ayanamsa_j2000)

    bodies = list(GRAHAS) + (list(OUTER_PLANETS) if settings.include_outer_planets else [])
    positions = tropical_positions(instant, bodies, settings.node_type)
    grahas = []
    for body in bodies:
        pos = positions[body]
        point = PointOut.of(pos.longitude, ayan_true)
        grahas.append(
            GrahaOut(
                **point.model_dump(),
                body=body,
                latitude=pos.latitude,
                speed=pos.speed,
                retrograde=pos.retrograde if body not in (Body.RAHU, Body.KETU) else True,
                distance_au=pos.distance_au,
            )
        )

    angles = chart_angles(instant, place.latitude, place.longitude)
    ascendant = PointOut.of(angles.ascendant, ayan_true)
    cusps = quadrant_cusps(settings.bhava_system, angles)
    whole_sign = [Sign((ascendant.sign + i) % 12) for i in range(12)]

    return ChartResult(
        engine_version=ENGINE_VERSION,
        ephemeris=EphemerisOut(
            name=eph.info.name, jd_start=eph.info.jd_start, jd_end=eph.info.jd_end
        ),
        settings=settings,
        settings_hash=settings.fingerprint(),
        birth=birth,
        rodden_rating=RODDEN_RATING[birth.time_source],
        time=TimeOut(
            local=resolution.local,
            zone=resolution.zone,
            interpretation=TimeInterpretationOut.of(resolution.chosen),
            alternatives=[TimeInterpretationOut.of(a) for a in resolution.alternatives],
            ambiguous=resolution.ambiguous,
            confidence=resolution.confidence,
            warnings=list(resolution.warnings),
            jd_ut=instant.jd_ut,
            jd_tt=instant.jd_tt,
            delta_t_seconds=instant.delta_t_seconds,
        ),
        ayanamsa=AyanamsaOut(
            system=settings.ayanamsa.value,
            label=ayanamsa_label(settings.ayanamsa),
            mean=ayan_mean,
            true=ayan_true,
        ),
        ascendant=ascendant,
        midheaven=PointOut.of(angles.mc, ayan_true),
        grahas=grahas,
        houses=HousesOut(
            system=cusps.system,
            fallback=cusps.fallback,
            cusps=[(c - ayan_true) % 360.0 for c in cusps.cusps],
            whole_sign=whole_sign,
        ),
        day=_day(instant, place, settings),
    )
