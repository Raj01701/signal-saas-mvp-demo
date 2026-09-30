"""Narratives: evidence IDs checked, banned claims blocked, Claude only through the checks."""

from __future__ import annotations

import importlib
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from jyotish_api.config import ApiSettings
from jyotish_api.main import create_app
from jyotish_api.narrative.evidence import EvidenceBundle, build_bundle
from jyotish_api.narrative.narrators import ClaudeNarrator, NarrativeRefusedError, TemplateNarrator
from jyotish_api.narrative.report import Paragraph, Report, Section, check
from jyotish_api.narrative.service import (
    ChatMessage,
    NarrativeRejectedError,
    answer_offline,
    chat_with_claude,
    write_report,
)
from jyotish_engine.chart import compute_chart
from jyotish_engine.models import BirthInput, ChartResult, PlaceInput

DELHI = {"name": "New Delhi", "latitude": 28.6139, "longitude": 77.2090}
BIRTH = {"local_datetime": "1990-05-17T12:00:00", "place": DELHI}
TODAY = date(2026, 9, 30)


@pytest.fixture(scope="module")
def chart() -> ChartResult:
    return compute_chart(
        BirthInput(local_datetime=datetime(1990, 5, 17, 12), place=PlaceInput(**DELHI))
    )


@pytest.fixture(scope="module")
def bundle(chart: ChartResult) -> EvidenceBundle:
    return build_bundle(chart, today=TODAY)


def test_bundle_has_stable_ids(bundle: EvidenceBundle) -> None:
    ids = [i.id for i in bundle.items]
    assert len(ids) == len(set(ids))
    kinds = {i.kind for i in bundle.items}
    assert {"reading", "yoga", "promise", "window", "dasha", "transit"} <= kinds
    assert "now:dasha" in ids and "promise:career" in ids
    assert not any("longevity" in i.domains for i in bundle.items)


def test_template_report_passes_the_checks(bundle: EvidenceBundle) -> None:
    out = write_report(bundle, TemplateNarrator())
    assert out.narrator == "template" and out.language == "en" and out.disclaimer
    assert {s.heading for s in out.report.sections} >= {
        "Temperament",
        "The present period",
        "The coming years",
    }
    assert {e.id for e in out.evidence} <= bundle.ids()


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("The native will die young.", "death timing"),
        ("Death in 2031 is indicated.", "death timing"),
        ("Stop taking your medication now.", "medical directive"),
        ("This mantra will cure the illness.", "cure claim"),
        ("Invest in shares during this period.", "financial directive"),
        ("You should sue your employer.", "legal directive"),
        ("Marriage is guaranteed this year.", "guaranteed outcome"),
        ("You must buy a blue sapphire.", "fear-based remedy selling"),
    ],
)
def test_banned_claims_are_caught(bundle: EvidenceBundle, text: str, reason: str) -> None:
    report = Report(
        title="t",
        sections=[
            Section(heading="h", paragraphs=[Paragraph(text=text, evidence_ids=["now:dasha"])])
        ],
    )
    assert any(p.startswith(reason) for p in check(report, bundle))


def test_ordinary_words_are_not_banned(bundle: EvidenceBundle) -> None:
    text = "The Moon in Cancer gives a secure home; a period that favours study and steady savings."
    report = Report(
        title="t",
        sections=[
            Section(heading="h", paragraphs=[Paragraph(text=text, evidence_ids=["now:dasha"])])
        ],
    )
    assert check(report, bundle) == []


def _tool_reply(name: str, data: dict[str, Any], call: str = "call-1") -> dict[str, Any]:
    return {
        "stop_reason": "tool_use",
        "content": [{"type": "tool_use", "id": call, "name": name, "input": data}],
        "usage": {"input_tokens": 1000, "output_tokens": 200},
    }


def test_claude_report_goes_through_the_checks(bundle: EvidenceBundle) -> None:
    sent: list[dict[str, Any]] = []
    good = {
        "title": "Reading",
        "sections": [
            {
                "heading": "Now",
                "paragraphs": [{"text": "A period for study.", "evidence_ids": ["now:dasha"]}],
            }
        ],
    }
    bad = {
        "title": "Reading",
        "sections": [
            {
                "heading": "Now",
                "paragraphs": [{"text": "Invented.", "evidence_ids": ["rule:made_up"]}],
            }
        ],
    }
    replies = [_tool_reply("write_report", bad), _tool_reply("write_report", good)]

    def transport(url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
        sent.append(payload)
        return replies.pop(0)

    out = write_report(bundle, ClaudeNarrator("key", transport=transport))
    assert out.narrator == "claude-opus-5-5" and out.usage == {
        "input_tokens": 1000,
        "output_tokens": 200,
    }
    assert len(sent) == 2  # the first reply cited an unknown ID and was retried
    payload = sent[0]
    assert payload["tool_choice"] == {"type": "tool", "name": "write_report"}
    assert payload["system"][0]["cache_control"] == {"type": "ephemeral"}

    always_bad = ClaudeNarrator("key", transport=lambda *_: _tool_reply("write_report", bad))
    with pytest.raises(NarrativeRejectedError, match="unknown evidence"):
        write_report(bundle, always_bad)
    refusing = ClaudeNarrator("key", transport=lambda *_: {"stop_reason": "refusal", "content": []})
    with pytest.raises(NarrativeRefusedError):
        write_report(bundle, refusing)


def test_offline_chat_uses_the_evidence(bundle: EvidenceBundle) -> None:
    out = answer_offline(bundle, "When is marriage likely?")
    assert out.evidence and all("marriage" in e.domains for e in out.evidence)
    assert "not certainties" in out.answer


def test_claude_chat_can_look_up_a_date(chart: ChartResult, bundle: EvidenceBundle) -> None:
    replies = [
        _tool_reply("period_at", {"date": "2028-01-15"}),
        _tool_reply(
            "answer",
            {"text": "Jupiter's period supports study.", "evidence_ids": ["at:2028-01-15:dasha"]},
        ),
    ]
    narrator = ClaudeNarrator("key", transport=lambda *_: replies.pop(0))
    out = chat_with_claude(
        narrator, chart, bundle, [ChatMessage(role="user", content="How is 2028?")]
    )
    assert [e.id for e in out.evidence] == ["at:2028-01-15:dasha"]
    lying = ClaudeNarrator(
        "key",
        transport=lambda *_: _tool_reply("answer", {"text": "x", "evidence_ids": ["rule:nope"]}),
    )
    with pytest.raises(NarrativeRejectedError):
        chat_with_claude(lying, chart, bundle, [ChatMessage(role="user", content="?")])


def test_routes_default_to_the_template() -> None:
    client = TestClient(create_app(ApiSettings(rate_limit="1000/minute")))
    body = {"birth": BIRTH, "today": "2026-09-30"}
    report = client.post("/v1/charts/report", json=body)
    assert report.status_code == 200 and report.json()["narrator"] == "template"
    chat = client.post(
        "/v1/charts/chat", json={**body, "messages": [{"role": "user", "content": "career now?"}]}
    )
    assert chat.status_code == 200 and chat.json()["evidence"]
    claude = TestClient(
        create_app(ApiSettings(rate_limit="1000/minute", narrative_provider="claude"))
    )
    assert claude.post("/v1/charts/report", json=body).status_code == 503


def test_eval_harness_passes_with_the_template(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    harness = importlib.import_module("narrative_eval")
    try:
        result = harness.evaluate(TemplateNarrator(), 3, TODAY)
        assert result.cases == 3 and result.passed == 3
    finally:
        sys.modules.pop("narrative_eval", None)
