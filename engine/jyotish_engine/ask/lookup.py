"""Lookups for questions about one chart: small, plain-data answers a chat can call.

The engine computes; a lookup only gathers what it computed into the shape of a
question people ask:

* where a planet is, what it rules and aspects, and how strong it is (``planet``);
* what a house holds: its sign, lord, occupants, aspects and Ashtakavarga bindus
  (``house``);
* which dasha periods and transits run on a date (``moment``) or across a range
  (``periods``, ``transits``);
* when a life area is emphasised, by the prediction timeline over the whole life
  (``area``);
* what a calendar year holds: the annual chart, the periods, the slow transits and
  the windows of every area (``year``).

Every result prints itself as one line of evidence (``summary``): the offline chat
shows these lines, and a language model reads and cites them. Dates are local dates
at the birth place.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta
from functools import cached_property
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from jyotish_engine.annual.varshaphal import compute_varshaphal
from jyotish_engine.astro.bodies import GRAHAS, Body
from jyotish_engine.astro.time import datetime_to_jd, jd_to_datetime
from jyotish_engine.core.aspects import graha_aspected_signs
from jyotish_engine.core.dignity import CO_LORDS
from jyotish_engine.core.zodiac import SIGN_LORDS, Sign
from jyotish_engine.dasha.nakshatra import NakshatraDasha
from jyotish_engine.dasha.tables import chart_dasha_table
from jyotish_engine.models import (
    ChartResult,
    DashaPeriodOut,
    DomainTimelineOut,
    GrahaOut,
    LifeWindowOut,
    MaritalInput,
    PredictionsOut,
    StrengthsOut,
)
from jyotish_engine.predict.domains import DOMAIN_SPECS, karakas
from jyotish_engine.predict.story import Reader
from jyotish_engine.predict.timeline import compute_predictions
from jyotish_engine.predict.words import HOUSE_AREAS
from jyotish_engine.rules.periods import compute_period_readings
from jyotish_engine.rules.schema import Domain
from jyotish_engine.strength.strengths import compute_strengths
from jyotish_engine.transit.timeline import sign_timeline

#: The slow grahas whose sign changes time the years.
SLOW: tuple[Body, ...] = (Body.SATURN, Body.JUPITER, Body.RAHU, Body.KETU)
#: Divisional charts reported per planet: marriage, career, children, property, parents,
#: education, wealth and siblings.
VARGAS: tuple[int, ...] = (9, 10, 7, 4, 12, 24, 2, 3)
#: At most this many periods per lookup, to keep answers small.
MAX_PERIODS = 80
#: Transits are searched this far either side of a range, so that each stay shows its
#: real ingress and egress (Saturn stays up to about three years in a sign).
TRANSIT_LEAD_DAYS = 3 * 366

#: Saturn counted from the natal Moon (transit/saturn.py names the same houses).
SATURN_FROM_MOON = {
    12: "Sade Sati, first phase",
    1: "Sade Sati, peak phase",
    2: "Sade Sati, last phase",
    4: "Ardhashtama (Kantaka) Shani",
    7: "Kantaka Shani",
    8: "Ashtama Shani",
    10: "Kantaka Shani",
}
#: Houses from the natal Moon where a slow graha's transit is traditionally favourable
#: (Phaladeepika 26), before vedha, which the dated transit rules apply.
GOOD_FROM_MOON = {
    Body.JUPITER: {2, 5, 7, 9, 11},
    Body.SATURN: {3, 6, 11},
    Body.RAHU: {3, 6, 11},
    Body.KETU: {3, 6, 11},
}
#: Muntha's house in the annual chart (Tajika Neelakanthi): tone, then what the year is
#: about for an adult and for someone under 18.
MUNTHA = {
    1: ("good", "personal initiative and fresh starts; health and confidence in focus",
        "confidence and fresh starts"),
    2: ("good", "income, savings and family", "family closeness and good habits"),
    3: ("good", "courage, effort, short journeys and siblings",
        "courage, hobbies and friendships"),
    4: ("mixed", "home, property and mother; keep worries at home in proportion",
        "home and family"),
    5: ("good", "studies, creativity and children", "studies and creativity"),
    6: ("hard", "work pressure and disputes; keep health and finances in order",
        "keeping health and routine steady"),
    7: ("mixed", "partnerships and marriage, which ask for patience and clear talk",
        "patience with friends and teamwork"),
    8: ("hard", "obstacles and delays; avoid risks and look after your health",
        "extra care and avoiding risks"),
    9: ("good", "one of the best placements: fortune, guidance, long journeys",
        "good fortune and guidance from teachers"),
    10: ("good", "one of the best placements: career, status and recognition",
         "achievement and recognition"),
    11: ("good", "one of the best placements: gains and wishes fulfilled",
         "gains and wishes fulfilled"),
    12: ("hard", "expenses, travel and rest; guard your savings", "travel, change and rest"),
}  # fmt: skip

#: Names people use for the grahas: English, Hindi in Latin letters and Devanagari.
PLANET_ALIASES: dict[str, Body] = {
    **{b.value: b for b in GRAHAS},
    "surya": Body.SUN, "सूर्य": Body.SUN,
    "chandra": Body.MOON, "chandrama": Body.MOON, "चंद्र": Body.MOON, "चन्द्र": Body.MOON,
    "mangal": Body.MARS, "mangala": Body.MARS, "kuja": Body.MARS, "मंगल": Body.MARS,
    "budh": Body.MERCURY, "budha": Body.MERCURY, "बुध": Body.MERCURY,
    "guru": Body.JUPITER, "brihaspati": Body.JUPITER, "गुरु": Body.JUPITER,
    "बृहस्पति": Body.JUPITER,
    "shukra": Body.VENUS, "शुक्र": Body.VENUS,
    "shani": Body.SATURN, "शनि": Body.SATURN,
    "राहु": Body.RAHU, "केतु": Body.KETU,
}  # fmt: skip
#: Words that name a life area. Latin words match whole words, or any word beginning
#: so when they end in "*"; Devanagari words match anywhere.
AREA_ALIASES: dict[Domain, tuple[str, ...]] = {
    Domain.CAREER: ("career*", "job*", "work*", "profession*", "promot*", "business*",
                    "naukri", "naukari", "नौकरी", "करियर", "व्यापार", "व्यवसाय"),
    Domain.MARRIAGE: ("marri*", "marry", "wedd*", "spouse", "wife", "husband", "partner*",
                      "shaadi", "shadi", "vivah", "शादी", "विवाह"),
    Domain.CHILDREN: ("child*", "kid*", "son", "sons", "daughter*", "baby", "babies",
                      "pregnan*", "santan", "बच्च", "संतान"),
    Domain.WEALTH: ("money", "wealth*", "income", "financ*", "saving*", "rich", "dhan",
                    "paisa", "पैसा", "धन"),
    Domain.PROPERTY: ("propert*", "home*", "land", "flat", "vehicle*", "car", "cars",
                      "a house", "own house", "new house", "my house", "our house", "ghar",
                      "makan", "घर", "मकान", "संपत्ति"),
    Domain.EDUCATION: ("study", "studies", "student*", "education*", "exam*", "degree*",
                       "college*", "school*", "padhai", "पढ़ाई", "शिक्षा"),
    Domain.PARENTS: ("father*", "mother*", "parent*", "pita", "mata", "पिता", "माता"),
    Domain.SPIRITUALITY: ("spiritual*", "meditat*", "religio*", "moksha", "dharma",
                          "आध्यात्म"),
    Domain.HEALTH: ("health*", "illness*", "disease*", "sick*", "sehat", "स्वास्थ्य", "सेहत"),
    Domain.TRAVEL: ("travel*", "abroad", "foreign*", "visa*", "settl*", "relocat*", "videsh",
                    "विदेश", "यात्रा"),
}  # fmt: skip
SPECS = {spec.domain: spec for spec in DOMAIN_SPECS}


def _pattern(words: tuple[str, ...]) -> re.Pattern[str]:
    latin = [
        re.escape(w[:-1]) + r"\w*" if w.endswith("*") else re.escape(w)
        for w in words
        if w.isascii()
    ]
    other = [re.escape(w) for w in words if not w.isascii()]
    parts = ([rf"\b(?:{'|'.join(latin)})\b"] if latin else []) + other
    return re.compile("|".join(parts), re.IGNORECASE)


_AREA_PATTERNS = {domain: _pattern(words) for domain, words in AREA_ALIASES.items()}
_PLANET_PATTERNS = {
    body: _pattern(tuple(name for name, b in PLANET_ALIASES.items() if b is body))
    for body in GRAHAS
}


def planet_of(name: str) -> Body:
    """The graha a name stands for: "Jupiter", "guru", "गुरु" ..."""
    body = PLANET_ALIASES.get(name.strip().lower())
    if body is None:
        raise LookupError(f"unknown planet {name!r}; use one of the nine grahas")
    return body


def area_of(name: str) -> Domain:
    """The life area a name stands for: "career", "job", "shaadi" ..."""
    text = name.strip().lower()
    for domain in Domain:
        if text == domain.value:
            return domain
    found = areas_in(text)
    if not found:
        raise LookupError(f"unknown life area {name!r}")
    return found[0]


def areas_in(text: str) -> list[Domain]:
    """The life areas a free-text question names, in the order of ``Domain``."""
    return [d for d, pattern in _AREA_PATTERNS.items() if pattern.search(text)]


def planets_in(text: str) -> list[Body]:
    """The grahas a free-text question names."""
    return [b for b, pattern in _PLANET_PATTERNS.items() if pattern.search(text)]


def sign_name(sign: int) -> str:
    s = Sign(sign % 12)
    return f"{s.name.title()} ({s.sanskrit})"


def ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def joined(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def houses(numbers: list[int]) -> str:
    return ("house " if len(numbers) == 1 else "houses ") + joined([str(n) for n in numbers])


def tone_word(tone: float) -> str:
    return "favourable" if tone > 0.15 else "challenging" if tone < -0.15 else "mixed"


def _title(body: Body) -> str:
    return body.value.title()


# --- Results ---------------------------------------------------------------------------


class PlanetFacts(BaseModel):
    planet: str
    sign: str
    degree: float
    house: int
    nakshatra: str
    pada: int
    nakshatra_lord: str
    dignity: str | None
    retrograde: bool
    combust: bool
    #: Houses whose sign the planet rules; ``co_rules`` for Rahu and Ketu's co-lordship.
    rules: list[int]
    co_rules: list[int]
    #: Houses it aspects (graha drishti), and the planets aspecting it or sharing its sign.
    aspects: list[int]
    aspected_by: list[str]
    joined_by: list[str]
    #: Its sign in the divisional charts, "D9" first.
    vargas: dict[str, str]
    vargottama: bool
    karaka: str | None
    #: Shadbala in rupas against the rupas required (the seven planets only).
    strength: str | None

    def summary(self) -> str:
        parts = [f"{self.planet}: {self.sign} {self.degree:.0f}°, house {self.house}"]
        flags = [x for x in (self.dignity, self.retrograde and "retrograde") if x]
        flags += ["combust"] if self.combust else []
        parts += [", ".join(flags)] if flags else []
        parts.append(f"{self.nakshatra} pada {self.pada} (star lord {self.nakshatra_lord})")
        if self.rules:
            parts.append(f"rules {houses(self.rules)}")
        if self.co_rules:
            parts.append(f"co-rules {houses(self.co_rules)}")
        parts.append(f"aspects {houses(self.aspects)}")
        if self.joined_by:
            parts.append(f"with {joined(self.joined_by)}")
        if self.aspected_by:
            parts.append(f"aspected by {joined(self.aspected_by)}")
        parts.append(", ".join(f"{k} {v}" for k, v in self.vargas.items()))
        parts += ["vargottama"] if self.vargottama else []
        parts += [self.karaka] if self.karaka else []
        parts += [f"Shadbala {self.strength}"] if self.strength else []
        return "; ".join(parts) + "."


class HouseFacts(BaseModel):
    house: int
    sign: str
    #: What the house stands for, in a few words.
    areas: str
    lord: str
    lord_house: int
    lord_sign: str
    lord_dignity: str | None
    occupants: list[str]
    aspected_by: list[str]
    #: Sarvashtakavarga bindus of the sign (28 is average).
    bindus: int
    #: Bhava Bala in rupas and its rank among the twelve houses.
    strength: str

    def summary(self) -> str:
        lord = f"lord {self.lord} in house {self.lord_house}, in {self.lord_sign}"
        lord += f", {self.lord_dignity}" if self.lord_dignity else ""
        parts = [f"House {self.house} ({self.areas}): {self.sign}", lord]
        parts.append(f"holds {joined(self.occupants)}" if self.occupants else "no planets")
        if self.aspected_by:
            parts.append(f"aspected by {joined(self.aspected_by)}")
        parts.append(f"{self.bindus} Ashtakavarga bindus (28 is average)")
        parts.append(f"Bhava Bala {self.strength}")
        return "; ".join(parts) + "."


class PeriodFacts(BaseModel):
    """A Vimshottari period; ``lords`` runs from the mahadasha lord down."""

    lords: list[str]
    start: date
    end: date

    def label(self) -> str:
        return " / ".join(self.lords)

    def summary(self) -> str:
        return f"{self.label()} {self.start} to {self.end}"


class TransitFacts(BaseModel):
    """A slow graha's stay in a sign."""

    planet: str
    sign: str
    start: date
    end: date
    house_from_moon: int
    house_from_lagna: int
    retrograde_entry: bool
    note: str | None

    def summary(self) -> str:
        text = (
            f"{self.planet} in {self.sign} {self.start} to {self.end}: "
            f"{ordinal(self.house_from_moon)} from the Moon, "
            f"{ordinal(self.house_from_lagna)} from the lagna"
        )
        return text + (f" ({self.note})" if self.note else "")


class PositionFacts(BaseModel):
    planet: str
    sign: str
    house_from_lagna: int
    house_from_moon: int


class RuleFacts(BaseModel):
    """A dasha or transit rule from the knowledge base that holds at a moment."""

    id: str
    name: str
    summary: str
    polarity: str


class MomentFacts(BaseModel):
    date: date
    age: int
    #: Mahadasha, antardasha and pratyantardasha.
    periods: list[PeriodFacts]
    positions: list[PositionFacts]
    readings: list[RuleFacts]

    def summary(self) -> str:
        levels = ("mahadasha", "antardasha", "pratyantardasha")
        running = [
            f"{p.lords[-1]} {level} until {p.end}"
            for level, p in zip(levels, self.periods, strict=False)
        ]
        slow = [p for p in self.positions if p.planet.lower() in {b.value for b in SLOW}]
        where = [
            f"{p.planet} in {p.sign}, {ordinal(p.house_from_moon)} from the Moon and "
            f"{ordinal(p.house_from_lagna)} from the lagna"
            for p in slow
        ]
        rules = [f"{r.name}: {r.summary}" for r in self.readings[:6]]
        text = f"On {self.date} (age {self.age}): {'; '.join(running)}. {'; '.join(where)}."
        return text + (f" Rules: {' | '.join(rules)}" if rules else "")


class WindowFacts(BaseModel):
    """A window when a life area is active: one of the windows the life reading tells, so
    the chat names the same times as the reading."""

    start: date
    #: The first day after the window.
    end: date
    peak: date
    ages: str = ""
    tone: str
    #: Strong: at least 80% as active as the area's strongest window (the reading tells a
    #: wedding or a birth only for a strong one); otherwise light.
    strength: str = ""
    #: How far the timing systems agree at the peak (not a probability).
    agreement: str
    #: The Vimshottari sub-periods the window falls in.
    periods: str
    reasons: list[str]

    def summary(self) -> str:
        last = self.end - timedelta(days=1)
        span = (
            f"{self.start:%Y-%m}"
            if (self.start.year, self.start.month) == (last.year, last.month)
            else f"{self.start:%Y-%m} to {last:%Y-%m}"
        )
        ages = f" {self.ages}" if self.ages else ""
        strength = f", {self.strength}" if self.strength else ""
        agreement = f", {self.agreement} agreement" if self.agreement else ""
        reasons = f": {'; '.join(self.reasons[:3])}" if self.reasons else ""
        return f"{span}{ages}, {self.tone}{strength}{agreement}, during {self.periods}{reasons}"


class AreaFacts(BaseModel):
    area: str
    houses: list[int]
    karakas: list[str]
    #: Natal promise, 0 to 1 (0.5 is average), and its main reasons.
    promise: float
    promise_reasons: list[str]
    windows: list[WindowFacts]
    note: str | None = None

    def summary(self) -> str:
        karaka = f"; karaka {joined(self.karakas)}" if self.karakas else ""
        head = (
            f"{self.area.title()} ({houses(self.houses)}{karaka}): "
            f"promise {self.promise:.2f} (0.5 is average), from " + "; ".join(self.promise_reasons)
        )
        if self.note:
            return f"{head}. {self.note}"
        if not self.windows:
            return f"{head}. No window of emphasis in this range."
        return f"{head}. Windows: " + " | ".join(w.summary() for w in self.windows)


class AnnualFacts(BaseModel):
    """The Tajika annual chart (Varshaphal) from a birthday."""

    start: date
    muntha_house: int
    year_lord: str
    lagna: str
    tone: str
    meaning: str

    def summary(self) -> str:
        return (
            f"annual chart from {self.start}: Muntha in the {ordinal(self.muntha_house)} house "
            f"({self.tone}: {self.meaning}), lord of the year {self.year_lord}, "
            f"annual lagna {self.lagna}"
        )


class YearFacts(BaseModel):
    year: int
    #: The age reached on the birthday in this year.
    turns: int
    annual: AnnualFacts | None
    #: Antardashas and pratyantardashas overlapping the year.
    periods: list[PeriodFacts]
    transits: list[TransitFacts]
    #: Windows of each life area overlapping the year.
    windows: dict[str, list[WindowFacts]]

    def summary(self) -> str:
        parts = [f"{self.year} (turns {self.turns} on the birthday)"]
        if self.annual:
            parts.append(self.annual.summary())
        parts.append("periods " + ", ".join(p.summary() for p in self.periods))
        parts.append("transits " + ", ".join(t.summary() for t in self.transits))
        found = [
            f"{area}: " + ", ".join(w.summary() for w in windows)
            for area, windows in self.windows.items()
        ]
        parts.append("windows " + (" | ".join(found) if found else "none"))
        return "; ".join(parts) + "."


# --- Lookups ---------------------------------------------------------------------------


class ChartLookup:
    """Lookups on one chart; the costly parts are computed once, when first needed."""

    def __init__(
        self,
        chart: ChartResult,
        *,
        today: date | None = None,
        gender: str | None = None,
        include_sensitive: bool = False,
        marital: MaritalInput | None = None,
    ) -> None:
        self.chart = chart
        self.today = today or datetime.now(UTC).date()
        self.gender = gender
        self.include_sensitive = include_sensitive
        #: What the person said about marriage: it decides how marriage windows are told.
        self.marital = marital
        self.zone = ZoneInfo(chart.time.zone or "UTC")
        self.grahas: dict[Body, GrahaOut] = {g.body: g for g in chart.grahas if g.body in GRAHAS}
        self.lagna = int(chart.ascendant.sign)
        self.moon = int(self.grahas[Body.MOON].sign)
        self.born = chart.birth.local_datetime.date()
        #: Transits and the prediction timeline are computed up to the ephemeris' end.
        self.first = jd_to_datetime(chart.ephemeris.jd_start + 2.0).date()
        self.last = jd_to_datetime(chart.ephemeris.jd_end - 31.0).date()

    # Helpers

    def _local(self, moment: datetime) -> date:
        aware = moment if moment.tzinfo else moment.replace(tzinfo=UTC)
        return aware.astimezone(self.zone).date()

    def _house(self, sign: int) -> int:
        return (sign - self.lagna) % 12 + 1

    def age(self, day: date) -> int:
        had_birthday = (day.month, day.day) >= (self.born.month, self.born.day)
        return day.year - self.born.year - (0 if had_birthday else 1)

    def _aspected_signs(self, body: Body) -> list[int]:
        nodes = self.chart.settings.node_aspects_5_9
        return graha_aspected_signs(body, int(self.grahas[body].sign), nodes)

    def _period(self, period: DashaPeriodOut) -> PeriodFacts:
        return PeriodFacts(
            lords=[_title(b) for b in period.lords],
            start=self._local(period.start),
            end=self._local(period.end),
        )

    @staticmethod
    def _window(window: LifeWindowOut) -> WindowFacts:
        return WindowFacts(
            start=window.start,
            end=window.end,
            peak=window.peak,
            ages=window.ages,
            tone=window.tone,
            strength=window.strength,
            agreement=window.agreement,
            periods=window.periods,
            reasons=window.reasons,
        )

    @cached_property
    def strengths(self) -> StrengthsOut:
        return compute_strengths(self.chart)

    @cached_property
    def dasha_rows(self) -> list[DashaPeriodOut]:
        """Vimshottari to the pratyantardasha, for the full 120-year cycle."""
        return chart_dasha_table(self.chart, NakshatraDasha.VIMSHOTTARI, depth=3).periods

    @cached_property
    def life(self) -> PredictionsOut:
        """The prediction timeline over the whole life the ephemeris covers (at most 100
        years): windows are chosen against the whole life, never one year alone."""
        first = self.born.replace(day=1)
        return compute_predictions(
            self.chart, first, date(first.year + 100, first.month, 1), gender=self.gender
        )

    @cached_property
    def reader(self) -> Reader:
        """The life reading's reader for this chart, today and what the person said about
        marriage: the chat tells the windows and the marriage timing the reading tells."""
        return Reader(self.chart, self.today, self.gender, None, 5, self.marital, life=self.life)

    @cached_property
    def windows(self) -> list[LifeWindowOut]:
        """The windows the life reading tells, over the whole life."""
        return self.reader.windows()

    def _windows(self, domain: Domain, start: date, end: date) -> list[WindowFacts]:
        if self._hidden(domain):
            return []
        return [
            self._window(w)
            for w in self.windows
            if w.domain is domain and w.end > start and w.start < end
        ]

    def _domain(self, domain: Domain) -> DomainTimelineOut:
        return next(d for d in self.life.domains if d.domain is domain)

    def _hidden(self, domain: Domain) -> bool:
        return domain is Domain.HEALTH and not self.include_sensitive

    # Natal

    def planet(self, name: str | Body) -> PlanetFacts:
        body = name if isinstance(name, Body) else planet_of(name)
        g = self.grahas[body]
        sign = int(g.sign)
        roles = {b: k for k, b in self.chart.special.karakas.items()}
        vargas = {v.division: v for v in self.chart.vargas}
        signs = {
            f"D{n}": sign_name(int(vargas[n].grahas[body].sign))
            for n in VARGAS
            if n in vargas and body in vargas[n].grahas
        }
        shadbala = next((s for s in self.strengths.shadbala if s.body is body), None)
        strength = None
        if shadbala is not None:
            word = (
                "strong"
                if shadbala.ratio >= 1.2
                else "adequate"
                if shadbala.ratio >= 1.0
                else "below the required strength"
            )
            strength = (
                f"{shadbala.rupas:.1f} of {shadbala.required_rupas:.1f} rupas needed ({word})"
            )
        others = [b for b in self.grahas if b is not body]
        d9 = vargas[9].grahas[body].sign if 9 in vargas and body in vargas[9].grahas else None
        return PlanetFacts(
            planet=_title(body),
            sign=sign_name(sign),
            degree=round(g.degrees_in_sign, 2),
            house=g.house,
            nakshatra=g.nakshatra.name,
            pada=g.nakshatra.pada,
            nakshatra_lord=_title(g.nakshatra.lord),
            dignity=g.dignity.value.replace("_", " ") if g.dignity else None,
            retrograde=g.retrograde,
            combust=g.combust,
            rules=sorted(self._house(int(s)) for s, lord in SIGN_LORDS.items() if lord is body),
            co_rules=sorted(
                self._house(int(s))
                for s, lords in CO_LORDS.items()
                if body in lords and SIGN_LORDS[s] is not body
            ),
            aspects=sorted(self._house(s) for s in self._aspected_signs(body)),
            aspected_by=[_title(b) for b in others if sign in self._aspected_signs(b)],
            joined_by=[_title(b) for b in others if int(self.grahas[b].sign) == sign],
            vargas=signs,
            vargottama=d9 is not None and int(d9) == sign,
            karaka=roles[body].value.title() if body in roles else None,
            strength=strength,
        )

    def house(self, number: int) -> HouseFacts:
        if not 1 <= number <= 12:
            raise ValueError("houses are numbered 1 to 12")
        sign = (self.lagna + number - 1) % 12
        lord = SIGN_LORDS[Sign(sign)]
        held = self.grahas[lord]
        bhava = sorted(self.strengths.bhava_bala, key=lambda h: -h.rupas)
        rank = next(i for i, h in enumerate(bhava, 1) if h.house == number)
        rupas = next(h.rupas for h in bhava if h.house == number)
        return HouseFacts(
            house=number,
            sign=sign_name(sign),
            areas=HOUSE_AREAS[number]["adult"],
            lord=_title(lord),
            lord_house=held.house,
            lord_sign=sign_name(int(held.sign)),
            lord_dignity=held.dignity.value.replace("_", " ") if held.dignity else None,
            occupants=[_title(b) for b, g in self.grahas.items() if int(g.sign) == sign],
            aspected_by=[_title(b) for b in self.grahas if sign in self._aspected_signs(b)],
            bindus=self.strengths.ashtakavarga.sav[sign],
            strength=f"{rupas:.1f} rupas, {ordinal(rank)} strongest of 12",
        )

    # Timing

    def moment(self, day: date) -> MomentFacts:
        """The periods, every graha's transit and the rules that hold on ``day``."""
        when = datetime(day.year, day.month, day.day, 12, tzinfo=UTC)
        out = compute_period_readings(self.chart, when, include_sensitive=self.include_sensitive)
        return MomentFacts(
            date=day,
            age=self.age(day),
            periods=[self._period(p) for p in out.dasha],
            positions=[
                PositionFacts(
                    planet=_title(t.body),
                    sign=sign_name(int(t.sign)),
                    house_from_lagna=t.house_from_lagna,
                    house_from_moon=t.house_from_moon,
                )
                for t in out.transits
                if t.body in GRAHAS
            ],
            readings=[
                RuleFacts(id=r.id, name=r.name, summary=r.summary, polarity=r.polarity.value)
                for r in [*out.dasha_readings, *out.transit_readings]
            ],
        )

    def periods(
        self,
        start: date,
        end: date,
        levels: tuple[int, ...] | None = None,
        limit: int | None = MAX_PERIODS,
    ) -> list[PeriodFacts]:
        """Periods overlapping ``[start, end)``: pratyantardashas for up to three years,
        antardashas for longer ranges, unless ``levels`` (1 to 3) says otherwise; at most
        ``limit`` of them (``None``: all)."""
        if end <= start:
            raise ValueError("the range must end after it starts")
        chosen = levels or ((3,) if (end - start).days <= 3 * 366 else (2,))
        found = [
            self._period(p)
            for p in self.dasha_rows
            if len(p.lords) in chosen and self._local(p.end) > start and self._local(p.start) < end
        ]
        return found if limit is None else found[:limit]

    def transits(
        self, start: date, end: date, planets: tuple[Body, ...] = SLOW
    ) -> list[TransitFacts]:
        """The signs ``planets`` occupy during ``[start, end)``, each stay from its ingress."""
        if min(end, self.last) <= start:
            return []
        jd = (
            datetime_to_jd(datetime(start.year, start.month, start.day, tzinfo=UTC)),
            datetime_to_jd(datetime(end.year, end.month, end.day, tzinfo=UTC)),
        )
        lead = max(jd[0] - TRANSIT_LEAD_DAYS, self.chart.ephemeris.jd_start + 2.0)
        until = min(jd[1] + TRANSIT_LEAD_DAYS, self.chart.ephemeris.jd_end - 2.0)
        out = []
        for body in planets:
            for stay in sign_timeline(body, lead, until, self.chart.settings):
                begin = self._local(jd_to_datetime(stay.start_jd_ut))
                finish = self._local(jd_to_datetime(stay.end_jd_ut))
                if finish <= start or begin >= end:
                    continue
                from_moon = (stay.sign - self.moon) % 12 + 1
                note = SATURN_FROM_MOON.get(from_moon) if body is Body.SATURN else None
                if note is None and from_moon in GOOD_FROM_MOON[body]:
                    note = "traditionally favourable from the Moon"
                out.append(
                    TransitFacts(
                        planet=_title(body),
                        sign=sign_name(stay.sign),
                        start=begin,
                        end=finish,
                        house_from_moon=from_moon,
                        house_from_lagna=self._house(stay.sign),
                        retrograde_entry=bool(stay.entered_retrograde),
                        note=note,
                    )
                )
        return sorted(out, key=lambda t: (t.start, t.planet))

    def area(
        self, name: str | Domain, start: date | None = None, end: date | None = None
    ) -> AreaFacts:
        """A life area's natal promise and its windows in ``[start, end)`` (whole life by
        default). Health is read as tendencies only, without windows, unless sensitive
        readings were asked for."""
        domain = name if isinstance(name, Domain) else area_of(name)
        spec = SPECS[domain]
        timeline = self._domain(domain)
        windows = self._windows(domain, start or date.min, end or date.max)
        top = sorted(timeline.promise.factors, key=lambda f: -abs(f.score) * f.weight)[:4]
        return AreaFacts(
            area=domain.value,
            houses=list(spec.houses),
            karakas=[_title(b) for b in karakas(spec, self.gender)],
            promise=round(timeline.promise.score, 2),
            promise_reasons=[f"{f.label} ({f.score:+.2f})" for f in top],
            windows=windows,
            note="Health is read as tendencies only, without dates."
            if self._hidden(domain)
            else None,
        )

    def annual(self, year: int) -> AnnualFacts | None:
        """The annual chart starting on the birthday in ``year``, if the ephemeris has it."""
        completed = year - self.born.year
        if completed < 0:
            return None
        try:
            annual = compute_varshaphal(self.chart, completed)
        except ValueError:  # outside the ephemeris
            return None
        house = (int(annual.muntha) - int(annual.chart.ascendant.sign)) % 12 + 1
        tone, adult, young = MUNTHA[house]
        return AnnualFacts(
            start=self._local(annual.start),
            muntha_house=house,
            year_lord=_title(annual.year_lord),
            lagna=sign_name(int(annual.chart.ascendant.sign)),
            tone=tone,
            meaning=adult if completed >= 18 else young,
        )

    def year(self, year: int) -> YearFacts:
        """Everything dated in one calendar year."""
        start, end = date(year, 1, 1), date(year + 1, 1, 1)
        windows = {
            d.domain.value: found
            for d in self.life.domains
            if (found := self._windows(d.domain, start, end))
        }
        return YearFacts(
            year=year,
            turns=year - self.born.year,
            annual=self.annual(year),
            periods=self.periods(start, end, (2, 3)),
            transits=self.transits(start, end),
            windows=windows,
        )


__all__ = [
    "AREA_ALIASES",
    "MUNTHA",
    "PLANET_ALIASES",
    "AnnualFacts",
    "AreaFacts",
    "ChartLookup",
    "HouseFacts",
    "MomentFacts",
    "PeriodFacts",
    "PlanetFacts",
    "TransitFacts",
    "WindowFacts",
    "YearFacts",
    "area_of",
    "areas_in",
    "planet_of",
    "planets_in",
    "sign_name",
]
