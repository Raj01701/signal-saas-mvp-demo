"""A life reading told the way a good astrologer talks: who you are, your life so far,
where you stand now and the years ahead.

The reading is built from the engine's own results: the Vimshottari periods, the
month-by-month prediction timeline, the transits of Saturn and Jupiter and the yogas.
It is written for the person, not for astrologers:

* **Age-aware.** Each stretch of life is read for the age the person was (or will be)
  then. Childhood is about home, school and family; marriage is read from 21 and
  children from 23; career and money from 18 (see ``words.MOMENTS``). A house is
  described by what it means at that age, so a child's chapter never mentions marriage.
* **Life-aware.** Marriage timing follows what the person says: for someone married,
  stretches after the wedding are about married life and the wedding is checked against
  the chart's windows; for someone single, later stretches are openings; when nobody
  has said, the reading allows for either.
* **Tense-aware.** The past is told in the past tense and dated in years, the way
  people remember it; the future is dated to the month, the way people plan.
* **Human.** A few strong moments per chapter instead of every window; sentences vary
  in shape, steadily for the same chart.
* **Careful.** Nothing about death, illness or certain outcomes; health is not read,
  a parent's difficult stretches are not singled out, and difficult times are framed
  with what helps.

Each part keeps a short technical basis for astrologers.
"""

from __future__ import annotations

import re
import statistics
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from jyotish_engine.astro.bodies import Body
from jyotish_engine.astro.time import datetime_to_jd, jd_to_datetime
from jyotish_engine.core.dignity import Relationship, natural_relationship
from jyotish_engine.core.zodiac import Sign
from jyotish_engine.match.tables import NAKSHATRA_GANA, NAKSHATRA_NADI, NAKSHATRA_YONI, YONI_ANIMALS
from jyotish_engine.models import (
    ChartResult,
    DashaPeriodOut,
    DomainTimelineOut,
    GlanceItemOut,
    LifeMomentOut,
    LifeReadingOut,
    MaritalInput,
    MaritalStatus,
    PredictionsOut,
    ReadingSectionOut,
    StoryChapterOut,
    Tone,
    WeddingCheckOut,
    YearOutlookOut,
    YogasOut,
)
from jyotish_engine.predict import topics, words
from jyotish_engine.predict.promise import functional_tone
from jyotish_engine.predict.timeline import compute_predictions
from jyotish_engine.predict.voice import (
    Voice,
    age_at,
    ages,
    area_words,
    cap,
    join,
    life_stage_words,
    month,
    stage_of,
    stage_title,
    when_future,
    when_past,
    years_between,
)
from jyotish_engine.rules.facts import ChartFacts
from jyotish_engine.rules.schema import Domain
from jyotish_engine.rules.yogas import compute_yogas
from jyotish_engine.transit.saturn import TransitEpisode, sade_sati
from jyotish_engine.transit.timeline import sign_timeline

#: The Mahapurusha yoga each planet forms; when present it speaks for the planet.
MAHAPURUSHA = {
    Body.MARS: "mahapurusha.ruchaka",
    Body.MERCURY: "mahapurusha.bhadra",
    Body.JUPITER: "mahapurusha.hamsa",
    Body.VENUS: "mahapurusha.malavya",
    Body.SATURN: "mahapurusha.sasa",
}
SEVEN = (Body.SUN, Body.MOON, Body.MARS, Body.MERCURY, Body.JUPITER, Body.VENUS, Body.SATURN)
#: An active stretch is a run of months in the top fifth of the person's own months for
#: that area (and at least this activation); runs this close together are told as one.
MIN_SCORE = 0.12
ACTIVE_QUANTILE = 0.8
MERGE_GAP_MONTHS = 3
#: Tenor of a stretch from its quality (see ``_episodes``).
GOOD_ABOVE = 0.06
HARD_BELOW = -0.06
#: The least support (activation times tenor, averaged by month) for a "brightest area".
BRIGHT_MIN = 0.004
#: How many moments a chapter, a year and the coming months tell.
CHAPTER_MOMENTS = 3
YEAR_MOMENTS = 3
#: Ages from which each life area appears in the "life areas" section.
AREA_AGES: dict[Domain, tuple[int, int | None]] = {
    Domain.CAREER: (14, None),
    Domain.WEALTH: (18, None),
    Domain.MARRIAGE: (18, None),
    Domain.CHILDREN: (23, None),
    Domain.PROPERTY: (18, None),
    Domain.EDUCATION: (4, 31),
    Domain.TRAVEL: (0, None),
    Domain.SPIRITUALITY: (25, None),
}
#: The ages at which each area's main past stretch is looked for (checks, life areas).
CHECK_AGES: dict[Domain, tuple[float, float]] = {
    Domain.EDUCATION: (13, 25),
    Domain.CAREER: (20, 70),
    Domain.MARRIAGE: (24, 36),
    Domain.CHILDREN: (25, 45),
    Domain.PROPERTY: (25, 90),
    Domain.TRAVEL: (16, 90),
    Domain.WEALTH: (21, 90),
    Domain.SPIRITUALITY: (25, 90),
}
#: Life areas people remember best; the summary prefers them when looking back.
MILESTONES = frozenset({Domain.CAREER, Domain.MARRIAGE, Domain.CHILDREN, Domain.PROPERTY})
NOTES = [
    "This reading follows traditional Vedic astrology (Jyotish), computed from the birth "
    "details. It describes tendencies and timing, not certainties, and it is not medical, "
    "legal or financial advice.",
    "The past is the best test. If the dates under 'Your life so far' match your life, the "
    "rest of the reading is more likely to fit you; if several are off by a year or more, "
    "the birth time may need checking.",
    "Health is read only as traditional tendencies; for any health concern, please see a doctor.",
    "Readings that depend on the rising sign change if the birth time is off by more than a "
    "few minutes.",
]


@dataclass(frozen=True, slots=True)
class _Episode:
    """An active stretch in one life area, with its tenor."""

    domain: Domain
    start: date
    #: The first day after the stretch.
    end: date
    peak: date
    score: float
    quality: float
    lords: tuple[Body, ...]

    @property
    def tone(self) -> Tone:
        if self.quality > GOOD_ABOVE:
            return "good"
        return "hard" if self.quality < HARD_BELOW else "mixed"


#: Marriage is read two years earlier for women (the legal ages in India are 18 and 21).
FEMALE_MARRIAGE_OFFSET = 2.0


def _band(domain: Domain, age: float, female: bool = False) -> words.Moment | None:
    if domain is Domain.MARRIAGE and female:
        age += FEMALE_MARRIAGE_OFFSET
    return next((m for m in words.MOMENTS.get(domain, ()) if m.covers(age)), None)


def _quantile(values: Sequence[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(q * (len(ordered) - 1) + 0.5))]


def _runs(flags: Sequence[bool], gap: int) -> list[tuple[int, int]]:
    """Index ranges of consecutive True values, joined across gaps of up to ``gap``."""
    runs: list[tuple[int, int]] = []
    begin = None
    for i, flag in enumerate([*flags, False]):
        if flag and begin is None:
            begin = i
        elif not flag and begin is not None:
            if runs and begin - runs[-1][1] <= gap:
                runs[-1] = (runs[-1][0], i)
            else:
                runs.append((begin, i))
            begin = None
    return runs


def _next_month(day: date) -> date:
    return date(day.year + day.month // 12, day.month % 12 + 1, 1)


def _baseline(timeline: DomainTimelineOut) -> float:
    """The part of the timeline's tone that comes from the natal promise."""
    return 0.5 * (2 * timeline.promise.score - 1)


def _level(score: float) -> words.Level:
    if score >= 0.6:
        return "strong"
    if score >= 0.53:
        return "good"
    return "average" if score >= 0.45 else "effort"


class _Dashas:
    """The Vimshottari table by level, with the chain running on any day."""

    def __init__(self, chart: ChartResult) -> None:
        periods = chart.dashas.vimshottari.periods
        self.levels: dict[int, list[DashaPeriodOut]] = {}
        for period in periods:
            self.levels.setdefault(len(period.lords), []).append(period)
        self.deepest = max(self.levels)

    def at(self, day: date, level: int) -> DashaPeriodOut:
        moment = datetime(day.year, day.month, day.day, 12, tzinfo=UTC)
        items = self.levels[min(level, self.deepest)]
        return next(
            (p for p in items if p.start <= moment < p.end),
            items[-1] if moment >= items[-1].end else items[0],
        )

    def chain(self, day: date) -> tuple[Body, ...]:
        return tuple(self.at(day, self.deepest).lords)


def _center(life: PredictionsOut) -> float:
    """The person's usual tenor. Stretches are judged against it, so that a chart whose
    transits run cool is not read as one long testing time."""
    relative = [
        tone - _baseline(t)
        for t in life.domains
        if t.domain in words.MOMENTS
        for score, tone in zip(t.scores, t.tones, strict=True)
        if score > 0
    ]
    return statistics.median(relative) if relative else 0.0


def _episodes(
    life: PredictionsOut,
    birth: date,
    dashas: _Dashas,
    center: float,
    since: date | None = None,
    female: bool = False,
) -> list[_Episode]:
    """Active stretches per life area, judged against the person's own months (or, with
    ``since``, against the months from then on)."""
    months = life.months
    years = [years_between(birth, m) for m in months]
    usable = [t for t in life.domains if t.domain in words.MOMENTS]
    episodes = []
    for timeline in usable:
        base = _baseline(timeline)
        scores = [
            score
            if _band(timeline.domain, age, female) and (since is None or day >= since)
            else 0.0
            for score, age, day in zip(timeline.scores, years, months, strict=True)
        ]
        positive = [s for s in scores if s > 0]
        if len(positive) < 6:
            continue
        threshold = max(MIN_SCORE, _quantile(positive, ACTIVE_QUANTILE))
        for first, stop in _runs([s >= threshold for s in scores], MERGE_GAP_MONTHS):
            span = range(first, stop)
            peak = max(span, key=lambda i: scores[i])
            weight = sum(scores[i] for i in span) or 1.0
            mean = sum(scores[i] * (timeline.tones[i] - base) for i in span) / weight
            quality = (mean - center) + 0.25 * (2 * timeline.promise.score - 1)
            episodes.append(
                _Episode(
                    timeline.domain,
                    months[first],
                    _next_month(months[stop - 1]),
                    months[peak],
                    scores[peak],
                    quality,
                    dashas.chain(months[peak]),
                )
            )
    return episodes


def _strongest(
    items: Sequence[_Episode],
    limit: int,
    *,
    hard_at_most: int = 1,
    weight: Callable[[_Episode], float] | None = None,
) -> list[_Episode]:
    """The strongest stretches, one per life area, in time order."""
    chosen: list[_Episode] = []
    hard = 0
    for item in sorted(items, key=lambda e: -(weight(e) if weight else e.score)):
        if any(c.domain is item.domain for c in chosen) or len(chosen) == limit:
            continue
        if item.tone == "hard":
            if hard == hard_at_most:
                continue
            hard += 1
        chosen.append(item)
    return sorted(chosen, key=lambda e: e.start)


class Reader:
    """Everything one reading needs, gathered once."""

    def __init__(
        self,
        chart: ChartResult,
        today: date,
        gender: str | None,
        name: str | None,
        years_ahead: int,
        marital: MaritalInput | None = None,
    ) -> None:
        self.chart = chart
        self.today = today
        self.gender = gender
        self.name = _first_name(name)
        self.facts = ChartFacts.from_chart(chart, gender)
        self.birth = chart.birth.local_datetime.date()
        if today < self.birth:
            raise ValueError("the reading date must not be before the birth")
        self.age = age_at(self.birth, today)
        self.dashas = _Dashas(chart)
        self.voice = Voice(f"{chart.settings_hash}|{chart.time.jd_ut:.5f}")
        self.years_ahead = years_ahead
        until = date(today.year + years_ahead, 1, 1)
        self.life = compute_predictions(chart, self.birth.replace(day=1), until, gender=gender)
        center = self.center = _center(self.life)
        self.female = gender == "female"
        self.minor = self.age < 18
        self.marital = marital or MaritalInput()
        self.wedding = self._wedding_span()
        lifetime = _episodes(self.life, self.birth, self.dashas, center, female=self.female)
        # The years ahead are also read against each other, as an astrologer compares one
        # year with the next; these stretches never displace the lifetime ones.
        local = [
            e
            for e in _episodes(
                self.life, self.birth, self.dashas, center, today.replace(day=1), self.female
            )
            if not any(
                o.domain is e.domain and o.start < e.end and e.start < o.end for o in lifetime
            )
        ]
        self.episodes = lifetime + local
        # The chart's main marriage stretch (21 to 35): children are read after it.
        marriage = [
            e
            for e in lifetime
            if e.domain is Domain.MARRIAGE and 24 <= self.marriage_age(e.start) < 36
        ]
        if marriage:
            strongest = max(e.score for e in marriage)
            self.marriage: date | None = min(
                e.start for e in marriage if e.score >= 0.85 * strongest
            )
        else:
            self.marriage = None
        if self.wedding is not None:
            self.marriage = self.wedding[0]
        self.yogas: YogasOut = compute_yogas(chart, gender=gender)
        self.moon_sign = int(self.facts.signs[Body.MOON])
        self.sade_sati = self._sade_sati()

    # -- chart facts in words --------------------------------------------------------

    def promise(self, domain: Domain) -> float:
        return next(t.promise.score for t in self.life.domains if t.domain is domain)

    def level(self, domain: Domain) -> words.Level:
        return _level(self.promise(domain))

    @staticmethod
    def level_tone(level: words.Level) -> Tone:
        return {"strong": "good", "good": "good", "average": "mixed", "effort": "hard"}[level]  # type: ignore[return-value]

    @staticmethod
    def day(jd: float) -> date:
        return _day(jd)

    def marriage_age(self, day: date) -> float:
        """Age on ``day`` as marriage is read (two years on for women)."""
        return years_between(self.birth, day) + (FEMALE_MARRIAGE_OFFSET if self.female else 0)

    @property
    def married(self) -> bool:
        return self.marital.status is MaritalStatus.MARRIED

    @property
    def single(self) -> bool:
        return self.marital.status is MaritalStatus.SINGLE

    def _wedding_span(self) -> tuple[date, date] | None:
        """The wedding as a span of days: its month, or its year when no month was given."""
        year, number = self.marital.wedding_year, self.marital.wedding_month
        if year is None:
            return None
        if number is None:
            start, end = date(year, 1, 1), date(year + 1, 1, 1)
        else:
            start, end = date(year, number, 1), date(year + number // 12, number % 12 + 1, 1)
        if years_between(self.birth, end) < 12 or start > self.today:
            raise ValueError("the wedding must come after the 12th birthday and not after today")
        return start, end

    def band(self, domain: Domain, start: date, end: date) -> words.Moment | None:
        """How a stretch reads: by the age it starts at, and for marriage also by what the
        person said. For someone married, stretches after the wedding (and any running now
        or ahead) are about married life; for someone single, past stretches are times when
        relationships were in focus and later ones are openings."""
        band = _band(domain, years_between(self.birth, start), self.female)
        if domain is not Domain.MARRIAGE or band is None:
            return band
        current = end > self.today
        if self.married:
            after = current or (self.wedding is not None and start >= self.wedding[0])
            return words.MARRIED_LIFE if after else band
        if self.single:
            if not current:
                return words.SINGLE_PAST if band.from_age >= 24 else band
            return words.SINGLE_LATER if band.until_age is None else band
        return band

    def area_name(self, domain: Domain) -> str:
        if domain is Domain.MARRIAGE and self.married:
            return "married life"
        return words.AREA_NAMES[domain]

    def area(self, house: int, age: float) -> str:
        if self.minor and house in words.MINOR_AREAS and age >= 18:
            return words.MINOR_AREAS[house]
        return area_words(house, age)

    def houses_of(self, body: Body) -> list[int]:
        """Houses a graha rules, then the one it occupies (a node: its dispositor's)."""
        facts = self.facts
        ruler = facts.dispositor(body) if body in (Body.RAHU, Body.KETU) else body
        owned = [h for h in range(1, 13) if facts.lord(h) is ruler]
        occupied = facts.house(body)
        ordered = [occupied, *owned] if body in (Body.RAHU, Body.KETU) else [*owned, occupied]
        return list(dict.fromkeys(ordered))

    def areas(self, body: Body, age: float, limit: int = 3) -> str:
        return join(list(dict.fromkeys(self.area(h, age) for h in self.houses_of(body)[:limit])))

    def tone_value(self, body: Body) -> float:
        try:
            return functional_tone(self.facts, body)
        except (KeyError, ValueError):
            return 0.0

    def standing(self, body: Body) -> Tone:
        value = self.tone_value(body)
        return "good" if value >= 0.4 else "hard" if value <= -0.3 else "mixed"

    def basis(self, body: Body) -> str:
        houses = ", ".join(str(h) for h in self.houses_of(body))
        return f"{_planet(body)}: houses {houses}; functional tone {self.tone_value(body):+.2f}"

    def link(self, body: Body, age: float, key: str) -> str:
        frame = self.voice.pick(key, words.LINKS, "link")
        return cap(frame.format(planet=_planet(body), areas=self.areas(body, age)))

    def feel(self, body: Body, age: float) -> str:
        if 13 <= age < 18:
            return words.TEEN_FEEL[body]
        if self.minor and stage_of(age) == "adult" and body in words.MINOR_FEEL:
            return words.MINOR_FEEL[body]
        return words.PERIOD_FEEL[body][stage_of(age)]

    def verdict(self, body: Body, tense: words.Tense) -> str:
        options = words.VERDICTS[tense][self.standing(body)]
        frame = self.voice.pick(f"verdict|{body}|{tense}", options, f"verdict-{tense}")
        return frame.format(planet=_planet(body))

    # -- moments -------------------------------------------------------------------

    def moment(
        self, item: _Episode, tense: words.Tense, *, with_ages: bool = True
    ) -> LifeMomentOut | None:
        band = self.band(item.domain, item.start, item.end)
        what = band.words(item.tone) if band else None
        if what is None:
            return None
        span = ages(self.birth, item.start, item.end)
        shown = span if with_ages else ""
        key = f"{item.domain.value}|{item.start}"
        if tense == "past":
            when = when_past(item.start, item.end)
            early = years_between(self.birth, item.start) < 6
            frame = self.voice.pick(key, words.EARLY_FRAMES if early else words.PAST_FRAMES, "past")
            text = frame.format(When=cap(when), when=when, ages=shown, what=what)
        elif tense == "now":
            when = f"until {month(item.end - timedelta(days=1))}"
            frame = self.voice.pick(key, words.NOW_FRAMES, "now")
            text = frame.format(end=month(item.end - timedelta(days=1)), what=what)
        else:
            when = when_future(item.start, item.end)
            frame = self.voice.pick(key, words.FUTURE_FRAMES[item.tone], f"future-{item.tone}")
            text = frame.format(When=cap(when), when=when, ages=shown, what=what)
        text = re.sub(r"\s+([,.;:])", r"\1", re.sub(r"\s{2,}", " ", text))
        lords = "/".join(_planet(b) for b in item.lords)
        return LifeMomentOut(
            domain=item.domain,
            area=words.AREA_NAMES[item.domain],
            start=item.start,
            end=item.end,
            ages=span,
            when=when,
            text=text,
            tone=item.tone,
            basis=f"{item.domain.value}: activation {item.score:.2f} peaking "
            f"{item.peak:%b %Y}, tenor {item.quality:+.2f}, dasha {lords}",
        )

    def moments(self, items: Sequence[_Episode], tense: words.Tense) -> list[LifeMomentOut]:
        out = [self.moment(item, tense) for item in items]
        return [m for m in out if m is not None]

    def told(self, item: _Episode) -> bool:
        if self.minor and item.domain in (Domain.MARRIAGE, Domain.CHILDREN):
            return False
        band = self.band(item.domain, item.start, item.end)
        if band is None or band.words(item.tone) is None:
            return False
        if item.domain is Domain.CHILDREN and self.marriage is not None:
            return item.start >= self.marriage
        return True

    # -- Sade Sati -----------------------------------------------------------------

    def _sade_sati(self) -> list[TransitEpisode]:
        start = self.chart.time.jd_ut
        end = min(self.chart.ephemeris.jd_end - 2.0, start + 100 * 365.25)
        try:
            return sade_sati(self.moon_sign, start, end, self.chart.settings)
        except ValueError:
            return []

    def sade_sati_now(self) -> tuple[TransitEpisode, int, date] | None:
        """The running episode, the house of the running phase and when that phase ends."""
        jd = datetime_to_jd(
            datetime(self.today.year, self.today.month, self.today.day, 12, tzinfo=UTC)
        )
        for episode in self.sade_sati:
            if episode.start_jd_ut <= jd < episode.end_jd_ut:
                span = next(
                    (s for s in episode.spans if s.start_jd_ut <= jd < s.end_jd_ut),
                    episode.spans[-1],
                )
                return episode, span.house, _day(span.end_jd_ut)
        return None

    # -- sections ------------------------------------------------------------------

    def chapter(self, period: DashaPeriodOut, kind: str) -> StoryChapterOut:
        lord = period.lords[0]
        start = max(period.start.date(), self.birth)
        end = period.end.date()
        first_age = age_at(self.birth, start)
        last_age = age_at(self.birth, end - timedelta(days=1))
        end_age = age_at(self.birth, end)
        stage_words = life_stage_words(first_age, last_age)
        current = start <= self.today < end
        middle = years_between(self.birth, start + (min(end, self.today) - start) / 2)
        feel_age = middle if kind == "past" else first_age
        paragraphs: list[str] = []
        moments: list[LifeMomentOut] = []
        tone = self.standing(lord)
        if kind == "later":
            opening = (
                f"In {month(start)}, when you are {first_age}, the {_planet(lord)} period begins "
                f"and runs until {end.year}, covering {stage_words}."
            )
            tense: words.Tense = "future"
        else:
            if period.start.date() < self.birth:
                opening = (
                    f"You were born in the {_planet(lord)} period, which ran until {end.year}, "
                    f"covering {stage_words}."
                    if not current
                    else f"You were born in the {_planet(lord)} period, which runs until "
                    f"{month(end)}."
                )
            elif current:
                opening = (
                    f"Since {month(start)}, when you were {first_age}, you have been in the "
                    f"{_planet(lord)} period. It runs until {month(end)}, when you will be "
                    f"{end_age}."
                )
            else:
                frame = self.voice.pick(f"open|{lord}", words.CHAPTER_OPENINGS, "opening")
                opening = frame.format(
                    y0=start.year,
                    y1=end.year,
                    a0=first_age,
                    a1=end_age,
                    planet=_planet(lord),
                    stage=stage_words,
                    Stage=cap(stage_words),
                )
            tense = "now" if current else "past"
        feel = self.feel(lord, feel_age)
        link_age = first_age if kind == "later" else max(first_age, min(feel_age, self.age))
        if current:
            paragraphs.append(
                f"{opening} What it means for you now is told under 'Where you stand now'."
            )
        else:
            link = self.link(lord, link_age, f"link|{lord}")
            paragraphs.append(" ".join([opening, feel, link, self.verdict(lord, tense)]))
        if kind != "later":
            upto = min(end, self.today)
            inside = [
                e
                for e in self.episodes
                if start <= e.start < upto and e.end <= self.today and e.domain is not Domain.HEALTH
            ]
            picked = _strongest([e for e in inside if self.told(e)], CHAPTER_MOMENTS)
            moments = self.moments(picked, "past")
            if moments:
                paragraphs.append(" ".join(m.text for m in moments))
            elif not current:
                quiet = (
                    "These were mostly quiet years of growing up, without one area of life "
                    "standing out."
                    if last_age < 13
                    else "No single area of life stands out strongly in these years; life "
                    "moved along steadily."
                )
                paragraphs.append(quiet)
        title_words = stage_title(stage_words)
        return StoryChapterOut(
            lord=lord,
            start=start,
            end=end,
            ages=f"{first_age} to {end_age}",
            title=f"{title_words}: the {_planet(lord)} years",
            paragraphs=paragraphs,
            tone=tone,
            moments=moments,
            current=current,
            basis=[f"Vimshottari mahadasha, {self.basis(lord)}"],
        )

    def present(self) -> ReadingSectionOut:
        today = self.today
        md = self.dashas.at(today, 1)
        ad = self.dashas.at(today, 2)
        lord, sub = md.lords[0], ad.lords[-1]
        paragraphs = []
        md_end = md.end.date()
        paragraphs.append(
            " ".join(
                [
                    f"Since {month(max(md.start.date(), self.birth))} you have been in the "
                    f"{_planet(lord)} period, which runs until {month(md_end)}, when you will be "
                    f"{age_at(self.birth, md_end)}.",
                    self.feel(lord, self.age),
                    self.link(lord, self.age, f"now-link|{lord}"),
                    self.verdict(lord, "now"),
                ]
            )
        )
        ad_start, ad_end = ad.start.date(), ad.end.date()
        sub_text = [
            f"Within it, the {_planet(sub)} sub-period runs from "
            f"{month(max(ad_start, self.birth))} to {month(ad_end)}: {words.SUB_PERIOD_FEEL[sub]}."
        ]
        if sub is lord:
            sub_text.append(
                f"This is the opening part of the {_planet(lord)} years, when their themes are "
                "strongest."
            )
        else:
            sub_text.append(self.link(sub, self.age, f"now-sub|{sub}"))
            if lord in SEVEN and sub in SEVEN:
                relation = natural_relationship(lord, sub)
                if relation is Relationship.FRIEND and natural_relationship(sub, lord) is not (
                    Relationship.ENEMY
                ):
                    sub_text.append(
                        f"{_planet(lord)} and {_planet(sub)} are friendly planets, so this part of "
                        "the period tends to flow more smoothly."
                    )
                elif relation is Relationship.ENEMY:
                    sub_text.append(
                        f"{_planet(lord)} and {_planet(sub)} pull in different directions, so "
                        "expect some tension between what you want and what the moment asks of "
                        "you."
                    )
        paragraphs.append(" ".join(sub_text))
        transits = self.transit_words()
        if transits:
            paragraphs.append(" ".join(transits))
        coming = self.coming_months()
        if coming:
            paragraphs.append(" ".join(coming))
        paragraphs.append(
            f"What helps now: {_lower_first(words.REMEDIES[lord])} The remedies at the end "
            "list practices chosen for your chart."
        )
        return ReadingSectionOut(
            key="present",
            title="Where you stand now",
            paragraphs=paragraphs,
            tone=self.standing(lord),
            basis=[
                f"Vimshottari mahadasha {self.basis(lord)}",
                f"antardasha {self.basis(sub)}",
            ],
        )

    def transit_words(self) -> list[str]:
        out = []
        jd = datetime_to_jd(
            datetime(self.today.year, self.today.month, self.today.day, 12, tzinfo=UTC)
        )
        running = self.sade_sati_now()
        if running:
            episode, house, phase_end = running
            order, adult, young = words.SADE_SATI_PHASES[house]
            rewards = (
                "patience, discipline and steady study"
                if self.age < 18
                else "patience, honesty and careful saving"
            )
            out.append(
                f"Saturn is also passing over your Moon sign, the 7½-year stretch known as Sade "
                f"Sati, until {month(_day(episode.end_jd_ut))}. You are in its {order} phase "
                f"(until {month(phase_end)}): {young if self.age < 18 else adult}. Sade Sati is "
                f"not something to fear; it rewards {rewards}."
            )
        else:
            stays = _stays(Body.SATURN, jd, self.chart)
            if stays:
                sign, until = stays[0]
                house = (sign - self.moon_sign) % 12 + 1
                if house in words.SATURN_NOW:
                    text = self.transit_text(words.SATURN_NOW[house])
                    out.append(f"{text}, until about {month(until)}.")
        stays = _stays(Body.JUPITER, jd, self.chart)
        if stays:
            sign, until = stays[0]
            text = self.transit_text(words.JUPITER_NOW[(sign - self.moon_sign) % 12 + 1])
            out.append(f"Until about {month(until)}, {text}.")
            if len(stays) > 1 and (until - self.today).days < 150:
                sign, later = stays[1]
                text = self.transit_text(words.JUPITER_NOW[(sign - self.moon_sign) % 12 + 1])
                out.append(f"After that, until about {month(later)}, {text}.")
        return out

    def transit_text(self, entry: tuple[Tone, str, str]) -> str:
        _, adult, young = entry
        return young if self.age < 18 and young else adult

    def coming_months(self) -> list[str]:
        horizon = self.today + timedelta(days=365)
        ongoing = [e for e in self.episodes if e.start <= self.today < e.end and self.told(e)]
        starting = [e for e in self.episodes if self.today < e.start < horizon and self.told(e)]
        order = ("good", "mixed", "hard")
        presence = _presence(self.today, horizon)
        picked = sorted(
            _strongest(ongoing + starting, 3, weight=presence), key=lambda e: order.index(e.tone)
        )
        out = []
        for item in picked:
            moment = self.moment(item, "now" if item.start <= self.today else "future")
            if moment:
                out.append(moment.text)
        if not out:
            return ["The coming months look steady, without strong swings in any one area."]
        return ["In the coming months:", *out]

    def future(self) -> list[YearOutlookOut]:
        outlooks = []
        today = self.today
        told: set[tuple[Domain, Tone]] = set()
        for year in range(today.year, today.year + self.years_ahead):
            first, last = max(date(year, 1, 1), today), date(year + 1, 1, 1)
            dated: list[tuple[date, str]] = []
            for period in self.dashas.levels.get(2, []):
                start = period.start.date()
                if not first < start < last:
                    continue
                lords = period.lords
                if lords[0] is lords[-1]:
                    dated.append(
                        (
                            start,
                            f"In {month(start)} a new chapter opens: the {_planet(lords[0])} "
                            f"period, {words.PERIOD_GIST[lords[0]]}, which lasts until "
                            f"{_mahadasha_end(self.dashas, lords[0], start)}.",
                        )
                    )
                else:
                    dated.append(
                        (
                            start,
                            f"In {month(start)} the {_planet(lords[-1])} sub-period begins: "
                            f"{words.SUB_PERIOD_FEEL[lords[-1]]}.",
                        )
                    )
            dated += self.sade_sati_events(first, last)
            in_year = [e for e in self.episodes if first <= e.start < last and self.told(e)]
            if year == today.year:
                in_year += [e for e in self.episodes if e.start < today < e.end and self.told(e)]
            presence = _presence(first, last)
            picked = _strongest(in_year, YEAR_MOMENTS, weight=presence)
            moments = [
                m
                for m in (
                    self.moment(e, "now" if e.start <= today else "future", with_ages=False)
                    for e in picked
                )
                if m is not None
            ]
            for m in moments:
                text = m.text
                if (m.domain, m.tone) in told and m.start > today:
                    when = cap(when_future(m.start, m.end))
                    text = words.AGAIN[m.tone].format(When=when, area=m.area)
                told.add((m.domain, m.tone))
                dated.append((max(m.start, first), text))
            dated.sort(key=lambda item: item[0])
            lead = _lead(picked, presence)
            bright = self.brightest(first, last)
            if bright is not None and all(m.domain is not bright for m in moments):
                frame = self.voice.pick(f"bright|{year}", words.BRIGHTEST, "bright")
                area = words.AREA_NAMES[bright]
                dated.append((last, frame.format(area=area, Area=cap(area))))
            elif lead is not None and lead.tone == "hard" and bright is None:
                closing = self.voice.pick(f"steady|{year}", words.STEADY, "steady")
                dated.append((last, closing))
            if lead is not None:
                title = words.YEAR_TITLES[lead.domain][lead.tone]
                tone: Tone = lead.tone
            else:
                title = "a new phase begins" if dated else "a steady year"
                tone = "mixed"
            if not dated:
                dated.append((first, "A steady year without strong swings in any one area."))
            span_ages = sorted(
                {age_at(self.birth, first), age_at(self.birth, last - timedelta(days=1))}
            )
            outlooks.append(
                YearOutlookOut(
                    year=year,
                    ages="–".join(str(a) for a in span_ages),
                    title=cap(title),
                    paragraphs=[" ".join(text for _, text in dated)],
                    tone=tone,
                    moments=moments,
                )
            )
        return outlooks

    def brightest(self, first: date, last: date) -> Domain | None:
        """The life area best supported between two dates, judged by activation and
        tenor month by month, among the areas told at the reader's age."""
        months = self.life.months
        best, best_value = None, 0.0
        for timeline in self.life.domains:
            domain = timeline.domain
            if domain not in words.MOMENTS or domain is Domain.PARENTS:
                continue
            if self.minor and domain in (Domain.MARRIAGE, Domain.CHILDREN):
                continue
            base = _baseline(timeline)
            lift = 0.25 * (2 * timeline.promise.score - 1)
            values = [
                score * max(0.0, tone - base - self.center + lift)
                for day, score, tone in zip(months, timeline.scores, timeline.tones, strict=True)
                if first <= day < last
                and _band(domain, years_between(self.birth, day), self.female) is not None
            ]
            if not values:
                continue
            value = sum(values) / len(values)
            if value > max(best_value, BRIGHT_MIN):
                best, best_value = domain, value
        return best

    def sade_sati_events(self, first: date, last: date) -> list[tuple[date, str]]:
        out = []
        for episode in self.sade_sati:
            start, end = _day(episode.start_jd_ut), _day(episode.end_jd_ut)
            if first < start < last:
                out.append(
                    (
                        start,
                        f"In {month(start)} Saturn's Sade Sati begins and runs until "
                        f"{month(end)}: a slower, more demanding stretch that rewards patience "
                        "and careful saving.",
                    )
                )
            if first < end < last:
                out.append(
                    (
                        end,
                        f"In {month(end)} Sade Sati ends; pressure eases and delayed matters "
                        "start to move.",
                    )
                )
        return out

    def nature(self) -> ReadingSectionOut:
        facts = self.facts
        lagna = Sign(facts.lagna_sign)
        moon = Sign(self.moon_sign)
        star = self.chart_moon_nakshatra()
        _, paragraphs = topics.portrait(self)
        gifts = []
        yogas = {y.id for y in self.yogas.present}
        for body in SEVEN:
            if MAHAPURUSHA.get(body) in yogas:
                continue
            if facts.exalted(body):
                gifts.append(
                    f"{_planet(body)} is exalted in your chart, giving you "
                    f"{words.PLANET_GIFTS[body]}."
                )
            elif facts.own_sign(body):
                gifts.append(
                    f"{_planet(body)} is in its own sign, giving you {words.PLANET_GIFTS[body]}."
                )
        gifts += self.yoga_words()[: max(0, 4 - len(gifts[:2]))]
        if gifts:
            paragraphs.append(" ".join(gifts[:4]))
        ruler = facts.lord(1)
        return ReadingSectionOut(
            key="nature",
            title="Who you are",
            paragraphs=paragraphs,
            basis=[
                f"Lagna {lagna.name.title()}; Moon {moon.name.title()} in nakshatra {star + 1}",
                f"Lagna lord {_planet(ruler)} in house {facts.house(ruler)}",
            ],
        )

    def chart_moon_nakshatra(self) -> int:
        moon = next(g for g in self.chart.grahas if g.body is Body.MOON)
        return moon.nakshatra.index

    def yoga_words(self) -> list[str]:
        out: list[str] = []
        for yoga in self.yogas.present:
            text = words.YOGA_WORDS.get(yoga.id) or next(
                (
                    t
                    for key, t in words.YOGA_WORDS.items()
                    if yoga.id.startswith(key + "_") or yoga.id.startswith(key + ".")
                ),
                None,
            )
            if text and text not in out:
                out.append(text)
        return out

    def areas_section(self) -> list[ReadingSectionOut]:
        """Career, money, home, children, studies, foreign travel, health and inner life, as
        suit the age. Marriage has its own section."""
        out = [topics.career(self)]
        for domain in (Domain.WEALTH, Domain.PROPERTY, Domain.CHILDREN, Domain.EDUCATION):
            card = self.area_card(domain)
            if card is not None:
                out.append(card)
        out += [topics.foreign(self), topics.health(self)]
        card = self.area_card(Domain.SPIRITUALITY)
        return out + ([card] if card is not None else [])

    def area_card(self, domain: Domain) -> ReadingSectionOut | None:
        low, high = AREA_AGES[domain]
        if self.age < low or (high is not None and self.age >= high):
            return None
        level = self.level(domain)
        young = words.AREA_PROMISE_YOUNG.get(domain) if self.age < 18 else None
        paragraphs = [(young or words.AREA_PROMISE[domain])[level]]
        if domain is Domain.WEALTH:
            house = self.facts.house(self.facts.lord(11))
            paragraphs[0] += (
                f" Your gains tend to come through {area_words(house, max(self.age, 25))}."
            )
        timing = self.area_timing(domain)
        if timing:
            paragraphs.append(timing)
        return ReadingSectionOut(
            key=domain.value,
            title=words.AREA_TITLES[domain],
            paragraphs=paragraphs,
            tone=self.level_tone(level),
            basis=[f"{domain.value} promise {self.promise(domain):.2f}"],
        )

    def area_timing(self, domain: Domain) -> str:
        parts = []
        best = self.best_past(domain) if domain in CHECK_AGES else None
        if best is not None and best.tone != "hard":
            parts.append(
                f"Looking back, {when_past(best.start, best.end)} "
                f"{ages(self.birth, best.start, best.end)} was the main stretch for this so far."
            )
        ahead = [
            e
            for e in self.episodes
            if e.domain is domain and e.start > self.today and e.tone != "hard" and self.told(e)
        ]
        if ahead:
            best = max(ahead, key=lambda e: e.score)
            parts.append(
                f"Ahead, the next strong stretch is {when_future(best.start, best.end)} "
                f"{ages(self.birth, best.start, best.end)}."
            )
        return " ".join(parts)

    def manglik(self) -> tuple[str, str]:
        ids = {y.id for y in self.yogas.present}
        cancelled = {y.id for y in self.yogas.cancelled}
        kinds = ("dosha.kuja_lagna", "dosha.kuja_moon", "dosha.kuja_venus")
        if any(k in ids for k in kinds):
            return "Yes", (
                "Mars sits in one of the houses that make a chart Manglik (Mangal dosha). It is "
                "traditionally weighed when matching charts for marriage, and it is commonly "
                "balanced by a similar placement in the partner's chart. It says nothing bad "
                "about you as a person."
            )
        if any(k in cancelled for k in kinds):
            return "Cancelled", (
                "Mars is in a Manglik position, but other factors in the chart cancel it, so "
                "it is not counted as Mangal dosha."
            )
        return "No", "Mars is not in a Manglik position, so there is no Mangal dosha."

    def good_to_know(self) -> list[ReadingSectionOut]:
        out = []
        if not self.minor:
            status, text = self.manglik()
            out.append(
                ReadingSectionOut(
                    key="manglik",
                    title=f"Manglik (Mangal dosha): {status}",
                    paragraphs=[text],
                    basis=sorted(y.id for y in self.yogas.present if y.id.startswith("dosha.kuja")),
                )
            )
        out.append(self.sade_sati_section())
        kala = [y for y in self.yogas.present if y.id.startswith("dosha.kala_sarpa")]
        if kala:
            out.append(
                ReadingSectionOut(
                    key="kala_sarpa",
                    title="Kala Sarpa",
                    paragraphs=[
                        "All the planets fall on one side of Rahu and Ketu in your chart, a "
                        "pattern modern astrologers call Kala Sarpa. It does not appear in the "
                        "classical texts, and many astrologers give it little weight; at most "
                        "it suggests ups and downs that settle with age."
                    ],
                    basis=[y.id for y in kala],
                )
            )
        ruler = self.facts.lord(1)
        gem, day, colour, number = words.LUCKY[ruler]
        out.append(
            ReadingSectionOut(
                key="lucky",
                title="Favourable for you",
                paragraphs=[
                    f"From the ruler of your rising sign, {_planet(ruler)}: lucky day {day}, "
                    f"{'colours' if ' and ' in colour else 'colour'} {colour}, number {number}, "
                    "and the traditional life stone "
                    f"{gem}. Wear a gemstone only after a careful check by an experienced "
                    "astrologer; it is never a substitute for effort or for professional "
                    "advice."
                ],
            )
        )
        return out

    def sade_sati_section(self) -> ReadingSectionOut:
        lines = []
        running = self.sade_sati_now()
        for episode in self.sade_sati:
            start, end = _day(episode.start_jd_ut), _day(episode.end_jd_ut)
            span = ages(self.birth, max(start, self.birth), end)
            if end <= self.today:
                lines.append(f"{start.year} to {end.year} {span}: already behind you.")
            elif start <= self.today:
                lines.append(f"{month(start)} to {month(end)} {span}: running now.")
            else:
                lines.append(f"{month(start)} to {month(end)} {span}: ahead.")
        title = "Sade Sati: running now" if running else "Sade Sati: not running now"
        intro = (
            "Sade Sati is the 7½ years when Saturn passes over your Moon sign and the signs "
            "on either side. It comes about every 30 years. It tends to bring responsibility, "
            "slower progress and lessons in patience, and it often ends with lasting gains."
        )
        return ReadingSectionOut(
            key="sade_sati",
            title=title,
            paragraphs=[
                intro,
                " ".join(lines) if lines else "No Sade Sati falls in the computed range.",
            ],
            tone="hard" if running else None,
        )

    def glance(self) -> list[GlanceItemOut]:
        chart = self.chart
        lagna = Sign(self.facts.lagna_sign)
        moon = next(g for g in chart.grahas if g.body is Body.MOON)
        sun = next(g for g in chart.grahas if g.body is Body.SUN)
        star = moon.nakshatra
        md = self.dashas.at(self.today, 1)
        ad = self.dashas.at(self.today, 2)
        running = self.sade_sati_now()
        if running:
            sade = f"Running until {month(_day(running[0].end_jd_ut))}"
        else:
            upcoming = [e for e in self.sade_sati if _day(e.start_jd_ut) > self.today]
            sade = (
                f"Not now; next from {_day(upcoming[0].start_jd_ut).year}"
                if upcoming
                else "Not now"
            )
        animal, male = NAKSHATRA_YONI[star.index]
        items = [
            GlanceItemOut(label="Rising sign (Lagna)", value=_sign_label(lagna)),
            GlanceItemOut(label="Moon sign (Rashi)", value=_sign_label(Sign(moon.sign))),
            GlanceItemOut(
                label="Birth star (Nakshatra)",
                value=f"{star.name}, pada {star.pada}",
                note=f"ruled by {_planet(star.lord)}",
            ),
            GlanceItemOut(label="Sun sign (Vedic)", value=_sign_label(Sign(sun.sign))),
            GlanceItemOut(
                label="Running period",
                value=f"{_planet(md.lords[0])}–{_planet(ad.lords[-1])}",
                note=f"until {month(ad.end.date())}",
            ),
            GlanceItemOut(label="Sade Sati", value=sade),
            GlanceItemOut(
                label="Gana, Nadi, Yoni",
                value=f"{NAKSHATRA_GANA[star.index].name.title()}, "
                f"{NAKSHATRA_NADI[star.index].name.title()}, "
                f"{YONI_ANIMALS[animal]} ({'male' if male else 'female'})",
                note="" if self.minor else "used in marriage matching",
            ),
        ]
        if not self.minor:
            items.insert(-1, GlanceItemOut(label="Manglik", value=self.manglik()[0]))
        return items

    def summary(self, nature_lagna: Sign, moon: Sign) -> list[str]:
        md = self.dashas.at(self.today, 1)
        ad = self.dashas.at(self.today, 2)
        lord, sub = md.lords[0], ad.lords[-1]
        lines, _ = topics.portrait(self)
        now = (
            f"Right now you are in the {_planet(lord)} period "
            f"({max(md.start.date(), self.birth).year}–{md.end.year}), {words.PERIOD_GIST[lord]}"
        )
        now += (
            "."
            if sub is lord
            else f", and within it the {_planet(sub)} sub-period until {month(ad.end.date())}: "
            f"{words.SUB_PERIOD_FEEL[sub]}."
        )
        lines.append(now)
        if self.age >= 12:
            mains = [self.best_past(d) for d in CHECK_AGES if d in words.CHECK_LABELS]
            remembered = [e for e in mains if e is not None and e.tone != "hard"]
            if self.age >= 25:
                remembered = [e for e in remembered if e.domain in MILESTONES] or remembered
            past = sorted(sorted(remembered, key=lambda e: -e.score)[:2], key=lambda e: e.start)
            if past:
                lines.append(
                    "Looking back, your chart's stand-out stretches were "
                    + join(
                        [
                            f"{when_past(e.start, e.end)} for {words.AREA_NAMES[e.domain]}"
                            for e in past
                        ]
                    )
                    + "."
                )
        ahead = [
            e
            for e in self.episodes
            if e.start > self.today
            and e.tone == "good"
            and self.told(e)
            and e.start < date(self.today.year + self.years_ahead, 1, 1)
            and (self.age >= 21 or e.domain not in (Domain.MARRIAGE, Domain.CHILDREN))
        ]
        if ahead:
            best = max(ahead, key=lambda e: e.score)
            lines.append(
                f"The most promising stretch ahead is {when_future(best.start, best.end)}, for "
                f"{self.area_name(best.domain)}."
            )
        if self.age < 14:
            lines.append(
                "For a child's chart, read this as a guide to temperament and timing; "
                "upbringing and choices shape the rest."
            )
        running = self.sade_sati_now()
        if running:
            lines.append(
                f"Saturn's Sade Sati runs until {month(_day(running[0].end_jd_ut))}: a time "
                "that rewards patience and steady effort."
            )
        return lines

    def best_past(self, domain: Domain) -> _Episode | None:
        """The main past stretch of an area, at the ages it is looked for. For marriage,
        the first stretch nearly as strong as the strongest: marriage tends to come with
        the first strong activation after maturity."""
        low, high = CHECK_AGES[domain]

        def age_of(day: date) -> float:
            if domain is Domain.MARRIAGE:
                return self.marriage_age(day)
            return years_between(self.birth, day)

        items = [
            e
            for e in self.episodes
            if e.domain is domain
            and e.end <= self.today
            and self.told(e)
            and low <= age_of(e.start) < high
        ]
        if not items:
            return None
        best = max(items, key=lambda e: e.score)
        if domain is Domain.MARRIAGE:
            return min((e for e in items if e.score >= 0.85 * best.score), key=lambda e: e.start)
        return best

    def checks(self) -> list[LifeMomentOut]:
        """The main past stretch in each area people remember, to compare with real
        events."""
        out: list[LifeMomentOut] = []
        for domain in CHECK_AGES:
            if domain not in words.CHECK_LABELS:
                continue
            best = self.best_past(domain)
            if best is None:
                continue
            when = when_past(best.start, best.end)
            span = ages(self.birth, best.start, best.end)
            label = words.CHECK_LABELS[domain]
            if domain is Domain.MARRIAGE and self.single:
                label = words.CHECK_LABEL_SINGLE
            text = f"{label}: {when} {span}" + (
                f", strongest around {best.peak.year}."
                if (best.end - best.start).days > 900
                else "."
            )
            if domain is Domain.MARRIAGE and self.wedding is not None:
                start, end = self.wedding
                wedding = f" Your wedding, in {self._wedding_words()},"
                check = self.wedding_check()
                if best.start < end and start < best.end:
                    text += f"{wedding} falls inside it."
                elif check is not None and check.fit != "outside" and check.window is not None:
                    where = "came in" if check.fit == "inside" else "came close to"
                    text += f"{wedding} {where} another window for marriage, {check.window.when}."
                else:
                    text += f"{wedding} falls outside it."
            out.append(
                LifeMomentOut(
                    domain=domain,
                    area=words.AREA_NAMES[domain],
                    start=best.start,
                    end=best.end,
                    ages=span,
                    when=when,
                    text=text,
                    tone=best.tone,
                    basis=f"{domain.value}: activation {best.score:.2f} peaking {best.peak:%b %Y}",
                )
            )
        return sorted(out, key=lambda m: m.start)

    def _wedding_words(self) -> str:
        assert self.wedding is not None
        start = self.wedding[0]
        return str(start.year) if self.marital.wedding_month is None else month(start)

    def wedding_check(self) -> WeddingCheckOut | None:
        """The wedding the person gave, against the chart's windows for marriage: inside
        one, within a year of one, or further away."""
        if self.wedding is None:
            return None
        start, end = self.wedding
        when = self._wedding_words()
        windows = [e for e in self.episodes if e.domain is Domain.MARRIAGE]
        if not windows:
            return WeddingCheckOut(
                when=when,
                fit="outside",
                text=f"Your wedding in {when} cannot be compared with the chart: no window "
                "for marriage stands out at the ages it is read.",
            )

        def gap(item: _Episode) -> int:
            if item.start < end and start < item.end:
                return 0
            return (item.start - end).days if item.start >= end else (start - item.end).days

        nearest = min(windows, key=lambda e: (gap(e), -e.score))
        days = gap(nearest)
        span = (
            when_past(nearest.start, nearest.end)
            + " "
            + ages(self.birth, nearest.start, nearest.end)
        )
        name = (
            "the chart's main window for marriage"
            if nearest is self.best_past(Domain.MARRIAGE)
            else "one of the chart's windows for marriage"
        )
        if days == 0:
            fit: Literal["inside", "near", "outside"] = "inside"
            text = (
                f"Your wedding in {when} came during {name}, {span}, so the chart's timing "
                "fits your life here."
            )
        elif days <= 366:
            fit = "near"
            text = (
                f"Your wedding in {when} came within a year of {name}, {span}: close, as the "
                "chart's timing often runs a little early or late."
            )
        else:
            fit = "outside"
            text = (
                f"Your wedding in {when} did not fall in a window the chart marks for "
                f"marriage; the nearest was {span}. Life events do not always follow the "
                "chart's timing, but if other dates under 'Your life so far' are also off, "
                "the birth time may need checking."
            )
        return WeddingCheckOut(when=when, fit=fit, window=self.moment(nearest, "past"), text=text)


def _planet(body: Body) -> str:
    return body.value.title()


def _day(jd: float) -> date:
    return jd_to_datetime(jd).date()


def _sign_label(sign: Sign) -> str:
    return f"{sign.name.title()} ({sign.sanskrit})"


def _stays(body: Body, jd: float, chart: ChartResult) -> list[tuple[int, date]]:
    """The signs a slow graha passes through over the next three years, with exit dates."""
    end = min(jd + 3 * 365.25, chart.ephemeris.jd_end - 2.0)
    if end <= jd:
        return []
    return [(s.sign, _day(s.end_jd_ut)) for s in sign_timeline(body, jd, end, chart.settings)]


def _mahadasha_end(dashas: _Dashas, lord: Body, start: date) -> int:
    """The year a mahadasha starting on ``start`` ends."""
    period = next(
        (p for p in dashas.levels[1] if p.lords[0] is lord and p.start.date() == start), None
    )
    return period.end.year if period else dashas.at(start + timedelta(days=2), 1).end.year


#: Titles skipped when addressing someone by first name.
TITLES = frozenset({"dr", "mr", "mrs", "ms", "miss", "shri", "sri", "smt", "kumari", "km"})


def _first_name(name: str | None) -> str | None:
    """The first name to address the reader by, when the name looks like a person's: no
    digits or symbols, titles such as "Dr." skipped."""
    text = (name or "").strip()
    if not text or re.search(r"[\d()\[\]{}<>@#$%^&*=+/\\|~`!?;:\"_]", text):
        return None
    words = [w for w in text.split() if w.rstrip(".").lower() not in TITLES]
    if not words:
        return None
    first = words[0]
    if first.islower() or first.isupper():
        first = first[:1].upper() + first[1:].lower()
    return first


def _lower_first(text: str) -> str:
    return text[:1].lower() + text[1:]


def _presence(first: date, last: date) -> Callable[[_Episode], float]:
    """How much a stretch shapes the time between two dates: strength times months."""

    def weight(item: _Episode) -> float:
        days = (min(item.end, last) - max(item.start, first)).days
        return item.score * min(max(days, 0) / 30.4, 6.0)

    return weight


def _lead(items: Sequence[_Episode], weight: Callable[[_Episode], float]) -> _Episode | None:
    """The stretch that names a year: the most present one, unless a good (or else a mixed)
    stretch is at least a third as present; a year is named for its difficulty only when
    difficulty clearly dominates."""
    if not items:
        return None
    top = max(items, key=weight)
    for tone in ("good", "mixed"):
        close = [e for e in items if e.tone == tone and weight(e) >= 0.35 * weight(top)]
        if close:
            return max(close, key=weight)
    return top


def life_reading(
    chart: ChartResult,
    today: date | None = None,
    *,
    gender: str | None = None,
    name: str | None = None,
    years_ahead: int = 5,
    marital: MaritalInput | None = None,
) -> LifeReadingOut:
    """Who you are, your life so far, where you stand now and the years ahead. What the
    person says about marriage (``marital``) decides how its timing is told."""
    today = today or datetime.now(UTC).date()
    reader = Reader(chart, today, gender, name, years_ahead, marital)
    mahadashas = reader.dashas.levels[1]
    past = [
        reader.chapter(p, "past")
        for p in mahadashas
        if p.start.date() <= today and p.end.date() > reader.birth
    ]
    later = [reader.chapter(p, "later") for p in mahadashas if p.start.date() > today][:2]
    nature = reader.nature()
    lagna = Sign(reader.facts.lagna_sign)
    moon = Sign(reader.moon_sign)
    return LifeReadingOut(
        today=today,
        name=reader.name,
        age=reader.age,
        summary=reader.summary(lagna, moon),
        glance=reader.glance(),
        nature=nature,
        past=past,
        checks=reader.checks() if reader.age >= 12 else [],
        present=reader.present(),
        future=reader.future(),
        later=later,
        areas=reader.areas_section(),
        marriage=topics.marriage(reader),
        marital=reader.marital,
        wedding=None if reader.minor else reader.wedding_check(),
        good_to_know=reader.good_to_know(),
        remedies=topics.remedies(reader),
        notes=NOTES,
    )
