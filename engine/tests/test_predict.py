"""Prediction timeline: deterministic, bounded, age-aware and explained."""

from __future__ import annotations

import time
from datetime import date, datetime

import pytest

from jyotish_engine.astro.bodies import GRAHAS
from jyotish_engine.chart import compute_chart
from jyotish_engine.models import BirthInput, ChartResult, PlaceInput, PredictionsOut
from jyotish_engine.predict import compute_predictions, timeline
from jyotish_engine.predict.domains import DOMAIN_SPECS
from jyotish_engine.predict.timeline import _link
from jyotish_engine.rules.facts import ChartFacts
from jyotish_engine.rules.schema import Domain

DELHI = PlaceInput(name="New Delhi", latitude=28.6139, longitude=77.2090)


@pytest.fixture(scope="module")
def chart() -> ChartResult:
    return compute_chart(BirthInput(local_datetime=datetime(1990, 5, 17, 12, 0), place=DELHI))


@pytest.fixture(scope="module")
def out(chart: ChartResult) -> PredictionsOut:
    return compute_predictions(chart, date(1990, 1, 1), date(2040, 1, 1))


def test_shape_and_bounds(out: PredictionsOut) -> None:
    assert out.start == date(1990, 5, 1) and out.end == date(2040, 1, 1)  # clipped to birth
    assert len(out.months) == 12 * 50 - 4
    assert [d.domain for d in out.domains] == [s.domain for s in DOMAIN_SPECS]
    for domain in out.domains:
        assert len(domain.scores) == len(domain.tones) == len(out.months)
        assert all(0.0 <= s <= 1.0 for s in domain.scores)
        assert all(-1.0 <= t <= 1.0 for t in domain.tones)
        assert 0.0 <= domain.promise.score <= 1.0 and domain.promise.factors
    assert out.periods[0].start_jd_ut <= out.periods[-1].start_jd_ut
    assert out.notes


def test_deterministic(chart: ChartResult, out: PredictionsOut) -> None:
    again = compute_predictions(chart, date(1990, 1, 1), date(2040, 1, 1))
    assert again.model_dump() == out.model_dump()


def test_windows_are_explained(out: PredictionsOut) -> None:
    for domain in out.domains:
        assert domain.windows, domain.domain
        for window in domain.windows:
            assert out.start <= window.start <= window.peak < window.end <= out.end
            kinds = {f.kind for f in window.factors}
            assert "period" in kinds, window
            if window.confidence == "strong":
                assert "convergence" in kinds and "trigger" in kinds
            assert all(r.evidence for r in window.rules)
            assert len(window.dasha) == 3


def test_events_are_read_by_age(out: PredictionsOut) -> None:
    months = out.months
    by_domain = {d.domain: d for d in out.domains}
    for domain, first_age in ((Domain.MARRIAGE, 18), (Domain.CAREER, 16)):
        early = [
            s
            for m, s in zip(months, by_domain[domain].scores, strict=True)
            if m.year < 1990 + first_age
        ]
        assert early and not any(early), domain
        assert all(w.start.year >= 1990 + first_age for w in by_domain[domain].windows)


def test_the_seventh_lord_links_to_marriage(chart: ChartResult) -> None:
    facts = ChartFacts.from_chart(chart)
    spec = next(s for s in DOMAIN_SPECS if s.domain is Domain.MARRIAGE)
    lord = facts.lord(7)
    value, reasons = _link(facts, spec, lord, None)
    assert value >= 0.9 and "owns the 7th house" in reasons
    assert all(0.0 <= _link(facts, spec, b, None)[0] < 1.0 for b in GRAHAS)


def test_range_is_checked(chart: ChartResult, monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="end after it starts"):
        compute_predictions(chart, date(2030, 1, 1), date(2020, 1, 1))
    clipped = compute_predictions(chart, date(2040, 1, 1), date(2100, 1, 1))
    assert clipped.end <= date(2053, 10, 1)  # the development ephemeris ends in 2053
    monkeypatch.setattr(timeline, "MAX_MONTHS", 12)
    with pytest.raises(ValueError, match="at most 1 years"):
        compute_predictions(chart, date(2020, 1, 1), date(2022, 1, 1))


def test_speed(chart: ChartResult) -> None:
    started = time.perf_counter()
    compute_predictions(chart)
    assert time.perf_counter() - started < 3.0  # about 0.4 s for 60 years here
