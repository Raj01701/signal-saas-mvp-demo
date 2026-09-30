"""Yogas of a computed chart."""

from __future__ import annotations

import time
from datetime import datetime

import pytest

from jyotish_engine.chart import compute_chart
from jyotish_engine.models import BirthInput, BirthTimeSource, ChartResult, PlaceInput, YogasOut
from jyotish_engine.rules.catalogue import default_catalogue
from jyotish_engine.rules.facts import ChartFacts
from jyotish_engine.rules.yogas import YOGA_CATEGORIES, compute_yogas

DELHI = PlaceInput(name="New Delhi", latitude=28.6139, longitude=77.2090, elevation_m=216)


@pytest.fixture(scope="module")
def chart() -> ChartResult:
    return compute_chart(
        BirthInput(
            local_datetime=datetime(1990, 5, 17, 12, 0),
            place=DELHI,
            time_source=BirthTimeSource.BIRTH_CERTIFICATE,
        )
    )


def test_yogas_of_a_real_chart(chart: ChartResult) -> None:
    yogas = compute_yogas(chart)
    yoga_rules = [r for r in default_catalogue() if r.rule.category in YOGA_CATEGORIES]
    assert yogas.catalogue_size == len(yoga_rules)
    assert not any(y.category not in YOGA_CATEGORIES for y in yogas.present)
    ids = [y.id for y in yogas.present + yogas.cancelled]
    assert len(ids) == len(set(ids))
    assert yogas.present, "every chart forms some yogas (at least one lunar or solar one)"
    for yoga in yogas.present:
        assert yoga.evidence and yoga.sources and yoga.summary
        assert not yoga.cancel_evidence
    for yoga in yogas.cancelled:
        assert yoga.cancel_evidence
    # Exactly one of the Sun-to-Moon gradings always applies.
    grading = [i for i in ids if i.startswith("chandra.moon_") and i.endswith("_from_sun")]
    assert len(grading) == 1


def test_gender_decides_the_rules_that_need_it(chart: ChartResult) -> None:
    undecided = {u.id: u.missing for u in compute_yogas(chart).undecided}
    assert undecided.get("named.maha_bhagya") == "gender"
    decided = compute_yogas(chart, gender="male")
    assert "named.maha_bhagya" not in {u.id for u in decided.undecided}


def test_matches_direct_catalogue_evaluation(chart: ChartResult) -> None:
    facts = ChartFacts.from_chart(chart, gender="female")
    results = default_catalogue().evaluate(facts, YOGA_CATEGORIES)
    direct = {r.rule.id for r in results if r.present}
    assert {y.id for y in compute_yogas(chart, gender="female").present} == direct


def test_yogas_serialise_to_json(chart: ChartResult) -> None:
    yogas = compute_yogas(chart, gender="female")
    again = YogasOut.model_validate_json(yogas.model_dump_json())
    assert again == yogas


def test_evaluation_is_fast(chart: ChartResult) -> None:
    compute_yogas(chart)  # warm the catalogue cache
    start = time.perf_counter()
    for _ in range(10):
        compute_yogas(chart, gender="male")
    assert (time.perf_counter() - start) / 10 < 0.1
