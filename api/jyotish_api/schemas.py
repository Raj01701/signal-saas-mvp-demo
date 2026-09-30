"""Request bodies of the compute routes."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from jyotish_engine.match.tables import KootaProfile
from jyotish_engine.models import BirthInput, PlaceInput
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
