"""Narratives: evidence IDs checked, banned claims blocked, Claude only through the checks."""

from __future__ import annotations

import importlib
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from jyotish_api.config import ApiSettings
from jyotish_api.main import create_app
from jyotish_api.narrative.evidence import EvidenceBundle, build_bundle
from jyotish_api.narrative.narrators import (
    ClaudeNarrator,
    NarrativeRefusedError,
    TemplateNarrator,
    strict_schema,
)
from jyotish_api.narrative.report import Paragraph, Report, Section, check
from jyotish_api.narrative.service import (
    ChatMessage,
    NarrativeRejectedError,
    answer_offline,
    chat_with_claude,
    write_report,
)
from jyotish_api.narrative.tools import LOOKUP_TOOLS, resolve_id, run_tool
from jyotish_engine.ask import ChartLookup
from jyotish_engine.chart import compute_chart
from jyotish_engine.models import BirthInput, ChartResult, MaritalInput, PlaceInput

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
        "content": [
            {"type": "thinking", "thinking": "", "signature": "sig"},
            {"type": "tool_use", "id": call, "name": name, "input": data},
        ],
        "usage": {"input_tokens": 1000, "output_tokens": 200},
    }


def _text_reply(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "stop_reason": "end_turn",
        "content": [{"type": "text", "text": json.dumps(data)}],
        "usage": {"input_tokens": 1000, "output_tokens": 200, "service_tier": "standard"},
    }


def _answer(text: str, ids: list[str]) -> dict[str, Any]:
    return _text_reply({"answer": text, "evidence_ids": ids})


def test_strict_schema_closes_every_object() -> None:
    schema = strict_schema(Report)
    text = json.dumps(schema)
    assert "minItems" not in text and "minLength" not in text
    assert schema["additionalProperties"] is False
    assert all(d["additionalProperties"] is False for d in schema["$defs"].values())


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
    replies = [_text_reply(bad), _text_reply(good)]

    def transport(params: dict[str, Any]) -> dict[str, Any]:
        sent.append(params)
        return replies.pop(0)

    out = write_report(bundle, ClaudeNarrator("key", transport=transport))
    assert out.narrator == "claude-opus-5-5" and out.usage == {
        "input_tokens": 1000,
        "output_tokens": 200,
    }
    assert len(sent) == 2  # the first reply cited an unknown ID and was retried
    params = sent[0]
    # The current models reject forced tool calls: the report comes as structured output.
    assert "tool_choice" not in params and "tools" not in params
    assert params["output_config"]["format"]["type"] == "json_schema"
    assert params["output_config"]["effort"] == "medium"
    assert params["system"][0]["cache_control"] == {"type": "ephemeral"}

    always_bad = ClaudeNarrator("key", transport=lambda _: _text_reply(bad))
    with pytest.raises(NarrativeRejectedError, match="unknown evidence"):
        write_report(bundle, always_bad)
    refusing = ClaudeNarrator("key", transport=lambda _: {"stop_reason": "refusal", "content": []})
    with pytest.raises(NarrativeRefusedError):
        write_report(bundle, refusing)
    garbled = ClaudeNarrator("key", transport=lambda _: _text_reply({"title": 3}))
    with pytest.raises(NarrativeRefusedError, match="not a valid report"):
        write_report(bundle, garbled)


def test_offline_chat_uses_the_evidence(bundle: EvidenceBundle) -> None:
    out = answer_offline(bundle, "When is marriage likely?")
    assert out.evidence and all("marriage" in e.domains for e in out.evidence)
    assert "not certainties" in out.answer


@pytest.fixture(scope="module")
def lookup(chart: ChartResult) -> ChartLookup:
    return ChartLookup(chart, today=TODAY)


def test_offline_chat_answers_custom_questions(bundle: EvidenceBundle, lookup: ChartLookup) -> None:
    year = answer_offline(bundle, "How will 2028 be for me?", lookup)
    assert [e.id for e in year.evidence] == ["year:2028"]
    assert "2028: you turn 38" in year.answer and "Periods:" in year.answer
    house = answer_offline(bundle, "What does my 7th house show?", lookup)
    assert [e.id for e in house.evidence] == ["house:7"] and house.answer.startswith("House 7")
    planets = answer_offline(bundle, "What do Guru and Shani do in my chart?", lookup)
    assert [e.id for e in planets.evidence] == ["planet:jupiter", "planet:saturn"]
    area = answer_offline(bundle, "Meri shaadi kab hogi?", lookup)
    assert [e.id for e in area.evidence] == ["area:marriage"]
    assert "Marriage: the birth chart's promise" in area.answer
    hindi = answer_offline(bundle, "नौकरी कब लगेगी?", lookup)
    assert [e.id for e in hindi.evidence] == ["area:career"]
    seventh = answer_offline(bundle, "मेरा सातवाँ भाव क्या बताता है?", lookup)
    assert [e.id for e in seventh.evidence] == ["house:7"]
    assert [e.id for e in answer_offline(bundle, "मेरा 10वां भाव", lookup).evidence] == ["house:10"]
    next_year = answer_offline(bundle, "How will next year be for me?", lookup)
    assert [e.id for e in next_year.evidence] == [f"year:{TODAY.year + 1}"]
    assert [e.id for e in answer_offline(bundle, "agle saal kaisa rahega", lookup).evidence] == [
        f"year:{TODAY.year + 1}"
    ]
    death = answer_offline(bundle, "When will I die?", lookup)
    assert death.answer.startswith("The chart is not used here to time death")
    assert [e.id for e in death.evidence] == ["area:health"]
    assert "202" not in death.answer.split("\n", 1)[1]  # no dates for health
    vague = answer_offline(bundle, "Tell me something nice", lookup)
    assert vague.evidence and vague.narrator == "template"
    child = compute_chart(
        BirthInput(local_datetime=datetime(2015, 2, 1, 9), place=PlaceInput(**DELHI))
    )
    young = answer_offline(
        build_bundle(child, today=TODAY),
        "When will I get married?",
        ChartLookup(child, today=TODAY),
    )
    assert young.answer.startswith("Marriage is read from adulthood") and not young.evidence


def test_lookup_tools_are_strict_and_resolvable(lookup: ChartLookup) -> None:
    assert {t["name"] for t in LOOKUP_TOOLS} == {
        "planet",
        "house",
        "period_at",
        "periods",
        "transits",
        "life_area",
        "year",
    }
    for tool in LOOKUP_TOOLS:
        schema = tool["input_schema"]
        assert tool["strict"] is True and schema["additionalProperties"] is False
        assert set(schema["required"]) == set(schema["properties"])
    item, data = run_tool(lookup, "periods", {"start": "2027-01-01", "end": "2028-01-01"})
    assert item.id == "periods:2027-01-01:2028-01-01" and data["evidence_id"] == item.id
    assert data["periods"] and item.kind == "lookup"
    for item_id in ("year:2030", "house:10", "planet:venus", "area:career", "at:2027-05-01"):
        resolved = resolve_id(lookup, item_id)
        assert resolved is not None and resolved.id == item_id
    for bad in ("year:1700", "house:13", "planet:pluto", "nothing", "at:1980-01-01", "year:"):
        assert resolve_id(lookup, bad) is None
    with pytest.raises(ValueError, match="at most 30 years"):
        run_tool(lookup, "transits", {"start": "2000-01-01", "end": "2040-01-01"})
    with pytest.raises(LookupError):
        run_tool(lookup, "horoscope", {})


def test_offline_marriage_answers_allow_for_a_wedding_already_held(
    bundle: EvidenceBundle, lookup: ChartLookup
) -> None:
    question = "When will I get married?"
    unknown = answer_offline(bundle, question, lookup).answer
    assert "Past windows from age 21:" in unknown and "If you are already married" in unknown
    married = answer_offline(
        bundle, question, lookup, MaritalInput(status="married", wedding_year=2016)
    ).answer
    assert "You said you are married (wedding in 2016)" in married
    assert "If you are already married" not in married
    single = answer_offline(bundle, question, lookup, MaritalInput(status="single")).answer
    assert "You said you are not married" in single


def test_claude_chat_looks_things_up_and_cites_them(
    chart: ChartResult, bundle: EvidenceBundle
) -> None:
    sent: list[dict[str, Any]] = []
    replies = [
        _tool_reply("period_at", {"date": "2028-01-15"}),
        _answer("Jupiter's period supports study.", ["at:2028-01-15", "year:2028"]),
    ]

    def transport(params: dict[str, Any]) -> dict[str, Any]:
        sent.append(json.loads(json.dumps(params)))
        return replies.pop(0)

    out = chat_with_claude(
        ClaudeNarrator("key", transport=transport),
        chart,
        bundle,
        [ChatMessage(role="user", content="How is 2028 for my studies?")],
        name="Asha",
        language="hi",
        marital=MaritalInput(status="married", wedding_year=2015, wedding_month=2),
    )
    # A cited lookup it did not call ("year:2028") is resolved by running it.
    assert [e.id for e in out.evidence] == ["at:2028-01-15", "year:2028"]
    first = sent[0]
    assert "tool_choice" not in first and first["cache_control"] == {"type": "ephemeral"}
    assert first["output_config"]["format"]["schema"]["required"] == ["answer", "evidence_ids"]
    context = first["messages"][0]["content"]
    assert "Asha, age 36" in context and "Devanagari" in context
    assert "They say they are married; the wedding was in 02-2015." in context
    assert "Never assume whether the person is married" in first["system"][0]["text"]
    # The tool result went back with the call's id, after the assistant turn unchanged.
    second = sent[1]["messages"]
    assert second[-2]["content"][0]["type"] == "thinking"
    result = second[-1]["content"][0]
    assert result["tool_use_id"] == "call-1" and "at:2028-01-15" in result["content"]


def test_claude_chat_retries_bad_answers(chart: ChartResult, bundle: EvidenceBundle) -> None:
    sent: list[dict[str, Any]] = []
    replies = [
        _tool_reply("year", {"year": 1500}),
        _answer("You will die in 2040.", ["now:dasha"]),
        _answer("A steady period.", ["rule:nope"]),
        _answer("A steady period for work.", ["now:dasha"]),
    ]

    def transport(params: dict[str, Any]) -> dict[str, Any]:
        sent.append(json.loads(json.dumps(params)))
        return replies.pop(0)

    out = chat_with_claude(
        ClaudeNarrator("key", transport=transport),
        chart,
        bundle,
        [ChatMessage(role="user", content="How is work now?")],
    )
    assert out.answer == "A steady period for work." and len(sent) == 4
    error = sent[1]["messages"][-1]["content"][0]
    assert error["is_error"] is True and "years run from" in error["content"]
    assert "death timing" in sent[2]["messages"][-1]["content"]
    assert "unknown evidence" in sent[3]["messages"][-1]["content"]
    lying = ClaudeNarrator("key", transport=lambda _: _answer("x", ["rule:nope"]))
    with pytest.raises(NarrativeRejectedError):
        chat_with_claude(lying, chart, bundle, [ChatMessage(role="user", content="?")])
    refusing = ClaudeNarrator("key", transport=lambda _: {"stop_reason": "refusal", "content": []})
    with pytest.raises(NarrativeRefusedError):
        chat_with_claude(refusing, chart, bundle, [ChatMessage(role="user", content="?")])


def test_routes_default_to_the_template() -> None:
    client = TestClient(create_app(ApiSettings(rate_limit="1000/minute")))
    body = {"birth": BIRTH, "today": "2026-09-30"}
    report = client.post("/v1/charts/report", json=body)
    assert report.status_code == 200 and report.json()["narrator"] == "template"
    chat = client.post(
        "/v1/charts/chat", json={**body, "messages": [{"role": "user", "content": "career now?"}]}
    )
    assert chat.status_code == 200 and chat.json()["evidence"]
    custom = client.post(
        "/v1/charts/chat",
        json={
            **body,
            "name": "Asha",
            "language": "en",
            "messages": [{"role": "user", "content": "What happens in 2029?"}],
        },
    )
    assert custom.status_code == 200
    assert [e["id"] for e in custom.json()["evidence"]] == ["year:2029"]
    assert custom.json()["evidence"][0]["kind"] == "lookup"
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


def test_narrative_routes_have_their_own_quota() -> None:
    client = TestClient(
        create_app(ApiSettings(rate_limit="1000/minute", narrative_rate_limit="1/hour"))
    )
    question = [{"role": "user", "content": "How is my career?"}]
    body = {"birth": BIRTH, "today": "2026-09-30", "messages": question}
    assert client.post("/v1/charts/chat", json=body).status_code == 200
    refused = client.post("/v1/charts/chat", json=body)
    assert refused.status_code == 429 and "1/hour" in refused.json()["detail"]
    too_long = {**body, "messages": [{"role": "user", "content": "x" * 4001}]}
    assert (
        TestClient(create_app(ApiSettings())).post("/v1/charts/chat", json=too_long).status_code
        == 422
    )
