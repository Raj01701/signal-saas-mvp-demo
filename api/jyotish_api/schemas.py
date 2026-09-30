"""Request bodies of the compute routes."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from jyotish_engine.match.tables import KootaProfile
from jyotish_engine.models import BirthInput, PlaceInput
from jyotish_engine.rectify import EventKind
from jyotish_engine.settings import Preset, Settings


class ChartRequest(BaseModel):
    birth: BirthInput
    #: Full calculation settings; when absent, ``preset`` (or the default) applies.
    settings: Settings | None = None
    preset: Preset | None = None


class YogasRequest(ChartRequest):
    gender: Literal["male", "female"] | None = None
    #: Include rules marked sensitive (health, longevity); professional use only.
    include_sensitive: bool = False


class ReadingsRequest(ChartRequest):
    #: Include rules marked sensitive (health, longevity); professional use only.
    include_sensitive: bool = False


class PeriodRequest(ChartRequest):
    #: The moment to read (UTC when no offset is given); default: now.
    moment: datetime | None = None
    #: Include rules marked sensitive (health, longevity); professional use only.
    include_sensitive: bool = False


class PredictionsRequest(ChartRequest):
    #: First month of the timeline (default: the birth month).
    start: date | None = None
    #: The first day after the timeline (default: 60 years after the start).
    end: date | None = None
    gender: Literal["male", "female"] | None = None


class LifeReadingRequest(ChartRequest):
    gender: Literal["male", "female"] | None = None
    #: The day the reading is written for (default: today).
    today: date | None = None
    #: Years told one by one after today.
    years_ahead: int = Field(default=5, ge=1, le=10)


class RectifyEventIn(BaseModel):
    kind: EventKind
    date: date


class RectifyOptions(BaseModel):
    #: Minutes either side of the recorded time to search.
    uncertainty_minutes: float = Field(60.0, gt=0, le=180)
    #: Spacing of the candidate times.
    step_seconds: float = Field(30.0, ge=5, le=600)
    #: Traditional checks to add to the score (off unless listed).
    priors: list[Literal["kunda", "pranapada", "navamsa_gender"]] = []


class RectifyRequest(ChartRequest, RectifyOptions):
    events: list[RectifyEventIn] = Field(min_length=2, max_length=40)
    gender: Literal["male", "female"] | None = None


class DashaRequest(ChartRequest):
    #: A nakshatra dasha (e.g. "vimshottari"), a sign dasha (e.g. "chara") or "kalachakra".
    system: str
    depth: int = Field(default=2, ge=1, le=3)


class TransitRequest(ChartRequest):
    start: date
    end: date


class AnnualRequest(ChartRequest):
    years_completed: int = Field(ge=0, le=120)
    #: Where the native lives that year; the birth place when absent.
    place: PlaceInput | None = None


class PanchangaRequest(BaseModel):
    date: date
    place: PlaceInput
    settings: Settings | None = None
    preset: Preset | None = None
    #: IANA zone; found from the coordinates when absent.
    zone: str | None = None


class MatchRequest(BaseModel):
    groom: BirthInput
    bride: BirthInput
    settings: Settings | None = None
    preset: Preset | None = None
    profile: KootaProfile = KootaProfile.POPULAR


class HoraryRequest(BaseModel):
    number: int = Field(ge=1, le=249)
    #: Moment of the question; a naive value is taken as UTC.
    moment: datetime
    place: PlaceInput
    settings: Settings | None = None
