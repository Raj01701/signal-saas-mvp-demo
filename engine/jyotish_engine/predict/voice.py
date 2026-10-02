"""Language helpers for life readings: dates and ages as people say them, lists, and
phrasing that varies from sentence to sentence but stays the same for the same chart."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import date, timedelta

from jyotish_engine.predict.words import HOUSE_AREAS, STUDENT_AREAS, Stage

#: Life stages: young until 18, adult until 60.
ADULT_AGE = 18
SENIOR_AGE = 60


def age_at(birth: date, day: date) -> int:
    """Completed years of age on ``day``."""
    years = day.year - birth.year - ((day.month, day.day) < (birth.month, birth.day))
    return max(0, years)


def years_between(birth: date, day: date) -> float:
    return (day - birth).days / 365.2425


def stage_of(age: float) -> Stage:
    return "young" if age < ADULT_AGE else "adult" if age < SENIOR_AGE else "senior"


def area_words(house: int, age: float) -> str:
    """What a house stands for at ``age``: no marriage or children talk for the young."""
    if house in STUDENT_AREAS and ADULT_AGE <= age < (21 if house == 7 else 23):
        return STUDENT_AREAS[house]
    return HOUSE_AREAS[house][stage_of(age)]


def join(items: Sequence[str]) -> str:
    """A list in prose; a serial comma keeps "and"-phrases apart."""
    items = [item for item in items if item]
    if len(items) <= 1:
        return "".join(items)
    if len(items) == 2 and not any(" and " in item for item in items):
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + ", and " + items[-1]


def cap(text: str) -> str:
    return text[:1].upper() + text[1:]


def _part(day: date) -> str:
    return "early" if day.month <= 4 else "mid" if day.month <= 8 else "late"


def _part_year(day: date) -> str:
    part = _part(day)
    return f"mid-{day.year}" if part == "mid" else f"{part} {day.year}"


def when_past(start: date, end: date) -> str:
    """A past stretch as people remember it: a year, part of a year, or a span of years."""
    last = end - timedelta(days=1)
    if start.year == last.year:
        return _part_year(start) if (last - start).days < 125 else str(start.year)
    if (last - start).days < 550:
        return f"{_part_year(start)} to {_part_year(last)}"
    if last.year - start.year >= 3:
        return f"{_part_year(start)} to {_part_year(last)}"
    return f"{start.year}–{last.year}"


def month(day: date) -> str:
    return f"{day:%B %Y}"


def when_future(start: date, end: date) -> str:
    """A coming stretch to the month, as someone planning ahead needs it."""
    last = end - timedelta(days=1)
    if (start.year, start.month) == (last.year, last.month):
        return month(start)
    if start.year == last.year:
        return f"{start:%B} to {last:%B %Y}"
    return f"{month(start)} to {month(last)}"


def ages(birth: date, start: date, end: date) -> str:
    """ "(age 24)" or "(ages 23–26)" for a stretch of time."""
    first = age_at(birth, start)
    last = age_at(birth, max(start, end - timedelta(days=1)))
    return f"(age {first})" if first == last else f"(ages {first}–{last})"


def life_stage_words(first_age: int, last_age: int) -> str:
    """Ages in words: "your early childhood", "your teens and early twenties"."""
    if last_age < 6:
        return "your early childhood"
    if last_age < 13:
        return "your childhood" if first_age < 6 else "your school years"
    names: list[str] = []
    for age in range(first_age, last_age + 1):
        if age < 6:
            name = "early childhood"
        elif age < 13:
            name = "school years"
        elif age < 20:
            name = "teens"
        else:
            name = ("twenties", "thirties", "forties", "fifties", "sixties", "seventies",
                    "eighties", "nineties")[min(age // 10 - 2, 7)]  # fmt: skip
        if not names or names[-1] != name:
            names.append(name)
    if names[0] == "early childhood" and len(names) > 1:
        names[0] = "childhood"
    first, last = names[0], names[-1]
    if first_age >= 20 and first_age % 10 >= 7:
        first = f"late {first}"
    elif first_age >= 20 and first_age % 10 >= 4 and len(names) > 1:
        first = f"mid-{first}"
    if last_age >= 13 and last_age % 10 <= 3 and len(names) > 1:
        last = f"early {last}"
    if len(names) == 1:
        return f"your {first}"
    if len(names) == 2:
        return f"your {first} and {last}"
    return f"your {first} to your {last}"


def stage_title(words: str) -> str:
    """A life-stage phrase as a heading: "your teens and early twenties" becomes "Teens
    and early twenties"."""
    return cap(words.replace("your ", ""))


class Voice:
    """Picks among ways of saying the same thing, steadily for one chart, and never the
    same way twice in a row within a family of sentences."""

    def __init__(self, seed: str) -> None:
        self.seed = seed
        self.last: dict[str, int] = {}

    def pick(self, key: str, options: Sequence[str], family: str) -> str:
        digest = hashlib.blake2b(f"{self.seed}|{key}".encode(), digest_size=4).digest()
        index = int.from_bytes(digest, "big") % len(options)
        if len(options) > 1 and self.last.get(family) == index:
            index = (index + 1) % len(options)
        self.last[family] = index
        return options[index]
