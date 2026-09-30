"""Synthetic life events generated from the engine's own rules, to test rectification.

For each event kind, the event is placed in the middle of the sookshma period
(between ages 18 and 60, at least four days long) whose four Vimshottari lords
signify the kind most strongly for the true birth time.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import timedelta

from jyotish_engine.astro.bodies import GRAHAS, Body
from jyotish_engine.astro.time import jd_to_datetime
from jyotish_engine.dasha.base import Period
from jyotish_engine.dasha.nakshatra import NakshatraDasha, sub_periods
from jyotish_engine.models import ChartResult
from jyotish_engine.predict.domains import DomainSpec
from jyotish_engine.predict.timeline import _link
from jyotish_engine.rectify.events import EVENT_SPECS, EventKind
from jyotish_engine.rectify.search import LEVEL_WEIGHTS, LifeEvent, _Model, _varga_score

YEAR = 365.25


def synthetic_events(
    chart: ChartResult, kinds: Sequence[EventKind], gender: str | None = None
) -> list[LifeEvent]:
    birth = chart.time.jd_ut
    model = _Model(chart, gender)
    candidate = model.candidate(0.0, birth + 61 * YEAR)
    level = candidate.mahadashas
    for _ in range(3):
        level = [sub for period in level for sub in sub_periods(NakshatraDasha.VIMSHOTTARI, period)]
    window = [
        p
        for p in level
        if birth + 18 * YEAR <= p.start_jd
        and p.end_jd <= birth + 60 * YEAR
        and p.end_jd - p.start_jd >= 4
    ]
    events: list[LifeEvent] = []
    used: set[float] = set()
    for kind in kinds:
        spec = EVENT_SPECS[kind]
        link = {b: _link(candidate.facts, spec, b, gender)[0] for b in GRAHAS}

        def strength(
            period: Period, spec: DomainSpec = spec, link: dict[Body, float] = link
        ) -> float:
            d1 = sum(w * link[b] for w, b in zip(LEVEL_WEIGHTS, period.lords, strict=True))
            return float(0.75 * d1 + 0.25 * _varga_score(candidate.facts, spec, period.lords))

        best = max((p for p in window if p.start_jd not in used), key=strength)
        used.add(best.start_jd)
        middle = jd_to_datetime((best.start_jd + best.end_jd) / 2)
        events.append(LifeEvent(kind, (middle - timedelta(hours=12)).date()))
    return events
