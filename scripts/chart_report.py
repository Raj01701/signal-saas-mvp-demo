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
from jyotish_engine.annual.varshaphal import compute_varshaphal
from jyotish_engine.astro.bodies import Body
from jyotish_engine.astro.time import datetime_to_jd, jd_to_datetime
from jyotish_engine.chart import compute_chart
from jyotish_engine.core.varga import varga_sign
from jyotish_engine.models import BirthInput, BirthTimeSource, ChartResult, PlaceInput
from jyotish_engine.panchanga.day import compute_panchanga
from jyotish_engine.place.geocode import dms as place_dms
from jyotish_engine.place.geocode import parse_coordinates, seconds_per_km
from jyotish_engine.place.geocode import resolve_place as find_place
from jyotish_engine.predict import life_reading
from jyotish_engine.predict.timeline import compute_predictions
from jyotish_engine.rectify.events import EventKind
from jyotish_engine.rectify.search import LifeEvent, rectify
from jyotish_engine.rules.schema import Domain
from jyotish_engine.rules.yogas import compute_yogas
from jyotish_engine.sensitivity import compute_sensitivity
from jyotish_engine.settings import Preset, preset
from jyotish_engine.transit.timeline import sign_timeline

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


#: How each dasha-year convention reads in the settings line.
YEAR_WORDS = {
    "julian": "365.25-day",
    "sidereal": "sidereal (365.256-day)",
    "true_sidereal": "true solar",
    "tropical": "tropical (365.242-day)",
    "savana": "360-day",
}


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


def _place_out(name: str, lat: float, lon: float, **extra: Any) -> dict[str, Any]:
    return {
        "name": name,
        "latitude": lat,
        "longitude": lon,
        "dms": place_dms(lat, lon),
        "map_url": f"https://www.google.com/maps/search/?api=1&query={lat:.5f},{lon:.5f}",
        "alternatives": [],
        "ambiguous": False,
        **extra,
    }


def resolve_place(request: dict[str, Any]) -> tuple[PlaceInput, dict[str, Any]]:
    """Coordinates as given (typed or pasted from a map), or the gazetteer's match for the
    place name, using the state or country written after a comma."""
    name = str(request.get("place") or "").strip()
    if request.get("latitude") not in (None, "") and request.get("longitude") not in (None, ""):
        lat, lon = float(request["latitude"]), float(request["longitude"])
        label = name or f"{lat:.4f}, {lon:.4f}"
        return PlaceInput(name=label, latitude=lat, longitude=lon), _place_out(
            label, lat, lon, matched="coordinates as entered", source="coordinates as entered"
        )
    pasted = parse_coordinates(name)
    if pasted is not None:
        lat, lon = pasted
        label = f"{lat:.5f}, {lon:.5f}"
        return PlaceInput(name=label, latitude=lat, longitude=lon), _place_out(
            label, lat, lon, matched="coordinates as entered", source="coordinates as entered"
        )
    if not name:
        raise ValueError("enter a place name or its coordinates")
    found = find_place(name)
    alternatives = [f"{p.label} ({p.latitude:.4f}, {p.longitude:.4f})" for p in found.alternatives]
    place = PlaceInput(name=found.label, latitude=found.latitude, longitude=found.longitude)
    return place, _place_out(
        found.label,
        found.latitude,
        found.longitude,
        matched=found.how,
        alternatives=alternatives,
        ambiguous=found.ambiguous,
        source="GeoNames town centre",
    )


def transits_ahead(chart: ChartResult, today: date, years: int = 10) -> list[dict[str, Any]]:
    """Where Saturn, Jupiter and Rahu travel over the coming years, counted from the
    natal Moon and the rising sign, for questions about future years."""
    start = datetime_to_jd(datetime(today.year, today.month, today.day, tzinfo=UTC))
    end = min(start + years * 365.25, chart.ephemeris.jd_end - 2.0)
    moon = next(int(g.sign) for g in chart.grahas if g.body is Body.MOON)
    lagna = int(chart.ascendant.sign)
    out = []
    for body in (Body.SATURN, Body.JUPITER, Body.RAHU):
        for stay in sign_timeline(body, start, end, chart.settings):
            out.append(
                {
                    "body": body.value.title(),
                    "sign": SIGN_NAMES[stay.sign],
                    "from": jd_to_datetime(stay.start_jd_ut).strftime("%Y-%m-%d"),
                    "until": jd_to_datetime(stay.end_jd_ut).strftime("%Y-%m-%d"),
                    "house_from_moon": (stay.sign - moon) % 12 + 1,
                    "house_from_lagna": (stay.sign - lagna) % 12 + 1,
                }
            )
    return out


def rectify_report(request: dict[str, Any]) -> dict[str, Any]:
    """Candidate birth times that fit the person's dated life events best."""
    place, place_out = resolve_place(request)
    clock = str(request["time"]).strip()
    local = datetime.fromisoformat(
        f"{request['date']}T{clock if clock.count(':') == 2 else clock + ':00'}"
    )
    birth = BirthInput(local_datetime=local, place=place)
    gender = request.get("gender") if request.get("gender") in ("male", "female") else None
    chart = compute_chart(birth, preset(Preset.INDIAN_SOFTWARE))
    events = [
        LifeEvent(EventKind(str(e["kind"])), date.fromisoformat(str(e["date"])))
        for e in request.get("events") or []
        if str(e.get("kind")) in {k.value for k in EventKind}
    ]
    window = float(request.get("uncertainty_minutes") or 60)
    result = rectify(
        chart,
        events,
        uncertainty_minutes=min(max(window, 5.0), 180.0),
        step_seconds=30.0,
        gender=gender,
    )
    candidates = []
    for c in result.candidates:
        candidates.append(
            {
                "time": c.local_time.strftime("%H:%M:%S"),
                "clock": c.local_time.strftime("%-I:%M %p"),
                "offset_minutes": round(c.offset_minutes, 1),
                "share": round(c.share, 3),
                "lagna": f"{SIGN_NAMES[int(c.lagna)]} {dms(c.lagna_degrees)}",
                "navamsa_lagna": SIGN_NAMES[int(c.navamsa_lagna)],
                "moon": f"{c.moon_nakshatra} pada {c.moon_pada}",
                "events": [
                    {
                        "kind": ev.kind,
                        "date": ev.date.isoformat(),
                        "score": round(ev.score, 2),
                        "dasha": " / ".join(b.value.title() for b in ev.dasha[:3]),
                    }
                    for ev in c.events
                ],
            }
        )
    best = candidates[0] if candidates else None
    recorded = local.strftime("%-I:%M %p")
    if best is None:
        summary = "No candidate time could be scored; add more events."
    elif abs(best["offset_minutes"]) < 1:
        summary = (
            f"Your recorded time ({recorded}) fits your life events best; there is no reason "
            "from these events to change it."
        )
    else:
        direction = "earlier" if best["offset_minutes"] < 0 else "later"
        summary = (
            f"Your life events fit best with a birth at {best['clock']}, "
            f"{int(abs(best['offset_minutes']) + 0.5)} minutes {direction} than recorded "
            f"({recorded}), "
            f"with {best['share'] * 100:.0f}% of the weight among the candidates. Treat it as a "
            "suggestion: more events, especially exact dates, make it firmer."
        )
    return {
        "recorded": local.strftime("%H:%M:%S"),
        "window_minutes": result.uncertainty_minutes,
        "summary": summary,
        "candidates": candidates,
        "differences": result.differences,
        "notes": result.notes,
        "events_used": len(events),
        "place": place_out["name"],
    }


#: What Muntha's house in the annual chart traditionally brings (Tajika Neelakanthi):
#: house -> (tone, for an adult, for a child).
MUNTHA = {
    1: ("good", "personal initiative and fresh starts; health and confidence in focus",
        "confidence and fresh starts"),
    2: ("good", "income, savings and family", "family closeness and good habits"),
    3: ("good", "courage, effort, short journeys and siblings",
        "courage, hobbies and friendships"),
    4: ("mixed", "home, property and mother; keep worries at home in proportion",
        "home and family"),
    5: ("good", "studies, creativity and children", "studies and creativity"),
    6: ("hard", "work pressure and disputes; keep health and finances in order",
        "keeping health and routine steady"),
    7: ("mixed", "partnerships and marriage, which ask for patience and clear talk",
        "patience with friends and teamwork"),
    8: ("hard", "obstacles and delays; avoid risks and look after your health",
        "extra care and avoiding risks"),
    9: ("good", "one of the best placements: fortune, guidance, long journeys",
        "good fortune and guidance from teachers"),
    10: ("good", "one of the best placements: career, status and recognition",
         "achievement and recognition"),
    11: ("good", "one of the best placements: gains and wishes fulfilled",
         "gains and wishes fulfilled"),
    12: ("hard", "expenses, travel and rest; guard your savings", "travel, change and rest"),
}  # fmt: skip
#: Life areas of the year-by-year timeline, in reading order.
TIMELINE_AREAS = (
    (Domain.CAREER, "Career"),
    (Domain.WEALTH, "Money"),
    (Domain.MARRIAGE, "Marriage"),
    (Domain.CHILDREN, "Children"),
    (Domain.PROPERTY, "Home and property"),
    (Domain.EDUCATION, "Studies"),
    (Domain.TRAVEL, "Travel"),
    (Domain.SPIRITUALITY, "Inner life"),
)
ADULT_AREAS = {Domain.MARRIAGE, Domain.CHILDREN}


def annual_years(
    chart: ChartResult, years: list[int], age_now: int, today: date
) -> list[dict[str, Any]]:
    """The Tajika annual chart starting on the birthday in each of ``years``: Muntha's
    house and the lord of the year."""
    born = chart.birth.local_datetime.year
    out = []
    for year in years:
        completed = year - born
        if completed < 0:
            continue
        try:
            annual = compute_varshaphal(chart, completed)
        except ValueError:  # outside the ephemeris
            continue
        house = (int(annual.muntha) - int(annual.chart.ascendant.sign)) % 12 + 1
        tone, adult, young = MUNTHA[house]
        out.append(
            {
                "year": year,
                "from": annual.start.date().isoformat(),
                "muntha_house": house,
                "tone": tone,
                "year_lord": annual.year_lord.value.title(),
                "text": (
                    f"From your birthday in {annual.start:%B %Y}, the annual chart (Varshaphal) "
                    f"puts Muntha in the {house}{ordinal_suffix(house)} house: a year of "
                    f"{adult if age_now + (year - today.year) >= 18 else young}. "
                    f"The lord of the year is {annual.year_lord.value.title()}."
                ),
            }
        )
    return out


def ordinal_suffix(n: int) -> str:
    return "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def life_timeline(
    chart: ChartResult, today: date, gender: str | None, age: int, years_ahead: int = 10
) -> dict[str, Any]:
    """Each life area's emphasis by year, birth to ``years_ahead`` from now, scaled 0-1
    within the area, with the mahadashas for a band above it."""
    born = chart.birth.local_datetime.date()
    end = date(today.year + years_ahead + 1, 1, 1)
    timeline = compute_predictions(chart, born.replace(day=1), end, gender=gender)
    first = born.year
    years = list(range(first, end.year))
    by_domain = {d.domain: d for d in timeline.domains}
    rows = []
    for domain, label in TIMELINE_AREAS:
        if domain in ADULT_AREAS and age < 18:
            continue
        line = by_domain[domain]
        # Each year's average emphasis, so one strong month does not fill the year.
        totals, counts = [0.0] * len(years), [0] * len(years)
        for month, score in zip(timeline.months, line.scores, strict=True):
            index = month.year - first
            if 0 <= index < len(years):
                totals[index] += score
                counts[index] += 1
        yearly = [t / n if n else 0.0 for t, n in zip(totals, counts, strict=True)]
        top = max(yearly) or 1.0
        rows.append(
            {"key": domain.value, "label": label, "values": [round(v / top, 2) for v in yearly]}
        )
    mahadashas = [
        {
            "lord": p.lords[0].value.title(),
            "start": p.start.date().isoformat(),
            "end": p.end.date().isoformat(),
        }
        for p in chart.dashas.vimshottari.periods
        if len(p.lords) == 1 and p.end.year >= first and p.start.year < end.year
    ]
    return {"years": years, "today": today.isoformat(), "areas": rows, "mahadashas": mahadashas}


def place_note(place_out: dict[str, Any], factors: list[Any]) -> str:
    """How much the birthplace's precision matters for this chart, in plain words."""
    per_km = seconds_per_km(float(place_out["latitude"]))
    lagna = next((f for f in factors if f.name == "Lagna"), None)
    margin = (
        min(lagna.minutes_before, lagna.minutes_after)
        if lagna and lagna.minutes_before is not None and lagna.minutes_after is not None
        else None
    )
    text = (
        f"Each kilometre east or west of these coordinates moves the chart by about "
        f"{per_km:.1f} seconds of clock time, so 10 km is about {10 * per_km:.0f} seconds."
    )
    if margin is not None:
        text += (
            f" Your rising sign holds for {margin:.0f} minutes either way, so a town-centre "
            "position is precise enough unless the birthplace is a different town."
        )
    if place_out.get("source") == "GeoNames town centre":
        text += (
            " The coordinates are the town centre from GeoNames; map services may show a "
            "point a kilometre or so away, which makes no practical difference."
        )
    return text


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
    chart = compute_chart(birth, preset(Preset.INDIAN_SOFTWARE))
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
        "annual": annual_years(chart, [y.year for y in life.future], life.age, today),
        "timeline": life_timeline(chart, today, gender, life.age),
        "time_note": time_note(sensitivity.factors),
        "transits_ahead": transits_ahead(chart, today),
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
        "place": {
            **place_out,
            "zone": chart.time.zone,
            "note": place_note(place_out, sensitivity.factors),
        },
        "time": {
            "local": local.strftime("%Y-%m-%d %H:%M:%S"),
            "clock": local.strftime("%-I:%M %p on %A, %-d %B %Y"),
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
            f"{chart.ayanamsa.label} ayanamsa {dms(chart.ayanamsa.true)}, "
            f"{chart.settings.node_type.value} nodes, whole-sign houses, Vimshottari with the "
            f"{YEAR_WORDS.get(chart.dashas.year.value, chart.dashas.year.value)} year "
            "(as in most Indian software)"
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
            "all_antardashas": [
                {
                    "lords": " / ".join(str(b.value).title() for b in p.lords),
                    "start": local_date(p.start),
                    "end": local_date(p.end),
                }
                for p in table.periods
                if len(p.lords) == 2
                and p.end.date() > chart.birth.local_datetime.date()
                and p.start.date() < date(chart.birth.local_datetime.year + 95, 1, 1)
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
    paths = [a for a in argv[1:] if not a.startswith("--")]
    if paths:
        with open(paths[0], encoding="utf-8") as handle:
            request = json.load(handle)
    else:
        request = json.load(sys.stdin)
    try:
        out = rectify_report(request) if "--rectify" in argv else report(request)
    except ValueError as error:  # the input's fault: say what to fix
        out = {"error": str(error), "input": request}
    json.dump(out, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
