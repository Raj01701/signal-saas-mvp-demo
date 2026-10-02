"""Birth-time rectification: score candidate times against dated life events.

For every candidate time in the uncertainty window, only what changes is
recomputed: the lagna (the sidereal angle advances at the sidereal rate), the Moon
(from its speed), and therefore the Vimshottari periods and every house-based
link. For each event the running lords down to the sookshma (level 4) are linked to
the event's houses, karakas and divisional chart, using the same links as the
prediction timeline; the candidate's log-likelihood sums ``log(0.05 + score)`` over
the events. Optional traditional priors refine it: **Kunda** (the lagna times 81
falls in a nakshatra of the Moon's nakshatra lord), **Pranapada** in a trine from
the lagna, and the **navamsa lagna's** sign matching the native's gender (odd for a
man). Their exact conditions vary between authors, so they are off unless asked for.

The result ranks distinct candidates (at least two minutes apart), gives each a
share of the probability among them, the dasha chain at each event, and what
differs between the leading candidates. Where several neighbouring grid times
score the same, the middle of that plateau is taken.
"""

from __future__ import annotations

import math
from collections.abc import Collection, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta

from jyotish_engine.astro.bodies import Body
from jyotish_engine.astro.houses import ascendant_from_armc, chart_angles
from jyotish_engine.astro.time import Instant, datetime_to_jd, jd_to_datetime
from jyotish_engine.chart import compute_chart_at
from jyotish_engine.core.nakshatra import nakshatra_of
from jyotish_engine.core.varga import varga_sign
from jyotish_engine.core.zodiac import SIGN_LORDS, Sign
from jyotish_engine.dasha.base import Period, active_chain
from jyotish_engine.dasha.nakshatra import DEFINITIONS, NakshatraDasha, mahadashas
from jyotish_engine.models import (
    ChartResult,
    RectificationCandidateOut,
    RectificationOut,
    RectifiedEventOut,
    ScanPointOut,
)
from jyotish_engine.predict.domains import DomainSpec
from jyotish_engine.predict.timeline import _link
from jyotish_engine.rectify.events import EVENT_SPECS, EventKind
from jyotish_engine.rules.facts import ChartFacts
from jyotish_engine.special.lagnas import pranapada

SIDEREAL_DEG_PER_DAY = 360.98564736629
LEVEL_WEIGHTS = (0.15, 0.2, 0.3, 0.35)  # mahadasha, antardasha, pratyantar, sookshma
FLOOR = 0.05
PRIOR_BONUS = {"kunda": math.log(1.5), "pranapada": math.log(1.3), "navamsa_gender": math.log(1.3)}
PRIORS = tuple(PRIOR_BONUS)
DISTINCT_MINUTES = 2.0
TOP = 5


@dataclass(frozen=True, slots=True)
class LifeEvent:
    kind: EventKind
    date: date


@dataclass(frozen=True, slots=True)
class _Candidate:
    offset_seconds: float
    jd_ut: float
    facts: ChartFacts
    mahadashas: list[Period]


class _Model:
    """What a candidate time changes: lagna, Moon, dashas; everything else is fixed."""

    def __init__(self, chart: ChartResult, gender: str | None) -> None:
        self.chart = chart
        self.gender = gender
        self.base = ChartFacts.from_chart(chart, gender=gender)
        place = chart.birth.place
        angles = chart_angles(Instant.from_jd_ut(chart.time.jd_ut), place.latitude, place.longitude)
        self.armc, self.obliquity, self.latitude = angles.armc, angles.obliquity, place.latitude
        self.ayanamsa = (angles.ascendant - chart.ascendant.sidereal_longitude) % 360.0
        moon = next(g for g in chart.grahas if g.body is Body.MOON)
        self.moon, self.moon_speed = moon.sidereal_longitude, moon.speed
        self.sun = self.base.positions[Body.SUN]
        self.year_days = chart.dashas.year_days
        self.definition = DEFINITIONS[NakshatraDasha.VIMSHOTTARI]
        sunrise = chart.day.sunrise
        self.sunrise_jd = datetime_to_jd(sunrise) if sunrise else None

    def candidate(self, offset_seconds: float, until_jd: float) -> _Candidate:
        days = offset_seconds / 86_400.0
        jd = self.chart.time.jd_ut + days
        armc = (self.armc + SIDEREAL_DEG_PER_DAY * days) % 360.0
        lagna = (ascendant_from_armc(armc, self.obliquity, self.latitude) - self.ayanamsa) % 360.0
        moon = (self.moon + self.moon_speed * days) % 360.0
        facts = replace(
            self.base, lagna=lagna, positions={**self.base.positions, Body.MOON: moon}, results={}
        )
        cycles = 2 + int((until_jd - jd) / (self.definition.total_years * self.year_days))
        periods = mahadashas(NakshatraDasha.VIMSHOTTARI, jd, moon, self.year_days, cycles)
        return _Candidate(offset_seconds, jd, facts, periods)

    def chain(self, candidate: _Candidate, jd: float) -> tuple[Body, ...]:
        definition = self.definition
        periods = active_chain(
            candidate.mahadashas, jd, definition.sequence, 4, definition.sub_period_rule
        )
        return periods[-1].lords

    def priors(self, candidate: _Candidate, wanted: Collection[str]) -> dict[str, bool]:
        facts = candidate.facts
        out: dict[str, bool] = {}
        if "kunda" in wanted:
            kunda = nakshatra_of((facts.lagna * 81.0) % 360.0).nakshatra.lord
            out["kunda"] = kunda is nakshatra_of(facts.positions[Body.MOON]).nakshatra.lord
        if "pranapada" in wanted and self.sunrise_jd is not None:
            minutes = (candidate.jd_ut - self.sunrise_jd) * 1440.0
            point = pranapada(self.sun, minutes)
            out["pranapada"] = (int(point // 30) - facts.lagna_sign) % 12 + 1 in (1, 5, 9)
        if "navamsa_gender" in wanted and self.gender is not None:
            odd = facts.navamsa_sign("lagna") % 2 == 0
            out["navamsa_gender"] = odd == (self.gender == "male")
        return out


def _varga_score(facts: ChartFacts, spec: DomainSpec, chain: Sequence[Body]) -> float:
    """Dasha lords ruling or occupying the event house in its divisional chart."""
    if spec.varga is None:
        return 0.0
    division = spec.varga
    lagna = int(varga_sign(facts.lagna, division))
    target = (lagna + spec.primary[0] - 1) % 12
    lord = SIGN_LORDS[Sign(target)]
    score = 0.0
    for weight, body in zip(LEVEL_WEIGHTS, chain, strict=False):
        if body is lord:
            score += weight
        elif int(varga_sign(facts.positions[body], division)) == target:
            score += 0.7 * weight
    return score


def _event_score(
    model: _Model, candidate: _Candidate, event: LifeEvent, jd: float
) -> tuple[float, tuple[Body, ...], list[str]]:
    spec = EVENT_SPECS[event.kind]
    chain = model.chain(candidate, jd)
    links = [_link(candidate.facts, spec, body, model.gender) for body in chain]
    d1 = sum(w * link for w, (link, _) in zip(LEVEL_WEIGHTS, links, strict=False))
    score = 0.75 * d1 + 0.25 * _varga_score(candidate.facts, spec, chain)
    reasons = [
        f"{b.value.title()}: " + "; ".join(r) for b, (_, r) in zip(chain, links, strict=False) if r
    ]
    return score, chain, reasons


def _plateau_centres(scores: Sequence[float]) -> list[int]:
    """Indices ordered by score; runs of equal neighbours are represented by their middle."""
    centres: list[int] = []
    i = 0
    while i < len(scores):
        j = i
        while j + 1 < len(scores) and abs(scores[j + 1] - scores[i]) < 1e-9:
            j += 1
        centres.append((i + j) // 2)
        i = j + 1
    return sorted(centres, key=lambda k: -scores[k])


def rectify(
    chart: ChartResult,
    events: Sequence[LifeEvent],
    *,
    uncertainty_minutes: float = 60.0,
    step_seconds: float = 60.0,
    gender: str | None = None,
    priors: Collection[str] = (),
) -> RectificationOut:
    """Rank birth times within ``±uncertainty_minutes`` of the chart's time by the events."""
    scored = [e for e in events if e.kind is not EventKind.OTHER]
    if len(scored) < 2:
        raise ValueError("rectification needs at least two dated events (other than 'other')")
    if not 0 < uncertainty_minutes <= 180 or not 5 <= step_seconds <= 600:
        raise ValueError("the window must be at most 180 minutes and the step 5 to 600 seconds")
    unknown = set(priors) - set(PRIORS)
    if unknown:
        raise ValueError(f"unknown priors {sorted(unknown)}; choose from {list(PRIORS)}")
    birth_date = jd_to_datetime(chart.time.jd_ut).date()
    if any(e.date <= birth_date for e in scored):
        raise ValueError("every event must fall after the birth")
    model = _Model(chart, gender)
    event_jds = [
        datetime_to_jd(datetime(e.date.year, e.date.month, e.date.day, 12, tzinfo=UTC))
        for e in scored
    ]
    until = max(event_jds) + 1.0
    steps = int(uncertainty_minutes * 60 // step_seconds)
    offsets = [k * step_seconds for k in range(-steps, steps + 1)]

    totals: list[float] = []
    for offset in offsets:
        candidate = model.candidate(offset, until)
        total = sum(
            math.log(FLOOR + _event_score(model, candidate, e, jd)[0])
            for e, jd in zip(scored, event_jds, strict=True)
        )
        total += sum(
            PRIOR_BONUS[name] for name, ok in model.priors(candidate, priors).items() if ok
        )
        totals.append(total)

    chosen: list[int] = []
    for index in _plateau_centres(totals):
        if all(abs(offsets[index] - offsets[c]) >= DISTINCT_MINUTES * 60 for c in chosen):
            chosen.append(index)
        if len(chosen) == TOP:
            break
    best = max(totals[i] for i in chosen)
    weights = [math.exp(totals[i] - best) for i in chosen]
    candidates = [
        _candidate_out(
            model, offsets[i], totals[i], w / sum(weights), scored, event_jds, until, priors
        )
        for i, w in zip(chosen, weights, strict=True)
    ]
    return RectificationOut(
        candidates=candidates,
        scan=[
            ScanPointOut(offset_minutes=o / 60.0, log_likelihood=round(t, 4))
            for o, t in zip(offsets, totals, strict=True)
        ],
        differences=_differences(candidates),
        step_seconds=step_seconds,
        uncertainty_minutes=uncertainty_minutes,
        priors=sorted(priors),
        notes=[
            "Candidate times are ranked by how well the running dasha lords, down to the "
            "sookshma, signify each event; review the leading candidates with the events "
            "you know best.",
            "The weights are working values until they are calibrated against recorded events.",
        ],
    )


def _candidate_out(
    model: _Model,
    offset: float,
    total: float,
    share: float,
    events: Sequence[LifeEvent],
    event_jds: Sequence[float],
    until: float,
    priors: Collection[str],
) -> RectificationCandidateOut:
    candidate = model.candidate(offset, until)
    facts = candidate.facts
    moon = nakshatra_of(facts.positions[Body.MOON])
    rectified = []
    for event, jd in zip(events, event_jds, strict=True):
        score, chain, reasons = _event_score(model, candidate, event, jd)
        rectified.append(
            RectifiedEventOut(
                kind=event.kind.value,
                date=event.date,
                dasha=list(chain),
                score=round(score, 3),
                reasons=reasons,
            )
        )
    return RectificationCandidateOut(
        offset_minutes=round(offset / 60.0, 3),
        local_time=model.chart.time.local + timedelta(seconds=offset),
        utc=jd_to_datetime(candidate.jd_ut),
        log_likelihood=round(total, 4),
        share=round(share, 4),
        lagna=Sign(facts.lagna_sign),
        lagna_degrees=round(facts.lagna % 30.0, 3),
        navamsa_lagna=Sign(facts.navamsa_sign("lagna")),
        moon_nakshatra=moon.nakshatra.name,
        moon_pada=moon.pada,
        priors=model.priors(candidate, priors),
        events=rectified,
    )


def _differences(candidates: Sequence[RectificationCandidateOut]) -> list[str]:
    """What separates each runner-up from the leading candidate."""
    if not candidates:
        return []
    best, out = candidates[0], []
    for other in candidates[1:]:
        at = f"{other.offset_minutes:+.1f} min"
        if other.lagna != best.lagna:
            out.append(
                f"{at}: lagna {other.lagna.name.title()} instead of {best.lagna.name.title()}"
            )
        if other.navamsa_lagna != best.navamsa_lagna:
            sign, leading = other.navamsa_lagna.name.title(), best.navamsa_lagna.name.title()
            out.append(f"{at}: navamsa lagna {sign} instead of {leading}")
        if (other.moon_nakshatra, other.moon_pada) != (best.moon_nakshatra, best.moon_pada):
            out.append(f"{at}: Moon in {other.moon_nakshatra} pada {other.moon_pada}")
        for mine, theirs in zip(best.events, other.events, strict=True):
            if mine.dasha != theirs.dasha:
                lords = " / ".join(b.value.title() for b in theirs.dasha)
                what = mine.kind.replace("_", " ")
                out.append(f"{at}: at the {what} of {mine.date} the periods are {lords}")
    return out


def best_chart(chart: ChartResult, result: RectificationOut) -> ChartResult:
    """The full chart at the leading candidate time."""
    offset = result.candidates[0].offset_minutes * 60.0
    return compute_chart_at(chart.time.jd_ut + offset / 86_400.0, chart.birth.place, chart.settings)
