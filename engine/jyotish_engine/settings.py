"""Calculation settings and presets that reproduce trusted tools.

Every chart stores its settings and a short hash of them, so a reading can always
be reproduced exactly.
"""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from jyotish_engine.astro.ayanamsa import Ayanamsa
from jyotish_engine.astro.houses import HouseSystem
from jyotish_engine.astro.positions import NodeType, PositionType
from jyotish_engine.astro.riseset import SunriseDefinition
from jyotish_engine.core.varga import VARGAS, VargaMethod


class DashaYear(StrEnum):
    """Length of the year used to convert dasha periods to calendar dates."""

    SIDEREAL = "sidereal"  # mean sidereal year, 365.256363 days
    #: The actual sidereal solar year containing the birth, from the Sun's entry
    #: into sidereal Aries (Mesha sankranti) before birth to the next one. It varies
    #: by a few minutes from year to year; PyJHora uses it by default.
    TRUE_SIDEREAL = "true_sidereal"
    JULIAN = "julian"  # 365.25 days
    TROPICAL = "tropical"  # 365.242190 days
    SAVANA = "savana"  # 360 days


#: Fixed year lengths in days (``TRUE_SIDEREAL`` is computed per chart).
DASHA_YEAR_DAYS: dict[DashaYear, float] = {
    DashaYear.SIDEREAL: 365.256363004,
    DashaYear.JULIAN: 365.25,
    DashaYear.TROPICAL: 365.24219,
    DashaYear.SAVANA: 360.0,
}


class Preset(StrEnum):
    CLASSIC_PARASHARI = "classic_parashari"
    DRIK_COMPATIBLE = "drik_compatible"
    KP = "kp"
    PVR_JHORA_STYLE = "pvr_jhora_style"


class Settings(BaseModel):
    """How a chart is calculated. Defaults are the Classic Parashari preset."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ayanamsa: Ayanamsa = Ayanamsa.LAHIRI
    user_ayanamsa_j2000: float | None = None
    node_type: NodeType = NodeType.TRUE
    position_type: PositionType = PositionType.APPARENT
    bhava_system: HouseSystem = HouseSystem.SRIPATI
    sunrise: SunriseDefinition = SunriseDefinition.HINDU
    dasha_year: DashaYear = DashaYear.SIDEREAL
    include_outer_planets: bool = False
    #: 8 includes Rahu among the chara karakas (Parashara); 7 excludes it (Jaimini).
    karaka_scheme: Literal[7, 8] = 8
    #: Per-division overrides of the Parashara varga rules, e.g. {24: "siddhamsa_from_leo"}.
    varga_methods: dict[int, VargaMethod] = Field(default_factory=dict)
    #: "common": Gulika at the start of Saturn's part, Mandi at its middle.
    #: "pvr_book": the reverse, as in P.V.R. Narasimha Rao's book.
    gulika_convention: Literal["common", "pvr_book"] = "common"
    node_aspects_5_9: bool = False

    @model_validator(mode="after")
    def _check(self) -> Settings:
        if self.ayanamsa is Ayanamsa.USER and self.user_ayanamsa_j2000 is None:
            raise ValueError("user_ayanamsa_j2000 is required for a user-defined ayanamsa")
        if self.bhava_system is HouseSystem.WHOLE_SIGN:
            raise ValueError(
                "bhava_system must be a quadrant or equal system; "
                "whole-sign houses are always provided"
            )
        unknown = set(self.varga_methods) - set(VARGAS)
        if unknown:
            raise ValueError(f"unsupported divisional charts: {sorted(unknown)}")
        return self

    def varga_method(self, division: int) -> VargaMethod:
        return self.varga_methods.get(division, VargaMethod.PARASHARA)

    def fingerprint(self) -> str:
        """Short, stable hash of the settings (16 hex characters)."""
        canonical = json.dumps(json.loads(self.model_dump_json()), sort_keys=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


PRESETS: dict[Preset, Settings] = {
    Preset.CLASSIC_PARASHARI: Settings(),
    Preset.DRIK_COMPATIBLE: Settings(sunrise=SunriseDefinition.UPPER_LIMB_REFRACTION),
    Preset.KP: Settings(
        ayanamsa=Ayanamsa.KRISHNAMURTI,
        bhava_system=HouseSystem.PLACIDUS,
        dasha_year=DashaYear.JULIAN,
    ),
    Preset.PVR_JHORA_STYLE: Settings(
        ayanamsa=Ayanamsa.TRUE_PUSHYA,
        position_type=PositionType.TRUE,
        dasha_year=DashaYear.TRUE_SIDEREAL,
        varga_methods={24: VargaMethod.SIDDHAMSA_FROM_LEO},
    ),
}


def preset(name: Preset) -> Settings:
    return PRESETS[name]
