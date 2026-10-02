"""A marriage match of two births, as JSON: what the Kundli Check page's match shows.

    uv run python scripts/match_report.py request.json > match.json

The request has ``groom`` and ``bride``, each a birth as ``chart_report.py`` takes it
(``date``, ``time``, ``place`` or ``latitude`` and ``longitude``, and optionally
``name`` and ``time_source``). The kootas, doshas, poruthams, Kuja dosha and papasamya
come from the engine (``match/``), the checks beyond the kootas from
``match/compatibility.py`` and the marriage windows from the prediction timeline, all
with the settings most Indian software uses.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, date, datetime
from typing import Any

from chart_report import SIGN_NAMES, ordinal_suffix, resolve_place

from jyotish_engine.astro.bodies import Body
from jyotish_engine.chart import compute_chart
from jyotish_engine.match.compatibility import cross_checks, dasha_sandhi
from jyotish_engine.match.compute import compute_match
from jyotish_engine.models import BirthInput, BirthTimeSource, ChartResult, MatchOut
from jyotish_engine.predict.timeline import compute_predictions
from jyotish_engine.rules.schema import Domain
from jyotish_engine.settings import Preset, preset

ADULT = 18
YEARS_AHEAD = 10
KOOTAS: dict[str, tuple[str, str]] = {
    "varna": ("Varna", "outlook on work and duty"),
    "vashya": ("Vashya", "attraction and how the two influence each other"),
    "tara": ("Tara", "the fortune and well-being the two bring each other"),
    "yoni": ("Yoni", "physical and emotional intimacy"),
    "graha_maitri": ("Graha Maitri", "friendship and how the two minds meet"),
    "gana": ("Gana", "temperament"),
    "bhakoot": ("Bhakoot", "love, family welfare and shared finances"),
    "nadi": ("Nadi", "health and children; traditionally the weightiest koota"),
}
DOSHAS = {
    "nadi": "Nadi dosha: both Moons are in the same nadi",
    "bhakoot": "Bhakoot dosha: the Moon signs are 2/12, 5/9 or 6/8 apart",
    "gana": "Gana dosha: the temperaments clash",
}
PORUTHAMS = {
    "dina": "Dina (daily well-being)",
    "gana": "Gana (temperament)",
    "mahendra": "Mahendra (prosperity and children)",
    "stree_deergha": "Stree Deergha (the bride's well-being)",
    "yoni": "Yoni (intimacy)",
    "rasi": "Rasi (family harmony)",
    "rasyadhipati": "Rasyadhipati (friendship of the Moon-sign lords)",
    "vasya": "Vasya (attraction)",
    "rajju": "Rajju (long married life; the most important in the South)",
    "vedha": "Vedha (no obstruction between the stars)",
}
KUJA_FROM = {
    "dosha.kuja_lagna": "the lagna",
    "dosha.kuja_moon": "the Moon",
    "dosha.kuja_venus": "Venus",
}
REFERENCES = {"lagna": "the lagna", "Moon": "the Moon", "Venus": "Venus"}
CHECK_TITLES = {
    "lagna_lords": "Rising-sign lords",
    "navamsa_lagnas": "Navamsa (D9) rising signs",
    "groom_moon": "The groom's Moon in the bride's chart",
    "bride_moon": "The bride's Moon in the groom's chart",
}


def _birth(request: dict[str, Any]) -> tuple[BirthInput, dict[str, Any]]:
    place, place_out = resolve_place(request)
    clock = str(request["time"]).strip()
    local = datetime.fromisoformat(
        f"{request['date']}T{clock if clock.count(':') == 2 else clock + ':00'}"
    )
    source = str(request.get("time_source") or "unknown")
    birth = BirthInput(
        local_datetime=local,
        place=place,
        time_source=BirthTimeSource(source)
        if source in {s.value for s in BirthTimeSource}
        else BirthTimeSource.UNKNOWN,
    )
    return birth, place_out


def _age(chart: ChartResult, today: date) -> int:
    born = chart.birth.local_datetime.date()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def _month(day: date) -> str:
    return day.strftime("%B %Y")


def _windows(chart: ChartResult, gender: str, today: date) -> list[dict[str, Any]]:
    """The strongest marriage windows in the coming years, in order of time."""
    start = today.replace(day=1)
    end = start.replace(year=start.year + YEARS_AHEAD)
    timeline = compute_predictions(chart, start, end, gender=gender)
    marriage = next(d for d in timeline.domains if d.domain is Domain.MARRIAGE)
    best = sorted(marriage.windows, key=lambda w: -w.score)[:4]
    return [
        {
            "start": w.start.isoformat(),
            "end": w.end.isoformat(),
            "when": f"{_month(w.start)} to {_month(w.end)}",
            "confidence": w.confidence,
            "score": w.score,
        }
        for w in sorted(best, key=lambda w: w.start)
    ]


def _overlap(a: list[dict[str, Any]], b: list[dict[str, Any]]) -> list[str]:
    out = []
    for x in a:
        for y in b:
            start, end = max(x["start"], y["start"]), min(x["end"], y["end"])
            if start < end:
                out.append(
                    f"{_month(date.fromisoformat(start))} to {_month(date.fromisoformat(end))}"
                )
    return out


def _person(
    request: dict[str, Any],
    chart: ChartResult,
    place_out: dict[str, Any],
    match: MatchOut,
    role: str,
    today: date,
) -> dict[str, Any]:
    moon = next(g for g in chart.grahas if g.body is Body.MOON)
    kuja = match.groom_kuja if role == "groom" else match.bride_kuja
    papa = match.groom_papa if role == "groom" else match.bride_papa
    age = _age(chart, today)
    return {
        "name": str(request.get("name") or ("Groom" if role == "groom" else "Bride")),
        "age": age,
        "born": chart.birth.local_datetime.strftime("%-I:%M %p on %A, %-d %B %Y"),
        "place": place_out,
        "moon_sign": SIGN_NAMES[int(moon.sign)],
        "nakshatra": f"{moon.nakshatra.name}, pada {moon.nakshatra.pada}",
        "lagna": SIGN_NAMES[int(chart.ascendant.sign)],
        "manglik": kuja.manglik,
        "manglik_from": [KUJA_FROM.get(r, r) for r in kuja.present],
        "manglik_cancelled": [KUJA_FROM.get(r, r) for r in kuja.cancelled],
        "papa": papa.points,
        "papa_items": [
            f"{i.planet.value.title()} in the {i.house}{ordinal_suffix(i.house)} from "
            f"{REFERENCES.get(i.reference, i.reference)} ({i.points:g})"
            for i in papa.items
        ],
        "windows": _windows(chart, "male" if role == "groom" else "female", today)
        if age >= ADULT
        else [],
    }


def _koota_value(name: str, value: str, moon_sign: str) -> str:
    """The partner's side of a koota in words: the Moon sign for Bhakoot, a planet's name
    for Graha Maitri."""
    if name == "bhakoot":
        return f"Moon in {moon_sign}"
    if name == "graha_maitri":
        return value.title()
    return value


def _band(total: float) -> tuple[str, str]:
    if total < 18:
        return "below the traditional minimum of 18", "hard"
    if total <= 24:
        return "an acceptable match", "mixed"
    if total <= 32:
        return "a good match", "good"
    return "an excellent match", "good"


def _verdict(match: MatchOut) -> dict[str, Any]:
    total = match.ashtakoota_total
    band, tone = _band(total)
    open_doshas = [d for d in match.doshas if d.present and not d.cancelled]
    reasons = [f"Guna Milan {total:g} of 36: {band}."]
    for d in match.doshas:
        if d.present:
            state = "cancelled by " + "; ".join(d.exceptions) if d.cancelled else "not cancelled"
            reasons.append(f"{DOSHAS.get(d.name, d.name)}, {state}.")
    if not match.kuja_balanced:
        reasons.append("Only one partner is Manglik, so Mangal dosha is not balanced.")
    if not match.papasamya_balanced:
        reasons.append(
            f"Papasamya: the bride's papa points ({match.bride_papa.points:g}) exceed the "
            f"groom's ({match.groom_papa.points:g})."
        )
    rajju = next((p for p in match.dashakoota if p.name == "rajju"), None)
    rajju_fails = rajju is not None and not rajju.agrees and rajju.relieved_by is None
    if rajju_fails:
        reasons.append("Rajju porutham fails, which South Indian practice weighs heavily.")
    serious = total < 18 or any(d.name in ("nadi", "bhakoot") for d in open_doshas)
    cautions = (
        not match.kuja_balanced or not match.papasamya_balanced or bool(open_doshas) or rajju_fails
    )
    if serious:
        label, tone = "Not recommended by traditional matching", "hard"
    elif cautions:
        label, tone = "Acceptable, with points to consider", "mixed"
    elif total > 24:
        label, tone = "Recommended", "good"
    else:
        label, tone = "Acceptable", "mixed"
    return {"label": label, "tone": tone, "band": band, "reasons": reasons}


def report(request: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    today = today or datetime.now(UTC).date()
    settings = preset(Preset.INDIAN_SOFTWARE)
    groom_birth, groom_place = _birth(request["groom"])
    bride_birth, bride_place = _birth(request["bride"])
    groom = compute_chart(groom_birth, settings)
    bride = compute_chart(bride_birth, settings)
    match = compute_match(groom, bride)
    moon_signs = {
        role: SIGN_NAMES[int(next(g for g in chart.grahas if g.body is Body.MOON).sign)]
        for role, chart in (("groom", groom), ("bride", bride))
    }
    people = {
        "groom": _person(request["groom"], groom, groom_place, match, "groom", today),
        "bride": _person(request["bride"], bride, bride_place, match, "bride", today),
    }
    adults = all(p["age"] >= ADULT for p in people.values())
    sandhi = dasha_sandhi(groom, bride, today)
    timing_notes = []
    if adults:
        overlap = _overlap(people["groom"]["windows"], people["bride"]["windows"])
        if overlap:
            timing_notes.append(
                "Both charts favour marriage together in " + "; ".join(overlap) + "."
            )
        else:
            timing_notes.append(
                "The two charts' strongest marriage windows in the next ten years do not "
                "overlap; the later of the two partners' windows is usually the one to plan by."
            )
    if sandhi.within_a_year:
        timing_notes.append(
            "Both partners' main periods (mahadashas) change within a year of each other "
            "(dasha sandhi), a time traditionally avoided for the wedding itself."
        )
    for hostile in sandhi.hostile:
        timing_notes.append(f"Note {hostile}, a junction named as difficult in tradition.")
    return {
        "today": today.isoformat(),
        "groom": people["groom"],
        "bride": people["bride"],
        "adults": adults,
        "score": match.ashtakoota_total,
        "maximum": 36,
        "verdict": _verdict(match),
        "kootas": [
            {
                "key": k.name,
                "name": KOOTAS.get(k.name, (k.name, ""))[0],
                "meaning": KOOTAS.get(k.name, ("", ""))[1],
                "points": k.points,
                "maximum": k.maximum,
                "groom": _koota_value(k.name, k.groom, moon_signs["groom"]),
                "bride": _koota_value(k.name, k.bride, moon_signs["bride"]),
                "detail": k.detail,
            }
            for k in match.ashtakoota
        ],
        "doshas": [
            {
                "key": d.name,
                "name": DOSHAS.get(d.name, d.name),
                "present": d.present,
                "cancelled": d.cancelled,
                "exceptions": d.exceptions,
            }
            for d in match.doshas
        ],
        "manglik": {
            "groom": match.groom_kuja.manglik,
            "bride": match.bride_kuja.manglik,
            "balanced": match.kuja_balanced,
        },
        "papasamya": {
            "groom": match.groom_papa.points,
            "bride": match.bride_papa.points,
            "balanced": match.papasamya_balanced,
        },
        "poruthams": {
            "agreements": match.dashakoota_agreements,
            "items": [
                {
                    "key": p.name,
                    "name": PORUTHAMS.get(p.name, p.name),
                    "agrees": p.agrees,
                    "detail": p.detail,
                    "relieved_by": p.relieved_by,
                }
                for p in match.dashakoota
            ],
        },
        "checks": [
            {
                "key": c.key,
                "title": CHECK_TITLES.get(c.key, c.key),
                "tone": c.tone,
                "detail": c.detail,
            }
            for c in cross_checks(groom, bride)
        ],
        "timing": {
            "notes": timing_notes,
            "groom_changes": sandhi.groom_changes,
            "bride_changes": sandhi.bride_changes,
            "within_a_year": sandhi.within_a_year,
        },
        "notes": [
            "Matching follows the classical Ashtakoota (36 points) with the traditional "
            "exceptions, Mangal dosha from the lagna, the Moon and Venus, papasamya and the "
            "ten South Indian poruthams, with the Lahiri ayanamsa.",
            "A score is a traditional guide, not a verdict on two people: understanding, "
            "shared values and effort matter at least as much. Consider it alongside a "
            "conversation with an experienced astrologer.",
        ],
    }


def main(argv: list[str]) -> int:
    paths = [a for a in argv[1:] if not a.startswith("--")]
    if paths:
        with open(paths[0], encoding="utf-8") as handle:
            request = json.load(handle)
    else:
        request = json.load(sys.stdin)
    try:
        out = report(request)
    except (KeyError, ValueError) as error:  # the input's fault: say what to fix
        out = {"error": str(error)}
    json.dump(out, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
