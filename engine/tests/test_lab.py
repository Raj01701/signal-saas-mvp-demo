"""Accuracy Lab: events scored against timelines, controls and the report."""

from __future__ import annotations

from datetime import date, datetime

from jyotish_engine.chart import compute_chart
from jyotish_engine.lab import Case, backtest, render_markdown, score_events
from jyotish_engine.models import BirthInput, PlaceInput
from jyotish_engine.predict import compute_predictions
from jyotish_engine.rectify import EventKind, LifeEvent
from jyotish_engine.rectify.synthetic import synthetic_events

KINDS = [EventKind.MARRIAGE, EventKind.JOB, EventKind.PROPERTY]


def _birth(when: datetime, latitude: float, longitude: float) -> BirthInput:
    return BirthInput(
        local_datetime=when, place=PlaceInput(name="x", latitude=latitude, longitude=longitude)
    )


def test_events_are_scored_within_the_range() -> None:
    birth = _birth(datetime(1985, 3, 9, 7, 40), 19.076, 72.8777)
    chart = compute_chart(birth)
    events = [*synthetic_events(chart, KINDS), LifeEvent(EventKind.OTHER, date(2010, 1, 1))]
    predictions = compute_predictions(chart, date(1985, 3, 1), date(2046, 1, 1))
    scores = score_events(predictions, [*events, LifeEvent(EventKind.JOB, date(2060, 1, 1))])
    assert len(scores) == len(KINDS)  # "other" and out-of-range events are skipped
    assert all(0.0 <= s.percentile <= 1.0 for s in scores)
    assert {s.domain for s in scores} == {"marriage", "career", "property"}


def test_backtest_separates_the_true_time_on_synthetic_cases() -> None:
    cases = []
    for when, lat, lon in [
        (datetime(1985, 3, 9, 7, 40), 19.076, 72.8777),
        (datetime(1972, 11, 23, 22, 5), 13.0827, 80.2707),
    ]:
        birth = _birth(when, lat, lon)
        cases.append(Case(birth, tuple(synthetic_events(compute_chart(birth), KINDS))))
    report = backtest(cases, replicates=2, seed=1)
    assert report.cases == 2 and report.events == 6 and len(report.replicate_means) == 2
    assert report.true["all"].mean_percentile > report.shuffled["all"].mean_percentile
    assert 0 < report.p_value <= 1
    assert sum(total for total, _ in report.calibration.values()) > 0
    text = render_markdown(report, "Lab", "note")
    assert "| all | 6 |" in text and "| strong |" in text
