"""The life reading's topic sections, each worked out from the person's own chart: the
personal portrait, career, foreign travel and settlement, health, marriage and spouse,
and remedies.

Every function takes the reading's ``Reader`` (see ``story.py``), which holds the chart
facts, the prediction timeline and the person's age, and returns plain-language text.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from datetime import timedelta
from typing import TYPE_CHECKING

from jyotish_engine.astro.bodies import Body
from jyotish_engine.core.zodiac import SIGN_LORDS, Sign
from jyotish_engine.models import ReadingSectionOut, RemedyOut, Tone
from jyotish_engine.predict import lore, words
from jyotish_engine.predict.voice import cap, join, month, when_future
from jyotish_engine.rules.schema import Domain
from jyotish_engine.special.karakas import Karaka

if TYPE_CHECKING:
    from jyotish_engine.predict.story import Reader

SEVEN = (Body.SUN, Body.MOON, Body.MARS, Body.MERCURY, Body.JUPITER, Body.VENUS, Body.SATURN)
GENTLE = frozenset({Body.JUPITER, Body.VENUS, Body.MERCURY, Body.MOON})
HARSH = frozenset({Body.SATURN, Body.MARS, Body.RAHU, Body.KETU, Body.SUN})
#: Which planets with the Moon say most about the emotional nature, first to last.
MOON_COMPANIONS = (
    Body.SATURN,
    Body.RAHU,
    Body.KETU,
    Body.MARS,
    Body.JUPITER,
    Body.VENUS,
    Body.MERCURY,
    Body.SUN,
)
#: Areas told in the portrait's strengths, with the ages they are told from.
PORTRAIT_AREAS: dict[Domain, int] = {
    Domain.CAREER: 14,
    Domain.WEALTH: 18,
    Domain.MARRIAGE: 18,
    Domain.CHILDREN: 25,
    Domain.PROPERTY: 18,
    Domain.EDUCATION: 0,
    Domain.TRAVEL: 0,
    Domain.SPIRITUALITY: 25,
}
GROWTH: dict[Domain, str] = {
    Domain.CAREER: "career moves at its own pace, so persistence pays",
    Domain.WEALTH: "money needs discipline: save in the good times",
    Domain.MARRIAGE: "relationships ask for more patience and open talk",
    Domain.CHILDREN: "family plans need patience",
    Domain.PROPERTY: "property comes through planning rather than luck",
    Domain.EDUCATION: "studies need steady habits more than talent alone",
    Domain.TRAVEL: "moves need careful planning",
    Domain.SPIRITUALITY: "peace of mind comes through practice",
}
#: The planets whose remedies help a weak life area.
AREA_PLANETS: dict[Domain, tuple[Body, ...]] = {
    Domain.CAREER: (Body.SUN, Body.SATURN),
    Domain.WEALTH: (Body.JUPITER, Body.VENUS),
    Domain.MARRIAGE: (Body.VENUS,),
    Domain.CHILDREN: (Body.JUPITER,),
    Domain.PROPERTY: (Body.MARS,),
    Domain.EDUCATION: (Body.MERCURY, Body.JUPITER),
    Domain.SPIRITUALITY: (Body.JUPITER,),
}


def _planet(body: Body) -> str:
    return body.value.title()


def _the(body: Body) -> str:
    """A planet's name in running text: "the Sun", "the Moon", "Mars"."""
    return f"the {_planet(body)}" if body in (Body.SUN, Body.MOON) else _planet(body)


def _house(r: Reader, house: int, *, adult: bool = True) -> str:
    """A house in running text: "your first house", "your house of career and status"; with
    ``adult`` false, in the words for the reader's own age."""
    if house == 1:
        return "your first house"
    return f"your house of {r.area(house, max(r.age, 25) if adult else r.age)}"


# -- the portrait ---------------------------------------------------------------------


def _elements(r: Reader) -> Counter[lore.Element]:
    facts = r.facts
    counts: Counter[lore.Element] = Counter({e: 0 for e in lore.ELEMENTS})
    counts[lore.ELEMENT[Sign(facts.lagna_sign)]] += 1
    for body in SEVEN:
        counts[lore.ELEMENT[Sign(facts.signs[body])]] += 1
    return counts


def _ranked_areas(r: Reader) -> tuple[list[Domain], Domain | None]:
    """The person's strongest areas (promise 0.55 and up) and the weakest (below 0.47),
    among those that suit the age."""
    told = [
        (r.promise(d), d)
        for d, low in PORTRAIT_AREAS.items()
        if r.age >= low
        and not (r.minor and d in (Domain.MARRIAGE, Domain.CHILDREN))
        and not (d is Domain.EDUCATION and r.age >= 31)
    ]
    ranked = sorted(told, key=lambda item: -item[0])
    strong = [d for score, d in ranked if score >= 0.55][:2]
    weak = next((d for score, d in reversed(ranked) if score < 0.47 and d not in strong), None)
    return strong, weak


def portrait(r: Reader) -> tuple[list[str], list[str]]:
    """The personal brief for the summary, and the "who you are" paragraphs."""
    facts = r.facts
    lagna, moon = Sign(facts.lagna_sign), Sign(r.moon_sign)
    first = [b for b in facts.occupants(1) if b in lore.FIRST_HOUSE]
    moon_house = facts.house(Body.MOON)
    companion = next(
        (b for b in MOON_COMPANIONS if b in facts.occupants(moon_house) and b is not Body.MOON),
        None,
    )
    counts = _elements(r)
    dominant = next((e for e, n in counts.most_common(1) if n >= 4), None)
    missing = [e for e in lore.ELEMENTS if counts[e] == 0]
    ruler = facts.lord(1)
    ruler_house = facts.house(ruler)
    sun_house = facts.house(Body.SUN)
    strong, weak = _ranked_areas(r)

    who = f"{r.name}, you are" if r.name else "You are"
    brief = [f"{who} {words.RISING[lagna][0]}, with {words.MOON_SIGN[moon][0]}."]
    traits = [lore.FIRST_HOUSE[b] for b in first[:2]]
    if not traits and companion is not None:
        traits.append(lore.MOON_WITH[companion])
    if dominant is not None:
        traits.append(lore.ELEMENT_DOMINANT[dominant])
    if traits:
        brief[0] += " " + cap(join(traits[:2])) + "."
    else:
        brief[0] += (
            f" {_planet(ruler)}, your chart's ruler, sits in the part of your chart for "
            f"{r.area(ruler_house, r.age)}, so {words.CHART_RULER_IN_HOUSE[ruler_house]}."
        )
    if strong:
        line = f"Your chart is strongest for {join([words.AREA_NAMES[d] for d in strong])}"
        line += f"; {GROWTH[weak]}." if weak is not None else "."
        brief.append(line)

    paragraphs = [words.RISING[lagna][1]]
    if first:
        paragraphs[0] += " " + cap(join([lore.FIRST_HOUSE[b] for b in first])) + "."
    emotional = words.MOON_SIGN[moon][1]
    if companion is not None:
        emotional += f" In your chart, {lore.MOON_WITH[companion]}."
    star = next(g for g in r.chart.grahas if g.body is Body.MOON).nakshatra.index
    paragraphs.append(f"{emotional} {words.NAKSHATRA_NATURE[star]}")
    drive = (
        f"{_planet(ruler)}, the planet that rules your rising sign, sits in the part of your "
        f"chart that stands for {r.area(ruler_house, r.age)}: "
        f"{words.CHART_RULER_IN_HOUSE[ruler_house]}. You shine most "
        f"{lore.SUN_SHINES[sun_house]}."
    )
    paragraphs.append(drive)
    balance = [cap(lore.ELEMENT_DOMINANT[dominant]) + "."] if dominant else []
    balance += [lore.ELEMENT_MISSING[e] for e in missing[:1]]
    if balance:
        paragraphs.append(" ".join(balance))
    return brief, paragraphs


# -- career -----------------------------------------------------------------------------


def career_fields(r: Reader, limit: int = 5) -> tuple[list[str], list[str]]:
    """Kinds of work ranked against the chart, with the reasons in plain words.

    Each field scores the chart factors that point to it: the ruler of the tenth house,
    the house it sits in, the tenth sign, planets in the tenth and those aspecting it, the
    source of earnings (the lord of the tenth lord's navamsa, Brihat Jataka) and the
    Jaimini career significator (amatyakaraka). Fields that more factors agree on rank
    first.
    """
    facts = r.facts
    sign10 = Sign(facts.sign_of_house(10))
    lord = facts.lord(10)
    house = facts.house(lord)
    inside = [b for b in facts.occupants(10) if b in lore.CAREER_PLANET]
    source = SIGN_LORDS[Sign(facts.navamsa_sign(lord))]
    amatya = r.chart.special.karakas.get(Karaka.AMATYA)
    aspecting = [b for b in SEVEN if b not in inside and facts.aspects_sign(b, int(sign10))]
    factors: list[tuple[str, float]] = [
        (lord.value, 3.0),
        (f"h{house}", 2.0),
        (sign10.name.lower(), 2.0),
        (source.value, 2.0),
        (Sign(facts.signs[lord]).name.lower(), 1.0),
        *((b.value, 2.5) for b in inside),
        *((b.value, 1.0) for b in aspecting),
    ]
    if amatya is not None:
        factors.append((amatya.value, 2.0))
    ranked = []
    for index, (name, tags) in enumerate(lore.FIELDS.items()):
        hits = [weight for tag, weight in factors if tag in tags]
        ranked.append((-sum(hits), -len(hits), index, name))
    fields = [name for score, _, _, name in sorted(ranked) if -score >= 2.5][:limit]
    reasons = [
        f"Your house of career falls in {sign10.name.title()} and is governed by "
        f"{_the(lord)}, which sits in {_house(r, house)}: that points to "
        f"{lore.CAREER_LORD_IN_HOUSE[house]}."
    ]
    if inside:
        reasons.append(
            cap(
                join(
                    [
                        f"{_the(b)} in your house of career adds {lore.CAREER_PLANET[b]}"
                        for b in inside[:2]
                    ]
                )
            )
            + "."
        )
    if source in lore.KARMAJIVA:
        reasons.append(
            f"By the classical rule for the source of earnings, {_the(source)} points to "
            f"{lore.KARMAJIVA[source]}."
        )
    if amatya in lore.CAREER_PLANET and amatya not in (lord, source, *inside):
        reasons.append(
            f"{cap(_the(amatya))}, the planet that guides your work in the Jaimini system, adds "
            f"{lore.CAREER_PLANET[amatya]}."
        )
    return fields, reasons


def _work_style(r: Reader) -> str:
    facts = r.facts
    house = facts.house(facts.lord(10))
    inside = facts.occupants(10)
    business = (
        (house in (1, 3, 7, 11))
        + (facts.house(facts.lord(7)) == 10)
        + (Body.MERCURY in inside or Body.RAHU in inside)
    )
    job = (
        (house in (6, 8, 12))
        + (Body.SATURN in inside or Body.SUN in inside)
        + (facts.house(facts.lord(6)) == 10)
    )
    if business > job:
        return "Your chart leans towards independent work or a business of your own."
    if job > business:
        return (
            "Your chart leans towards a salaried career that grows steadily within an organisation."
        )
    return (
        "Your chart supports both a job and independent work; many people with this pattern "
        "start in a job and branch out later."
    )


def career(r: Reader) -> ReadingSectionOut:
    level = r.level(Domain.CAREER)
    fields, reasons = career_fields(r)
    if r.age < 14:
        return ReadingSectionOut(
            key="talents",
            title="Talents and future work",
            paragraphs=[
                f"When it is time to choose a direction, fields that suit this chart include "
                f"{join(fields[:4])}. Encourage the interests that come naturally; the chart only "
                "shows tendencies.",
                " ".join(reasons[:2]),
            ],
            basis=[f"career fields from the tenth house: {', '.join(fields)}"],
        )
    paragraphs = [
        f"{words.AREA_PROMISE[Domain.CAREER][level]} {_work_style(r)}",
        f"Fields that suit you best: {join(fields)}.",
        " ".join(reasons),
    ]
    timing = r.area_timing(Domain.CAREER)
    if timing:
        paragraphs.append(timing)
    return ReadingSectionOut(
        key="career",
        title="Career and work",
        paragraphs=paragraphs,
        tone=r.level_tone(level),
        basis=[
            f"career promise {r.promise(Domain.CAREER):.2f}",
            f"tenth lord {r.facts.lord(10).value} in house {r.facts.house(r.facts.lord(10))}",
        ],
    )


# -- foreign travel and settlement --------------------------------------------------------


def foreign(r: Reader) -> ReadingSectionOut:
    facts = r.facts
    lord12, ruler, lord4, lord9 = facts.lord(12), facts.lord(1), facts.lord(4), facts.lord(9)
    h12, hr, h4, h9 = (facts.house(b) for b in (lord12, ruler, lord4, lord9))
    rahu = facts.house(Body.RAHU)
    moon = facts.house(Body.MOON)
    in12 = facts.occupants(12)
    travel: list[tuple[float, str]] = []
    settle = 0.0
    named = "the planet that rules foreign lands"
    if h12 == 1:
        travel.append((2.0, f"{named} sits in your first house"))
        settle += 2.0
    elif h12 == 12:
        travel.append((2.0, f"{named} sits in its own house"))
        settle += 1.5
    elif h12 == 4:
        travel.append((1.5, f"{named} sits in your house of home"))
        settle += 1.5
    elif h12 in (7, 9, 10):
        travel.append((1.0, f"{named} sits in {_house(r, h12)}"))
    if hr == 12 and ruler is not lord12:
        travel.append((2.0, "the ruler of your rising sign sits in your house of foreign lands"))
        settle += 2.0
    elif hr == 9:
        travel.append((1.0, "the ruler of your rising sign sits in your house of long journeys"))
    if h4 == 12 and lord4 is not lord12:
        travel.append((1.5, "the ruler of your home sits in your house of foreign lands"))
        settle += 1.5
    if (h9 == 12 or h12 == 9) and lord9 is not lord12:
        travel.append((1.0, "the rulers of long journeys and foreign lands are linked"))
    if rahu in (1, 4, 7, 9, 10, 12):
        travel.append((1.0, f"Rahu, the planet of distant places, sits in {_house(r, rahu)}"))
        settle += 1.0 if rahu in (4, 12) else 0.0
    if Body.SATURN in in12:
        travel.append((1.0, "Saturn in your house of foreign lands points to long stays away"))
        settle += 1.0
    if any(b in GENTLE for b in in12):
        travel.append(
            (0.5, "gentle planets in your house of foreign lands make time abroad pleasant")
        )
    if moon in (9, 12):
        travel.append((0.5, f"the Moon in {_house(r, moon)} adds a love of travel"))
    if Sign(facts.lagna_sign) in lore.MOVABLE_SIGNS:
        travel.append((0.5, "a movable rising sign adds a love of change"))
    if Sign(facts.sign_of_house(12)) in lore.WATER_SIGNS:
        travel.append(
            (0.5, "a water sign on your house of foreign lands traditionally points across the sea")
        )
    score = sum(w for w, _ in travel) + (0.5 if r.promise(Domain.TRAVEL) >= 0.58 else 0.0)
    level = "strong" if score >= 3 else "likely" if score >= 1.5 else "occasional"
    reasons = [text for _, text in sorted(travel, key=lambda item: -item[0])[:2]]
    first = lore.TRAVEL_LEVEL[level]
    if reasons:
        first += f" {cap(join(reasons))}."
    settled = "strong" if settle >= 3 else "possible" if settle >= 1.5 else "unlikely"
    settling = lore.SETTLE_LEVEL[settled]
    if r.age < 18:
        settling = "Later in life: " + settling[:1].lower() + settling[1:]
    paragraphs = [first, settling]
    timing = r.area_timing(Domain.TRAVEL)
    upcoming = _sub_periods(r, (lord12, Body.RAHU), years=10)
    if upcoming:
        timing += (" " if timing else "") + upcoming
    if timing:
        paragraphs.append(timing)
    return ReadingSectionOut(
        key="foreign",
        title="Travel and new places" if r.age < 18 else "Foreign travel and settlement",
        paragraphs=paragraphs,
        tone={"strong": "good", "likely": "good", "occasional": "mixed"}[level],
        basis=[f"travel indicators {score:.1f}, settlement {settle:.1f}", *reasons],
    )


def _sub_periods(r: Reader, lords: Sequence[Body], years: int) -> str:
    """The next sub-period of one of ``lords`` within ``years``, as a sentence."""
    until = r.today + timedelta(days=365 * years)
    for period in r.dashas.levels.get(2, []):
        start, end = period.start.date(), period.end.date()
        if end <= r.today or start > until or period.lords[-1] not in lords:
            continue
        who = _planet(period.lords[-1])
        if start <= r.today:
            return (
                f"By the classical rule, the {who} sub-period running until {month(end)} "
                "favours travel abroad."
            )
        return (
            f"By the classical rule, the {who} sub-period, from {month(start)} to "
            f"{month(end - timedelta(days=1))}, favours travel abroad."
        )
    return ""


# -- health -----------------------------------------------------------------------------


def health(r: Reader) -> ReadingSectionOut:
    facts = r.facts
    lagna = Sign(facts.lagna_sign)
    sign6 = Sign(facts.sign_of_house(6))
    ruler = facts.lord(1)
    points = {"good": 1.0, "mixed": 0.0, "hard": -1.0}[r.standing(ruler)]
    for body in (Body.SUN, Body.MOON):
        points += 0.5 if facts.dignified(body) else -0.5 if facts.debilitated(body) else 0.0
    points += 0.5 if facts.waxing else -0.25
    vitality = "good" if points >= 1 else "care" if points <= -1 else "steady"
    paragraphs = [f"{lore.VITALITY[vitality]} {lore.CONSTITUTION[lore.ELEMENT[lagna]]}"]
    areas = [lore.SIGN_BODY[lagna]]
    if lore.SIGN_BODY[sign6] not in areas:
        areas.append(lore.SIGN_BODY[sign6])
    care = (
        f"By tradition, your rising sign rules {lore.SIGN_BODY[lagna]}, and your house of "
        f"health falls in a sign that rules {lore.SIGN_BODY[sign6]}; these are the areas to "
        "look after."
        if len(areas) > 1
        else f"By tradition, {lore.SIGN_BODY[lagna]} are the areas to look after."
    )
    strained = [
        (b, f"in {_house(r, h, adult=False)}")
        for h in (6, 8)
        for b in facts.occupants(h)
        if b in lore.PLANET_CARE
    ]
    strained += [
        (b, "in its weakest sign")
        for b in (Body.SUN, Body.MOON)
        if facts.debilitated(b) and all(b is not s for s, _ in strained)
    ]
    for body, where in strained[:2]:
        care += f" With {_the(body)} {where}, look after {lore.PLANET_CARE[body]}."
    paragraphs.append(care)
    timing = _health_timing(r)
    if timing:
        paragraphs.append(timing)
    paragraphs.append(lore.HEALTH_NOTE)
    return ReadingSectionOut(
        key="health",
        title="Health and well-being",
        paragraphs=paragraphs,
        tone={"good": "good", "steady": "mixed", "care": "hard"}[vitality],
        basis=[
            f"vitality points {points:+.2f}; lagna {lagna.name.title()}; sixth {sign6.name.title()}"
        ],
    )


def _health_timing(r: Reader) -> str:
    until = r.today.replace(year=r.today.year + r.years_ahead)
    ahead = [
        e for e in r.episodes if e.domain is Domain.HEALTH and e.end > r.today and e.start < until
    ]
    parts = []
    careful = [e for e in ahead if e.tone == "hard"]
    if careful:
        when = join(
            [when_future(e.start, e.end) for e in sorted(careful, key=lambda e: e.start)[:2]]
        )
        parts.append(
            f"Give your health extra attention in {when}: rest, a steady routine and timely "
            "check-ups."
        )
    good = [e for e in ahead if e.tone == "good"]
    if good:
        best = max(good, key=lambda e: e.score)
        parts.append(
            f"{cap(when_future(best.start, best.end))} is a good time for energy and fitness."
        )
    running = r.sade_sati_now()
    if running and running[1] == 1:
        parts.append(
            "During the middle phase of Sade Sati, until "
            f"{month(running[2])}, rest and routine matter more than usual."
        )
    return " ".join(parts)


# -- marriage and spouse ------------------------------------------------------------------


def marriage(r: Reader) -> ReadingSectionOut | None:
    """Marriage and the spouse, for readers 18 and over."""
    if r.minor:
        return None
    facts = r.facts
    sign7 = Sign(facts.sign_of_house(7))
    lord7, lord5 = facts.lord(7), facts.lord(5)
    h7 = facts.house(lord7)
    inside = [b for b in facts.occupants(7) if b in lore.SPOUSE_PLANET]
    level = r.level(Domain.MARRIAGE)
    promise = words.AREA_PROMISE[Domain.MARRIAGE][level]
    if r.married and level == "effort":
        promise = (
            "Relationships ask for extra patience in your chart: married life does best with "
            "time, adjustment and talking things through."
        )
    first = [promise]
    if facts.dignified(Body.VENUS):
        lead = "On the bright side, " if level in ("average", "effort") else ""
        first.append(f"{lead}Venus, the planet of love, is strong in your chart.")
    elif facts.debilitated(Body.VENUS) or facts.combust(Body.VENUS):
        first.append(
            "Venus, the planet of love, needs support in your chart, so give relationships "
            "time and care."
        )
    if Body.SATURN in inside or facts.aspects_sign(Body.SATURN, int(sign7)):
        first.append(
            "Saturn's influence on your house of marriage asks for patience and maturity in "
            "married life, and it gives a lasting bond."
            if r.married
            else "Saturn's influence on your house of marriage often brings marriage a little "
            "later, and it works best with a mature, steady partner."
        )
    if Body.JUPITER in inside or facts.aspects_sign(Body.JUPITER, int(sign7)):
        first.append("Jupiter's blessing on your house of marriage protects married life.")
    spouse = f"The chart describes a partner who is {words.PARTNER[sign7]}."
    if inside:
        spouse += (
            f" With {_the(inside[0])} in your house of marriage, your partner may also be "
            f"{lore.SPOUSE_PLANET[inside[0]]}."
        )
        for body in inside[1:2]:
            spouse += f" {cap(_the(body))} there too adds {lore.SPOUSE_ALSO[body]}."
    dara = r.chart.special.karakas.get(Karaka.DARA)
    if dara is not None and dara not in inside and dara in lore.SPOUSE_PLANET:
        spouse += (
            f" {_planet(dara)}, the planet that stands for the spouse in your chart, adds "
            f"someone {lore.SPOUSE_PLANET[dara]}."
        )
    spouse += f" You are likely to meet your partner {lore.WHERE_MEET[h7]}."
    love = (
        facts.signs[lord5] == facts.signs[lord7]
        or facts.house(lord5) == 7
        or h7 == 5
        or (facts.aspects(lord5, lord7) and facts.aspects(lord7, lord5))
    )
    spouse += (
        " Your chart links romance with marriage, so a love marriage, or a match you choose "
        "yourself, is quite likely."
        if love and lord5 is not lord7
        else " A match introduced or arranged through family is the more likely path, with "
        "your own choice counting too."
    )
    harsh = [b for b in facts.occupants(7) if b in HARSH]
    gentle = [b for b in facts.occupants(7) if b in GENTLE]
    if facts.debilitated(lord7) or facts.debilitated(Body.VENUS) or (harsh and not gentle):
        life = (
            "Married life asks for give-and-take: talk things through early and give each other "
            "space, and the bond grows stronger with time."
        )
    elif gentle or facts.dignified(lord7):
        life = (
            "Married life is likely to be warm and stable, with a partner who supports your growth."
        )
    else:
        life = (
            "Married life does best with patience and open talk; small disagreements pass "
            "quickly when handled calmly."
        )
    status, _ = r.manglik()
    if status == "Yes":
        life += (
            f" You are Manglik, counted from {join(r.manglik_from())}, which is traditionally "
            "checked when matching charts; see the Manglik note under 'Doshas and remedies'."
        )
    elif status == "Cancelled":
        life += " A Manglik placement is present but cancelled, so it is not counted."
    paragraphs = [" ".join(first), spouse, life]
    timing = marriage_timing(r)
    if timing:
        paragraphs.append(timing)
    tone: Tone = r.level_tone(level)
    return ReadingSectionOut(
        key="marriage",
        title="Marriage and spouse",
        paragraphs=paragraphs,
        tone=tone,
        basis=[
            f"marriage promise {r.promise(Domain.MARRIAGE):.2f}; seventh {sign7.name.title()}",
            f"seventh lord {lord7.value} in house {h7}; darakaraka {dara.value if dara else '-'}",
        ],
    )


def marriage_timing(r: Reader) -> str:
    """Marriage timing for the life the person has, from the reading's own windows (the
    same ones the checks, the years ahead and the windows list name): for someone
    married, the wedding against the chart and married life ahead; for someone single,
    the windows passed and the next one; when nobody has said, both readings."""
    past = r.main_windows(Domain.MARRIAGE, past=True)[:2]
    were = join([r.when(e) for e in past])
    ahead = r.main_windows(Domain.MARRIAGE, past=False)
    first = ahead[0] if ahead else None
    top = max(ahead, key=lambda e: e.score) if ahead else None
    later = f", and the strongest ahead is {r.when(top)}" if top is not first and top else ""
    parts: list[str] = []
    if r.married:
        check = r.wedding_check()
        if check is not None:
            parts.append(check.text)
        elif past:
            main = "main window" if len(past) == 1 else "main windows"
            parts.append(
                f"The chart's {main} for marriage {'was' if len(past) == 1 else 'were'} {were}; "
                f"if you married {'then' if len(past) == 1 else 'in one of them'}, the "
                "chart's timing fits your life."
            )
        if first is not None:
            parts.append(
                f"Ahead, {r.when(first)} brings warmth to married life."
                if first.tone == "good"
                else f"Ahead, {r.when(first)} brings shared plans and changes in married life."
            )
        return " ".join(parts)
    if r.single:
        if past:
            parts.append(
                f"{'An earlier window' if len(past) == 1 else 'Earlier windows'} for marriage, "
                f"{were}, {'has' if len(past) == 1 else 'have'} passed; a chart shows when the "
                "door is open, and choices and circumstances decide the rest."
            )
        if first is not None:
            parts.append(f"The next strong window for marriage is {r.when(first)}{later}.")
        return " ".join(parts)
    if past:
        main = "main window" if len(past) == 1 else "main windows"
        parts.append(
            f"The chart's {main} for marriage so far {'was' if len(past) == 1 else 'were'} "
            f"{were}. If you are married, compare {'it' if len(past) == 1 else 'them'} with "
            "your wedding date: a close match suggests the birth time is right."
        )
    if first is not None:
        if r.marriage_age(max(first.start, r.today)) >= 36:
            what = (
                "warmth to married life"
                if first.tone == "good"
                else "shared plans and changes in married life"
            )
            parts.append(
                f"Ahead, {r.when(first)} brings {what}, or a real opening for partnership if "
                "you are single."
            )
        elif past or r.age >= 24:
            parts.append(
                f"If you are not married yet, the next strong window is {r.when(first)}{later}."
            )
        else:
            parts.append(f"The next strong window for marriage is {r.when(first)}{later}.")
    return " ".join(parts)


# -- remedies -------------------------------------------------------------------------------


def _practices(body: Body) -> list[str]:
    return [
        f"Chant {lore.MANTRA[body]} 108 times, ideally on {lore.DAY[body]}s.",
        f"{cap(lore.WORSHIP[body])}.",
        f"Give {lore.DONATE[body]} on {lore.DAY[body]}s.",
        f"{cap(lore.CONDUCT[body])}.",
    ]


def _weakness(r: Reader, body: Body) -> str | None:
    facts = r.facts
    if facts.debilitated(body):
        return "in its weakest sign"
    if body in SEVEN and body is not Body.SUN and facts.combust(body):
        return "too close to the Sun"
    if r.tone_value(body) <= -0.3:
        return "under strain"
    return None


def remedies(r: Reader) -> list[RemedyOut]:
    """Traditional remedies chosen for this chart: the running period, weak planets,
    doshas, the weakest life area, gemstones and daily practice."""
    facts = r.facts
    out: list[RemedyOut] = []
    covered: set[Body] = set()
    md = r.dashas.at(r.today, 1).lords[0]
    ad = r.dashas.at(r.today, 2).lords[-1]
    lords = [md] if ad is md else [md, ad]
    out.append(
        RemedyOut(
            key="period",
            title=f"For the running {'–'.join(_planet(b) for b in lords)} period",
            reason=(
                f"Your current period is ruled by {join([_the(b) for b in lords])}; "
                f"strengthening {'it' if len(lords) == 1 else 'them'} supports "
                f"{join([lore.STRENGTHENS[b] for b in lords])}."
                + (
                    " For a child, parents traditionally follow these practices on the "
                    "child's behalf."
                    if r.minor
                    else ""
                )
            ),
            practices=[p for b in lords for p in _practices(b)[:3]] + [cap(lore.CONDUCT[md]) + "."],
            planets=lords,
        )
    )
    covered.update(lords)
    order = list(
        dict.fromkeys(
            [
                facts.lord(1),
                Body.MOON,
                Body.SUN,
                facts.lord(10),
                facts.lord(7),
                facts.lord(9),
                facts.lord(5),
                *SEVEN,
            ]
        )
    )
    weak = [(b, why) for b in order if b not in covered and (why := _weakness(r, b))]
    for body, why in weak[:2]:
        governs = join(
            list(dict.fromkeys(r.area(h, max(r.age, 25)) for h in r.houses_of(body)[:2]))
        )
        out.append(
            RemedyOut(
                key=f"planet-{body.value}",
                title=f"To strengthen {_the(body)}",
                reason=(
                    f"{cap(_the(body))} is {why} in your chart, and it looks after {governs}. "
                    f"Strengthening it supports {lore.STRENGTHENS[body]}."
                ),
                practices=_practices(body),
                planets=[body],
            )
        )
        covered.add(body)
    running = r.sade_sati_now()
    soon = [e for e in r.sade_sati if 0 <= (r.day(e.start_jd_ut) - r.today).days <= 730]
    if running or soon:
        when = (
            f"Sade Sati is running until {month(r.day(running[0].end_jd_ut))}"
            if running
            else f"Sade Sati begins in {month(r.day(soon[0].start_jd_ut))}"
        )
        out.append(
            RemedyOut(
                key="sade-sati",
                title="For Sade Sati",
                reason=(
                    f"{when}; these practices are traditionally followed to ease Saturn's pressure."
                ),
                practices=[
                    "Recite the Hanuman Chalisa on Tuesdays and Saturdays.",
                    "Chant Om Sham Shanaischaraya Namah 108 times on Saturdays.",
                    "Give mustard oil, black sesame or warm clothes to people in need on "
                    "Saturdays.",
                    "Serve elders and working people, and avoid shortcuts in money matters.",
                ],
                planets=[Body.SATURN],
            )
        )
    present = {y.id for y in r.yogas.present}
    if not r.minor and r.manglik()[0] == "Yes":
        out.append(
            RemedyOut(
                key="mangal-dosha",
                title="For Mangal dosha",
                reason="Mars sits in a Manglik position; these are the traditional remedies.",
                practices=[
                    "Recite the Hanuman Chalisa on Tuesdays.",
                    "Chant Om Angarakaya Namah 108 times on Tuesdays.",
                    "Give red lentils or jaggery on Tuesdays.",
                    "When matching charts for marriage, a partner with a similar placement "
                    "balances the dosha.",
                ],
                planets=[Body.MARS],
            )
        )
    if any(i.startswith("dosha.kala_sarpa") for i in present):
        out.append(
            RemedyOut(
                key="kala-sarpa",
                title="For Kala Sarpa",
                reason=(
                    "A modern pattern of Rahu and Ketu; these practices are commonly "
                    "followed for it."
                ),
                practices=[
                    "Pray to Lord Shiva with Om Namah Shivaya, especially on Mondays.",
                    f"Chant {lore.MANTRA[Body.RAHU]} and {lore.MANTRA[Body.KETU]} 108 times on "
                    "Saturdays.",
                    "Feed birds and help people in need.",
                ],
                planets=[Body.RAHU, Body.KETU],
            )
        )
    if "dosha.pitru" in present:
        out.append(
            RemedyOut(
                key="pitru-dosha",
                title="For Pitru dosha",
                reason="The chart shows the traditional sign of debts to the ancestors.",
                practices=[
                    "Offer water and food in memory of your ancestors on Amavasya, the "
                    "new-moon day.",
                    "Observe shraddha during Pitru Paksha.",
                    "Feed people in need, cows or crows in your ancestors' name.",
                ],
                planets=[Body.SUN],
            )
        )
    _, weak_area = _ranked_areas(r)
    if weak_area is not None and weak_area in AREA_PLANETS:
        planets = [b for b in AREA_PLANETS[weak_area] if b not in covered]
        if weak_area is Domain.MARRIAGE and r.female and Body.JUPITER not in covered:
            planets.append(Body.JUPITER)
        if planets:
            out.append(
                RemedyOut(
                    key=f"area-{weak_area.value}",
                    title=f"For {words.AREA_NAMES[weak_area]}",
                    reason=(
                        "This is the area of life that asks most of you; "
                        f"{join([_the(b) for b in planets])} "
                        f"{'governs' if len(planets) == 1 else 'govern'} it, so these practices "
                        "strengthen it."
                    ),
                    practices=[p for b in planets for p in _practices(b)[:2]],
                    planets=planets,
                )
            )
            covered.update(planets)
    out.append(_gemstones(r))
    ruler = facts.lord(1)
    out.append(
        RemedyOut(
            key="daily",
            title="Every day, for a better life",
            reason=(
                f"Simple habits that steady any chart, with one for {_the(ruler)}, the ruler "
                "of your rising sign."
            ),
            practices=[*lore.DAILY_PRACTICES, cap(lore.CONDUCT[ruler]) + "."],
            planets=[ruler],
        )
    )
    return out


def _gemstones(r: Reader) -> RemedyOut:
    facts = r.facts
    difficult = {facts.lord(h) for h in (6, 8, 12)}
    stones = [(facts.lord(1), "life stone", "the ruler of your rising sign")]
    for house, label, role in (
        (5, "lucky stone", "the ruler of your house of intelligence"),
        (9, "fortune stone", "the ruler of your house of luck"),
    ):
        lord = facts.lord(house)
        if lord not in difficult and lord not in (s[0] for s in stones):
            stones.append((lord, label, role))
    practices = [
        f"{cap(label)}: {lore.GEMSTONE[body]}, for {_the(body)}, {role}."
        for body, label, role in stones
        if body in lore.GEMSTONE
    ]
    practices.append(
        "Wear a stone only after an experienced astrologer has checked your chart and the "
        "stone; a stone never replaces effort or professional advice."
    )
    return RemedyOut(
        key="gemstones",
        title="Gemstones",
        reason="Traditional stones for the planets that work in your favour.",
        practices=practices,
        planets=[s[0] for s in stones],
    )
