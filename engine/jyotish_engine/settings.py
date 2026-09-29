"""Calculation settings and presets that reproduce trusted tools.

Every chart stores its settings and a short hash of them, so a reading can always
be reproduced exactly.
"""

from __future__ import annotations

import hashlib
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, model_validator

from jyotish_engine.astro.ayanamsa import Ayanamsa
from jyotish_engine.astro.houses import HouseSystem
from jyotish_engine.astro.positions import NodeType
from jyotish_engine.astro.riseset import SunriseDefinition


class DashaYear(StrEnum):
    """Length of the year used to convert dasha periods to calendar dates."""

    SIDEREAL = "sidereal"  # 365.256363 days
    JULIAN = "julian"  # 365.25 days
    TROPICAL = "tropical"  # 365.242190 days
    SAVANA = "savana"  # 360 days


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
    bhava_system: HouseSystem = HouseSystem.SRIPATI
    sunrise: SunriseDefinition = SunriseDefinition.HINDU
    dasha_year: DashaYear = DashaYear.SIDEREAL
    include_outer_planets: bool = False

    @model_validator(mode="after")
    def _check_user_ayanamsa(self) -> Settings:
        if self.ayanamsa is Ayanamsa.USER and self.user_ayanamsa_j2000 is None:
            raise ValueError("user_ayanamsa_j2000 is required for a user-defined ayanamsa")
        if self.bhava_system is HouseSystem.WHOLE_SIGN:
            raise ValueError(
                "bhava_system must be a quadrant or equal system; "
                "whole-sign houses are always provided"
            )
        return self

    def fingerprint(self) -> str:
        """Short, stable hash of the settings (16 hex characters)."""
        canonical = self.model_dump_json(exclude_none=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


PRESETS: dict[Preset, Settings] = {
    Preset.CLASSIC_PARASHARI: Settings(),
    Preset.DRIK_COMPATIBLE: Settings(sunrise=SunriseDefinition.UPPER_LIMB_REFRACTION),
    Preset.KP: Settings(
        ayanamsa=Ayanamsa.KRISHNAMURTI,
        bhava_system=HouseSystem.PLACIDUS,
        dasha_year=DashaYear.JULIAN,
    ),
    Preset.PVR_JHORA_STYLE: Settings(ayanamsa=Ayanamsa.TRUE_PUSHYA),
}


def preset(name: Preset) -> Settings:
    return PRESETS[name]
