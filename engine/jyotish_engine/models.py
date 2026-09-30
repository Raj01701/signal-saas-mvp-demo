"""Input and output models of the engine's public API (pydantic, JSON-serialisable)."""

from __future__ import annotations

from datetime import date, datetime
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
from jyotish_engine.rules.schema import (
    Category,
    Domain,
    Polarity,
    Provenance,
    School,
    Status,
    Strength,
)
from jyotish_engine.settings import DashaYear, Settings
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


class DashaPeriodOut(BaseModel):
    """One dasha period; ``lords`` runs from the mahadasha lord down to this level."""

    lords: list[Body]
    start: datetime
    end: datetime
    start_jd_ut: float
    end_jd_ut: float


class DashaTableOut(BaseModel):
    system: str
    label: str
    year_days: float
    #: The mahadasha running at birth and the part of it still to run.
    birth_lord: Body
    balance_years: float
    #: Periods depth-first: each mahadasha, then its sub-periods, and so on.
    periods: list[DashaPeriodOut]


class SignDashaPeriodOut(BaseModel):
    """One sign dasha period; ``signs`` runs from the mahadasha sign down."""

    signs: list[Sign]
    start: datetime
    end: datetime
    start_jd_ut: float
    end_jd_ut: float


class SignDashaTableOut(BaseModel):
    system: str
    label: str
    year_days: float
    first_sign: Sign
    #: Periods depth-first: each mahadasha, then its sub-periods, and so on.
    periods: list[SignDashaPeriodOut]


class KalachakraTableOut(SignDashaTableOut):
    #: The Moon's pada at birth (0 = Ashwini 1 .. 107 = Revati 4), its span of life
    #: and its deha (first) and jeeva (last) signs.
    pada: int
    paramayus: int
    deha: Sign
    jeeva: Sign


class DashaApplicabilityOut(BaseModel):
    system: str
    applicable: bool | None
    rule: str


class DashasOut(BaseModel):
    year: DashaYear
    year_days: float
    vimshottari: DashaTableOut
    applicability: list[DashaApplicabilityOut]


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
    dashas: DashasOut


class AnnualPeriodOut(BaseModel):
    """A period of an annual-chart dasha; ``lords`` are planet names or "lagna"."""

    lords: list[str]
    start: datetime
    end: datetime
    start_jd_ut: float
    end_jd_ut: float


class TajikaRelationOut(BaseModel):
    faster: Body
    slower: Body
    aspect: str
    friendly: bool
    gap: float
    orb: float
    yoga: str | None


class OfficeBearersOut(BaseModel):
    natal_lagna_lord: Body
    varsha_lagna_lord: Body
    muntha_lord: Body
    tri_rashi_lord: Body
    dina_ratri_lord: Body
    candidates: list[Body]


class SahamOut(BaseModel):
    name: str
    meaning: str
    sidereal_longitude: float
    sign: Sign
    #: Disease, death and similar topics: shown only when explicitly requested.
    sensitive: bool


class VarshaphalOut(BaseModel):
    """The Tajika annual chart for the year after ``years_completed`` years of life."""

    years_completed: int
    start: datetime
    start_jd_ut: float
    end: datetime
    end_jd_ut: float
    chart: ChartResult
    muntha: Sign
    muntha_lord: Body
    by_day: bool | None
    office_bearers: OfficeBearersOut
    #: Lord of the year and whether it aspects the annual lagna (pending review).
    year_lord: Body
    year_lord_aspects_lagna: bool
    #: All seven planets in kendras and panapharas (Ikkavala) or in apoklimas (Induvara).
    ikkavala: bool
    induvara: bool
    #: Tajika pancha-vargiya bala of the seven planets, out of 20.
    pancha_vargiya: dict[Body, float]
    tajika: list[TajikaRelationOut]
    #: The 36 Tajika sahams of the annual chart; sensitive ones are flagged.
    sahams: list[SahamOut]
    mudda: list[AnnualPeriodOut]
    patyayini: list[AnnualPeriodOut]


class TithiPraveshaOut(BaseModel):
    years_completed: int
    moment: datetime
    jd_ut: float
    elongation: float
    chart: ChartResult


class ShadbalaOut(BaseModel):
    """Shadbala of one planet in virupas (60 virupas = 1 rupa)."""

    body: Body
    uchcha: float
    saptavargaja: float
    ojayugma: float
    kendradi: float
    drekkana: float
    sthana: float
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
    kala: float
    cheshta: float
    naisargika: float
    drik: float
    total: float
    rupas: float
    required_rupas: float
    #: Strength relative to the required minimum (1 = just strong enough).
    ratio: float
    ishta_phala: float
    kashta_phala: float


class BhavaBalaOut(BaseModel):
    house: int
    madhya: float
    lord: Body
    adhipati: float
    dig: float
    drishti: float
    total: float
    rupas: float


class AshtakavargaOut(BaseModel):
    moon_table: str
    #: Bindus per sign (Aries first) for each planet and "lagna".
    bav: dict[str, list[int]]
    sav: list[int]
    #: After trikona and ekadhipatya shodhana, and the resulting pindas.
    reduced: dict[str, list[int]]
    rasi_pinda: dict[str, int]
    graha_pinda: dict[str, int]
    shodhya_pinda: dict[str, int]


class StrengthsOut(BaseModel):
    shadbala: list[ShadbalaOut]
    bhava_bala: list[BhavaBalaOut]
    ashtakavarga: AshtakavargaOut
    #: Vimshopaka bala (out of 20) under each varga scheme.
    vimshopaka: dict[str, dict[Body, float]]


class LimbSpanOut(BaseModel):
    """One tithi, nakshatra, yoga or karana, with its full start and end."""

    limb: str
    #: 1-based: tithi 1-30, nakshatra and yoga 1-27, karana 1-60 within the month.
    number: int
    name: str
    #: For tithis: "shukla" (bright half) or "krishna" (dark half).
    paksha: str | None = None
    start: datetime
    end: datetime
    start_jd_ut: float
    end_jd_ut: float


class PeriodOut(BaseModel):
    name: str
    start: datetime
    end: datetime
    start_jd_ut: float
    end_jd_ut: float
    lord: Body | None = None
    #: For choghadiyas: "good", "neutral" or "bad".
    quality: str | None = None


class LunarMonthOut(BaseModel):
    """An amanta month, from one new moon to the next."""

    #: 1 = Chaitra ... 12 = Phalguna.
    number: int
    name: str
    #: Intercalary month, in which the Sun enters no sign.
    adhika: bool
    #: The regular month that follows an adhika month of the same name.
    nija: bool
    #: For a kshaya month (the Sun enters two signs), the second name it carries.
    kshaya_name: str | None = None
    start: datetime
    end: datetime
    start_jd_ut: float
    end_jd_ut: float


class CalendarOut(BaseModel):
    """The calendar date of a Hindu day: lunar values at sunrise, Tamil date at sunset."""

    amanta: LunarMonthOut
    #: Purnimanta month of the day (the dark half belongs to the next month).
    purnimanta_number: int
    purnimanta_name: str
    purnimanta_adhika: bool
    paksha: str
    #: The tithi at sunrise counted within its paksha, 1-15.
    paksha_day: int
    #: Season by lunar month.
    ritu: str
    #: Uttarayana from Makara to Karka sankranti (sidereal), else dakshinayana.
    ayana_sidereal: str
    #: Uttarayana from the winter to the summer solstice (tropical).
    ayana_tropical: str
    kali_year: int
    shaka_year: int
    vikram_year: int
    #: Gujarati (Kartikadi) Vikram year.
    vikram_year_kartikadi: int
    #: 1 = Prabhava ... 60 = Akshaya, continuous with the Shaka year.
    samvatsara_number: int
    samvatsara: str
    #: Tamil solar month (1 = Chittirai) and day, by the sunset rule.
    tamil_month_number: int
    tamil_month: str
    tamil_day: int
    tamil_samvatsara: str
    #: Tithis (1-30) that begin after sunrise and end before the next (kshaya).
    kshaya_tithis: list[int]
    #: The tithi at sunrise also prevailed at the previous sunrise (vriddhi).
    vriddhi_tithi: bool


class PanchangaOut(BaseModel):
    """The panchanga of one Hindu day, from sunrise to the next sunrise.

    Times are UTC; ``utc_offset_seconds`` gives the local offset at the start of the
    civil date. Each limb lists every span overlapping the day.
    """

    civil_date: date
    place: PlaceInput
    settings: Settings
    zone: str | None
    utc_offset_seconds: float
    #: 0 = Sunday.
    weekday: int
    vara: str
    vara_lord: Body
    sunrise: datetime
    sunrise_jd_ut: float
    sunset: datetime
    sunset_jd_ut: float
    next_sunrise: datetime
    next_sunrise_jd_ut: float
    #: Within the civil date (local midnight to midnight), if the Moon rises or sets.
    moonrise: datetime | None
    moonset: datetime | None
    calendar: CalendarOut
    tithis: list[LimbSpanOut]
    nakshatras: list[LimbSpanOut]
    yogas: list[LimbSpanOut]
    karanas: list[LimbSpanOut]
    #: Rahu kalam, Yamaganda and Gulika kalam.
    kalams: list[PeriodOut]
    abhijit: PeriodOut
    brahma_muhurta: PeriodOut
    durmuhurtas: list[PeriodOut]
    horas: list[PeriodOut]
    choghadiyas: list[PeriodOut]


class CitationOut(BaseModel):
    text: str
    edition: str | None
    chapter: int | str | None
    verses: str | None
    locator: str | None
    #: Whether someone has checked the citation against that edition.
    verified: bool


class KootaOut(BaseModel):
    name: str
    points: float
    maximum: float
    groom: str
    bride: str
    detail: str
    sources: list[CitationOut]


class MatchDoshaOut(BaseModel):
    name: str
    present: bool
    cancelled: bool
    #: The traditional exceptions that apply; any one cancels the dosha.
    exceptions: list[str]
    sources: list[CitationOut]


class PoruthamOut(BaseModel):
    name: str
    agrees: bool
    detail: str
    relieved_by: str | None


class KujaOut(BaseModel):
    manglik: bool
    #: Kuja dosha rules present (and not cancelled), and those cancelled.
    present: list[str]
    cancelled: list[str]


class MatchOut(BaseModel):
    """Marriage matching of two charts (groom first)."""

    #: Which points tables were used ("popular" or "maitreya").
    profile: str
    ashtakoota: list[KootaOut]
    ashtakoota_total: float
    doshas: list[MatchDoshaOut]
    dashakoota: list[PoruthamOut]
    dashakoota_agreements: int
    groom_kuja: KujaOut
    bride_kuja: KujaOut
    #: Both partners manglik, or neither.
    kuja_balanced: bool
    sources: list[CitationOut]


class KpCuspOut(BaseModel):
    house: int
    longitude: float
    lords: KpOut


class KpPlanetOut(BaseModel):
    body: Body
    longitude: float
    #: Placidus bhava, cusp to cusp.
    house: int
    lords: KpOut
    #: Houses signified at the four KP levels, strongest first.
    signifies: list[list[int]]


class KpChartOut(BaseModel):
    """KP chart: cusps with their lords, planets, significators, ruling planets."""

    cusps: list[KpCuspOut]
    planets: list[KpPlanetOut]
    #: For each house (1-12), the planets signifying it at the four levels.
    house_significators: list[list[list[Body]]]
    day_lord: Body
    ruling_planets: list[Body]
    #: For a horary chart: the KP number and the moment its ascendant rises.
    horary_number: int | None = None
    horary_cusp_jd_ut: float | None = None


class SensitiveFactorOut(BaseModel):
    name: str
    value: str
    #: Minutes the factor has held before the birth time, and will hold after it;
    #: None when it holds beyond the search span.
    minutes_before: float | None
    minutes_after: float | None
    #: It would change within the birth time's uncertainty.
    fragile: bool


class SensitivityOut(BaseModel):
    uncertainty_minutes: float
    factors: list[SensitiveFactorOut]


class YogaOut(BaseModel):
    """A knowledge-base rule (yoga or dosha) found in a chart, with its evidence."""

    id: str
    name: str
    category: Category
    school: School
    provenance: Provenance
    status: Status
    description: str
    domains: list[Domain]
    polarity: Polarity
    strength: Strength
    summary: str
    #: The chart facts that made the rule true, in rule-language terms.
    evidence: list[str]
    #: For a cancelled rule, the facts that cancelled it.
    cancel_evidence: list[str]
    #: Planets forming the yoga; their dashas are when it is expected to act.
    participants: list[Body]
    sources: list[CitationOut]


class UndecidedRuleOut(BaseModel):
    id: str
    name: str
    #: The birth fact the rule needs, for example "gender".
    missing: str


class YogasOut(BaseModel):
    #: Number of rules evaluated.
    catalogue_size: int
    present: list[YogaOut]
    cancelled: list[YogaOut]
    undecided: list[UndecidedRuleOut]
