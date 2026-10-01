"""A full report for one birth, as JSON: what the "try it" page shows.

    uv run python scripts/chart_report.py request.json > report.json

The request is a JSON object: ``date`` (YYYY-MM-DD), ``time`` (HH:MM or HH:MM:SS,
local clock time), ``place`` (a place name) or ``latitude`` and ``longitude``, and
optionally ``name``, ``gender`` ("male" or "female"), ``time_source`` and
``uncertainty_minutes``. Everything comes from the engine and the knowledge base with
the Classic Parashari settings; the plain-language reading is the offline template
narrator's.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from jyotish_api.narrative.evidence import build_bundle
from jyotish_api.narrative.narrators import TemplateNarrator
from jyotish_api.narrative.service import write_report
from jyotish_engine.chart import compute_chart
from jyotish_engine.core.varga import varga_sign
from jyotish_engine.models import BirthInput, BirthTimeSource, ChartResult, PlaceInput
from jyotish_engine.panchanga.day import compute_panchanga
from jyotish_engine.place.geocode import search_places
from jyotish_engine.predict import life_reading
from jyotish_engine.predict.timeline import compute_predictions
from jyotish_engine.rules.yogas import compute_yogas
from jyotish_engine.sensitivity import compute_sensitivity
from jyotish_engine.settings import Settings

ABBREVIATIONS = {
    "sun": "Su",
    "moon": "Mo",
    "mars": "Ma",
    "mercury": "Me",
    "jupiter": "Ju",
    "venus": "Ve",
    "saturn": "Sa",
    "rahu": "Ra",
    "ketu": "Ke",
}
SIGN_NAMES = (
    "Mesha",
    "Vrishabha",
    "Mithuna",
    "Karka",
    "Simha",
    "Kanya",
    "Tula",
    "Vrishchika",
    "Dhanu",
    "Makara",
    "Kumbha",
    "Meena",
)


def dms(degrees: float) -> str:
    total = round(degrees * 3600)
    return f"{total // 3600:02d}°{total % 3600 // 60:02d}′{total % 60:02d}″"


def sign_label(value: str) -> str:
    """ "sign 5" (1-based) as the sign's name; other values unchanged."""
    number = value.removeprefix("sign ").strip()
    return SIGN_NAMES[int(number) - 1] if value.startswith("sign ") and number.isdigit() else value


def time_note(factors: list[Any]) -> str:
    """How exact the birth time must be, in plain words."""
    by_name = {f.name: f for f in factors}
    notes = []
    lagna = by_name.get("Lagna")
    if lagna and lagna.minutes_before is not None and lagna.minutes_after is not None:
        notes.append(
            "Your rising sign stays the same if the true birth time is up to "
            f"{lagna.minutes_before:.0f} minutes earlier or "
            f"{lagna.minutes_after:.0f} minutes later."
        )
    d9 = by_name.get("D9 lagna")
    if d9 and d9.minutes_before is not None and d9.minutes_after is not None:
        notes.append(
            "The finer divisional readings change within "
            f"{min(d9.minutes_before, d9.minutes_after):.0f} minutes, so treat those with care "
            "unless the time is from a birth record."
        )
    return " ".join(notes)


def resolve_place(request: dict[str, Any]) -> tuple[PlaceInput, dict[str, Any]]:
    """Coordinates as given, or the best gazetteer match for the place name."""
    name = str(request.get("place") or "").strip()
    if request.get("latitude") not in (None, "") and request.get("longitude") not in (None, ""):
        lat, lon = float(request["latitude"]), float(request["longitude"])
        return PlaceInput(name=name or f"{lat:.4f}, {lon:.4f}", latitude=lat, longitude=lon), {
            "name": name or "Coordinates",
            "latitude": lat,
            "longitude": lon,
            "matched": "coordinates as entered",
            "alternatives": [],
        }
    matches = search_places(name, limit=5) if name else []
    if not matches and "," in name:
        matches = search_places(name.split(",")[0].strip(), limit=5)
    if not matches:
        raise ValueError(
            f'no place called "{name}" was found; enter latitude and longitude instead'
        )
    wanted = name.split(",")[0].strip().lower()
    best = next((p for p in matches if p.name.lower() == wanted), matches[0])
    alternatives = [
        f"{p.name} ({p.country_code}, {p.latitude:.3f}, {p.longitude:.3f})"
        for p in matches
        if p is not best
    ]
    place = PlaceInput(name=best.name, latitude=best.latitude, longitude=best.longitude)
    return place, {
        "name": f"{best.name}, {best.country_code}",
        "latitude": best.latitude,
        "longitude": best.longitude,
        "matched": f'best match for "{name}" (population {best.population:,})',
        "alternatives": alternatives,
    }


def birth_panchanga(chart: ChartResult, zone: ZoneInfo) -> dict[str, str]:
    """The five limbs at the moment of birth (the Hindu day runs sunrise to sunrise)."""
    moment = chart.time.interpretation.utc
    place = chart.birth.place
    day = chart.birth.local_datetime.date()
    panchanga = compute_panchanga(day, place, chart.settings, chart.time.zone)
    if moment < panchanga.sunrise:
        panchanga = compute_panchanga(
            day - timedelta(days=1), place, chart.settings, chart.time.zone
        )

    def at(spans: list[Any]) -> Any:
        return next((s for s in spans if s.start <= moment < s.end), spans[0])

    tithi = at(panchanga.tithis)
    return {
        "vara": panchanga.vara,
        "tithi": f"{tithi.name} ({tithi.paksha} paksha)",
        "nakshatra": at(panchanga.nakshatras).name,
        "yoga": at(panchanga.yogas).name,
        "karana": at(panchanga.karanas).name,
        "sunrise": panchanga.sunrise.astimezone(zone).strftime("%H:%M"),
        "sunset": panchanga.sunset.astimezone(zone).strftime("%H:%M"),
    }


def report(request: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    today = today or datetime.now(UTC).date()
    place, place_out = resolve_place(request)
    clock = str(request["time"]).strip()
    local = datetime.fromisoformat(
        f"{request['date']}T{clock if clock.count(':') == 2 else clock + ':00'}"
    )
    source = str(request.get("time_source") or "unknown")
    uncertainty = request.get("uncertainty_minutes")
    birth = BirthInput(
        local_datetime=local,
        place=place,
        time_source=BirthTimeSource(source)
        if source in {s.value for s in BirthTimeSource}
        else BirthTimeSource.UNKNOWN,
        uncertainty_minutes=float(uncertainty) if uncertainty not in (None, "") else None,
    )
    gender = request.get("gender") if request.get("gender") in ("male", "female") else None
    chart = compute_chart(birth, Settings())
    zone = ZoneInfo(chart.time.zone) if chart.time.zone else ZoneInfo("UTC")

    def local_date(value: datetime) -> str:
        return value.astimezone(zone).strftime("%Y-%m-%d")

    lagna = chart.ascendant
    grahas = [
        {
            "body": str(g.body.value).title(),
            "abbr": ABBREVIATIONS.get(str(g.body.value), str(g.body.value)[:2].title()),
            "sign_index": int(g.sign),
            "sign": g.sign_name,
            "degree": dms(g.degrees_in_sign),
            "nakshatra": g.nakshatra.name,
            "pada": g.nakshatra.pada,
            "lord": str(g.nakshatra.lord.value).title(),
            "house": g.house,
            "dignity": str(g.dignity.value).replace("_", " ") if g.dignity else "",
            "retrograde": g.retrograde,
            "combust": g.combust,
            "d9_sign_index": int(varga_sign(g.sidereal_longitude, 9)),
        }
        for g in chart.grahas
        if str(g.body.value) in ABBREVIATIONS
    ]
    now = datetime(today.year, today.month, today.day, 12, tzinfo=UTC)
    table = chart.dashas.vimshottari
    running = sorted(
        (p for p in table.periods if p.start <= now < p.end), key=lambda p: len(p.lords)
    )
    current_md = running[0].lords[0] if running else None
    yogas = compute_yogas(chart, gender=gender)
    predictions = compute_predictions(
        chart,
        today.replace(day=1),
        (today.replace(day=1) + timedelta(days=370)).replace(day=1),
        gender=gender,
    )
    narrative = write_report(build_bundle(chart, today=today, gender=gender), TemplateNarrator())
    sensitivity = compute_sensitivity(chart)
    name = str(request.get("name") or "").strip() or None
    life = life_reading(chart, today, gender=gender, name=name)
    interpretation = chart.time.interpretation
    return {
        "life": life.model_dump(mode="json"),
        "time_note": time_note(sensitivity.factors),
        "input": {
            k: request.get(k)
            for k in (
                "name",
                "date",
                "time",
                "place",
                "latitude",
                "longitude",
                "gender",
                "time_source",
                "uncertainty_minutes",
            )
        },
        "place": {**place_out, "zone": chart.time.zone},
        "time": {
            "local": local.strftime("%Y-%m-%d %H:%M:%S"),
            "utc": interpretation.utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "standard": interpretation.label,
            "utc_offset_hours": round(interpretation.utc_offset_seconds / 3600, 4),
            "confidence": str(chart.time.confidence.value),
            "warnings": list(chart.time.warnings),
            "alternatives": [
                f"{a.label}: {a.utc.strftime('%Y-%m-%d %H:%M UTC')}"
                for a in chart.time.alternatives
            ],
        },
        "settings": (
            f"{chart.ayanamsa.label} ayanamsa {dms(chart.ayanamsa.true)}, true nodes, "
            "whole-sign houses, Vimshottari with the "
            f"{chart.dashas.year.value.replace('_', ' ')} year"
        ),
        "engine": {"version": chart.engine_version, "ephemeris": chart.ephemeris.name},
        "lagna": {
            "sign_index": int(lagna.sign),
            "sign": lagna.sign_name,
            "degree": dms(lagna.degrees_in_sign),
            "nakshatra": lagna.nakshatra.name,
            "pada": lagna.nakshatra.pada,
            "lord": str(lagna.nakshatra.lord.value).title(),
            "d9_sign_index": int(varga_sign(lagna.sidereal_longitude, 9)),
        },
        "grahas": grahas,
        "sign_names": list(SIGN_NAMES),
        "birth_panchanga": birth_panchanga(chart, zone),
        "sensitivity": [
            {
                "name": f.name,
                "value": sign_label(f.value),
                "before": f.minutes_before,
                "after": f.minutes_after,
                "fragile": f.fragile,
            }
            for f in sensitivity.factors
        ],
        "dasha": {
            "birth": (
                f"{str(table.birth_lord.value).title()} mahadasha, "
                f"{table.balance_years:.2f} years left at birth"
            ),
            "mahadashas": [
                {
                    "lord": str(p.lords[0].value).title(),
                    "start": local_date(p.start),
                    "end": local_date(p.end),
                    "current": p.lords[0] == current_md and p.start <= now < p.end,
                }
                for p in table.periods
                if len(p.lords) == 1
            ],
            "antardashas": [
                {
                    "lords": " / ".join(str(b.value).title() for b in p.lords),
                    "start": local_date(p.start),
                    "end": local_date(p.end),
                    "current": p.start <= now < p.end,
                }
                for p in table.periods
                if len(p.lords) == 2 and current_md is not None and p.lords[0] == current_md
            ],
            "running": [
                {
                    "lords": " / ".join(str(b.value).title() for b in p.lords),
                    "end": local_date(p.end),
                }
                for p in running
            ],
        },
        "yogas": [
            {
                "name": y.name,
                "category": str(y.category.value).replace("_", " "),
                "polarity": str(y.polarity.value),
                "summary": y.summary or y.description,
                "evidence": y.evidence[:3],
                "sources": [s.text for s in y.sources[:2]],
            }
            for y in yogas.present
        ],
        "cancelled_yogas": [
            f"{y.name}: {'; '.join(y.cancel_evidence[:1])}" for y in yogas.cancelled
        ],
        "report": {
            "sections": [
                {"heading": s.heading, "paragraphs": [p.text for p in s.paragraphs]}
                for s in narrative.report.sections
            ],
            "disclaimer": narrative.disclaimer,
        },
        "windows": sorted(
            (
                {
                    "domain": str(d.domain.value).replace("_", " "),
                    "start": str(w.start),
                    "end": str(w.end),
                    "confidence": w.confidence,
                    "tone": round(w.tone, 2),
                }
                for d in predictions.domains
                for w in d.windows
            ),
            key=lambda w: w["start"],
        ),
        "promises": sorted(
            (
                {
                    "domain": str(d.domain.value).replace("_", " "),
                    "score": round(d.promise.score, 2),
                }
                for d in predictions.domains
            ),
            key=lambda p: -p["score"],
        ),
    }


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        with open(argv[1], encoding="utf-8") as handle:
            request = json.load(handle)
    else:
        request = json.load(sys.stdin)
    try:
        out = report(request)
    except ValueError as error:  # the input's fault: say what to fix
        out = {"error": str(error), "input": request}
    json.dump(out, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
