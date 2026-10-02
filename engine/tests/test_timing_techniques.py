"""The further timing techniques: divisional charts, Chara dasha, KP house groups,
Ashtakavarga weights and Saturn on the house lord, each switchable."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime

import pytest

from jyotish_engine.astro.bodies import GRAHAS, Body
from jyotish_engine.chart import compute_chart
from jyotish_engine.models import BirthInput, ChartResult, PlaceInput
from jyotish_engine.predict.domains import DOMAIN_SPECS
from jyotish_engine.predict.techniques import (
    CLASSIC,
    FULL,
    KP_GROUPS,
    CharaTiming,
    Target,
    bindu_factor,
    chara_support,
    chara_targets,
    chara_value,
    kp_houses,
    kp_value,
    sav_factor,
    varga_parts,
)
from jyotish_engine.predict.timeline import _confidence, compute_predictions
from jyotish_engine.rules.schema import Domain

TECHNIQUES = ("varga", "chara", "kp", "ashtakavarga", "saturn_on_lord")


@pytest.fixture(scope="module")
def chart() -> ChartResult:
    place = PlaceInput(name="Varanasi", latitude=25.3176, longitude=82.9739)
    return compute_chart(BirthInput(local_datetime=datetime(1985, 3, 14, 6, 20), place=place))


def _spec(domain: Domain):  # type: ignore[no-untyped-def]
    return next(s for s in DOMAIN_SPECS if s.domain is domain)


def test_models() -> None:
    assert CLASSIC.systems == 1 and FULL.systems == 3
    assert not any(getattr(CLASSIC, t) for t in TECHNIQUES)
    assert all(getattr(FULL, t) for t in TECHNIQUES)


def test_kp_house_groups_cover_the_domains() -> None:
    assert KP_GROUPS[Domain.MARRIAGE] == (2, 7, 11)
    assert KP_GROUPS[Domain.CAREER] == (2, 6, 10, 11)
    assert KP_GROUPS[Domain.CHILDREN] == (2, 5, 11)
    # The 11th (fulfilment) is in every group of worldly gains.
    worldly = (Domain.CAREER, Domain.MARRIAGE, Domain.CHILDREN, Domain.WEALTH, Domain.PROPERTY)
    assert all(11 in KP_GROUPS[d] for d in worldly)


def test_kp_value(chart: ChartResult) -> None:
    houses = kp_houses(chart)
    assert set(houses) == set(GRAHAS)
    assert all(h <= frozenset(range(1, 13)) and h for h in houses.values())
    everything = {b: frozenset(range(1, 13)) for b in GRAHAS}
    nothing = {b: frozenset[int]() for b in GRAHAS}
    chain = (Body.VENUS, Body.MOON, Body.MARS)
    assert kp_value(everything, (2, 7, 11), chain, (0.5, 0.35, 0.15)) == pytest.approx(1.0)
    assert kp_value(nothing, (2, 7, 11), chain, (0.5, 0.35, 0.15)) == 0.0
    value = kp_value(houses, (2, 7, 11), chain, (0.5, 0.35, 0.15))
    assert 0.0 <= value <= 1.0


def test_chara_targets_and_support(chart: ChartResult) -> None:
    targets = chara_targets(chart, _spec(Domain.MARRIAGE), "male")
    labels = " | ".join(t.label for t in targets)
    assert "Darakaraka" in labels and "Upapada" in labels and "7th house" in labels
    target = Target(sign=4, label="the 7th house", planet=False)
    assert chara_support(4, [target]) == (0.5, ["is the 7th house"])
    # Leo (fixed) aspects the movable signs but Cancer, the sign behind it.
    assert chara_support(0, [target])[0] == 0.25
    assert chara_support(3, [target])[0] == 0.0
    assert chara_support(4, [target] * 4)[0] == 1.0


def test_chara_timing_runs_from_birth(chart: ChartResult) -> None:
    timing = CharaTiming(chart, chart.time.jd_ut + 50 * 365.25)
    md, ad = timing.at(chart.time.jd_ut + 1)
    assert md == int(chart.ascendant.sign)  # Chara dasha starts from the lagna
    assert 0 <= ad < 12
    targets = chara_targets(chart, _spec(Domain.CAREER), None)
    assert 0.0 <= chara_value((md, ad), targets) <= 1.0


def test_varga_parts_read_the_domain_chart(chart: ChartResult) -> None:
    for domain, label in ((Domain.MARRIAGE, "D9"), (Domain.CAREER, "D10")):
        parts = [p for b in GRAHAS for p in varga_parts(chart, _spec(domain), b)]
        assert parts and all(label in text for _, text in parts)
    # The wealth chart (D2) is not read by houses.
    assert not any(varga_parts(chart, _spec(Domain.WEALTH), b) for b in GRAHAS)


def test_ashtakavarga_factors() -> None:
    bav = {"jupiter": (4, 0, 8, 4, 4, 4, 4, 4, 4, 4, 4, 4)}
    assert bindu_factor(bav, Body.JUPITER, 0) == 1.0
    assert bindu_factor(bav, Body.JUPITER, 1) == 0.5
    assert bindu_factor(bav, Body.JUPITER, 2) == 1.5
    sav = (28, 20, 40, 30, 28, 28, 28, 28, 28, 28, 28, 28)
    assert sav_factor(sav, 0) == 1.0 and sav_factor(sav, 1) == 0.8 and sav_factor(sav, 2) == 1.2


def test_confidence_needs_the_systems_to_agree() -> None:
    assert _confidence(0.6, 0.6, 1, 1) == "strong"
    assert _confidence(0.6, 0.6, 1, 2) == "moderate"
    assert _confidence(0.6, 0.6, 2, 2) == "strong"
    assert _confidence(0.4, 0.2, 0, 2) == "weak"


def _labels(predictions) -> str:  # type: ignore[no-untyped-def]
    return " | ".join(f.label for d in predictions.domains for w in d.windows for f in w.factors)


def test_classic_and_full_models(chart: ChartResult) -> None:
    start, end = date(1990, 1, 1), date(2030, 1, 1)
    classic = compute_predictions(chart, start, end, gender="male", model=CLASSIC)
    full = compute_predictions(chart, start, end, gender="male", model=FULL)
    assert "Chara dasha" not in _labels(classic) and "KP (houses" not in _labels(classic)
    assert "Chara dasha" in _labels(full) and "KP (houses" in _labels(full)
    assert any(a.scores != b.scores for a, b in zip(classic.domains, full.domains, strict=True))
    for domain in full.domains:
        assert all(0.0 <= s <= 1.0 for s in domain.scores)


@pytest.mark.parametrize("technique", TECHNIQUES)
def test_each_technique_changes_the_timeline(chart: ChartResult, technique: str) -> None:
    start, end = date(1990, 1, 1), date(2040, 1, 1)
    base = compute_predictions(chart, start, end, gender="male", model=CLASSIC)
    one = compute_predictions(
        chart, start, end, gender="male", model=replace(CLASSIC, **{technique: True})
    )
    assert any(a.scores != b.scores for a, b in zip(base.domains, one.domains, strict=True))
