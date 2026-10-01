"""The life reading: everyday language, read for the person's age, the whole life covered
and sensitive matters left out."""

from __future__ import annotations

import re
from datetime import date, datetime
from itertools import pairwise

import pytest

from jyotish_engine.astro.bodies import Body
from jyotish_engine.chart import compute_chart
from jyotish_engine.core.zodiac import Sign
from jyotish_engine.models import BirthInput, ChartResult, LifeReadingOut, PlaceInput
from jyotish_engine.predict import life_reading, words
from jyotish_engine.predict.voice import (
    Voice,
    age_at,
    ages,
    area_words,
    life_stage_words,
    stage_title,
    when_future,
    when_past,
)
from jyotish_engine.rules.schema import Domain

DELHI = PlaceInput(name="New Delhi", latitude=28.6139, longitude=77.2090)
TODAY = date(2026, 9, 30)
GRAHAS = tuple(Body)[:9]
#: Astrologer's shorthand that must not reach the reader.
JARGON = re.compile(
    r"\blords?\b|lord\(|house\(|dusthana|kendra|trikona|bindu|shadbala|virupa|\bdashas?\b|"
    r"mahadasha|antardasha|\b\d+(?:st|nd|rd|th) (?:house|lord|from)\b",
    re.IGNORECASE,
)
SENSITIVE = re.compile(
    r"\bdeath\b|\bdie[sd]?\b|\bdying\b|illness|disease|surgery|accident|divorce|widow|"
    r"mrityu|maraka|longevity|\bhospital\b|\bfatal",
    re.IGNORECASE,
)
GROWN_UP = re.compile(
    r"marri|spouse|wedding|romance|child's birth|pregnan|children|settle down|proposals",
    re.IGNORECASE,
)


def _chart(when: datetime) -> ChartResult:
    return compute_chart(BirthInput(local_datetime=when, place=DELHI))


@pytest.fixture(scope="module")
def chart() -> ChartResult:
    return _chart(datetime(1990, 5, 17, 12, 0))


@pytest.fixture(scope="module")
def reading(chart: ChartResult) -> LifeReadingOut:
    return life_reading(chart, TODAY, gender="male", name="arjun")


@pytest.fixture(scope="module")
def child() -> LifeReadingOut:
    return life_reading(_chart(datetime(2017, 6, 14, 8, 20)), TODAY, gender="female")


def _texts(r: LifeReadingOut) -> list[str]:
    sections = [r.nature, r.present, *r.areas, *r.good_to_know]
    texts = list(r.summary) + [f"{g.label} {g.value} {g.note}" for g in r.glance]
    texts += [s.title for s in sections] + [p for s in sections for p in s.paragraphs]
    for chapter in r.past + r.later:
        texts += [chapter.title, *chapter.paragraphs, *(m.text for m in chapter.moments)]
    for year in r.future:
        texts += [year.title, *year.paragraphs]
    return texts + [m.text for m in r.checks] + r.notes


def test_the_reading_is_plain_and_leaves_out_sensitive_matters(
    reading: LifeReadingOut, child: LifeReadingOut
) -> None:
    for text in _texts(reading) + _texts(child):
        assert not JARGON.search(text), text
        assert not SENSITIVE.search(text), text
        assert "  " not in text and " ." not in text and "::" not in text, text


def test_it_speaks_to_the_person(reading: LifeReadingOut) -> None:
    assert reading.name == "Arjun" and reading.age == 36
    assert reading.summary[0].startswith("Arjun, you are ")
    labels = [g.label for g in reading.glance]
    assert labels[:3] == ["Rising sign (Lagna)", "Moon sign (Rashi)", "Birth star (Nakshatra)"]
    assert "Manglik" in labels


def test_the_past_runs_from_birth_to_today(chart: ChartResult, reading: LifeReadingOut) -> None:
    assert reading.past[0].start == chart.birth.local_datetime.date()
    for before, after in pairwise(reading.past):
        assert before.end == after.start and not before.current
    assert reading.past[-1].current and reading.past[-1].start <= TODAY < reading.past[-1].end
    assert reading.later and reading.later[0].start == reading.past[-1].end


def test_moments_suit_the_age_they_fall_in(reading: LifeReadingOut) -> None:
    birth = date(1990, 5, 17)
    moments = [m for c in reading.past for m in c.moments]
    moments += [m for y in reading.future for m in y.moments] + reading.checks
    assert moments
    for moment in moments:
        age = age_at(birth, moment.start)
        if moment.domain is Domain.MARRIAGE:
            assert age >= 21
        if moment.domain is Domain.CHILDREN:
            assert age >= 25
        if moment.domain in (Domain.CAREER, Domain.WEALTH):
            assert age >= 18
        assert moment.domain is not Domain.HEALTH
    for chapter in reading.past:
        last_age = age_at(birth, chapter.end) - 1
        if last_age < 21:
            assert not GROWN_UP.search(" ".join(chapter.paragraphs)), chapter.title


def test_children_are_read_after_the_marriage_stretch(reading: LifeReadingOut) -> None:
    checks = {m.domain: m for m in reading.checks}
    if Domain.MARRIAGE in checks and Domain.CHILDREN in checks:
        assert checks[Domain.CHILDREN].start >= checks[Domain.MARRIAGE].start


def test_a_child_reads_nothing_grown_up(child: LifeReadingOut) -> None:
    assert child.age == 9
    for text in _texts(child):
        assert not GROWN_UP.search(text), text
    assert all(s.key != "manglik" for s in child.good_to_know)
    assert all(g.label != "Manglik" for g in child.glance)
    assert {s.key for s in child.areas} <= {"education", "travel", "talents"}
    assert not child.checks
    assert "child's chart" in " ".join(child.summary)


def test_the_past_is_told_in_the_past_and_the_future_ahead(reading: LifeReadingOut) -> None:
    for chapter in reading.past[:-1]:
        text = " ".join(chapter.paragraphs)
        assert "looks promising" not in text and "is likely to" not in text
    for year in reading.future:
        assert " brought " not in year.paragraphs[0]
        assert year.paragraphs[0] and year.title[0].isupper()


def test_present_and_future(reading: LifeReadingOut) -> None:
    assert reading.present.paragraphs[0].startswith("Since ")
    assert "sub-period" in reading.present.paragraphs[1]
    assert reading.present.paragraphs[-1].startswith("What helps now: ")
    assert [y.year for y in reading.future] == [2026, 2027, 2028, 2029, 2030]
    assert {s.key for s in reading.good_to_know} >= {"manglik", "sade_sati", "lucky", "remedies"}


def test_areas_follow_the_age(reading: LifeReadingOut) -> None:
    keys = [s.key for s in reading.areas]
    assert keys[:4] == ["career", "wealth", "marriage", "children"]
    assert "education" not in keys  # read until 30


def test_the_reading_is_deterministic(chart: ChartResult, reading: LifeReadingOut) -> None:
    assert life_reading(chart, TODAY, gender="male", name="arjun") == reading


def test_phrasing_varies_within_a_reading(reading: LifeReadingOut) -> None:
    openings = [p.split(" ")[0] for c in reading.past for p in c.paragraphs[1:]]
    texts = _texts(reading)
    assert len(set(texts)) >= 0.95 * len(texts)
    assert len(openings) <= 1 or len(set(openings)) > 1


def test_the_words_cover_every_case() -> None:
    for body in GRAHAS:
        assert set(words.PERIOD_FEEL[body]) == {"young", "adult", "senior"}
        assert words.TEEN_FEEL[body] and words.SUB_PERIOD_FEEL[body] and words.PERIOD_GIST[body]
        assert words.REMEDIES[body] and words.CAREER_FIELDS[body]
    for sign in Sign:
        assert words.RISING[sign] and words.MOON_SIGN[sign] and words.PARTNER[sign]
    assert len(words.NAKSHATRA_NATURE) == 27
    for house in range(1, 13):
        assert set(words.HOUSE_AREAS[house]) == {"young", "adult", "senior"}
        assert words.CHART_RULER_IN_HOUSE[house]
    for domain, bands in words.MOMENTS.items():
        assert domain is not Domain.HEALTH
        for before, after in pairwise(bands):
            assert before.until_age == after.from_age
        for band in bands:
            assert band.good and all(t is None or t.strip() for t in (band.mixed, band.hard))
    assert set(words.YEAR_TITLES) == set(words.MOMENTS)


def test_the_reader_is_addressed_by_first_name() -> None:
    from jyotish_engine.predict.story import _first_name

    assert _first_name("lalit kumar") == "Lalit" and _first_name("Dr. Rao") == "Rao"
    assert _first_name("अर्जुन शर्मा") == "अर्जुन" and _first_name("O'Brien") == "O'Brien"
    assert _first_name("Sample A (example)") is None and _first_name("x2") is None


def test_voice_helpers() -> None:
    birth = date(1990, 5, 17)
    assert age_at(birth, date(2026, 5, 16)) == 35 and age_at(birth, date(2026, 5, 17)) == 36
    assert when_past(date(2011, 6, 1), date(2014, 8, 1)) == "mid-2011 to mid-2014"
    assert when_past(date(2019, 3, 1), date(2019, 5, 1)) == "early 2019"
    assert when_past(date(2009, 1, 1), date(2010, 9, 1)) == "2009–2010"
    assert when_future(date(2027, 3, 1), date(2027, 9, 1)) == "March to August 2027"
    assert when_future(date(2027, 12, 1), date(2028, 2, 1)) == "December 2027 to January 2028"
    assert ages(birth, date(2013, 1, 1), date(2016, 1, 1)) == "(ages 22–25)"
    assert life_stage_words(13, 22) == "your teens and early twenties"
    assert life_stage_words(48, 63) == "your late forties to your early sixties"
    assert life_stage_words(0, 4) == "your early childhood"
    assert stage_title(life_stage_words(30, 47)) == "Thirties and forties"
    assert area_words(7, 10) == "friendships" and area_words(7, 19) == "close relationships"
    assert area_words(7, 30) == "marriage and partnerships"
    assert area_words(5, 20) == "studies and romance" and area_words(5, 30).startswith("children")
    voice = Voice("seed")
    options = ("a", "b", "c")
    picks = [voice.pick(f"k{i}", options, "family") for i in range(12)]
    assert all(x != y for x, y in pairwise(picks))
    assert Voice("seed").pick("k0", options, "f") == Voice("seed").pick("k0", options, "f")
