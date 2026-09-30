"""A life reading in everyday language: past chapters, the present, the years ahead.

The reading is assembled from the engine's own results: the Vimshottari periods, the
prediction timeline, the period rules and the natal readings. They are translated
into plain words. Houses become the areas of life they stand for, grahas the
qualities they bring, and scores become "favourable", "mixed" or "testing". Every
line keeps a short technical basis for astrologers.

Nothing here predicts death, illness or certain outcomes. Health is left out of the
timeline, and a parent's testing periods are not singled out. Childhood chapters
mention only studies and family.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from jyotish_engine.astro.bodies import Body
from jyotish_engine.astro.time import datetime_to_jd, jd_to_datetime
from jyotish_engine.models import (
    ChartResult,
    DashaPeriodOut,
    LifeReadingOut,
    PredictionsOut,
    PredictionWindowOut,
    StoryChapterOut,
    StoryLineOut,
    StoryPresentOut,
    Tone,
    YearOutlookOut,
    YogaOut,
)
from jyotish_engine.predict.promise import functional_tone
from jyotish_engine.predict.timeline import compute_predictions
from jyotish_engine.rules.facts import ChartFacts
from jyotish_engine.rules.periods import compute_period_readings
from jyotish_engine.rules.readings import compute_readings
from jyotish_engine.rules.schema import Domain, Polarity, Strength
from jyotish_engine.rules.yogas import compute_yogas
from jyotish_engine.transit.saturn import sade_sati

#: The areas of life each house stands for, in everyday words.
AREAS = {
    1: "your health and confidence",
    2: "money and family",
    3: "courage and siblings",
    4: "home and property",
    5: "children and studies",
    6: "work and competition",
    7: "marriage and partnerships",
    8: "sudden changes",
    9: "luck and higher learning",
    10: "career and status",
    11: "income and friends",
    12: "expenses and time abroad",
}
#: What each graha brings to its period, in everyday words.
NATURE = {
    Body.SUN: "authority, confidence and recognition",
    Body.MOON: "feelings, family life and public contact",
    Body.MARS: "energy, drive and property matters",
    Body.MERCURY: "learning, trade and communication",
    Body.JUPITER: "growth, wisdom and good fortune",
    Body.VENUS: "relationships, comfort and the arts",
    Body.SATURN: "hard work, patience and responsibility",
    Body.RAHU: "ambition, change and unconventional paths",
    Body.KETU: "detachment, introspection and a spiritual search",
}
#: The timeline's life domains in everyday words; health is not read here.
DOMAIN_WORDS = {
    Domain.CAREER: "work and career",
    Domain.MARRIAGE: "marriage and partnership",
    Domain.CHILDREN: "children",
    Domain.WEALTH: "money and savings",
    Domain.PROPERTY: "home and property",
    Domain.EDUCATION: "studies and learning",
    Domain.PARENTS: "parents and elders",
    Domain.SPIRITUALITY: "spiritual life",
    Domain.TRAVEL: "travel and time abroad",
}
#: The only domains read for childhood (before this age).
CHILDHOOD_AGE = 16
CHILDHOOD_DOMAINS = {Domain.EDUCATION, Domain.PARENTS}
#: Transits worth a line in the present, in order of weight.
TRANSIT_ORDER = (
    "transit.sade_sati",
    "transit.double_",
    "transit.jupiter_",
    "transit.saturn_",
    "transit.rahu_",
    "transit.ketu_",
)
STRENGTH_ORDER = {Strength.MAJOR: 0, Strength.MODERATE: 1, Strength.MINOR: 2}
POLARITY_TONE: dict[Polarity, Tone] = {
    Polarity.POSITIVE: "good",
    Polarity.NEGATIVE: "hard",
    Polarity.MIXED: "mixed",
}
NOTES = [
    "This reading describes traditional Jyotish interpretations computed from the birth "
    "data. It is not a certainty, and not medical, legal or financial advice.",
    "The past chapters are the best test: if they match your life, the rest of the "
    "reading is more likely to fit you.",
    "Health is not read here; for health questions, see a doctor.",
    "Readings that depend on the rising sign change if the birth time is off by more than "
    "a few minutes.",
]
#: Astrologer's shorthand that must not reach the plain text (see ``plain``).
JARGON = re.compile(
    r"\blords?\b|\blord\(|house\(|dusthana|kendra|trikona|bindu|shadbala|virupa|"
    r"\b\d+(?:st|nd|rd|th) (?:house|lord|from)\b|\bdashas?\b",
    re.IGNORECASE,
)
REWRITES = (
    (
        r"starting in the \d+(?:st|nd|rd|th) house emphasises its matters \(([^)]*)\)",
        r"emphasises \1",
    ),
    (
        r"the \d+(?:st|nd|rd|th) house \(([^)]*)\) is ripe for events",
        r"matters of \1 are ripe for events",
    ),
    (r"the \d+(?:st|nd|rd|th) house \(([^)]*)\)", r"\1"),
    (r";?\s*the planet in the \d+(?:st|nd|rd|th) from the (?:Moon|Sun) colours the result", ""),
    (
        r"(active|especially) in the dashas of the two lords",
        r"\1 during the periods of the two planets involved",
    ),
    (r"if the lord is strong", "if its ruling planet is strong"),
    (r"the planet that rules both a kendra and a trikona", "one especially helpful planet"),
    (r"the two lords' matters", "the areas the two planets govern"),
    (r"the two lords", "the two planets"),
    (r"\bmahadashas?\b", "major period"),
    (r"\bantardashas?\b", "sub-period"),
    (r"\bdashas\b", "periods"),
    (r"\bdasha\b", "period"),
)


def plain(text: str) -> str:
    """A rule's effect in everyday words: technical conditions and shorthand removed."""
    effect = text.split(":", 1)[1].strip() if ":" in text else text.strip()
    for pattern, replacement in REWRITES:
        effect = re.sub(pattern, replacement, effect, flags=re.IGNORECASE)
    effect = re.sub(
        r"the (\d+)(?:st|nd|rd|th) house",
        lambda m: AREAS.get(int(m.group(1)), "life"),
        effect,
        flags=re.IGNORECASE,
    )
    effect = re.sub(r"\s+([,.;])", r"\1", effect).strip()
    if not effect:
        return effect
    return effect[0].upper() + effect[1:] + ("" if effect.endswith((".", "!", "?")) else ".")


def plain_name(name: str) -> str:
    """A rule's name without its technical qualifier: "Raja Yoga (1st and 4th lords)"."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()


def _join(items: Sequence[str]) -> str:
    """A list in prose, with a serial comma so "and"-phrases stay readable."""
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    if len(items) == 2 and not any(" and " in i for i in items):
        return " and ".join(items)
    return ", ".join(items[:-1]) + ", and " + items[-1]


def _tone(value: float) -> Tone:
    return "good" if value > 0.15 else "hard" if value < -0.15 else "mixed"


def _phrase(tone: Tone, strong: bool) -> str:
    if tone == "good":
        return "a strongly favourable time" if strong else "a favourable time"
    if tone == "hard":
        return "a clearly testing time" if strong else "a testing time"
    return "an eventful, mixed time"


def _month(day: date) -> str:
    return f"{day:%B %Y}"


def _span(start: date, end: date) -> str:
    last = end - timedelta(days=1)
    if (start.year, start.month) == (last.year, last.month):
        return _month(start)
    if start.year == last.year:
        return f"{start:%B}–{last:%B %Y}"
    return f"{_month(start)}–{_month(last)}"


def _age(birth: date, day: date) -> int:
    return max(0, int((day - birth).days / 365.2425))


def _name(body: Body) -> str:
    return body.value.title()


def _lower_first(text: str) -> str:
    return text[:1].lower() + text[1:]


def _upper_first(text: str) -> str:
    return text[:1].upper() + text[1:]


@dataclass(frozen=True, slots=True)
class _Window:
    domain: Domain
    window: PredictionWindowOut

    @property
    def tone(self) -> Tone:
        return _tone(self.window.tone)


class _Chart:
    """The chart facts a reading needs, gathered once."""

    def __init__(self, chart: ChartResult, gender: str | None) -> None:
        self.chart = chart
        self.facts = ChartFacts.from_chart(chart, gender)
        self.birth = chart.birth.local_datetime.date()

    def houses_of(self, body: Body) -> list[int]:
        """Houses a graha rules, then the one it occupies (a node: its dispositor's)."""
        facts = self.facts
        ruler = facts.dispositor(body) if body in (Body.RAHU, Body.KETU) else body
        houses = [h for h in range(1, 13) if facts.lord(h) is ruler]
        occupied = facts.house(body)
        ordered = [occupied, *houses] if body in (Body.RAHU, Body.KETU) else [*houses, occupied]
        return list(dict.fromkeys(ordered))

    def tone_of(self, body: Body) -> float:
        try:
            return functional_tone(self.facts, body)
        except (KeyError, ValueError):
            return 0.0

    def areas(self, body: Body, limit: int = 3) -> str:
        return _join([AREAS[h] for h in self.houses_of(body)[:limit]])

    def verdict(self, body: Body) -> tuple[Tone, str]:
        value = self.tone_of(body)
        if value >= 0.4:
            return "good", f"{_name(body)} is well placed in your chart, so this tends to go well."
        if value <= -0.3:
            return "hard", (
                f"{_name(body)} is under some strain in your chart, so results come through "
                "patience and steady effort."
            )
        return "mixed", "Results are mixed: some areas open up while others take effort."

    def basis(self, body: Body) -> str:
        houses = ", ".join(str(h) for h in self.houses_of(body))
        return f"{_name(body)}: houses {houses}; tone {self.tone_of(body):+.2f}"


def _usable(item: _Window, birth: date) -> bool:
    """Windows worth telling: not weak, not health, no parent's testing time, no
    grown-up matters in childhood."""
    if item.window.confidence == "weak" or item.domain not in DOMAIN_WORDS:
        return False
    if item.domain is Domain.PARENTS and item.tone == "hard":
        return False
    return _age(birth, item.window.start) >= CHILDHOOD_AGE or item.domain in CHILDHOOD_DOMAINS


def _windows(predictions: PredictionsOut | None, birth: date) -> list[_Window]:
    if predictions is None:
        return []
    items = [_Window(d.domain, w) for d in predictions.domains for w in d.windows]
    return [i for i in items if _usable(i, birth)]


def _grouped(items: list[_Window], limit: int) -> list[tuple[date, StoryLineOut]]:
    """One line per life area and tenor, its strongest spans first, told in time order."""
    groups: dict[tuple[Domain, Tone], list[_Window]] = {}
    for item in items:
        groups.setdefault((item.domain, item.tone), []).append(item)
    ranked = sorted(
        groups.items(),
        key=lambda kv: (
            not any(i.window.confidence == "strong" for i in kv[1]),
            -max(i.window.score for i in kv[1]),
        ),
    )[:limit]
    lines = []
    for (domain, tone), members in ranked:
        group = sorted(members, key=lambda i: i.window.start)[:3]
        spans = _join([_span(i.window.start, i.window.end) for i in group])
        strong = any(i.window.confidence == "strong" for i in group)
        lords = "; ".join(" / ".join(_name(b) for b in i.window.dasha) for i in group)
        lines.append(
            (
                group[0].window.start,
                StoryLineOut(
                    text=f"{spans}: {_phrase(tone, strong)} for {DOMAIN_WORDS[domain]}.",
                    tone=tone,
                    basis=f"{domain.value} windows ({'strong' if strong else 'moderate'}); {lords}",
                ),
            )
        )
    return sorted(lines, key=lambda item: item[0])


def _chapter(
    reading: _Chart, period: DashaPeriodOut, windows: list[_Window], today: date
) -> StoryChapterOut:
    lord = period.lords[0]
    start = max(period.start.date(), reading.birth)
    end = period.end.date()
    tone, verdict = reading.verdict(lord)
    headline = (
        f"{_name(lord)} brings {NATURE[lord]}; for you it touches {reading.areas(lord)}. {verdict}"
    )
    upto = min(end, today)
    inside = [w for w in windows if start <= w.window.start < upto]
    return StoryChapterOut(
        lord=lord,
        start=start,
        end=end,
        ages=f"{_age(reading.birth, start)} to {_age(reading.birth, end)}",
        title=f"{_name(lord)} period, {start.year}–{end.year}",
        headline=headline,
        tone=tone,
        lines=[line for _, line in _grouped(inside, 5)],
        current=start <= today < end,
    )


def _transit_label(rule: YogaOut) -> str:
    if rule.id == "transit.sade_sati":
        return "Sade Sati (Saturn's 7½-year passage over your Moon sign)"
    double = re.fullmatch(r"transit\.double_h(\d+)", rule.id)
    if double:
        return f"Jupiter and Saturn together activate {AREAS[int(double.group(1))]}"
    single = re.fullmatch(r"transit\.(\w+?)_h(\d+)", rule.id)
    if single:
        area = AREAS[int(single.group(2))]
        return f"{single.group(1).title()}'s current position (on {area}, counted from your Moon)"
    return plain_name(rule.name)


def _transit_rank(rule: YogaOut) -> int:
    return next(
        (i for i, p in enumerate(TRANSIT_ORDER) if rule.id.startswith(p)), len(TRANSIT_ORDER)
    )


def _present(
    reading: _Chart, now: datetime, future: PredictionsOut | None
) -> tuple[StoryPresentOut, list[str]]:
    periods = compute_period_readings(reading.chart, now)
    md, ad = periods.dasha[0], periods.dasha[1]
    headline = (
        f"You are in the {_name(md.lords[0])} major period (mahadasha) from "
        f"{_month(md.start.date())} to {_month(md.end.date())}. Within it, the "
        f"{_name(ad.lords[-1])} sub-period (antardasha) runs until {_month(ad.end.date())}."
    )
    lines: list[StoryLineOut] = []
    for body, role in ((md.lords[0], "major period"), (ad.lords[-1], "sub-period")):
        tone, verdict = reading.verdict(body)
        lines.append(
            StoryLineOut(
                text=f"The {_name(body)} {role} brings {NATURE[body]}, touching "
                f"{reading.areas(body, 2)}. {verdict}",
                tone=tone,
                basis=reading.basis(body),
            )
        )
    seen: set[str] = set()
    for rule in sorted(periods.dasha_readings, key=lambda r: STRENGTH_ORDER[r.strength]):
        text = plain(rule.summary)
        if text and text not in seen and len(seen) < 4:
            seen.add(text)
            lines.append(
                StoryLineOut(text=text, tone=POLARITY_TONE[rule.polarity], basis=rule.name)
            )
    slow = [r for r in periods.transit_readings if _transit_rank(r) < len(TRANSIT_ORDER)]
    has_sade_sati = any(r.id == "transit.sade_sati" for r in slow)
    notes: list[str] = []
    shown = 0
    for rule in sorted(slow, key=_transit_rank):
        if shown == 3 or (has_sade_sati and rule.id.startswith("transit.saturn_")):
            continue
        shown += 1
        text = f"{_transit_label(rule)}: {_lower_first(plain(rule.summary))}"
        lines.append(StoryLineOut(text=text, tone=POLARITY_TONE[rule.polarity], basis=rule.name))
        if rule.id == "transit.sade_sati":
            notes.append(
                "Saturn's Sade Sati is running: a time for patience, saving and steady work. "
                "Shortcuts rarely pay now, while sustained effort does."
            )
    if future is not None:
        active = [
            d
            for d in sorted(future.domains, key=lambda d: -(d.scores[0] if d.scores else 0.0))
            if d.domain in DOMAIN_WORDS
            and d.scores
            and not (d.domain is Domain.PARENTS and _tone(d.tones[0]) == "hard")
        ][:3]
        if active:
            words = {"good": "favourable", "hard": "testing", "mixed": "mixed"}
            listing = _join(
                [f"{DOMAIN_WORDS[d.domain]} ({words[_tone(d.tones[0])]})" for d in active]
            )
            lines.append(
                StoryLineOut(
                    text=f"The areas most active this month: {listing}.",
                    basis="current month of the timeline",
                )
            )
    return StoryPresentOut(headline=headline, lines=lines), notes


def _sade_sati_lines(reading: _Chart, today: date, end: date) -> list[tuple[date, StoryLineOut]]:
    chart = reading.chart
    moon_sign = int(next(g for g in chart.grahas if g.body is Body.MOON).sign)
    start_jd = datetime_to_jd(datetime(today.year, today.month, today.day, tzinfo=UTC))
    end_jd = datetime_to_jd(datetime(end.year, end.month, end.day, tzinfo=UTC))
    try:
        episodes = sade_sati(moon_sign, start_jd, end_jd, chart.settings)
    except ValueError:
        return []
    lines = []
    for episode in episodes:
        if not episode.open_start:
            day = jd_to_datetime(episode.start_jd_ut).date()
            lines.append(
                (
                    day,
                    StoryLineOut(
                        text=f"{_month(day)}: Sade Sati, Saturn's 7½-year passage over your Moon "
                        "sign, begins: a slower, more demanding stretch that rewards patience.",
                        tone="hard",
                        basis="Sade Sati begins",
                    ),
                )
            )
        if not episode.open_end:
            day = jd_to_datetime(episode.end_jd_ut).date()
            lines.append(
                (
                    day,
                    StoryLineOut(
                        text=f"{_month(day)}: Sade Sati ends; pressure eases and delayed matters "
                        "start to move.",
                        tone="good",
                        basis="Sade Sati ends",
                    ),
                )
            )
    return lines


def _year_headline(items: list[_Window]) -> str:
    good = list(dict.fromkeys(DOMAIN_WORDS[i.domain] for i in items if i.tone == "good"))
    hard = list(dict.fromkeys(DOMAIN_WORDS[i.domain] for i in items if i.tone == "hard"))
    if good and hard:
        return f"Favourable for {_join(good[:2])}; go steady with {_join(hard[:1])}."
    if good:
        return f"A favourable year for {_join(good[:3])}."
    if hard:
        return f"A year to go steady, especially with {_join(hard[:2])}."
    return "A steady year without strong swings."


def _future(
    reading: _Chart,
    today: date,
    years: int,
    future: PredictionsOut | None,
    periods: list[DashaPeriodOut],
) -> list[YearOutlookOut]:
    windows = _windows(future, reading.birth)
    sade_sati_lines = _sade_sati_lines(reading, today, date(today.year + years, 1, 1))
    outlooks = []
    for year in range(today.year, today.year + years):
        first, last = date(year, 1, 1), date(year + 1, 1, 1)
        dated: list[tuple[date, StoryLineOut]] = []
        for period in periods:
            start = period.start.date()
            if not (first <= start < last and start >= today) or len(period.lords) > 2:
                continue
            if len(period.lords) == 2 and period.lords[0] is period.lords[1]:
                continue  # a major period's own first sub-period: its start is told once
            body = period.lords[-1]
            tone, _ = reading.verdict(body)
            if len(period.lords) == 1:
                text = (
                    f"{_month(start)}: a new chapter begins, the {_name(body)} major period "
                    "(see the chapters ahead)."
                )
            else:
                text = (
                    f"{_month(start)}: the {_name(body)} sub-period begins, bringing "
                    f"{NATURE[body]} and touching {reading.areas(body, 2)}."
                )
            dated.append((start, StoryLineOut(text=text, tone=tone, basis=reading.basis(body))))
        dated += [item for item in sade_sati_lines if first <= item[0] < last]
        in_year = [
            w
            for w in windows
            if first <= w.window.start < last
            or (year == today.year and w.window.start < today < w.window.end)
        ]
        dated += _grouped(in_year, 5)
        dated.sort(key=lambda item: item[0])
        outlooks.append(
            YearOutlookOut(
                year=year,
                headline=_year_headline(in_year),
                lines=[line for _, line in dated],
            )
        )
    return outlooks


def _nature(chart: ChartResult) -> list[StoryLineOut]:
    readings = compute_readings(chart).readings
    wanted = [
        next((r for r in readings if r.id.startswith("lagna.")), None),
        next((r for r in readings if r.id.startswith("nakshatra.moon_")), None),
        next((r for r in readings if r.id.startswith("planet_in_sign.moon_")), None),
    ]
    return [
        StoryLineOut(text=f"{r.name}: {_lower_first(r.summary)}", basis=r.id) for r in wanted if r
    ]


def _strengths_cautions(
    chart: ChartResult, gender: str | None, life: PredictionsOut | None
) -> tuple[list[StoryLineOut], list[StoryLineOut]]:
    yogas = compute_yogas(chart, gender=gender).present
    strengths: list[StoryLineOut] = []
    cautions: list[StoryLineOut] = []
    if life is not None:
        promised = sorted(
            (d for d in life.domains if d.domain in DOMAIN_WORDS), key=lambda d: -d.promise.score
        )
        best = [DOMAIN_WORDS[d.domain] for d in promised if d.promise.score >= 0.6][:3]
        weak = [DOMAIN_WORDS[d.domain] for d in promised if d.promise.score <= 0.45][-2:]
        if best:
            strengths.append(
                StoryLineOut(
                    text=f"Your birth chart gives good support for {_join(best)}.",
                    tone="good",
                    basis="natal promise",
                )
            )
        if weak:
            text = f"{_join(weak)} tend to need more effort and patience."
            cautions.append(
                StoryLineOut(text=text[0].upper() + text[1:], tone="hard", basis="natal promise")
            )
    seen: set[str] = set()
    for yoga in sorted(yogas, key=lambda y: STRENGTH_ORDER[y.strength]):
        text = plain(yoga.summary)
        if not text or text in seen:
            continue
        seen.add(text)
        label = plain_name(yoga.name)
        line = StoryLineOut(
            text=f"{text[:-1]} ({label})." if not JARGON.search(label) else text,
            tone=POLARITY_TONE[yoga.polarity],
            basis=yoga.id,
        )
        if yoga.polarity is Polarity.POSITIVE and len(strengths) < 6:
            strengths.append(line)
        elif yoga.polarity is Polarity.NEGATIVE and len(cautions) < 5:
            cautions.append(line)
    return strengths, cautions


def life_reading(
    chart: ChartResult,
    today: date | None = None,
    *,
    gender: str | None = None,
    years_ahead: int = 5,
) -> LifeReadingOut:
    """Past, present and future for ``chart`` as of ``today``, in everyday language."""
    today = today or datetime.now(UTC).date()
    reading = _Chart(chart, gender)
    now = datetime(today.year, today.month, today.day, 12, tzinfo=UTC)
    birth_month = reading.birth.replace(day=1)
    this_month = today.replace(day=1)
    past = None
    if this_month > birth_month:
        past = compute_predictions(chart, birth_month, this_month, gender=gender)
    try:
        future = compute_predictions(
            chart, this_month, date(today.year + years_ahead, today.month, 1), gender=gender
        )
    except ValueError:
        future = None
    table = chart.dashas.vimshottari.periods
    mahadashas = [p for p in table if len(p.lords) == 1]
    past_windows = _windows(past, reading.birth)
    chapters = [
        _chapter(reading, p, past_windows, today)
        for p in mahadashas
        if max(p.start.date(), reading.birth) <= today and p.end.date() > reading.birth
    ]
    ahead = [_chapter(reading, p, [], today) for p in mahadashas if p.start.date() > today][:2]
    present, transit_notes = _present(reading, now, future)
    years = _future(reading, today, years_ahead, future, list(table))
    nature = _nature(chart)
    strengths, cautions = _strengths_cautions(chart, gender, past or future)
    summary = []
    if nature:
        summary.append(
            "By nature: "
            + " ".join(_upper_first(n.text.split(": ", 1)[1].rstrip(".")) + "." for n in nature[:2])
        )
    summary.append(present.headline)
    summary += transit_notes
    if years:
        summary.append(f"The year ahead ({years[0].year}): {years[0].headline}")
    return LifeReadingOut(
        today=today,
        summary=summary,
        nature=nature,
        strengths=strengths,
        cautions=cautions,
        past=chapters,
        present=present,
        future=years,
        chapters_ahead=ahead,
        notes=NOTES,
    )
