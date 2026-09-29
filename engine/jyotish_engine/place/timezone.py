"""Turn a recorded local birth time into UTC, with honest ambiguity reporting.

The IANA tz database is the baseline, but it only guarantees accuracy after 1970 and
merges regions whose clocks differed earlier. For India, curated rules
(``overrides/india.yaml``) add Bombay Time, Calcutta Time and local mean time, and
flag windows where records are known to be ambiguous. The result always lists the
alternative interpretations so the user or astrologer can pick the right one.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml
from timezonefinder import TimezoneFinder

OVERRIDES_DIR = Path(__file__).with_name("overrides")
EARTH_RADIUS_KM = 6371.0088
INDIA_ZONES = frozenset({"Asia/Kolkata", "Asia/Calcutta"})


class TimeStandard(StrEnum):
    AUTO = "auto"
    ZONE = "zone"
    LMT = "lmt"
    BOMBAY_TIME = "bombay_time"
    CALCUTTA_TIME = "calcutta_time"
    FIXED_OFFSET = "fixed_offset"


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True, slots=True)
class TimeInterpretation:
    standard: TimeStandard
    label: str
    utc: datetime
    utc_offset_seconds: float
    note: str | None = None


@dataclass(frozen=True, slots=True)
class TimeResolution:
    local: datetime
    zone: str | None
    chosen: TimeInterpretation
    alternatives: tuple[TimeInterpretation, ...] = ()
    ambiguous: bool = False
    confidence: Confidence = Confidence.HIGH
    warnings: tuple[str, ...] = field(default_factory=tuple)


@lru_cache(maxsize=1)
def _finder() -> TimezoneFinder:
    return TimezoneFinder(in_memory=True)


@lru_cache(maxsize=1)
def _india_rules() -> dict[str, Any]:
    with (OVERRIDES_DIR / "india.yaml").open(encoding="utf-8") as handle:
        data: dict[str, Any] = yaml.safe_load(handle)
    return data


def timezone_for(latitude: float, longitude: float) -> str | None:
    """IANA zone name for a coordinate (offline lookup), or ``None`` at sea."""
    zone: str | None = _finder().timezone_at(lng=longitude, lat=latitude)
    return zone


def _parse_offset(text: str) -> float:
    sign = -1.0 if text.startswith("-") else 1.0
    parts = [int(p) for p in text.lstrip("+-").split(":")]
    while len(parts) < 3:
        parts.append(0)
    return sign * (parts[0] * 3600 + parts[1] * 60 + parts[2])


def _to_date(value: Any) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _fixed(
    local: datetime,
    offset_seconds: float,
    standard: TimeStandard,
    label: str,
    note: str | None = None,
) -> TimeInterpretation:
    utc = (local - timedelta(seconds=offset_seconds)).replace(tzinfo=UTC)
    return TimeInterpretation(standard, label, utc, offset_seconds, note)


def lmt_interpretation(local: datetime, longitude: float) -> TimeInterpretation:
    offset = longitude * 240.0  # four minutes of time per degree
    return _fixed(
        local,
        offset,
        TimeStandard.LMT,
        "Local Mean Time",
        "Clock time kept by the Sun's mean motion at the birthplace's longitude.",
    )


def zone_interpretations(local: datetime, zone: str) -> tuple[list[TimeInterpretation], list[str]]:
    """Interpretations under the tz database, handling DST folds and gaps."""
    tz = ZoneInfo(zone)
    warnings: list[str] = []
    candidates: list[TimeInterpretation] = []
    for fold in (0, 1):
        aware = local.replace(tzinfo=tz, fold=fold)
        offset = aware.utcoffset()
        assert offset is not None
        utc = aware.astimezone(UTC)
        interp = TimeInterpretation(
            TimeStandard.ZONE, f"{zone} (tz database)", utc, offset.total_seconds()
        )
        if all(c.utc != utc for c in candidates):
            candidates.append(interp)
    if len(candidates) == 2:
        warnings.append(
            "This local time occurs twice because clocks were turned back; "
            "the earlier occurrence is used unless you choose otherwise."
        )
    roundtrip = candidates[0].utc.astimezone(tz).replace(tzinfo=None)
    if roundtrip != local:
        warnings.append(
            "This local time did not exist because clocks were moved forward; check the record."
        )
    return candidates, warnings


def _india_auto(
    local: datetime,
    latitude: float,
    longitude: float,
    zone: str,
    zone_options: list[TimeInterpretation],
    warnings: list[str],
) -> TimeResolution:
    rules = _india_rules()
    day = local.date()
    alternatives: list[TimeInterpretation] = []

    for key, rule in rules["local_times"].items():
        area = rule["area"]
        inside = (
            _distance_km(latitude, longitude, area["latitude"], area["longitude"])
            <= area["radius_km"]
        )
        if not inside or not (_to_date(rule["from"]) <= day < _to_date(rule["until"])):
            continue
        city = _fixed(
            local,
            _parse_offset(rule["utc_offset"]),
            TimeStandard(key),
            rule["label"],
            " ".join(str(rule["note"]).split()),
        )
        ambiguous = day >= _to_date(rule["ambiguous_from"])
        others = [*zone_options, lmt_interpretation(local, longitude)]
        return TimeResolution(
            local,
            zone,
            city,
            tuple(others),
            ambiguous=ambiguous,
            confidence=Confidence.MEDIUM,
            warnings=tuple(warnings),
        )

    if day < _to_date(rules["lmt_before"]):
        lmt = lmt_interpretation(local, longitude)
        warnings.append(
            "Before Indian Standard Time (1906) most records used local mean time; "
            "the tz database uses Madras time instead."
        )
        return TimeResolution(
            local,
            zone,
            lmt,
            tuple(zone_options),
            ambiguous=True,
            confidence=Confidence.LOW,
            warnings=tuple(warnings),
        )

    ambiguous = False
    for advisory in rules["advisories"]:
        if _to_date(advisory["from"]) <= day < _to_date(advisory["until"]):
            warnings.append(" ".join(str(advisory["note"]).split()))
            ambiguous = True
            ist_plus_one = _fixed(
                local, 6.5 * 3600, TimeStandard.FIXED_OFFSET, "IST + 1 hour (war-time clock)"
            )
            if all(c.utc != ist_plus_one.utc for c in zone_options):
                alternatives.append(ist_plus_one)
    confidence = Confidence.HIGH if day.year >= 1970 and not ambiguous else Confidence.MEDIUM
    chosen, *rest = zone_options
    return TimeResolution(
        local,
        zone,
        chosen,
        tuple(rest + alternatives),
        ambiguous=ambiguous,
        confidence=confidence,
        warnings=tuple(warnings),
    )


def resolve_local_time(
    local: datetime,
    latitude: float,
    longitude: float,
    standard: TimeStandard = TimeStandard.AUTO,
    utc_offset_seconds: float | None = None,
    zone: str | None = None,
) -> TimeResolution:
    """Convert a naive local birth time to UTC.

    ``standard`` forces an interpretation. ``FIXED_OFFSET`` needs
    ``utc_offset_seconds``; ``zone`` overrides the coordinate lookup.
    """
    if local.tzinfo is not None:
        raise ValueError("pass the local time as recorded, without a timezone")
    zone = zone or timezone_for(latitude, longitude)

    if standard is TimeStandard.FIXED_OFFSET:
        if utc_offset_seconds is None:
            raise ValueError("FIXED_OFFSET requires utc_offset_seconds")
        chosen = _fixed(local, utc_offset_seconds, standard, "Fixed UTC offset")
        return TimeResolution(local, zone, chosen)
    if standard is TimeStandard.LMT:
        return TimeResolution(local, zone, lmt_interpretation(local, longitude))
    if standard in (TimeStandard.BOMBAY_TIME, TimeStandard.CALCUTTA_TIME):
        rule = _india_rules()["local_times"][standard.value]
        chosen = _fixed(local, _parse_offset(rule["utc_offset"]), standard, rule["label"])
        return TimeResolution(local, zone, chosen)

    if zone is None:
        lmt = lmt_interpretation(local, longitude)
        return TimeResolution(
            local,
            None,
            lmt,
            ambiguous=True,
            confidence=Confidence.LOW,
            warnings=("No time zone at these coordinates; local mean time assumed.",),
        )

    zone_options, warnings = zone_interpretations(local, zone)
    if standard is TimeStandard.ZONE:
        chosen, *rest = zone_options
        return TimeResolution(
            local, zone, chosen, tuple(rest), ambiguous=bool(rest), warnings=tuple(warnings)
        )

    if zone in INDIA_ZONES:
        return _india_auto(local, latitude, longitude, zone, zone_options, warnings)

    chosen, *rest = zone_options
    ambiguous = bool(rest) or any("did not exist" in w for w in warnings)
    if local.year < 1970:
        warnings.append(
            "Time-zone history before 1970 is incomplete in the tz database; "
            "verify the offset if the birth record allows."
        )
    confidence = Confidence.HIGH if local.year >= 1970 and not ambiguous else Confidence.MEDIUM
    return TimeResolution(
        local,
        zone,
        chosen,
        tuple(rest),
        ambiguous=ambiguous,
        confidence=confidence,
        warnings=tuple(warnings),
    )
