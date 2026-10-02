"""The report format every narrator must produce, and the server-side checks on it."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from jyotish_api.narrative.evidence import EvidenceBundle, EvidenceItem

DISCLAIMER = (
    "This reading describes traditional Jyotish interpretations computed from the birth data. "
    "It is not a prediction of certain outcomes and not medical, legal or financial advice."
)


class Paragraph(BaseModel):
    text: str = Field(min_length=1)
    #: IDs of the evidence items the paragraph rests on.
    evidence_ids: list[str] = Field(min_length=1)


class Section(BaseModel):
    heading: str
    paragraphs: list[Paragraph] = Field(min_length=1)


class Report(BaseModel):
    title: str
    sections: list[Section] = Field(min_length=1)


class NarrativeOut(BaseModel):
    report: Report
    #: The evidence items the report cites.
    evidence: list[EvidenceItem]
    #: "template" (offline) or the language model's id.
    narrator: str
    language: str
    disclaimer: str = DISCLAIMER
    #: Token usage reported by the language model, if one wrote the report.
    usage: dict[str, int] | None = None


#: Claims the product never makes (plan section 8): death timing, medical, legal or
#: financial directives, guaranteed outcomes and fear-based remedy selling.
BANNED: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"\bwill\s+die\b|\bdate\s+of\s+(your\s+)?death\b"
            r"|\bdeath\s+(in|by|around|before)\s+(19|20)\d\d",
            re.I,
        ),
        "death timing",
    ),
    (re.compile(r"\b(life\s*span|longevity)\s+(of|is)\s+\d+", re.I), "death timing"),
    (
        re.compile(
            r"\b(stop|start|change)\s+(taking\s+)?(your\s+)?(medicine|medication|treatment)\b", re.I
        ),
        "medical directive",
    ),
    (
        re.compile(r"\b(will|can|to)\s+cure\b|\bcures?\s+(your|the|any)\s+(disease|illness)", re.I),
        "cure claim",
    ),
    (
        re.compile(
            r"\b(invest|buy|sell)\s+(in\s+)?(shares|stocks|crypto|gold|land|property)\b"
            r"|\bguaranteed\s+returns?\b",
            re.I,
        ),
        "financial directive",
    ),
    (re.compile(r"\byou\s+should\s+(sue|file\s+for\s+divorce|divorce)\b", re.I), "legal directive"),
    (
        re.compile(r"\b100\s*%|\bguarantee[sd]?\b|\b(certainly|definitely|surely)\s+will\b", re.I),
        "guaranteed outcome",
    ),
    (
        re.compile(
            r"\bmust\s+(buy|wear|perform|pay\s+for)\b|\bor\s+else\b|\bbefore\s+it\s+is\s+too\s+late\b",
            re.I,
        ),
        "fear-based remedy selling",
    ),
]


def check(report: Report, bundle: EvidenceBundle) -> list[str]:
    """Problems with a report: evidence IDs outside the bundle, and banned claims."""
    known = bundle.ids()
    problems = []
    for section in report.sections:
        for paragraph in section.paragraphs:
            unknown = [i for i in paragraph.evidence_ids if i not in known]
            if unknown:
                problems.append(f"unknown evidence {unknown} in {section.heading!r}")
            for pattern, reason in BANNED:
                match = pattern.search(paragraph.text)
                if match:
                    problems.append(f"{reason}: {match.group(0)!r} in {section.heading!r}")
    return problems


def cited(report: Report, bundle: EvidenceBundle) -> list[EvidenceItem]:
    ids = [i for s in report.sections for p in s.paragraphs for i in p.evidence_ids]
    seen = list(dict.fromkeys(ids))
    return [item for i in seen if (item := bundle.get(i)) is not None]
