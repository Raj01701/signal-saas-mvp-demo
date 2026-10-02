"""A marriage match of two births, as JSON: what the Kundli Check page's match shows.

    uv run python scripts/match_report.py request.json > match.json

The request has ``groom`` and ``bride``, each a birth as ``chart_report.py`` takes it
(``date``, ``time``, ``place`` or ``latitude`` and ``longitude``, and optionally
``name`` and ``time_source``). The kootas, doshas, poruthams, Kuja dosha and papasamya
come from the engine (``match/``), the checks beyond the kootas from
``match/compatibility.py`` and each partner's marriage windows from that partner's life
reading (``life_windows``: the same windows the reading tells, strong ones only), all
with the settings most Indian software uses.

A couple already married adds ``married: true`` and, if they like, ``wedding_year`` (and
``wedding_month``): the wedding is then checked against both charts' windows, and the
windows ahead are read as times for married life rather than wedding dates.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, date, datetime, timedelta
from typing import Any

from chart_report import SIGN_NAMES, ordinal_suffix, resolve_place

from jyotish_engine.astro.bodies import Body
from jyotish_engine.chart import compute_chart
from jyotish_engine.match.compatibility import cross_checks, dasha_sandhi
from jyotish_engine.match.compute import compute_match
from jyotish_engine.models import (
    BirthInput,
    BirthTimeSource,
    ChartResult,
    LifeWindowOut,
    MaritalInput,
    MaritalStatus,
    MatchOut,
)
from jyotish_engine.predict import life_windows
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


def _strong_marriage(windows: list[LifeWindowOut]) -> list[LifeWindowOut]:
    return [w for w in windows if w.domain is Domain.MARRIAGE and w.strength == "strong"]


def _windows(windows: list[LifeWindowOut], today: date) -> list[dict[str, Any]]:
    """The partner's strong marriage windows in the coming years, as their reading tells
    them, in order of time."""
    until = date(today.year + YEARS_AHEAD, today.month, 1)
    ahead = [
        w
        for w in _strong_marriage(windows)
        if w.end > today and w.start < until and w.tone != "hard"
    ]
    return [
        {
            "start": w.start.isoformat(),
            "end": w.end.isoformat(),
            "when": f"{w.when} {w.ages}",
            "confidence": w.agreement,
            "periods": w.periods,
        }
        for w in ahead[:4]
    ]


def _wedding(
    request: dict[str, Any], births: tuple[date, date], today: date
) -> tuple[date, date] | None:
    """The wedding as a span of days (its month, or its year), when a married couple gave it."""
    year = request.get("wedding_year")
    if not request.get("married") or year in (None, ""):
        return None
    year = int(year)
    number = request.get("wedding_month")
    if number in (None, ""):
        start, end = date(year, 1, 1), date(year + 1, 1, 1)
    else:
        number = int(number)
        if not 1 <= number <= 12:
            raise ValueError("the wedding month must be 1 to 12")
        start, end = date(year, number, 1), date(year + number // 12, number % 12 + 1, 1)
    if start > today or any(end.year - born.year < 12 for born in births):
        raise ValueError("the wedding must come after both partners turned 12 and not after today")
    return start, end


def _wedding_fit(
    windows: list[LifeWindowOut], name: str, wedding: tuple[date, date]
) -> dict[str, Any]:
    """One partner's strong marriage windows around the wedding: inside one, within a year
    of one, or further away."""
    start, end = wedding
    strong = _strong_marriage(windows)
    if not strong:
        text = f"{name}'s chart shows no strong window for marriage."
        return {"fit": "outside", "window": None, "text": text}

    def gap(w: LifeWindowOut) -> int:
        if w.start < end and start < w.end:
            return 0
        return (w.start - end).days if w.start >= end else (start - w.end).days

    nearest = min(strong, key=lambda w: (gap(w), w.start))
    when = f"{nearest.when} {nearest.ages}"
    days = gap(nearest)
    if days == 0:
        fit, text = (
            "inside",
            f"{name}'s chart had a window for marriage in {when}, and the wedding falls inside it.",
        )
    elif days <= 366:
        fit, text = (
            "near",
            f"{name}'s chart had a window for marriage in {when}, within a year of the wedding.",
        )
    else:
        fit, text = (
            "outside",
            f"The wedding did not fall in one of {name}'s windows for marriage; the nearest "
            f"was {when}.",
        )
    return {"fit": fit, "window": when, "text": text}


def _overlap(a: list[dict[str, Any]], b: list[dict[str, Any]]) -> list[str]:
    out = []
    for x in a:
        for y in b:
            start, end = max(x["start"], y["start"]), min(x["end"], y["end"])
            if start < end:
                first = date.fromisoformat(start)
                last = date.fromisoformat(end) - timedelta(days=1)
                out.append(
                    _month(first)
                    if (first.year, first.month) == (last.year, last.month)
                    else f"{_month(first)} to {_month(last)}"
                )
    return out


def _person(
    request: dict[str, Any],
    chart: ChartResult,
    place_out: dict[str, Any],
    match: MatchOut,
    role: str,
    today: date,
    windows: list[LifeWindowOut],
) -> dict[str, Any]:
    moon = next(g for g in chart.grahas if g.body is Body.MOON)
    kuja = match.groom_kuja if role == "groom" else match.bride_kuja
    papa = match.groom_papa if role == "groom" else match.bride_papa
    age = _age(chart, today)
    return {
        "name": _display_name(request.get("name"), "Groom" if role == "groom" else "Bride"),
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
        "windows": _windows(windows, today) if age >= ADULT else [],
    }


def _display_name(name: Any, fallback: str) -> str:
    """The name as typed, capitalised when it was typed all in lower case."""
    text = " ".join(str(name or "").split())
    if not text:
        return fallback
    return text if any(c.isupper() for c in text) else text.title()


#: Other software's tables, by profile.
PROFILE_LABELS = {"maitreya": "the Maitreya program's tables"}


def _hours(value: float) -> str:
    if value < 1:
        return f"{round(value * 60)} minutes"
    return f"{value:.0f} hour{'s' if round(value) != 1 else ''}"


def _precision(name: str, before: float, after: float) -> dict[str, str]:
    """Whether a slightly wrong birth time could change the score: how long the Moon kept
    the nakshatra and sign (and Vashya half) that matching reads."""
    margin = min(before, after)
    span = f"{_hours(before)} before and {_hours(after)} after the given time"
    if margin >= 3:
        return {
            "tone": "good",
            "text": f"{name}'s Moon keeps the same nakshatra and sign from {span}, so a "
            "birth time off by an hour or two does not change the score.",
        }
    if margin >= 1:
        return {
            "tone": "mixed",
            "text": f"{name}'s Moon keeps the same nakshatra and sign from {span}; a birth "
            "time off by more than that would change the score.",
        }
    return {
        "tone": "hard",
        "text": f"{name}'s Moon changes nakshatra or sign within {_hours(margin)} of the "
        "given time, so the score depends on an exact birth time.",
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
    married = bool(request.get("married"))
    births = (groom.birth.local_datetime.date(), bride.birth.local_datetime.date())
    wedding = _wedding(request, births, today)
    # Each partner's windows as their own reading tells them: married life for a married
    # couple (checked against the wedding when given), openings for marriage otherwise.
    marital = (
        MaritalInput(
            status=MaritalStatus.MARRIED,
            wedding_year=wedding[0].year if wedding else None,
            wedding_month=wedding[0].month
            if wedding and request.get("wedding_month") not in (None, "")
            else None,
        )
        if married
        else MaritalInput(status=MaritalStatus.SINGLE)
    )
    windows = {
        role: life_windows(chart, today, gender=gender, marital=marital)
        for role, chart, gender in (("groom", groom, "male"), ("bride", bride, "female"))
    }
    people = {
        role: _person(request[role], chart, place, match, role, today, windows[role])
        for role, chart, place in (
            ("groom", groom, groom_place),
            ("bride", bride, bride_place),
        )
    }
    adults = all(p["age"] >= ADULT for p in people.values())
    sandhi = dasha_sandhi(groom, bride, today)
    timing_notes = []
    wedding_out = None
    if wedding is not None:
        given = (
            str(wedding[0].year)
            if request.get("wedding_month") in (None, "")
            else _month(wedding[0])
        )
        fits = {
            role: _wedding_fit(windows[role], people[role]["name"], wedding)
            for role in ("groom", "bride")
        }
        wedding_out = {"when": given, **fits}
        inside = sum(f["fit"] == "inside" for f in fits.values())
        close = sum(f["fit"] != "outside" for f in fits.values())
        if inside == 2:
            verdict = (
                "Both charts had a marriage window at that time, so their timing fits your life."
            )
        elif close == 2:
            verdict = (
                "Both charts had a marriage window at or within a year of that time, so their "
                "timing broadly fits your life."
            )
        elif close == 1:
            verdict = "One of the two charts had a marriage window at or close to that time."
        else:
            verdict = (
                "Neither chart marks that time for marriage; life events do not always follow "
                "the chart's timing, but if other dates are off too, the birth times may need "
                "checking."
            )
        timing_notes.append(f"You married in {given}. {verdict}")
    if adults:
        overlap = _overlap(people["groom"]["windows"], people["bride"]["windows"])
        if married and overlap:
            timing_notes.append(
                "Ahead, both charts emphasise married life together in "
                + "; ".join(overlap)
                + ": good times for shared plans."
            )
        elif married:
            pass
        elif overlap:
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
            "(dasha sandhi), a time of adjustment for the couple."
            if married
            else "Both partners' main periods (mahadashas) change within a year of each other "
            "(dasha sandhi), a time traditionally avoided for the wedding itself."
        )
    for hostile in sandhi.hostile:
        timing_notes.append(f"Note {hostile}, a junction named as difficult in tradition.")
    return {
        "today": today.isoformat(),
        "groom": people["groom"],
        "bride": people["bride"],
        "adults": adults,
        "married": married,
        "wedding": wedding_out,
        "score": match.ashtakoota_total,
        "maximum": 36,
        "verdict": _verdict(match),
        "variants": [
            {
                "profile": v.profile,
                "label": PROFILE_LABELS.get(v.profile, v.profile),
                "total": v.total,
                "differences": [
                    f"{KOOTAS.get(d.name, (d.name, ''))[0]} {d.variant_points:g} instead of "
                    f"{d.points:g}"
                    for d in v.differences
                ],
            }
            for v in match.variants
            if v.differences
        ],
        "precision": [
            _precision(people[role]["name"], margin.holds_before_hours, margin.holds_after_hours)
            for role, margin in (("groom", match.groom_moon), ("bride", match.bride_moon))
            if margin is not None
        ],
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
            "Points follow the tables Indian matchmaking guides and apps print, read with the "
            "bride's side down the rows as they print them (for Gana, a Deva bride with a "
            "Manushya groom gets 6 and the reverse 5). Some programs read a few cells "
            "differently, so their totals can differ by a point or two; where the best-known "
            "alternative tables give another total, it is shown alongside.",
            "A score is a traditional guide, not a verdict on two people: understanding, "
            "shared values and effort matter at least as much. Consider it alongside a "
            "conversation with an experienced astrologer.",
            *(
                [
                    "You are already married: the score describes how the two charts fit by "
                    "tradition, not how your marriage is or will be."
                ]
                if married
                else []
            ),
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
