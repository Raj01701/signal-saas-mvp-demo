"""Narrators turn an evidence bundle into a report: offline templates, or Claude.

``TemplateNarrator`` needs no network and costs nothing; it is the default. The
``ClaudeNarrator`` is used only when an Anthropic API key is configured. It sends the
bundle with a cached system prompt and forces the report format through a tool
call, so the reply is always the ``Report`` schema. Both go through the same checks.
"""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable, Iterable
from typing import Any, Protocol

from jyotish_api.narrative.evidence import EvidenceBundle, EvidenceItem
from jyotish_api.narrative.report import Paragraph, Report, Section

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
#: POST a JSON payload with headers and return the JSON reply (injectable for tests).
Transport = Callable[[str, dict[str, str], dict[str, Any]], dict[str, Any]]

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
Reply by calling write_report exactly once.
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


def http_transport(url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    if not url.startswith("https://"):
        raise ValueError("the narrative transport only calls https URLs")
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers=headers, method="POST"
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        reply: dict[str, Any] = json.loads(response.read())
        return reply


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
    """Claude writes the report through a forced ``write_report`` tool call."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-opus-5-5",
        transport: Transport = http_transport,
        max_tokens: int = 6000,
    ) -> None:
        self.api_key = api_key
        self.name = model
        self.transport = transport
        self.max_tokens = max_tokens

    def headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": API_VERSION,
            "content-type": "application/json",
        }

    def payload(self, bundle: EvidenceBundle, language: str) -> dict[str, Any]:
        return {
            "model": self.name,
            "max_tokens": self.max_tokens,
            "system": [
                {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}
            ],
            "messages": [{"role": "user", "content": render_bundle(bundle, language)}],
            "tools": [
                {
                    "name": "write_report",
                    "description": "The reading: sections of paragraphs citing evidence ids.",
                    "input_schema": Report.model_json_schema(),
                }
            ],
            "tool_choice": {"type": "tool", "name": "write_report"},
        }

    def write(self, bundle: EvidenceBundle, language: str) -> tuple[Report, dict[str, int] | None]:
        reply = self.transport(API_URL, self.headers(), self.payload(bundle, language))
        if reply.get("stop_reason") == "refusal":
            raise NarrativeRefusedError("the model declined to write this reading")
        block = next((b for b in reply.get("content", []) if b.get("type") == "tool_use"), None)
        if block is None:
            raise NarrativeRefusedError("the model did not return a report")
        usage = {k: int(v) for k, v in reply.get("usage", {}).items() if isinstance(v, int)}
        return Report.model_validate(block["input"]), usage


def batch_requests(
    narrator: ClaudeNarrator, bundles: dict[str, EvidenceBundle], language: str = "en"
) -> list[dict[str, Any]]:
    """Requests for the Message Batches API (half price), keyed by ``custom_id``."""
    return [
        {"custom_id": key, "params": narrator.payload(bundle, language)}
        for key, bundle in bundles.items()
    ]
