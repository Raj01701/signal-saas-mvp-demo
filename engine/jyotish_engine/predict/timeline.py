"""The prediction timeline: promise × period × trigger, month by month, per life domain.

For each domain and each month (sampled mid-month):

- **Promise** ``P`` (0-1): the natal support for the domain (``predict/promise.py``).
- **Period** ``A`` (0-1): how strongly the running Vimshottari lords link to the
  domain, weighted 0.5 (mahadasha), 0.35 (antardasha) and 0.15 (pratyantardasha).
  A lord links by owning, occupying or aspecting the domain's houses, joining the
  main house's lord, being its karaka, through its star lord (as in KP), and for
  Rahu and Ketu through their dispositors.
- **Trigger** ``G`` (0-1): transits of Jupiter and Saturn over the domain's houses
  (double transit counts most), over its house lord's natal sign, and the dasha
  lords transiting its houses.
- **Convergence:** when the running Yogini dasha lords also link to the domain, a
  second timing system agrees and the score rises by 15 %.
- **Further techniques** (``predict/techniques.py``, each switchable for the Accuracy
  Lab): the dasha lords' links in the domain's divisional chart; Jaimini Chara dasha
  and KP house groups as further agreeing systems (each moves the score by up to
  ±15 %); Jupiter's and Saturn's transits weighed by Ashtakavarga bindus; and Saturn
  with Jupiter on the house lord (K.N. Rao's double transit).
- **Age:** results are read in the context of age (desha-kala-patra): marriage,
  children and property from 18, career and wealth from 16, education from 4 to 35.

The score is ``P × A × (0.5 + 0.5 G)`` (with the convergence bonus). The tone
(-1 to 1) says whether the emphasis is likely to feel favourable: the promise, the
dasha lords' functional nature, and Jupiter's and Saturn's gochara from the Moon.
Windows are runs of months in a domain's top fifth; a window is **strong** only when
the dasha systems agree (Vimshottari with two of Yogini, Chara and KP) and a transit
confirms. All weights
are working values to be calibrated by the Accuracy Lab (milestone M12).
"""

from __future__ import annotations

import bisect
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Literal

import numpy as np

from jyotish_engine.astro.bodies import GRAHAS, Body
from jyotish_engine.astro.series import jd_ut_to_tt, sidereal_longitudes
from jyotish_engine.astro.time import datetime_to_jd, jd_to_datetime
from jyotish_engine.core.aspects import graha_aspected_signs
from jyotish_engine.core.nakshatra import nakshatra_of
from jyotish_engine.dasha.base import Period
from jyotish_engine.dasha.nakshatra import DEFINITIONS, NakshatraDasha, mahadashas, sub_periods
from jyotish_engine.dasha.tables import period_out
from jyotish_engine.models import (
    ChartResult,
    DomainPromiseOut,
    DomainTimelineOut,
    PredictionFactorOut,
    PredictionRuleOut,
    PredictionsOut,
    PredictionWindowOut,
)
from jyotish_engine.predict.domains import DOMAIN_SPECS, DomainSpec, karakas
from jyotish_engine.predict.promise import Factor, clamp, domain_promise, functional_tone, name
from jyotish_engine.predict.techniques import (
    FULL,
    KP_GROUPS,
    CharaTiming,
    Target,
    TimingModel,
    bindu_factor,
    chara_label,
    chara_targets,
    chara_value,
    kp_houses,
    kp_label,
    kp_value,
    sav_factor,
    varga_parts,
)
from jyotish_engine.rules.catalogue import Catalogue, CompiledRule, RuleResult, default_catalogue
from jyotish_engine.rules.facts import NODES, ChartFacts
from jyotish_engine.rules.schema import READING_CATEGORIES, Category, ordinal
from jyotish_engine.rules.yogas import YOGA_CATEGORIES
from jyotish_engine.strength.ashtakavarga import Ashtakavarga, ashtakavarga
from jyotish_engine.strength.shadbala import REQUIRED_RUPAS, compute_shadbala
from jyotish_engine.transit.gochara import NO_VEDHA, VEDHA

LEVELS = (("Mahadasha", 0.5), ("Antardasha", 0.35), ("Pratyantardasha", 0.15))
CONVERGENCE_BONUS = 1.15
#: How far a further system (Chara, KP) can move a month's score either way.
SYSTEM_SWING = 0.15
#: A further system agrees when its support reaches this share.
AGREES = 0.6
MAX_MONTHS = 1200
MAX_WINDOWS = 12
SLOW = (Body.JUPITER, Body.SATURN, Body.RAHU, Body.KETU)
#: Transit rules that depend only on the slow grahas (so they can be cached by sign).
SLOW_RULES = (
    "transit.jupiter_",
    "transit.saturn_",
    "transit.rahu_",
    "transit.ketu_",
    "transit.double_",
    "transit.sade_sati",
    "transit.kantaka_shani",
)
NOTES = [
    "Scores combine the natal promise of each domain, the running Vimshottari periods "
    "(also read in the domain's divisional chart) and the monthly transits of Jupiter "
    "and Saturn weighed by Ashtakavarga; agreement of the Yogini and Chara dashas and of "
    "the KP house groups raises confidence.",
    "Weights are working values until they are calibrated against recorded life events; "
    "read windows as periods of emphasis, not certainties.",
    "Health windows describe tendencies only and are no substitute for medical advice.",
]


@dataclass(frozen=True, slots=True)
class _Month:
    start: date
    jd_ut: float  # mid-month


def _months(start: date, end: date) -> list[_Month]:
    out = []
    year, month = start.year, start.month
    while date(year, month, 1) < end:
        mid = datetime(year, month, 15, 12, tzinfo=UTC)
        out.append(_Month(date(year, month, 1), datetime_to_jd(mid)))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return out


def _add_months(day: date, months: int) -> date:
    index = day.year * 12 + day.month - 1 + months
    return date(index // 12, index % 12 + 1, 1)


def _flat_periods(
    chart: ChartResult, system: NakshatraDasha, depth: int, until_jd: float
) -> list[Period]:
    """All periods of ``system`` at ``depth`` from birth to ``until_jd``, in order."""
    moon = next(g.sidereal_longitude for g in chart.grahas if g.body is Body.MOON)
    year_days = chart.dashas.year_days
    birth = chart.time.jd_ut
    cycles = 2 + int((until_jd - birth) / (DEFINITIONS[system].total_years * year_days))
    level = mahadashas(system, birth, moon, year_days, cycles)
    for _ in range(depth - 1):
        level = [sub for period in level for sub in sub_periods(system, period)]
    return level


class _Lookup:
    def __init__(self, periods: list[Period]) -> None:
        self.periods = periods
        self.starts = [p.start_jd for p in periods]

    def at(self, jd: float) -> Period:
        return self.periods[max(0, bisect.bisect_right(self.starts, jd) - 1)]


def _link(
    facts: ChartFacts,
    spec: DomainSpec,
    body: Body,
    gender: str | None,
    chart: ChartResult | None = None,
) -> tuple[float, list[str]]:
    """How strongly a dasha lord links to a domain (0-1), and how; with ``chart``, its
    links in the domain's divisional chart count too."""
    parts: list[tuple[float, str]] = []
    for houses, own, occupy, aspect in (
        (spec.primary, 0.9, 0.7, 0.4),
        (spec.secondary, 0.5, 0.4, 0.2),
    ):
        for house in houses:
            if facts.lord(house) is body:
                parts.append((own, f"owns the {ordinal(house)} house"))
            if facts.house(body) == house:
                parts.append((occupy, f"occupies the {ordinal(house)} house"))
            elif facts.aspects_sign(body, facts.sign_of_house(house)):
                parts.append((aspect, f"aspects the {ordinal(house)} house"))
    for house in spec.primary:
        lord = facts.lord(house)
        if lord is not body and facts.signs[lord] == facts.signs[body]:
            parts.append((0.4, f"joins the {ordinal(house)} lord {name(lord)}"))
    if body in karakas(spec, gender):
        parts.append((0.5, f"is a karaka of {spec.domain.value}"))
    star = nakshatra_of(facts.longitude(body)).nakshatra.lord
    if star is not body and any(
        facts.lord(h) is star or facts.house(star) == h for h in spec.primary
    ):
        parts.append(
            (0.35, f"its star lord {name(star)} rules or occupies a {spec.domain.value} house")
        )
    if body in NODES:
        dispositor = facts.dispositor(body)
        owned = [h for h in spec.primary if facts.lord(h) is dispositor]
        if owned:
            parts.append(
                (
                    0.6,
                    f"acts for its dispositor {name(dispositor)}, lord of the {ordinal(owned[0])}",
                )
            )
    if chart is not None:
        parts += varga_parts(chart, spec, body)
    value = 1.0 - math.prod(1.0 - weight for weight, _ in parts)
    return value, [label for _, label in parts]


def _influences(body: Body, sign: int, target: int, node_aspects: bool) -> bool:
    return sign == target or target in graha_aspected_signs(body, sign, node_aspects)


class _Transits:
    """Monthly sidereal signs of the grahas, with the chart's settings."""

    def __init__(self, chart: ChartResult, jds: Sequence[float]) -> None:
        settings = chart.settings
        tt = jd_ut_to_tt(np.asarray(jds, dtype=float))
        self.longitudes = {
            body: sidereal_longitudes(
                body,
                tt,
                ayanamsa=settings.ayanamsa,
                user_ayanamsa_j2000=settings.user_ayanamsa_j2000,
                position_type=settings.position_type,
                node_type=settings.node_type,
            )
            for body in GRAHAS
        }
        self.signs = {b: (lons // 30.0).astype(int) % 12 for b, lons in self.longitudes.items()}

    def sign(self, body: Body, month: int) -> int:
        return int(self.signs[body][month])

    def positions(self, month: int, bodies: Sequence[Body] = GRAHAS) -> dict[Body, float]:
        return {b: float(self.longitudes[b][month]) for b in bodies}


def _gochara_tone(transits: _Transits, month: int, moon_sign: int) -> tuple[float, list[str]]:
    """Jupiter's and Saturn's gochara from the natal Moon: +1 good, 0 obstructed, -1 bad."""
    houses = {b: (transits.sign(b, month) - moon_sign) % 12 + 1 for b in GRAHAS}
    notes = []
    tone = 0.0
    for body, weight in ((Body.JUPITER, 0.6), (Body.SATURN, 0.4)):
        house = houses[body]
        blocked = VEDHA[body].get(house)
        if blocked is None:
            value, how = -1.0, "an unfavourable"
        elif any(
            o is not body and frozenset({body, o}) not in NO_VEDHA and houses[o] == blocked
            for o in GRAHAS
        ):
            value, how = 0.0, "a favourable but obstructed"
        else:
            value, how = 1.0, "a favourable"
        tone += weight * value
        notes.append(f"{name(body)} in {how} house ({ordinal(house)}) from the Moon")
    if houses[Body.SATURN] in (12, 1, 2):
        tone -= 0.2
        notes.append("Sade Sati")
    return clamp(tone), notes


def _trigger(
    facts: ChartFacts,
    spec: DomainSpec,
    transits: _Transits,
    month: int,
    lords: Sequence[Body],
    av: Ashtakavarga | None = None,
    saturn_on_lord: bool = False,
) -> tuple[float, list[Factor]]:
    jupiter, saturn = transits.sign(Body.JUPITER, month), transits.sign(Body.SATURN, month)
    aspects = facts.node_aspects_5_9
    factors: list[Factor] = []
    # With Ashtakavarga, a transit counts by the planet's own bindus in the sign it
    # crosses and by the sarvashtakavarga of the house it reaches.
    j_bindus = bindu_factor(av.bav, Body.JUPITER, jupiter) if av else 1.0
    s_bindus = bindu_factor(av.bav, Body.SATURN, saturn) if av else 1.0
    j_note = f" ({av.bav['jupiter'][jupiter]} of 8 bindus)" if av else ""
    s_note = f" ({av.bav['saturn'][saturn]} of 8 bindus)" if av else ""

    def add(value: float, label: str) -> None:
        factors.append(Factor("trigger", label, value, 1.0))

    for house in spec.primary:
        target = facts.sign_of_house(house)
        strength = sav_factor(av.sav, target) if av else 1.0
        j = _influences(Body.JUPITER, jupiter, target, aspects)
        s = _influences(Body.SATURN, saturn, target, aspects)
        if j and s:
            add(
                0.45 * strength * (j_bindus + s_bindus) / 2,
                f"Jupiter and Saturn both influence the {ordinal(house)} house (double transit)",
            )
        elif j:
            add(
                0.25 * strength * j_bindus,
                f"Jupiter influences the {ordinal(house)} house{j_note}",
            )
        elif s:
            add(
                0.15 * strength * s_bindus,
                f"Saturn influences the {ordinal(house)} house{s_note}",
            )
        from_moon = facts.sign_of_house(house, Body.MOON)
        if _influences(Body.JUPITER, jupiter, from_moon, aspects) and _influences(
            Body.SATURN, saturn, from_moon, aspects
        ):
            add(0.15, f"double transit on the {ordinal(house)} from the Moon")
        lord = facts.lord(house)
        on_lord = _influences(Body.JUPITER, jupiter, facts.signs[lord], aspects)
        saturn_on = saturn_on_lord and _influences(Body.SATURN, saturn, facts.signs[lord], aspects)
        if on_lord and saturn_on:
            add(
                0.15,
                f"Jupiter and Saturn both influence the natal {ordinal(house)} lord "
                f"{name(lord)} (double transit)",
            )
        elif on_lord:
            add(0.1, f"Jupiter influences the natal {ordinal(house)} lord {name(lord)}")
        elif saturn_on:
            add(0.05, f"Saturn influences the natal {ordinal(house)} lord {name(lord)}")
    targets = {facts.sign_of_house(h): h for h in spec.houses}
    for level, lord in zip(("mahadasha", "antardasha"), lords[:2], strict=False):
        sign = transits.sign(lord, month)
        if sign in targets:
            add(0.15, f"the {level} lord {name(lord)} transits the {ordinal(targets[sign])} house")
    return min(1.0, 0.15 + sum(f.score for f in factors)), factors


def _confidence(
    activation: float, trigger: float, agreeing: int, needed: int
) -> Literal["strong", "moderate", "weak"]:
    """Strong needs ``needed`` systems to agree with Vimshottari and a transit to confirm."""
    if activation >= 0.5 and trigger >= 0.5 and agreeing >= needed:
        return "strong"
    if activation >= 0.35 and (trigger >= 0.4 or agreeing >= 1):
        return "moderate"
    return "weak"


def _factor_out(factor: Factor) -> PredictionFactorOut:
    return PredictionFactorOut(
        kind=factor.kind,
        label=factor.label,
        score=round(factor.score, 3),
        weight=factor.weight,
        rules=list(factor.rules),
    )


def _rule_out(result: RuleResult) -> PredictionRuleOut:
    rule = result.rule
    return PredictionRuleOut(
        id=rule.id,
        name=rule.name,
        summary=rule.effects.summary,
        polarity=rule.effects.polarity,
        evidence=list(result.evidence),
    )


def compute_predictions(
    chart: ChartResult,
    start: date | None = None,
    end: date | None = None,
    *,
    gender: str | None = None,
    catalogue: Catalogue | None = None,
    model: TimingModel = FULL,
) -> PredictionsOut:
    """Monthly scores, tones and windows for each life domain between ``start`` and ``end``.

    ``start`` defaults to the birth month and ``end`` (exclusive) to 60 years later; both
    are kept within the birth and the ephemeris. At most 100 years are computed.
    ``model`` chooses the timing techniques combined (all of them by default).
    """
    rules = catalogue or default_catalogue()
    birth_day = jd_to_datetime(chart.time.jd_ut).date().replace(day=1)
    last_day = jd_to_datetime(chart.ephemeris.jd_end - 31.0).date().replace(day=1)
    first = max(birth_day, (start or birth_day).replace(day=1))
    stop = min(last_day, end or _add_months(first, 720))
    if stop <= first:
        raise ValueError("the prediction range must end after it starts, after the birth")
    months = _months(first, stop)
    if len(months) > MAX_MONTHS:
        raise ValueError(f"the prediction range may cover at most {MAX_MONTHS // 12} years")

    facts = ChartFacts.from_chart(chart, gender=gender)
    natal = rules.evaluate(facts, YOGA_CATEGORIES | READING_CATEGORIES)
    av = ashtakavarga(facts.lagna_sign, facts.signs)
    sav = av.sav
    shadbala = compute_shadbala(chart)
    ratio = {b: s.rupas / REQUIRED_RUPAS[b] for b, s in shadbala.items()}
    tones = {b: functional_tone(facts, b) for b in GRAHAS}
    until = months[-1].jd_ut + 31.0
    vimshottari = _Lookup(_flat_periods(chart, NakshatraDasha.VIMSHOTTARI, 3, until))
    yogini = _Lookup(_flat_periods(chart, NakshatraDasha.YOGINI, 2, until))
    transits = _Transits(chart, [m.jd_ut for m in months])
    moon_sign = facts.signs[Body.MOON]
    gochara = [_gochara_tone(transits, i, moon_sign) for i in range(len(months))]
    chains = [vimshottari.at(m.jd_ut).lords for m in months]
    yogini_lords = [yogini.at(m.jd_ut).lords for m in months]
    evidence = _PeriodEvidence(facts, rules, transits)
    chara_signs = [CharaTiming(chart, until).at(m.jd_ut) for m in months] if model.chara else []
    signified = kp_houses(chart) if model.kp else {}
    level_weights = [w for _, w in LEVELS]

    domains = []
    for spec in DOMAIN_SPECS:
        promise, promise_factors = domain_promise(spec, facts, sav, ratio, natal, gender)
        links = {b: _link(facts, spec, b, gender, chart if model.varga else None) for b in GRAHAS}
        targets = chara_targets(chart, spec, gender) if model.chara else []
        group = KP_GROUPS.get(spec.domain) if model.kp else None
        scores, month_tones, detail = [], [], []
        for i, chain in enumerate(chains):
            weights = [
                (w, links[lord][0], lord) for (_, w), lord in zip(LEVELS, chain, strict=True)
            ]
            activation = sum(w * link for w, link, _ in weights)
            toned = sum(w * link * tones[lord] for w, link, lord in weights)
            period_tone = toned / activation if activation else 0.0
            trigger, trigger_factors = _trigger(
                facts,
                spec,
                transits,
                i,
                chain,
                av if model.ashtakavarga else None,
                model.saturn_on_lord,
            )
            second = max(links[lord][0] for lord in yogini_lords[i])
            converges = second >= 0.5
            chara = chara_value(chara_signs[i], targets) if targets else 0.0
            kp = kp_value(signified, group, chain, level_weights) if group else 0.0
            agreeing = converges + (chara >= AGREES) + (kp >= AGREES)
            age = (months[i].jd_ut - chart.time.jd_ut) / 365.25
            score = promise * activation * (0.5 + 0.5 * trigger) * spec.plausible(age)
            if targets:
                score *= 1.0 - SYSTEM_SWING + 2 * SYSTEM_SWING * chara
            if group:
                score *= 1.0 - SYSTEM_SWING + 2 * SYSTEM_SWING * kp
            score = min(1.0, score * (CONVERGENCE_BONUS if converges else 1.0))
            tone = clamp(0.5 * (2 * promise - 1) + 0.3 * period_tone + 0.2 * gochara[i][0])
            scores.append(score)
            month_tones.append(tone)
            detail.append((activation, trigger, trigger_factors, converges, agreeing))

        def further(
            month: int,
            targets: list[Target] = targets,
            group: tuple[int, ...] | None = group,
        ) -> list[Factor]:
            """The Chara and KP agreement behind a window's peak month."""
            out = []
            if targets:
                label = chara_label(chara_signs[month], targets)
                if label:
                    value = chara_value(chara_signs[month], targets)
                    out.append(Factor("convergence", label, value, 1.0))
            if group:
                label = kp_label(signified, group, chains[month])
                if label:
                    value = kp_value(signified, group, chains[month], level_weights)
                    out.append(Factor("convergence", label, value, 1.0))
            return out

        windows = _windows(
            spec,
            months,
            scores,
            month_tones,
            detail,
            chains,
            yogini_lords,
            links,
            evidence,
            further,
            model.systems,
        )
        domains.append(
            DomainTimelineOut(
                domain=spec.domain,
                houses=list(spec.houses),
                karakas=list(karakas(spec, gender)),
                promise=DomainPromiseOut(
                    score=round(promise, 3), factors=[_factor_out(f) for f in promise_factors]
                ),
                scores=[round(s, 3) for s in scores],
                tones=[round(t, 3) for t in month_tones],
                windows=windows,
            )
        )
    periods = [
        period_out(p)
        for p in _flat_periods(chart, NakshatraDasha.VIMSHOTTARI, 2, until)
        if p.end_jd > months[0].jd_ut - 15 and p.start_jd < until
    ]
    return PredictionsOut(
        start=first,
        end=stop,
        months=[m.start for m in months],
        periods=periods,
        domains=domains,
        notes=NOTES,
    )


class _PeriodEvidence:
    """Knowledge-base dasha and slow-transit rules, cached by lords and by signs."""

    def __init__(self, facts: ChartFacts, catalogue: Catalogue, transits: _Transits) -> None:
        self.facts = facts
        self.transits = transits
        self.dasha = [
            r for r in catalogue if r.rule.category is Category.DASHA and not r.rule.sensitive
        ]
        self.slow = [r for r in catalogue if r.rule.id.startswith(SLOW_RULES)]
        self.catalogue = catalogue
        self._dasha_cache: dict[tuple[Body, ...], list[RuleResult]] = {}
        self._transit_cache: dict[tuple[int, ...], list[RuleResult]] = {}

    def _run(self, compiled: Sequence[CompiledRule], facts: ChartFacts) -> list[RuleResult]:
        results = (self.catalogue.evaluate_rule(c, facts) for c in compiled)
        return [r for r in results if r.present]

    def dasha_rules(self, lords: tuple[Body, ...]) -> list[RuleResult]:
        key = lords[:2]
        if key not in self._dasha_cache:
            self._dasha_cache[key] = self._run(self.dasha, self.facts.with_period(dasha=key))
        return self._dasha_cache[key]

    def transit_rules(self, month: int) -> list[RuleResult]:
        key = tuple(self.transits.sign(b, month) for b in SLOW)
        if key not in self._transit_cache:
            positions = self.transits.positions(month, SLOW)
            self._transit_cache[key] = self._run(
                self.slow, self.facts.with_period(transits=positions)
            )
        return self._transit_cache[key]


def _windows(
    spec: DomainSpec,
    months: Sequence[_Month],
    scores: Sequence[float],
    tones: Sequence[float],
    detail: Sequence[tuple[float, float, list[Factor], bool, int]],
    chains: Sequence[tuple[Body, ...]],
    yogini_lords: Sequence[tuple[Body, ...]],
    links: dict[Body, tuple[float, list[str]]],
    evidence: _PeriodEvidence,
    further: Callable[[int], list[Factor]],
    systems: int,
) -> list[PredictionWindowOut]:
    threshold = max(0.15, float(np.quantile(scores, 0.8)))
    runs: list[tuple[int, int]] = []
    begin = None
    for i, score in enumerate([*scores, -1.0]):
        if score >= threshold and begin is None:
            begin = i
        elif score < threshold and begin is not None:
            runs.append((begin, i))
            begin = None
    best = sorted(runs, key=lambda r: -max(scores[r[0] : r[1]]))[:MAX_WINDOWS]
    out = []
    for first, stop in sorted(best):
        peak = max(range(first, stop), key=lambda i: scores[i])
        activation, trigger, trigger_factors, converges, agreeing = detail[peak]
        chain = chains[peak]
        factors = [
            Factor(
                "period",
                f"{level} of {name(lord)}: " + "; ".join(links[lord][1]),
                links[lord][0],
                weight,
            )
            for (level, weight), lord in zip(LEVELS, chain, strict=True)
            if links[lord][0] > 0
        ]
        factors.extend(trigger_factors)
        if converges:
            lord = max(yogini_lords[peak], key=lambda b: links[b][0])
            label = f"Yogini dasha of {name(lord)} also links: " + "; ".join(links[lord][1])
            factors.append(Factor("convergence", label, links[lord][0], 1.0))
        factors.extend(further(peak))
        rules = [
            r
            for r in evidence.dasha_rules(chain) + evidence.transit_rules(peak)
            if spec.domain in r.rule.effects.domains
        ]
        out.append(
            PredictionWindowOut(
                start=months[first].start,
                end=_add_months(months[stop - 1].start, 1),
                peak=months[peak].start,
                score=round(scores[peak], 3),
                tone=round(tones[peak], 3),
                confidence=_confidence(activation, trigger, agreeing, min(2, systems)),
                dasha=list(chain),
                factors=[_factor_out(f) for f in factors],
                rules=[_rule_out(r) for r in rules],
            )
        )
    return out
