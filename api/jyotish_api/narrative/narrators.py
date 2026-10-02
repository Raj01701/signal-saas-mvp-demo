"""Narrators turn an evidence bundle into a report: offline templates, or Claude.

``TemplateNarrator`` needs no network and costs nothing; it is the default. The
``ClaudeNarrator`` is used only when an Anthropic API key is configured. It calls the
Messages API through the official SDK with a cached system prompt and asks for the
``Report`` schema as structured output, so the reply always parses as a report (the
current models do not accept forced tool calls). Both go through the same checks.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from functools import lru_cache
from typing import Any, Protocol

import anthropic
from pydantic import BaseModel, ValidationError

from jyotish_api.narrative.evidence import EvidenceBundle, EvidenceItem
from jyotish_api.narrative.report import Paragraph, Report, Section

#: Send one Messages API request (the arguments of ``messages.create``) and return the
#: reply as a plain dict; injectable for tests.
Transport = Callable[[dict[str, Any]], dict[str, Any]]
#: Server-side refusal fallback: a declined request is re-run, inside the same call, on
#: a model the API chooses by the refusal's category.
FALLBACK_BETA = "server-side-fallback-2026-07-01"
#: Thinking and the answer share this budget; readings and chat answers are short.
MAX_TOKENS = 16000
#: Schema keywords structured outputs do not accept (checked here by pydantic instead).
UNSUPPORTED_KEYWORDS = {"minLength", "maxLength", "minItems", "maxItems", "minimum", "maximum"}

SYSTEM_PROMPT = """\
You write Vedic astrology (Jyotish) readings for the Jyotish Platform.

You never calculate anything. The user message holds an evidence bundle computed by
the engine; every item has an id. Write only what the evidence supports, in plain,
warm and careful language, and cite the ids behind every paragraph in its
evidence_ids. Use only ids from the bundle.

Rules:
- Present traditional interpretations, never certainties: say "tends to", "the
  tradition associates", "a period that favours".
- Never give dates or timing of death, lifespan, or anything about longevity.
- Never give medical, legal or financial directives; for health, speak only of
  tendencies and suggest consulting a doctor.
- Never promise outcomes ("guaranteed", "100%", "will definitely").
- Never use fear to sell remedies; do not tell the reader they must buy or perform
  anything.
- Keep Sanskrit terms, explained briefly the first time (for example "dasha, a
  planetary period").
Reply with the report in the requested JSON format.
"""


class NarrativeRefusedError(RuntimeError):
    """The language model declined to write the report."""


class Narrator(Protocol):
    name: str

    def write(
        self, bundle: EvidenceBundle, language: str
    ) -> tuple[Report, dict[str, int] | None]: ...


def _by(items: Iterable[EvidenceItem], kind: str) -> list[EvidenceItem]:
    return [i for i in items if i.kind == kind]


def _paragraph(items: list[EvidenceItem], lead: str = "") -> Paragraph:
    text = " ".join(f"{i.title}: {i.text}" for i in items)
    return Paragraph(text=f"{lead}{text}", evidence_ids=[i.id for i in items])


class TemplateNarrator:
    """A deterministic report assembled from the evidence texts (English)."""

    name = "template"

    def write(self, bundle: EvidenceBundle, language: str) -> tuple[Report, dict[str, int] | None]:
        items = bundle.items
        sections: list[Section] = []
        readings = _by(items, "reading")
        first = [i for i in readings if i.id.startswith(("rule:lagna.", "rule:nakshatra."))]
        if first:
            sections.append(Section(heading="Temperament", paragraphs=[_paragraph(first)]))
        promises = sorted(_by(items, "promise"), key=lambda i: i.text)
        strong = [p for p in promises if p.polarity == "positive"]
        weak = [p for p in promises if p.polarity == "negative"]
        overview = [_paragraph(strong, "Areas the birth chart supports well. ")] if strong else []
        overview += [_paragraph(weak, "Areas that ask for more effort. ")] if weak else []
        if overview:
            sections.append(Section(heading="Strengths of the chart", paragraphs=overview))
        yogas = _by(items, "yoga")
        good = [y for y in yogas if y.polarity == "positive"][:6]
        hard = [y for y in yogas if y.polarity == "negative"][:6]
        combos = [_paragraph([y]) for y in good + hard]
        if combos:
            sections.append(Section(heading="Yogas", paragraphs=combos))
        now = _by(items, "dasha") + _by(items, "transit")[:4]
        if now:
            sections.append(Section(heading="The present period", paragraphs=[_paragraph(now)]))
        windows = sorted(_by(items, "window"), key=lambda w: w.period or "")[:10]
        if windows:
            paragraphs = [
                Paragraph(text=f"{w.period}: {w.title}, {w.text}", evidence_ids=[w.id])
                for w in windows
            ]
            sections.append(Section(heading="The coming years", paragraphs=paragraphs))
        return Report(title=f"Reading: {bundle.subject}", sections=sections), None


@lru_cache(maxsize=4)
def _client(api_key: str) -> anthropic.Anthropic:
    # The SDK retries rate limits, overloads and connection errors itself.
    return anthropic.Anthropic(api_key=api_key, timeout=180.0)


def sdk_transport(api_key: str) -> Transport:
    """Requests through the Anthropic SDK, with server-side refusal fallbacks on."""

    def send(params: dict[str, Any]) -> dict[str, Any]:
        reply = _client(api_key).beta.messages.create(
            **params, betas=[FALLBACK_BETA], fallbacks="default"
        )
        out: dict[str, Any] = reply.to_dict()
        return out

    return send


def strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    """``model``'s JSON schema in the form structured outputs accept: every object closed
    with ``additionalProperties: false`` and no length or range keywords."""

    def fix(node: Any) -> Any:
        if isinstance(node, dict):
            out = {k: fix(v) for k, v in node.items() if k not in UNSUPPORTED_KEYWORDS}
            if out.get("type") == "object":
                out["additionalProperties"] = False
            return out
        if isinstance(node, list):
            return [fix(v) for v in node]
        return node

    schema: dict[str, Any] = fix(model.model_json_schema())
    return schema


def final_text(reply: dict[str, Any]) -> str | None:
    """The last text block of a reply (structured output arrives as one text block)."""
    texts = [b.get("text", "") for b in reply.get("content", []) if b.get("type") == "text"]
    return texts[-1] if texts else None


def usage_of(reply: dict[str, Any]) -> dict[str, int]:
    return {k: v for k, v in reply.get("usage", {}).items() if isinstance(v, int)}


def render_bundle(bundle: EvidenceBundle, language: str) -> str:
    """The user message: the task, then the evidence as JSON lines."""
    lines = [
        f"Write a reading for: {bundle.subject}. Today is {bundle.today.isoformat()}.",
        f"Language: {'Hindi (Devanagari script)' if language == 'hi' else 'English'}.",
        "Sections: temperament, strengths and challenges of the chart, the present period, "
        "and the coming years by area of life.",
        "Evidence:",
    ]
    lines += [item.model_dump_json(exclude_defaults=True) for item in bundle.items]
    return "\n".join(lines)


class ClaudeNarrator:
    """Claude writes the report as structured output in the ``Report`` schema."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-opus-5-5",
        transport: Transport | None = None,
        max_tokens: int = MAX_TOKENS,
        effort: str = "medium",
    ) -> None:
        self.name = model
        self.transport = transport or sdk_transport(api_key)
        self.max_tokens = max_tokens
        #: How hard the model thinks (low, medium, high, xhigh, max).
        self.effort = effort

    def payload(self, bundle: EvidenceBundle, language: str) -> dict[str, Any]:
        return {
            "model": self.name,
            "max_tokens": self.max_tokens,
            "system": [
                {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}
            ],
            "messages": [{"role": "user", "content": render_bundle(bundle, language)}],
            "output_config": {
                "effort": self.effort,
                "format": {"type": "json_schema", "schema": strict_schema(Report)},
            },
        }

    def write(self, bundle: EvidenceBundle, language: str) -> tuple[Report, dict[str, int] | None]:
        reply = self.transport(self.payload(bundle, language))
        if reply.get("stop_reason") == "refusal":
            raise NarrativeRefusedError("the model declined to write this reading")
        text = final_text(reply)
        if text is None:
            raise NarrativeRefusedError("the model did not return a report")
        try:
            report = Report.model_validate_json(text)
        except ValidationError as error:
            raise NarrativeRefusedError(f"the reply was not a valid report: {error}") from error
        return report, usage_of(reply)


def batch_requests(
    narrator: ClaudeNarrator, bundles: dict[str, EvidenceBundle], language: str = "en"
) -> list[dict[str, Any]]:
    """Requests for the Message Batches API (half price), keyed by ``custom_id``."""
    return [
        {"custom_id": key, "params": narrator.payload(bundle, language)}
        for key, bundle in bundles.items()
    ]
