"""Reports and grounded chat: narrate the evidence, then check before anything is shown."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from datetime import date, timedelta
from typing import Any, Literal

from pydantic import BaseModel, Field

from jyotish_api.narrative.evidence import EvidenceBundle, EvidenceItem
from jyotish_api.narrative.narrators import (
    MAX_TOKENS,
    ClaudeNarrator,
    NarrativeRefusedError,
    Narrator,
    final_text,
)
from jyotish_api.narrative.report import BANNED, NarrativeOut, check, cited
from jyotish_api.narrative.tools import LOOKUP_TOOLS, resolve_id, run_tool
from jyotish_engine.ask import ChartLookup
from jyotish_engine.ask.lookup import (
    AreaFacts,
    YearFacts,
    areas_in,
    ordinal,
    planets_in,
)
from jyotish_engine.models import ChartResult, MaritalInput, MaritalStatus
from jyotish_engine.rules.schema import Domain


class NarrativeRejectedError(RuntimeError):
    """The narrator's output failed the checks (unknown evidence or banned claims)."""


def write_report(
    bundle: EvidenceBundle, narrator: Narrator, language: str = "en", retries: int = 1
) -> NarrativeOut:
    """A checked report: every cited ID is in the bundle and no banned claim appears."""
    problems: list[str] = []
    for _ in range(retries + 1):
        report, usage = narrator.write(bundle, language)
        problems = check(report, bundle)
        if not problems:
            used = language if narrator.name != "template" else "en"
            return NarrativeOut(
                report=report,
                evidence=cited(report, bundle),
                narrator=narrator.name,
                language=used,
                usage=usage,
            )
    raise NarrativeRejectedError("; ".join(problems))


# --- Chat -----------------------------------------------------------------------------


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatOut(BaseModel):
    answer: str
    evidence: list[EvidenceItem]
    narrator: str


ChatLanguage = Literal["auto", "en", "hi"]
LANGUAGE_LINES = {
    "auto": "Reply in the language and script of each question.",
    "en": "Reply in English.",
    "hi": "Reply in Hindi, in Devanagari script.",
}
CLOSING = "These are traditional indications from the chart, not certainties."
DECLINE = (
    "The chart is not used here to time death, lifespan, accidents or illness. "
    "What it shows about well-being is a set of tendencies, and a doctor is the right "
    "person for any health concern."
)

# --- Offline answers: the facts the question names, without a language model ---------

DOMAIN_WORDS = {
    "career": ("career", "job", "work", "promotion", "business", "profession", "naukri"),
    "marriage": ("marriage", "marry", "spouse", "wife", "husband", "partner", "wedding", "shaadi"),
    "children": ("child", "children", "son", "daughter", "baby", "pregnan"),
    "wealth": ("money", "wealth", "income", "finance", "savings", "rich", "dhan"),
    "property": ("house", "home", "property", "land", "vehicle", "car"),
    "education": ("study", "studies", "education", "exam", "degree", "college", "school"),
    "parents": ("father", "mother", "parent"),
    "spirituality": ("spiritual", "meditation", "religion", "moksha", "god"),
    "health": ("health", "illness", "disease", "sick"),
    "travel": ("travel", "abroad", "foreign", "visa", "relocat", "settle"),
}
NOW_WORDS = ("now", "current", "present", "this year", "these days", "running")
YEAR_WORD = re.compile(r"\b(19\d\d|20\d\d|21\d\d)\b")
HOUSE_WORD = re.compile(
    r"\b(1[0-2]|[1-9])(?:st|nd|rd|th)?\s+(?:house|bhava)\b|\bhouse\s+(1[0-2]|[1-9])\b"
    r"|(1[0-2]|[1-9])\s*(?:वां|वें|वाँ)?\s*(?:भाव|घर)",
    re.IGNORECASE,
)
HOUSE_ORDINALS = (
    "first", "second", "third", "fourth", "fifth", "sixth",
    "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth",
)  # fmt: skip
ORDINAL_HOUSE = re.compile(rf"\b({'|'.join(HOUSE_ORDINALS)})\s+(?:house|bhava)\b", re.IGNORECASE)
#: Hindi ordinals ("सातवाँ भाव", "दसवें घर"), by their stems.
HINDI_ORDINALS = (
    "पहल", "दूसर", "तीसर", "चौथ", "पा[ंँ]चव", "छठ",
    "सातव", "आठव", "नौव", "दसव", "ग्यारहव", "बारहव",
)  # fmt: skip
HINDI_HOUSE = re.compile(rf"({'|'.join(HINDI_ORDINALS)})\S*\s*(?:भाव|घर)")
#: "Next year" and "this year", in English, Hinglish and Hindi: years from today.
RELATIVE_YEARS = (
    (re.compile(r"\bnext\s+year\b|\bagle\s+(?:saal|sal|varsh)\b|अगल[ाे]\s+(?:साल|वर्ष)", re.I), 1),
    (re.compile(r"\bthis\s+year\b|\bis\s+(?:saal|sal|varsh)\b|इस\s+(?:साल|वर्ष)", re.I), 0),
)
SENSITIVE_WORD = re.compile(
    r"\b(?:die|dies|death|dying|lifespan|life\s+span|longevity|accidents?)\b|मृत्यु|मौत",
    re.IGNORECASE,
)
#: An offline answer covers at most this many years, houses, planets or areas.
OFFLINE_LIMIT = 2
#: Areas read only from adulthood (the life reading's age rule).
ADULT_ONLY = {Domain.MARRIAGE, Domain.CHILDREN}


def _day(d: date) -> str:
    return f"{d.day} {d:%b %Y}"


def _span(start: date, end: date) -> str:
    last = end - timedelta(days=1)
    return (
        f"{start:%b %Y}"
        if (start.year, start.month) == (last.year, last.month)
        else (f"{start:%b %Y} to {last:%b %Y}")
    )


def _houses_in(question: str) -> list[int]:
    found = [int(next(g for g in m.groups() if g)) for m in HOUSE_WORD.finditer(question)]
    found += [
        HOUSE_ORDINALS.index(m.group(1).lower()) + 1 for m in ORDINAL_HOUSE.finditer(question)
    ]
    found += [
        next(i for i, stem in enumerate(HINDI_ORDINALS, 1) if re.match(stem, m.group(1)))
        for m in HINDI_HOUSE.finditer(question)
    ]
    return list(dict.fromkeys(found))


def _years_in(question: str, today: date) -> list[int]:
    found = [int(y) for y in YEAR_WORD.findall(question)]
    found += [today.year + ahead for pattern, ahead in RELATIVE_YEARS if pattern.search(question)]
    return list(dict.fromkeys(found))[:OFFLINE_LIMIT]


def _year_lines(facts: YearFacts) -> list[str]:
    lines = [f"{facts.year}: you turn {facts.turns} on your birthday."]
    if facts.annual:
        a = facts.annual
        lines.append(
            f"The annual chart from {_day(a.start)} puts Muntha in the {ordinal(a.muntha_house)} "
            f"house ({a.tone}: {a.meaning}); the lord of the year is {a.year_lord}."
        )
    main = [p for p in facts.periods if len(p.lords) == 2]
    if main:
        lines.append(
            "Periods: "
            + "; ".join(f"{'–'.join(p.lords)} from {_day(p.start)} to {_day(p.end)}" for p in main)
            + "."
        )
    for planet in ("Saturn", "Jupiter"):
        stays = [t for t in facts.transits if t.planet == planet]
        if stays:
            lines.append(
                f"{planet}: "
                + "; then ".join(
                    f"{t.sign} until {_day(t.end)} ({ordinal(t.house_from_moon)} from your Moon"
                    + (f", {t.note}" if t.note and "Sade Sati" in t.note else "")
                    + ")"
                    for t in stays
                )
                + "."
            )
    windows = [
        f"{area} ({_span(w.start, w.end)}, {w.tone})"
        for area, found in facts.windows.items()
        for w in found
    ]
    lines.append(
        "Areas emphasised: " + "; ".join(windows) + "." if windows else "No area stands out."
    )
    return lines


def _area_lines(facts: AreaFacts, today: date) -> list[str]:
    reasons = " and ".join(r.rsplit(" (", 1)[0] for r in facts.promise_reasons[:2])
    lines = [
        f"{facts.area.title()}: the birth chart's promise is {facts.promise:.2f} "
        f"(0.5 is average), mainly from {reasons}."
    ]
    if facts.note:
        return [*lines, facts.note]
    horizon = date(today.year + 10, today.month, 1)
    coming = [w for w in facts.windows if w.end > today and w.start < horizon][:3]
    if not coming:
        return [*lines, "No window of emphasis in the next ten years."]
    return [
        *lines,
        "Coming windows: "
        + "; ".join(
            f"{_span(w.start, w.end)} ({'running now, ' if w.start <= today else ''}"
            f"{w.tone}, {w.agreement} agreement, {'–'.join(w.periods.split(' / '))} period)"
            for w in coming
        )
        + ".",
    ]


def _marriage_lines(
    facts: AreaFacts, lookup: ChartLookup, marital: MaritalInput | None
) -> list[str]:
    """Marriage for the life the person has: the windows already passed (from 21) as
    well as the coming ones, read by what they said about being married."""
    status = marital.status if marital else MaritalStatus.UNKNOWN
    head, *rest = _area_lines(facts, lookup.today)
    adult = date(lookup.born.year + 21, lookup.born.month, 1)
    past = [w for w in facts.windows if w.end <= lookup.today and w.start >= adult][-3:]
    lines = [head]
    if past:
        lines.append(
            "Past windows from age 21: "
            + "; ".join(f"{_span(w.start, w.end)} ({w.tone})" for w in past)
            + "."
        )
    if status is MaritalStatus.MARRIED:
        year = marital.wedding_year if marital else None
        wedding = f" (wedding in {year})" if year else ""
        lines.append(
            f"You said you are married{wedding}: compare the wedding with the past windows; "
            "the coming windows are read as times for married life."
        )
    elif status is MaritalStatus.SINGLE:
        lines.append("You said you are not married, so the coming windows are the ones to watch.")
    elif past:
        lines.append(
            "If you are already married, compare your wedding date with the past windows; if "
            "not, the coming windows are the ones to watch."
        )
    return [*lines, *rest]


def _retrieve(bundle: EvidenceBundle, question: str) -> ChatOut:
    """Retrieval from the bundle alone: the evidence on the areas the question names."""
    q = question.lower()
    domains = [d for d, words in DOMAIN_WORDS.items() if any(w in q for w in words)]
    items = [
        i
        for i in bundle.items
        if i.kind in ("promise", "window") and any(d in i.domains for d in domains)
    ]
    if not domains or any(w in q for w in NOW_WORDS):
        items = [i for i in bundle.items if i.id == "now:dasha"] + items
    if not items:
        items = [i for i in bundle.items if i.kind == "promise"][:3]
    lines = [f"{i.title}{f' ({i.period})' if i.period else ''}: {i.text}" for i in items[:8]]
    return ChatOut(answer="\n".join([*lines, CLOSING]), evidence=items[:8], narrator="template")


def answer_offline(
    bundle: EvidenceBundle,
    question: str,
    lookup: ChartLookup | None = None,
    marital: MaritalInput | None = None,
) -> ChatOut:
    """An answer without a language model: the engine's facts on the years, houses,
    planets and life areas the question names, in short sentences (English)."""
    if lookup is None:
        return _retrieve(bundle, question)
    if SENSITIVE_WORD.search(question):
        health = lookup.area(Domain.HEALTH)
        item, _ = run_tool(lookup, "life_area", {"area": "health"})
        return ChatOut(
            answer="\n".join([DECLINE, *_area_lines(health, lookup.today), CLOSING]),
            evidence=[item],
            narrator="template",
        )
    lines: list[str] = []
    items: list[EvidenceItem] = []
    years = _years_in(question, lookup.today)
    for year in years:
        try:
            item, _ = run_tool(lookup, "year", {"year": year})
        except ValueError as error:
            lines.append(f"{year}: {error}.")
            continue
        items.append(item)
        lines += _year_lines(lookup.year(year))
    for number in _houses_in(question)[:OFFLINE_LIMIT]:
        item, _ = run_tool(lookup, "house", {"number": number})
        items.append(item)
        lines.append(item.text)
    for body in planets_in(question)[:OFFLINE_LIMIT]:
        item, _ = run_tool(lookup, "planet", {"name": body.value})
        items.append(item)
        lines.append(item.text)
    if not years:
        minor = lookup.age(lookup.today) < 18
        for domain in [d for d in areas_in(question) if d.value in DOMAIN_WORDS][:OFFLINE_LIMIT]:
            if minor and domain in ADULT_ONLY:
                lines.append(
                    f"{domain.value.title()} is read from adulthood; for now the chart speaks "
                    "about studies, talents, good habits and family."
                )
                continue
            item, _ = run_tool(lookup, "life_area", {"area": domain.value})
            items.append(item)
            facts = lookup.area(domain)
            lines += (
                _marriage_lines(facts, lookup, marital)
                if domain is Domain.MARRIAGE
                else _area_lines(facts, lookup.today)
            )
    if not lines:
        return _retrieve(bundle, question)
    return ChatOut(answer="\n".join([*lines, CLOSING]), evidence=items, narrator="template")


# --- Chat with Claude: lookups as tools, the answer as checked structured output -------

CHAT_SYSTEM = """\
You are the Jyotish Platform's astrologer. You answer one person's questions about their
own Vedic (Jyotish) birth chart, warmly, plainly and personally, as a good astrologer does
in a consultation.

Facts. Never calculate or invent anything. Everything rests on the evidence in the first
message (each item has an id) and on the lookup tools, which return the engine's own
results: planet, house, period_at, periods, transits, life_area and year. Call a tool
whenever a question names a date, a year, a planet, a house or a life area that the
evidence does not already cover; call several at once when a question needs them.

Answer. Lead with the direct answer, then the reasons in plain words: which period or
transit, which house and which planet. Give timing in months and years. Usually 80 to 200
words, in plain paragraphs or a short list with "- ". Explain any Sanskrit term in a few
words. Follow the language line in the first message.

Care. Speak of tendencies and of supportive or testing times, never of certainties. Never
say when anyone will die, how long anyone will live, or when accidents or illnesses will
come, and never diagnose; on health give only the traditional tendencies and suggest a
doctor. No medical, legal or financial directives, no guarantees, no fear and no costly
remedies. If the person is under 18, keep to studies, talents, habits and family: nothing
about marriage, romance or children. If asked how accurate this is, say plainly that the
calculations are exact, but the timing rules are traditional and have not beaten chance in
controlled tests.

Marriage. Never assume whether the person is married: the first message says what they
told us. When it is not known and they ask when they will marry, give the chart's main
window already passed (life_area lists windows across the whole life) as well as the next
one, saying which applies if they are already married, or ask them. For someone married,
read later marriage windows as times for married life, and when they give their wedding
date, compare it with the windows.

Reply in the requested JSON format: "answer" is the text the person reads, and
"evidence_ids" lists the id of every evidence item and lookup result (each lookup returns
an evidence_id) the answer rests on.
"""


class ChatAnswer(BaseModel):
    answer: str
    evidence_ids: list[str]


ANSWER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "evidence_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["answer", "evidence_ids"],
    "additionalProperties": False,
}


def _marital_line(marital: MaritalInput | None) -> str:
    status = marital.status if marital else MaritalStatus.UNKNOWN
    if status is MaritalStatus.MARRIED:
        assert marital is not None
        if marital.wedding_year is None:
            return "They say they are married; the wedding date was not given."
        month = f"{marital.wedding_month:02d}-" if marital.wedding_month else ""
        return f"They say they are married; the wedding was in {month}{marital.wedding_year}."
    if status is MaritalStatus.SINGLE:
        return "They say they are not married."
    return "Whether they are married is not known."


def render_chat(
    bundle: EvidenceBundle,
    lookup: ChartLookup,
    name: str | None,
    language: ChatLanguage,
    marital: MaritalInput | None = None,
) -> str:
    """The first message of every chat: whose chart, the language, then the evidence."""
    who = f"{' '.join(name.split())}, " if name and name.strip() else ""
    lines = [
        f"Questions about one birth chart: {bundle.subject}.",
        f"The person asking ({who}age {lookup.age(bundle.today)}) owns this chart. "
        f"Today is {bundle.today.isoformat()}.",
        _marital_line(marital),
        LANGUAGE_LINES[language],
        "Evidence, one JSON object per line:",
    ]
    lines += [item.model_dump_json(exclude_defaults=True) for item in bundle.items]
    return "\n".join(lines)


def _tool_result(
    lookup: ChartLookup, call: dict[str, Any], known: dict[str, EvidenceItem]
) -> dict[str, Any]:
    try:
        item, data = run_tool(lookup, str(call.get("name")), dict(call.get("input") or {}))
    except (LookupError, ValueError, KeyError, TypeError) as error:
        return {
            "type": "tool_result",
            "tool_use_id": call["id"],
            "content": f"Error: {error}",
            "is_error": True,
        }
    known[item.id] = item
    return {"type": "tool_result", "tool_use_id": call["id"], "content": json.dumps(data)}


def _problems(
    reply: dict[str, Any], lookup: ChartLookup, known: dict[str, EvidenceItem]
) -> tuple[ChatAnswer | None, list[EvidenceItem], list[str]]:
    """The parsed answer, the evidence it cites, and what keeps it from being shown."""
    text = final_text(reply)
    try:
        answer = ChatAnswer.model_validate_json(text or "")
    except ValueError:
        return None, [], ["the reply was not the requested JSON"]
    cited: list[EvidenceItem] = []
    unknown: list[str] = []
    for item_id in dict.fromkeys(answer.evidence_ids):
        item = known.get(item_id) or resolve_id(lookup, item_id)
        if item is None:
            unknown.append(item_id)
        else:
            known[item_id] = item
            cited.append(item)
    problems = [f"unknown evidence ids {unknown}"] if unknown else []
    problems += [] if cited else ["no evidence cited"]
    problems += [
        f"{reason}: {m.group(0)!r}" for p, reason in BANNED if (m := p.search(answer.answer))
    ]
    return answer, cited, problems


def chat_with_claude(
    narrator: ClaudeNarrator,
    chart: ChartResult,
    bundle: EvidenceBundle,
    messages: Sequence[ChatMessage],
    *,
    lookup: ChartLookup | None = None,
    name: str | None = None,
    language: ChatLanguage = "auto",
    marital: MaritalInput | None = None,
    max_rounds: int = 6,
) -> ChatOut:
    """Tool-grounded chat: the model looks things up in the engine, then answers in a
    fixed JSON shape; an answer citing unknown evidence or making a banned claim is sent
    back for another try instead of being shown."""
    lookup = lookup or ChartLookup(chart, today=bundle.today)
    known = {i.id: i for i in bundle.items}
    history: list[dict[str, Any]] = [
        {"role": "user", "content": render_chat(bundle, lookup, name, language, marital)}
    ]
    history += [{"role": m.role, "content": m.content} for m in messages]
    for _ in range(max_rounds):
        reply = narrator.transport(
            {
                "model": narrator.name,
                "max_tokens": MAX_TOKENS,
                "system": [{"type": "text", "text": CHAT_SYSTEM}],
                "messages": history,
                "tools": LOOKUP_TOOLS,
                "output_config": {
                    "effort": narrator.effort,
                    "format": {"type": "json_schema", "schema": ANSWER_SCHEMA},
                },
                # Cache the growing prefix: the evidence and the conversation so far.
                "cache_control": {"type": "ephemeral"},
            }
        )
        if reply.get("stop_reason") == "refusal":
            raise NarrativeRefusedError("the model declined to answer")
        content = reply.get("content", [])
        history.append({"role": "assistant", "content": content})
        calls = [b for b in content if b.get("type") == "tool_use"]
        if calls:
            history.append(
                {"role": "user", "content": [_tool_result(lookup, c, known) for c in calls]}
            )
            continue
        answer, evidence, problems = _problems(reply, lookup, known)
        if answer is not None and not problems:
            return ChatOut(answer=answer.answer, evidence=evidence, narrator=narrator.name)
        history.append(
            {
                "role": "user",
                "content": "That answer cannot be shown: "
                + "; ".join(problems)
                + ". Answer again within the rules, citing only ids from the evidence "
                "or from lookups.",
            }
        )
    raise NarrativeRejectedError("the model gave no acceptable answer within the allowed rounds")
