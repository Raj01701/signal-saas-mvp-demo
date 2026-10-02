"""One set of windows across the reading: every section that names a time for marriage or
children names one of the reading's own windows, the same ones whatever the date of the
reading, and never a lighter stretch as the time of a wedding or a birth."""

from __future__ import annotations

import re
from datetime import date, datetime

import pytest

from jyotish_engine.chart import compute_chart
from jyotish_engine.models import (
    BirthInput,
    LifeMomentOut,
    LifeReadingOut,
    LifeWindowOut,
    MaritalInput,
    MaritalStatus,
    PlaceInput,
)
from jyotish_engine.predict import life_reading
from jyotish_engine.rules.schema import Domain

TODAY = date(2026, 9, 30)
LATER = date(2027, 6, 15)
EVENTS = (Domain.MARRIAGE, Domain.CHILDREN)
#: Made-up births across five decades, both genders, three cities.
BIRTHS = [
    (datetime(1972, 2, 11, 5, 40), 19.076, 72.8777, "female"),
    (datetime(1983, 8, 29, 16, 5), 22.5726, 88.3639, "male"),
    (datetime(1990, 5, 17, 12, 0), 28.6139, 77.209, "male"),
    (datetime(1994, 12, 3, 21, 50), 28.6139, 77.209, "female"),
    (datetime(1999, 4, 23, 9, 15), 22.5726, 88.3639, "male"),
]
STATUSES = {
    "unknown": None,
    "single": MaritalInput(status=MaritalStatus.SINGLE),
    "married": MaritalInput(status=MaritalStatus.MARRIED),
}
YEAR = re.compile(r"\b(?:19|20)\d\d\b")


def _reading(index: int, status: str, today: date = TODAY) -> LifeReadingOut:
    when, lat, lon, gender = BIRTHS[index]
    chart = compute_chart(
        BirthInput(local_datetime=when, place=PlaceInput(name="", latitude=lat, longitude=lon))
    )
    return life_reading(chart, today, gender=gender, marital=STATUSES[status])


@pytest.fixture(scope="module", params=[(i, s) for i in range(len(BIRTHS)) for s in STATUSES])
def reading(request: pytest.FixtureRequest) -> LifeReadingOut:
    index, status = request.param
    return _reading(index, status)


def _spans(windows: list[LifeWindowOut], domain: Domain) -> set[tuple[date, date]]:
    return {(w.start, w.end) for w in windows if w.domain is domain}


def _moments(r: LifeReadingOut) -> list[LifeMomentOut]:
    out = [m for c in r.past for m in c.moments] + [m for y in r.future for m in y.moments]
    return out + ([r.wedding.window] if r.wedding and r.wedding.window else [])


def test_every_moment_is_one_of_the_windows(reading: LifeReadingOut) -> None:
    for moment in _moments(reading):
        if moment.domain is Domain.HEALTH:
            continue
        assert (moment.start, moment.end) in _spans(reading.windows, moment.domain), moment
    for check in reading.checks:
        spans = _spans(reading.windows, check.domain)
        assert any(start == check.start for start, _ in spans), check
        assert any(end == check.end for _, end in spans), check


def test_only_strong_windows_stand_for_a_wedding_or_a_birth(reading: LifeReadingOut) -> None:
    married = reading.marital.status is MaritalStatus.MARRIED
    for window in reading.windows:
        if window.domain is Domain.CHILDREN or (window.domain is Domain.MARRIAGE and not married):
            assert window.strength == "strong", window
    if not married:
        assert all(w.end > reading.today for w in reading.windows if w.domain is Domain.CHILDREN), (
            "children are not told as past events for someone not known to be married"
        )


def test_the_marriage_section_names_only_the_windows(reading: LifeReadingOut) -> None:
    if reading.marriage is None:
        return
    timing = reading.marriage.paragraphs[-1]
    for w in reading.windows:
        if w.domain is Domain.MARRIAGE:
            timing = timing.replace(f"{w.when} {w.ages}", "")
    timing = re.sub(r"now, until \w+ \d{4}", "", timing)
    assert not YEAR.search(timing), timing


def test_the_next_window_is_the_first_one_ahead(reading: LifeReadingOut) -> None:
    if reading.marriage is None or reading.marital.status is MaritalStatus.MARRIED:
        return
    timing = reading.marriage.paragraphs[-1]
    match = re.search(r"next strong window(?: for marriage)? is ([^,.]+\))", timing)
    if match is None:
        return
    ahead = [
        w
        for w in reading.windows
        if w.domain is Domain.MARRIAGE and w.end > reading.today and w.strength == "strong"
    ]
    assert ahead and match.group(1) == f"{ahead[0].when} {ahead[0].ages}"


def test_the_summary_names_a_window(reading: LifeReadingOut) -> None:
    line = next((s for s in reading.summary if s.startswith("The most promising")), None)
    if line is None:
        return
    assert any(
        line.startswith(f"The most promising stretch ahead is {w.when},") for w in reading.windows
    )


@pytest.mark.parametrize("index", [1, 3])
def test_the_windows_do_not_depend_on_the_reading_date(index: int) -> None:
    def key(r: LifeReadingOut) -> set[tuple[Domain, date, date, str]]:
        return {
            (w.domain, w.start, w.end, w.strength)
            for w in r.windows
            if w.domain is not Domain.CHILDREN
        }

    assert key(_reading(index, "unknown")) == key(_reading(index, "unknown", LATER))
