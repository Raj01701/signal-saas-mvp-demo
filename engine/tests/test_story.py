"""The life reading: everyday language, the whole life covered, sensitive matters left out."""

from __future__ import annotations

from datetime import date, datetime
from itertools import pairwise

import pytest

from jyotish_engine.chart import compute_chart
from jyotish_engine.models import BirthInput, ChartResult, LifeReadingOut, PlaceInput
from jyotish_engine.predict import life_reading
from jyotish_engine.predict.story import CHILDHOOD_AGE, JARGON, plain, plain_name
from jyotish_engine.rules.catalogue import default_catalogue

DELHI = PlaceInput(name="New Delhi", latitude=28.6139, longitude=77.2090)
TODAY = date(2026, 9, 30)


@pytest.fixture(scope="module")
def chart() -> ChartResult:
    return compute_chart(BirthInput(local_datetime=datetime(1990, 5, 17, 12, 0), place=DELHI))


@pytest.fixture(scope="module")
def reading(chart: ChartResult) -> LifeReadingOut:
    return life_reading(chart, TODAY, gender="male")


def _texts(r: LifeReadingOut) -> list[str]:
    lines = r.nature + r.strengths + r.cautions + r.present.lines
    lines += [line for chapter in r.past + r.chapters_ahead for line in chapter.lines]
    lines += [line for year in r.future for line in year.lines]
    return (
        r.summary
        + [r.present.headline]
        + [c.headline for c in r.past + r.chapters_ahead]
        + [y.headline for y in r.future]
        + [line.text for line in lines]
    )


def test_every_rule_reads_in_plain_words() -> None:
    for entry in default_catalogue().rules:
        rule = entry.rule
        text = plain(rule.effects.summary)
        assert text and not JARGON.search(text), (rule.id, text)
        assert text[0].isupper() and text.endswith("."), (rule.id, text)


@pytest.mark.parametrize(
    ("summary", "expected"),
    [
        ("The 5th lord in the 11th: gains through children.", "Gains through children."),
        (
            "The 1st house (body, health and standing) is ripe for events.",
            "Matters of body, health and standing are ripe for events.",
        ),
        (
            "a Dhana yoga, active in the dashas of the two lords",
            "A Dhana yoga, active during the periods of the two planets involved.",
        ),
    ],
)
def test_plain_rewrites(summary: str, expected: str) -> None:
    assert plain(summary) == expected


def test_names_lose_their_technical_qualifier() -> None:
    assert plain_name("Raja Yoga (1st and 4th lords)") == "Raja Yoga"
    assert plain_name("Hamsa Yoga") == "Hamsa Yoga"


def test_the_reading_is_plain_and_leaves_out_sensitive_matters(reading: LifeReadingOut) -> None:
    for text in _texts(reading):
        assert not JARGON.search(text), text
        lowered = text.lower()
        assert "time for health" not in lowered
        assert not any(word in lowered for word in (" death", " die ", "longevity", "lifespan"))


def test_the_past_runs_from_birth_to_today(chart: ChartResult, reading: LifeReadingOut) -> None:
    chapters = reading.past
    assert chapters[0].start == chart.birth.local_datetime.date()
    for before, after in pairwise(chapters):
        assert abs((after.start - before.end).days) <= 1
    assert [c.current for c in chapters].count(True) == 1 and chapters[-1].current
    assert chapters[-1].end > TODAY and all(c.start > TODAY for c in reading.chapters_ahead)


def test_childhood_chapters_speak_only_of_studies_and_family(reading: LifeReadingOut) -> None:
    birth = reading.past[0].start
    for chapter in reading.past:
        if (chapter.end - birth).days / 365.2425 <= CHILDHOOD_AGE:
            for line in chapter.lines:
                assert line.text.endswith(
                    ("for studies and learning.", "for parents and elders.")
                ), line.text


def test_present_and_future(reading: LifeReadingOut) -> None:
    assert "major period (mahadasha)" in reading.present.headline
    assert "sub-period (antardasha)" in reading.present.headline
    assert [y.year for y in reading.future] == [2026, 2027, 2028, 2029, 2030]
    assert all(y.headline for y in reading.future)
    assert reading.summary[0].startswith("By nature: ")
    assert len(reading.notes) >= 3


def test_the_reading_is_deterministic(chart: ChartResult, reading: LifeReadingOut) -> None:
    assert life_reading(chart, TODAY, gender="male") == reading
