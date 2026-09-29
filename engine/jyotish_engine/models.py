"""Input and output models of the engine's public API (pydantic, JSON-serialisable)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from jyotish_engine.astro.bodies import Body
from jyotish_engine.astro.houses import HouseSystem
from jyotish_engine.core.dignity import Dignity
from jyotish_engine.core.nakshatra import nakshatra_of
from jyotish_engine.core.states import BaladiAvastha, JagradadiAvastha
from jyotish_engine.core.varga import VargaMethod
from jyotish_engine.core.zodiac import Sign, degrees_in_sign, sign_of
from jyotish_engine.kp.subdivisions import kp_lords
from jyotish_engine.place.timezone import Confidence, TimeInterpretation, TimeStandard
from jyotish_engine.settings import Settings
from jyotish_engine.special.karakas import Karaka
from jyotish_engine.special.upagraha import Upagraha


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


class NakshatraOut(BaseModel):
    index: int
    name: str
    pada: int
    lord: Body
    deity: str
    fraction_elapsed: float


class KpOut(BaseModel):
    sign_lord: Body
    star_lord: Body
    sub_lord: Body
    sub_sub_lord: Body


class PointOut(BaseModel):
    """A sidereal point with its tropical source value."""

    tropical_longitude: float
    sidereal_longitude: float
    sign: Sign
    sign_name: str
    degrees_in_sign: float
    nakshatra: NakshatraOut
    kp: KpOut

    @classmethod
    def of(cls, tropical: float, ayanamsa_true: float) -> PointOut:
        return cls.from_sidereal((tropical - ayanamsa_true) % 360.0, ayanamsa_true)

    @classmethod
    def from_sidereal(cls, sidereal: float, ayanamsa_true: float) -> PointOut:
        sidereal %= 360.0
        sign = sign_of(sidereal)
        nak = nakshatra_of(sidereal)
        lords = kp_lords(sidereal)
        return cls(
            tropical_longitude=(sidereal + ayanamsa_true) % 360.0,
            sidereal_longitude=sidereal,
            sign=sign,
            sign_name=sign.sanskrit,
            degrees_in_sign=degrees_in_sign(sidereal),
            nakshatra=NakshatraOut(
                index=nak.nakshatra.index,
                name=nak.nakshatra.name,
                pada=nak.pada,
                lord=nak.nakshatra.lord,
                deity=nak.nakshatra.deity,
                fraction_elapsed=nak.fraction_elapsed,
            ),
            kp=KpOut(
                sign_lord=lords.sign_lord,
                star_lord=lords.star_lord,
                sub_lord=lords.sub_lord,
                sub_sub_lord=lords.sub_sub_lord,
            ),
        )


class GrahaOut(PointOut):
    body: Body
    latitude: float
    speed: float
    retrograde: bool
    distance_au: float
    house: int  # whole-sign house from the ascendant, 1..12
    dignity: Dignity | None
    combust: bool
    baladi_avastha: BaladiAvastha
    jagradadi_avastha: JagradadiAvastha | None
    gandanta: bool


class HousesOut(BaseModel):
    system: HouseSystem
    fallback: bool
    #: Sidereal start of each bhava (sandhi) for Sripati, or cusp for other systems.
    cusps: list[float]
    #: Whole-sign houses: house number to sign (house 1 is the ascendant's sign).
    whole_sign: list[Sign]


class VargaPlacement(BaseModel):
    sign: Sign
    longitude: float


class VargaChartOut(BaseModel):
    division: int
    name: str
    method: VargaMethod
    ascendant: VargaPlacement
    grahas: dict[Body, VargaPlacement]


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
    sunrise: datetime | None
    sunset: datetime | None
    next_sunrise: datetime | None
    weekday: int | None  # 0 = Sunday
    born_during_day: bool | None


class PlanetaryWarOut(BaseModel):
    planets: list[Body]
    separation_deg: float
    winner: Body


class SpecialPointsOut(BaseModel):
    bhava_lagna: PointOut | None
    hora_lagna: PointOut | None
    ghati_lagna: PointOut | None
    pranapada: PointOut | None
    indu_lagna: PointOut
    sree_lagna: PointOut
    upagrahas: dict[Upagraha, PointOut]
    #: Signs of the bhava arudhas A1 (Arudha Lagna) ... A12 (Upapada).
    arudhas: list[Sign]
    karakas: dict[Karaka, Body]
    planetary_wars: list[PlanetaryWarOut]


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
    vargas: list[VargaChartOut]
    special: SpecialPointsOut
    day: DayOut
