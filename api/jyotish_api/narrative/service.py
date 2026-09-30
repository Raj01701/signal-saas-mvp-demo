"""Reports and grounded chat: narrate the evidence, then check before anything is shown."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, date, datetime
from typing import Any, Literal

from pydantic import BaseModel

from jyotish_api.narrative.evidence import EvidenceBundle, EvidenceItem, _rule_item
from jyotish_api.narrative.narrators import (
    API_URL,
    ClaudeNarrator,
    NarrativeRefusedError,
    Narrator,
    render_bundle,
)
from jyotish_api.narrative.report import BANNED, NarrativeOut, check, cited
from jyotish_engine.models import ChartResult
from jyotish_engine.rules.periods import compute_period_readings


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
    content: str


class ChatOut(BaseModel):
    answer: str
    evidence: list[EvidenceItem]
    narrator: str


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
CLOSING = "These are traditional indications from the chart, not certainties."


def answer_offline(bundle: EvidenceBundle, question: str) -> ChatOut:
    """Retrieval without a language model: the evidence on the areas the question names."""
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


CHAT_SYSTEM = """\
You answer questions about one person's Vedic astrology (Jyotish) chart for the
Jyotish Platform. You never calculate: use the evidence bundle in the first message,
and call period_at to get the running periods and transits for another date. Answer
briefly and carefully, as traditional indications rather than certainties, and cite
the evidence ids you relied on. Never discuss death timing or longevity, never give
medical, legal or financial directives, never promise outcomes, never press remedies.
Finish by calling answer exactly once.
"""


def _chat_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "period_at",
            "description": "Running dasha periods and transit results for a date (YYYY-MM-DD).",
            "input_schema": {
                "type": "object",
                "properties": {"date": {"type": "string", "description": "YYYY-MM-DD"}},
                "required": ["date"],
            },
        },
        {
            "name": "answer",
            "description": "Give the final answer with the ids of the evidence it rests on.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "evidence_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                },
                "required": ["text", "evidence_ids"],
            },
        },
    ]


def _period_items(chart: ChartResult, day: date) -> list[EvidenceItem]:
    moment = datetime(day.year, day.month, day.day, 12, tzinfo=UTC)
    out = compute_period_readings(chart, moment)
    lords = " / ".join(p.lords[-1].value.title() for p in out.dasha)
    head = EvidenceItem(id=f"at:{day}:dasha", kind="dasha", title=f"Periods on {day}", text=lords)
    rules = [_rule_item(r, "dasha", f"at:{day}") for r in out.dasha_readings]
    rules += [_rule_item(r, "transit", f"at:{day}") for r in out.transit_readings]
    return [head, *rules]


def chat_with_claude(
    narrator: ClaudeNarrator,
    chart: ChartResult,
    bundle: EvidenceBundle,
    messages: Sequence[ChatMessage],
    max_rounds: int = 4,
) -> ChatOut:
    """Tool-grounded chat: the model may look up any date; its answer must cite known ids."""
    known = {i.id: i for i in bundle.items}
    history: list[dict[str, Any]] = [
        {"role": "user", "content": render_bundle(bundle, "en")},
        {"role": "assistant", "content": "I have the evidence. What would you like to know?"},
    ]
    history += [{"role": m.role, "content": m.content} for m in messages]
    for _ in range(max_rounds):
        payload = {
            "model": narrator.name,
            "max_tokens": 1500,
            "system": [
                {"type": "text", "text": CHAT_SYSTEM, "cache_control": {"type": "ephemeral"}}
            ],
            "messages": history,
            "tools": _chat_tools(),
            "tool_choice": {"type": "any"},
        }
        reply = narrator.transport(API_URL, narrator.headers(), payload)
        if reply.get("stop_reason") == "refusal":
            raise NarrativeRefusedError("the model declined to answer")
        calls = [b for b in reply.get("content", []) if b.get("type") == "tool_use"]
        final = next((c for c in calls if c["name"] == "answer"), None)
        if final is not None:
            text, ids = final["input"]["text"], final["input"]["evidence_ids"]
            unknown = [i for i in ids if i not in known]
            banned = [reason for pattern, reason in BANNED if pattern.search(text)]
            if unknown or banned:
                raise NarrativeRejectedError(f"unknown evidence {unknown}; banned: {banned}")
            return ChatOut(answer=text, evidence=[known[i] for i in ids], narrator=narrator.name)
        results = []
        for call in calls:
            items = _period_items(chart, date.fromisoformat(call["input"]["date"]))
            known.update({i.id: i for i in items})
            content = json.dumps([i.model_dump(exclude_defaults=True) for i in items])
            results.append({"type": "tool_result", "tool_use_id": call["id"], "content": content})
        history += [
            {"role": "assistant", "content": reply["content"]},
            {"role": "user", "content": results},
        ]
    raise NarrativeRejectedError("the model did not answer within the allowed tool rounds")
