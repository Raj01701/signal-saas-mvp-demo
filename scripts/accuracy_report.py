"""Regenerate docs/ACCURACY.md from the golden fixtures.

Runs the engine over every reference case and records maximum and median
differences per quantity. Uses only the product environment: it reads the numeric
fixtures and never imports the AGPL oracle tools.

    uv run python scripts/accuracy_report.py
"""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jyotish_engine import ENGINE_VERSION
from jyotish_engine.annual.dashas import (
    SEVEN,
    patyayini_dashas,
    patyayini_scheme,
    patyayini_sub_periods,
)
from jyotish_engine.annual.returns import tithi_pravesha, varsha_pravesha
from jyotish_engine.annual.sahams import compute_sahams
from jyotish_engine.astro.ayanamsa import EPOCH_SYSTEMS, STAR_SYSTEMS, true_ayanamsa
from jyotish_engine.astro.bodies import EPHEMERIS_BODIES, GRAHAS, Body
from jyotish_engine.astro.ephemeris import get_ephemeris
from jyotish_engine.astro.houses import HouseSystem, chart_angles, quadrant_cusps
from jyotish_engine.astro.positions import (
    PositionType,
    angular_distance,
    mean_node_position,
    tropical_positions,
    true_node_position,
)
from jyotish_engine.astro.riseset import (
    SunriseDefinition,
    next_moonrise,
    next_moonset,
    next_sunrise,
    next_sunset,
)
from jyotish_engine.astro.series import jd_ut_to_tt
from jyotish_engine.astro.time import Instant
from jyotish_engine.core.varga import VargaMethod, varga_sign_index
from jyotish_engine.dasha.base import Period, SubPeriodRule, subdivide
from jyotish_engine.dasha.conditions import applicability
from jyotish_engine.dasha.nakshatra import DEFINITIONS, NakshatraDasha, mahadashas
from jyotish_engine.dasha.sign import SignDasha, SignPeriod, sign_mahadashas, sign_sub_periods
from jyotish_engine.dasha.years import true_sidereal_year_days
from jyotish_engine.panchanga.elements import Limb
from jyotish_engine.panchanga.timing import all_limb_spans
from jyotish_engine.rules.catalogue import default_catalogue
from jyotish_engine.rules.facts import ChartFacts
from jyotish_engine.settings import Settings
from jyotish_engine.transit.search import sign_ingresses, stations

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "engine" / "tests" / "fixtures" / "astro_swisseph.json"
OUT = ROOT / "docs" / "ACCURACY.md"
SAHAM_FIXTURE = ROOT / "engine" / "tests" / "fixtures" / "sahams_pyjhora.json"
PANCHANGA_FIXTURE = ROOT / "engine" / "tests" / "fixtures" / "panchanga_swisseph.json"


def _row(name: str, values: list[float], unit: str, target: str) -> str:
    return (
        f"| {name} | {len(values)} | {max(values):.4f}{unit} | "
        f"{statistics.median(values):.4f}{unit} | {target} |"
    )


def _jyotish_section() -> list[str]:
    """M2: divisional charts and special points versus PyJHora."""
    fixtures = ROOT / "engine" / "tests" / "fixtures"
    vargas: dict[str, Any] = json.loads((fixtures / "vargas_pyjhora.json").read_text("utf-8"))
    supported = {m.value for m in VargaMethod} | {"raman_anti_zodiacal", "parashara_double_reverse"}
    rename = {
        "raman_anti_zodiacal": VargaMethod.RAMAN,
        "parashara_double_reverse": VargaMethod.SIDDHAMSA_FROM_LEO,
    }
    tables = matched = 0
    for division_text, methods in vargas["tables"].items():
        division = int(division_text)
        for name, table in methods.items():
            if name not in supported:
                continue
            method = rename.get(name) or VargaMethod(name)
            width = 30.0 / division
            ours = [
                [varga_sign_index(s, (p + 0.5) * width, division, method) for p in range(division)]
                for s in range(12)
            ]
            tables += 1
            matched += ours == table
    return [
        "## Jyotish layer (M2) versus PyJHora 4.8.7",
        "",
        f"* Divisional charts: {matched} of {tables} reference tables (23 divisions with "
        "their Parashara, parivritti, Somanatha, Jagannatha, Raman and siddhamsa variants) "
        "match exactly, sign by sign and part by part; the unequal Trimsamsa (D30) and "
        "divisional longitudes also match.",
        "* Chara karakas, compound (panchadha) relationships: exact on all 120 charts.",
        "* Bhava arudhas: exact on every chart where PyJHora's convention of counting the "
        "Lagna as a planet does not apply.",
        "* Bhava, Hora and Ghati lagnas within 0.12′; Indu lagna within 0.03′; Sree lagna "
        "within 1′ (it moves 27 times faster than the Moon).",
        "* Sun-based upagrahas exact; time-based upagrahas within 1′ for day births where "
        "both part-lord conventions agree.",
        "",
        "Reference deviations found and documented (the engine follows the classical texts):",
        "",
        "* PyJHora's PyPI package ships no planetary data files, so Swiss Ephemeris falls "
        "back to the Moshier model (Moon off by up to ~3″, nodes by up to ~50″); fixtures "
        "are generated with the real files.",
        "* It uses true (geometric) positions, about 20″ from the apparent positions most "
        "almanacs use; the engine offers both (`position_type`).",
        "* It adds the timezone twice when taking the Sun at sunrise for special lagnas, "
        "counts a clock second as one tharparai in Pranapada, measures night upagraha "
        "parts from sunrise, and places the lordless eighth part after Saturn.",
        "",
    ]


def _transit_section() -> list[str]:
    """M3: sign ingresses and stations versus Swiss Ephemeris."""
    fixture = ROOT / "engine" / "tests" / "fixtures" / "transits_swisseph.json"
    data: dict[str, Any] = json.loads(fixture.read_text("utf-8"))
    lines = [
        "## Transit events (M3) versus Swiss Ephemeris",
        "",
        f"Reference: {data['reference']}, sidereal sign ingresses 1995–2025 (the Moon "
        "1995–1996) and planetary stations, each bisected to about 10 ms.",
        "",
        "| Body | Ingresses (engine / reference) | Max | Median | Stations | Max | Median |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, ref in data["bodies"].items():
        body = Body(name)
        ours = sign_ingresses(body, ref["start"], ref["end"])
        ingress = [
            abs(a.jd_ut - b[0]) * 86400 for a, b in zip(ours, ref["ingresses"], strict=False)
        ]
        row = (
            f"| {name.title()} | {len(ours)} / {len(ref['ingresses'])} | "
            f"{max(ingress):.2f} s | {statistics.median(ingress):.2f} s |"
        )
        if ref["stations"]:
            found = stations(body, ref["start"], ref["end"])
            diffs = [
                abs(a.jd_ut - b[0]) * 86400 for a, b in zip(found, ref["stations"], strict=False)
            ]
            row += (
                f" {len(found)} / {len(ref['stations'])} | {max(diffs):.2f} s | "
                f"{statistics.median(diffs):.2f} s |"
            )
        else:
            row += " — | — | — |"
        lines.append(row)
    lines += [
        "",
        "Milestone target: ingress times within one minute. The true node's reversals "
        "are not reported as stations (Rahu and Ketu are treated as always retrograde).",
        "",
    ]
    return lines


def _flatten(
    periods: list[Period], system: NakshatraDasha, rule: SubPeriodRule, depth: int
) -> list[Period]:
    if depth == 1:
        return periods
    out: list[Period] = []
    for period in periods:
        children = subdivide(period, DEFINITIONS[system].sequence, rule)
        out += _flatten(children, system, rule, depth - 1)
    return out


def _dasha_section() -> list[str]:
    """M3: nakshatra dashas versus PyJHora, given the same Moon longitude and year."""
    fixture = ROOT / "engine" / "tests" / "fixtures" / "dashas_pyjhora.json"
    data: dict[str, Any] = json.loads(fixture.read_text("utf-8"))
    cases: list[dict[str, Any]] = data["cases"]
    equal_rule = {NakshatraDasha.VIMSHOTTARI, NakshatraDasha.ASHTOTTARI}
    lines = [
        "## Nakshatra dashas (M3) versus PyJHora 4.8.7",
        "",
        f"{len(cases)} charts; the engine is given PyJHora's Moon longitude and dasha year, "
        "so these numbers measure the dasha arithmetic itself.",
        "",
        "| System | Periods compared | Lords matching | Max start difference |",
        "|---|---|---|---|",
    ]
    for system in NakshatraDasha:
        rule = SubPeriodRule.PROPORTIONAL if system in equal_rule else SubPeriodRule.EQUAL
        compared = matching = 0
        worst = 0.0
        for case in cases:
            periods = mahadashas(system, case["jd_ut"], case["moon"], case["year_days"], 3)
            ours = _flatten(periods, system, rule, 2)
            for period, (lords, offset) in zip(ours, case["systems"][system.value], strict=False):
                compared += 1
                matching += [list(GRAHAS).index(b) for b in period.lords] == lords
                worst = max(worst, abs(period.start_jd - case["jd_ut"] - offset) * 86400)
        label = DEFINITIONS[system].name
        lines.append(f"| {label} | {compared} | {matching} | {worst:.3f} s |")
    year_errors = [
        abs(
            true_sidereal_year_days(c["jd_ut"], Settings(position_type=PositionType.TRUE))
            - c["true_sidereal_year_days"]
        )
        * 86400
        for c in cases
    ]
    reference_errors = [abs(c["year_days"] - c["true_sidereal_year_days"]) * 86400 for c in cases]
    close = [e for e in reference_errors if e < 3600.0]
    gross = [e for e in reference_errors if e >= 3600.0]
    names = {
        "ashtottari": NakshatraDasha.ASHTOTTARI,
        "chaturaaseeti_sama": NakshatraDasha.CHATURASHITI_SAMA,
        "dwadasottari": NakshatraDasha.DWADASHOTTARI,
        "dwisatpathi": NakshatraDasha.DWISAPTATI_SAMA,
        "panchottari": NakshatraDasha.PANCHOTTARI,
        "satabdika": NakshatraDasha.SHATABDIKA,
        "shashtisama": NakshatraDasha.SHASHTIHAYANI,
    }
    agree = total = 0
    for case in cases:
        sidereal = dict(zip(GRAHAS, case["grahas"], strict=True))
        verdicts = {
            a.system: a.applicable for a in applicability(case["ascendant"], sidereal, None)
        }
        expected = {names[n] for n in case["applicable"]}
        for system in names.values():
            total += 1
            agree += verdicts[system] == (system in expected)
    lines += [
        "",
        "* Antardashas are divided the way PyJHora divides them: in proportion to the "
        "lords' years for Vimshottari and Ashtottari, equally for the rest. BPHS divides "
        "them proportionally in every system, which is the engine's default.",
        f"* True sidereal year (Mesha sankranti to Mesha sankranti): the engine is within "
        f"{max(year_errors):.2f} s of an exact Swiss Ephemeris bisection on every chart. "
        f"PyJHora's own value is off by up to {max(close):.0f} s, because it interpolates "
        "each sankranti from sunrise samples"
        + (
            f", and on {len(gross)} chart(s) by {max(gross) / 86400:.1f} days (a wrong "
            "sankranti day); its dasha dates move accordingly."
            if gross
            else "."
        ),
        f"* Applicability of the conditional dashas: {agree} of {total} verdicts agree "
        "(7 systems; PyJHora has no rule for Shodashottari or Shattrimsha Sama).",
        "* Yogini dasha follows BPHS's formula, (birth nakshatra + 3) mod 8; a cyclic "
        "count from Ardra gives different lords for births in Ashwini to Mrigashira.",
        "",
    ]
    return lines


def _sign_matches(case: dict[str, Any], ours: list[SignPeriod], rows: list[Any]) -> bool:
    return all(
        list(p.signs) == signs and abs(p.start_jd - case["jd_ut"] - offset) * 86400 < 1.0
        for p, (signs, offset) in zip(ours, rows, strict=False)
    )


def _sign_dasha_section() -> list[str]:
    """M3: Jaimini sign dashas versus PyJHora, given identical positions."""
    fixture = ROOT / "engine" / "tests" / "fixtures" / "sign_dashas_pyjhora.json"
    cases: list[dict[str, Any]] = json.loads(fixture.read_text("utf-8"))["cases"]
    chara = narayana = 0
    for case in cases:
        sidereal = dict(zip(GRAHAS, case["grahas"], strict=True))
        args = (case["ascendant"], sidereal, case["jd_ut"], case["year_days"])
        chara += _sign_matches(case, sign_mahadashas(SignDasha.CHARA, *args), case["chara_kn_rao"])
        mahas = sign_mahadashas(SignDasha.NARAYANA, *args)
        subs = [x for m in mahas for x in sign_sub_periods(SignDasha.NARAYANA, m, sidereal)]
        narayana += _sign_matches(case, subs, case["narayana"])
    return [
        "## Jaimini sign dashas (M3) versus PyJHora 4.8.7",
        "",
        f"{len(cases)} charts, identical positions. Chara dasha (K.N. Rao): mahadasha "
        f"signs, lengths and dates match exactly on {chara} charts. Narayana dasha "
        f"(both rounds, mahadashas and antardashas): exact on {narayana} charts.",
        "",
        "Every other chart differs only through one of these reference behaviours, which "
        "`test_sign_dasha_golden.py` detects chart by chart (the engine follows the rule "
        "as written):",
        "",
        "* Mercury in Virgo is not treated as exalted (BPHS: exalted), so Gemini and Virgo "
        "dashas are a year shorter;",
        "* the lagna is counted as a planet when choosing between co-lords;",
        "* in the stronger-sign test (rule 2), Jupiter or Mercury is counted twice when it "
        "also rules the sign, and a lord in its own sign is missed;",
        "* when the co-lord rules tie, the co-lord whose own sign has the longer dasha wins, "
        "rather than the one that gives the sign in question the longer dasha.",
        "",
        "PyJHora also gives every Chara mahadasha the same antardasha order, starting from "
        "the lagna; the engine uses K.N. Rao's order (from the sign after the dasha sign, "
        "ending with the dasha sign), so Chara antardashas are not compared.",
        "",
        "**Kalachakra dasha** (same charts, same Moon): the signs, balance at birth and "
        "proportional antardashas agree to the second wherever both follow the same "
        "reading. The engine continues after the birth pada with the next pada in the "
        "zodiac, where PyJHora switches to the paired nakshatra group (the same pada for "
        "padas 1-3 and some pada-4 births); it runs the first mahadasha's antardashas from "
        "the mahadasha's true start, where PyJHora squeezes them into the balance left at "
        "birth; and a sign that occurs twice in a pada starts its antardashas from its own "
        "place rather than its first occurrence.",
        "",
    ]


def _annual_section() -> list[str]:
    """M3: annual return moments versus Swiss Ephemeris, Patyayini versus PyJHora."""
    fixture = ROOT / "engine" / "tests" / "fixtures" / "annual_swisseph.json"
    data: dict[str, Any] = json.loads(fixture.read_text("utf-8"))
    cases: list[dict[str, Any]] = data["cases"]
    errors: dict[str, list[float]] = defaultdict(list)
    names = {str(i): body.value for i, body in enumerate(SEVEN)} | {"lagna": "lagna"}
    patyayini_ok = 0
    for case in cases:
        for key, ours in (
            (
                "varsha_pravesha",
                varsha_pravesha(case["birth_jd_ut"], case["sun"], case["years_completed"]),
            ),
            (
                "tithi_pravesha",
                tithi_pravesha(
                    case["birth_jd_ut"], case["sun"], case["moon"], case["years_completed"]
                ),
            ),
        ):
            theirs_tt = case[key] + case[f"{key}_delta_t_days"]
            errors[key].append(abs(float(jd_ut_to_tt([ours])[0]) - theirs_tt) * 86400)
        krisamsas = case["patyayini_krisamsas"]
        sidereal = {Body(names[k]): v for k, v in krisamsas.items() if k != "lagna"}
        scheme = patyayini_scheme(krisamsas["lagna"], sidereal)
        start = case["varsha_pravesha"]
        ours_rows = [
            sub
            for maha in patyayini_dashas(scheme, start, case["patyayini_year_days"])
            for sub in patyayini_sub_periods(scheme, maha)
        ]
        patyayini_ok += all(
            list(p.lords) == [names[str(x)] for x in lords]
            and abs(p.start_jd - start - offset) * 86400 < 1.0
            for p, (lords, offset) in zip(ours_rows, case["patyayini"], strict=True)
        )
    return [
        "## Annual charts (M3)",
        "",
        f"{len(cases)} births, a random year of life each (up to 50 years on). The reference "
        "finds each moment independently by bisecting Swiss Ephemeris positions (Lahiri, "
        "apparent); times are compared in TT, because future Delta T is a prediction on "
        "which tools differ by about a second in the 2030s.",
        "",
        "| Moment | Cases | Max | Median | Target |",
        "|---|---|---|---|---|",
        _row("Varsha Pravesha (solar return)", errors["varsha_pravesha"], " s", "≤ 1 s"),
        _row("Tithi Pravesha", errors["tithi_pravesha"], " s", "≤ 1 s"),
        "",
        f"* Patyayini dasha (annual), given PyJHora's krisamsas and year: {patyayini_ok} of "
        f"{len(cases)} tables identical, mahadashas and antardashas to the second.",
        "* Mudda dasha is Vimshottari compressed into the Tajika year, built on the same "
        "period tree as the natal dashas above; PyJHora scales its balance and periods "
        "differently (a 360-day balance within a sidereal-year cycle), so it is not "
        "compared.",
        "",
    ]


def _strength_and_rules_section() -> list[str]:
    """M4: strength checks, and the yoga catalogue run against its own test charts."""
    catalogue = default_catalogue()
    charts = passed = 0
    for compiled in catalogue:
        tests = compiled.rule.tests
        for kind, specs in (
            ("positive", tests.positive),
            ("negative", tests.negative),
            ("cancelled", tests.cancelled),
        ):
            for spec in specs:
                result = catalogue.evaluate_rule(compiled, ChartFacts.from_spec(spec))
                expected = {
                    "positive": result.present,
                    "negative": not (result.present or result.cancelled),
                    "cancelled": result.cancelled and not result.present,
                }[kind]
                charts += 1
                passed += expected
    categories = Counter(r.rule.category.value for r in catalogue)
    provenance = Counter(r.rule.provenance.value for r in catalogue)
    citations = [c for r in catalogue for c in r.rule.sources]
    saham_data: dict[str, Any] = json.loads(SAHAM_FIXTURE.read_text("utf-8"))
    saham_total = saham_same = 0
    for case in saham_data["cases"]:
        sidereal = {Body(k): v for k, v in case["planets"].items()}
        ours = compute_sahams(case["lagna"], sidereal, not case["night"])
        for saham in ours:
            theirs = case["sahams"][saham.name]
            saham_total += 1
            saham_same += abs((saham.longitude - theirs + 180.0) % 360.0 - 180.0) < 1e-7
    lines = [
        "## Strength (M4)",
        "",
        "* Ashtakavarga: identical to P.V.R. Narasimha Rao's worked Chart 7, before and "
        "after both reductions (`test_ashtakavarga.py`).",
        "* Shadbala: every component of B.V. Raman's and V.P. Jain's worked examples within "
        "1 virupa, apart from the book slips and method differences listed in "
        "`test_shadbala.py`.",
        "",
        "## Tajika sahams (M4)",
        "",
        f"The 36 sahams of Rao's table on {len(saham_data['cases'])} random sets of "
        f"positions, day and night: {saham_same} of {saham_total} values identical to "
        "PyJHora's. Every other value is reproduced exactly by one of three PyJHora "
        "departures from the table, which `test_sahams_golden.py` checks case by case: "
        "house cusps not reduced below 360 degrees before its between-signs test, Rahu or "
        "Ketu taken as the lord of Aquarius or Scorpio, and Labha reversed by night.",
        "",
        "## Yogas and doshas (M4)",
        "",
        f"{len(catalogue)} rules in `knowledge/yogas/`, all `draft` until a qualified "
        f"Jyotishi reviews them. They carry {len(citations)} citations, "
        f"{sum(c.verified for c in citations)} checked against their edition so far. "
        f"Provenance: {provenance['classical']} classical, {provenance['traditional']} "
        f"traditional (documented by modern authors, classical source not yet identified), "
        f"{provenance['modern']} modern.",
        "",
        "| Category | Rules |",
        "|---|---|",
        *(f"| {name} | {count} |" for name, count in categories.most_common()),
        "",
        f"* Test charts: {passed} of {charts} behave as each rule specifies (present, "
        "absent, or present but cancelled).",
        "* Property tests on random charts check catalogue invariants (for example, "
        "exactly one of Sunapha, Anapha, Durudhura and Kemadruma holds) and compare the "
        "Mahapurusha, Parivartana, Gajakesari, Kala Sarpa and lunar yogas with separate "
        "plain-Python implementations (`test_rules_properties.py`).",
        "",
    ]
    return lines


def _panchanga_section() -> list[str]:
    """M5: rise and set of the Sun and Moon, and limb end times, versus Swiss Ephemeris."""
    data: dict[str, Any] = json.loads(PANCHANGA_FIXTURE.read_text("utf-8"))
    cases: list[dict[str, Any]] = data["cases"]
    errors: dict[str, list[float]] = defaultdict(list)
    unmatched = 0
    for case in cases:
        lat, lon, elevation = case["latitude"], case["longitude"], case["elevation_m"]
        midnight = Instant.from_jd_ut(case["midnight_jd_ut"])
        rise = next_sunrise(midnight, lat, lon, elevation)
        assert rise is not None
        events = {
            "sunrise": rise,
            "sunset": next_sunset(rise, lat, lon, elevation),
            "moonrise": next_moonrise(midnight, lat, lon, elevation),
            "moonset": next_moonset(midnight, lat, lon, elevation),
        }
        for name, event in events.items():
            assert event is not None
            errors[name].append(abs(event.jd_ut - case[name]) * 86400)
        spans = all_limb_spans(case["sunrise"], case["next_sunrise"])
        for limb in Limb:
            theirs: dict[int, list[float]] = defaultdict(list)
            for jd_ut, _, after, delta_t_days in case["changes"][limb.value]:
                theirs[int(after)].append(jd_ut + delta_t_days)
            starts = jd_ut_to_tt([s.start_jd_ut for s in spans[limb]])
            for span, ours in zip(spans[limb], starts, strict=True):
                if not theirs[span.index]:
                    unmatched += 1
                    continue
                errors[limb.value].append(min(abs(ours - t) for t in theirs[span.index]) * 86400)
    labels = {
        "sunrise": "Sunrise (Hindu: disc centre, no refraction)",
        "sunset": "Sunset (Hindu)",
        "moonrise": "Moonrise (upper limb, refraction, topocentric)",
        "moonset": "Moonset (upper limb, refraction, topocentric)",
        **{limb.value: f"{limb.value.title()} changes" for limb in Limb},
    }
    return [
        "## Panchanga (M5) versus Swiss Ephemeris",
        "",
        f"Reference: {data['reference']}. {len(cases)} civil dates from 1950 to 2040: 100 "
        "each at New Delhi, Mumbai, Chennai, Kolkata and Bengaluru, and 20 each at London, "
        "New York and Sydney. The reference finds every event independently: rise and set "
        "with its own routine, and each change of tithi, nakshatra, yoga and karana by "
        "bisection on its positions. Limb changes are compared in TT, because Delta T for "
        "future dates is a prediction that differs between tools by about a second.",
        "",
        "| Event | Cases | Max | Median | Target |",
        "|---|---|---|---|---|",
        *(_row(label, errors[key], " s", "≤ 60 s") for key, label in labels.items()),
        "",
        f"Every limb span the engine reports from sunrise to the next sunrise matches a "
        f"change in the reference ({unmatched} unmatched). The milestone target is one "
        "minute against Drik Panchang with the same sunrise definition; Drik Panchang "
        "cannot be reached from this environment, so that comparison is left to the manual "
        "spot checks.",
        "",
    ]


def main() -> None:
    data: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    cases: list[dict[str, Any]] = data["cases"]
    errors: dict[str, list[float]] = defaultdict(list)

    for case in cases:
        instant = Instant(jd_ut=case["jd_ut"], jd_tt=case["jd_tt"])
        ref = case["positions_tropical"]
        for body, pos in tropical_positions(instant, EPHEMERIS_BODIES).items():
            errors[body.value].append(angular_distance(pos.longitude, ref[body.value][0]) * 3600)
        errors["mean_node"].append(
            angular_distance(mean_node_position(instant).longitude, ref["mean_node"][0]) * 3600
        )
        errors["true_node"].append(
            angular_distance(true_node_position(instant).longitude, ref["true_node"][0]) * 3600
        )
        for system in (*EPOCH_SYSTEMS, *STAR_SYSTEMS):
            key = system.value.replace("chitra", "citra")
            errors[f"ayanamsa:{system.value}"].append(
                abs(true_ayanamsa(instant, system) - case["ayanamsa_true"][key]) * 3600
            )
        angles = chart_angles(Instant.from_jd_ut(case["jd_ut"]), case["lat"], case["lon"])
        errors["ascendant"].append(
            angular_distance(angles.ascendant, case["houses"]["ascendant"]) * 3600
        )
        errors["midheaven"].append(angular_distance(angles.mc, case["houses"]["mc"]) * 3600)
        for name in ("placidus", "porphyry", "equal", "sripati"):
            reference = case["houses"][name]
            if not reference["ok"]:
                continue
            cusps = quadrant_cusps(HouseSystem(name), angles).cusps
            errors[f"houses:{name}"].append(
                max(angular_distance(a, b) for a, b in zip(cusps, reference["cusps"], strict=True))
                * 3600
            )
        if case["jd_ut"] <= 2460000.0:
            ours = Instant.from_jd_ut(case["jd_ut"]).delta_t_seconds
            errors["delta_t"].append(abs(ours - case["delta_t_s"]))

    for case in cases[::2]:
        if abs(case["lat"]) >= 60.0:
            continue
        start = Instant.from_jd_ut(case["jd_ut"] - 0.5)
        for definition in SunriseDefinition:
            args = (start, case["lat"], case["lon"], case["alt_m"], definition)
            for event, ours in (("rise", next_sunrise(*args)), ("set", next_sunset(*args))):
                theirs = case["sun_rise_set"][f"{definition.value}_{event}"]
                if ours is not None and theirs is not None:
                    errors[f"sun_{event}:{definition.value}"].append(
                        abs(ours.jd_ut - theirs) * 86400
                    )

    eph = get_ephemeris().info
    lines = [
        "# Accuracy report",
        "",
        f"*Generated {datetime.now(UTC):%Y-%m-%d} by `scripts/accuracy_report.py`, engine "
        f"{ENGINE_VERSION}, ephemeris {eph.name}.* Reference: {data['reference']}; "
        f"{len(cases)} cases (1900–2050, latitudes −60° to +78°, seed {data['seed']}).",
        "",
        "The engine and the reference are given identical TT/UT1 instants, so these "
        "numbers measure the astronomy itself. Delta T is compared separately.",
        "",
        "## Positions (tropical, apparent, true equinox of date)",
        "",
        "| Quantity | Cases | Max | Median | Target |",
        "|---|---|---|---|---|",
    ]
    for body in EPHEMERIS_BODIES:
        lines.append(_row(body.value.title(), errors[body.value], '"', '≤ 1"'))
    lines.append(_row("Rahu (mean node)", errors["mean_node"], '"', '≤ 1"'))
    lines.append(_row("Rahu (true node)", errors["true_node"], '"', '≤ 5"'))
    lines += [
        "",
        "## Ayanamsa (true, including nutation)",
        "",
        "| System | Cases | Max | Median | Target |",
        "|---|---|---|---|---|",
    ]
    for system in (*EPOCH_SYSTEMS, *STAR_SYSTEMS):
        lines.append(_row(system.value, errors[f"ayanamsa:{system.value}"], '"', '≤ 0.5"'))
    lines += [
        "",
        "## Angles and houses (tropical)",
        "",
        "| Quantity | Cases | Max | Median | Target |",
        "|---|---|---|---|---|",
        _row("Ascendant", errors["ascendant"], '"', '≤ 2"'),
        _row("Midheaven", errors["midheaven"], '"', '≤ 2"'),
    ]
    for name in ("placidus", "porphyry", "equal", "sripati"):
        label = f"{name.title()} cusps (worst of 12)"
        lines.append(_row(label, errors[f"houses:{name}"], '"', '≤ 2"'))
    lines += [
        "",
        "Placidus is undefined inside the polar circles; there the engine falls back to "
        "Porphyry and flags it, as the reference does.",
        "",
        "## Sunrise and sunset (|latitude| < 60°)",
        "",
        "| Event | Cases | Max | Median | Target |",
        "|---|---|---|---|---|",
    ]
    for definition in SunriseDefinition:
        for event in ("rise", "set"):
            key = f"sun_{event}:{definition.value}"
            lines.append(_row(f"Sun{event} ({definition.value})", errors[key], " s", "≤ 2 s"))
    lines += [
        "",
        "Above about 60° the reference's own sunset times depend on where its search "
        "starts (one case at 62° N moved by 6 minutes); restarted near the event it "
        "agrees with the engine to 0.05 s.",
        "",
        "## Delta T (TT − UT1), dates up to 2023",
        "",
        "| Quantity | Cases | Max | Median | Note |",
        "|---|---|---|---|---|",
        _row("Delta T", errors["delta_t"], " s", "both follow IERS values"),
        "",
        "Future Delta T is a prediction in every tool; by 2050 models differ by seconds, "
        "which moves the Moon by about 0.5″ per second of difference.",
        "",
    ]
    lines += _jyotish_section()
    lines += _transit_section()
    lines += _dasha_section()
    lines += _sign_dasha_section()
    lines += _annual_section()
    lines += _strength_and_rules_section()
    lines += _panchanga_section()
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
