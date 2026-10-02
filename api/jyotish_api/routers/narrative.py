"""Narrative routes: checked, cited readings and grounded chat (milestone M10)."""

from __future__ import annotations

from datetime import date
from typing import Literal

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import Field

from jyotish_api.charts import ChartCache, resolve_settings
from jyotish_api.config import ApiSettings
from jyotish_api.narrative.evidence import EvidenceBundle, build_bundle
from jyotish_api.narrative.narrators import (
    ClaudeNarrator,
    NarrativeRefusedError,
    Narrator,
    TemplateNarrator,
)
from jyotish_api.narrative.report import NarrativeOut
from jyotish_api.narrative.service import (
    ChatLanguage,
    ChatMessage,
    ChatOut,
    NarrativeRejectedError,
    answer_offline,
    chat_with_claude,
    write_report,
)
from jyotish_api.ratelimit import narrative_quota
from jyotish_api.schemas import ChartRequest
from jyotish_engine.ask import ChartLookup
from jyotish_engine.models import ChartResult

router = APIRouter(prefix="/v1", tags=["narrative"])


class NarrativeRequest(ChartRequest):
    gender: Literal["male", "female"] | None = None
    #: The day the reading is written for (default: today).
    today: date | None = None


class ReportRequest(NarrativeRequest):
    language: Literal["en", "hi"] = "en"
    #: Include rules marked sensitive (health, longevity); professional use only.
    include_sensitive: bool = False


class ChatRequest(NarrativeRequest):
    #: The conversation so far, oldest first, ending with the person's question.
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)
    #: The reply's language: "auto" answers in the language of each question.
    language: ChatLanguage = "auto"
    #: The person's first name, for a more personal answer.
    name: str | None = Field(default=None, max_length=60)


def narrator_for(settings: ApiSettings) -> Narrator:
    """Claude when configured, otherwise the offline template narrator."""
    provider = settings.narrative_provider
    if provider == "template" or (provider == "auto" and not settings.anthropic_api_key):
        return TemplateNarrator()
    if not settings.anthropic_api_key:
        raise HTTPException(503, "the Claude narrator needs JYOTISH_API_ANTHROPIC_API_KEY")
    return ClaudeNarrator(settings.anthropic_api_key, settings.narrative_model)


def _inputs(
    request: Request, body: NarrativeRequest, sensitive: bool = False
) -> tuple[ChartResult, EvidenceBundle]:
    cache: ChartCache = request.app.state.charts
    chart = cache.chart(body.birth, resolve_settings(body.settings, body.preset))
    bundle = build_bundle(chart, today=body.today, gender=body.gender, include_sensitive=sensitive)
    return chart, bundle


@router.post("/charts/report", dependencies=[Depends(narrative_quota)])
def report(request: Request, body: ReportRequest) -> NarrativeOut:
    """A reading in plain language; every paragraph cites the engine evidence behind it."""
    _, bundle = _inputs(request, body, body.include_sensitive)
    try:
        return write_report(bundle, narrator_for(request.app.state.settings), body.language)
    except (NarrativeRefusedError, NarrativeRejectedError) as error:
        raise HTTPException(502, str(error)) from error
    except anthropic.APIError as error:
        raise HTTPException(502, "the language model could not be reached") from error


@router.post("/charts/chat", dependencies=[Depends(narrative_quota)])
def chat(request: Request, body: ChatRequest) -> ChatOut:
    """Answer any question about the chart in the person's own words: Claude looks up
    what it needs in the engine and cites it; without Claude, the engine's facts on what
    the question names are listed instead."""
    if body.messages[-1].role != "user":
        raise HTTPException(422, "the last message must be the user's question")
    chart, bundle = _inputs(request, body)
    lookup = ChartLookup(chart, today=bundle.today, gender=body.gender)
    narrator = narrator_for(request.app.state.settings)
    if not isinstance(narrator, ClaudeNarrator):
        return answer_offline(bundle, body.messages[-1].content, lookup)
    try:
        return chat_with_claude(
            narrator,
            chart,
            bundle,
            body.messages,
            lookup=lookup,
            name=body.name,
            language=body.language,
        )
    except (NarrativeRefusedError, NarrativeRejectedError) as error:
        raise HTTPException(502, str(error)) from error
    except anthropic.APIError as error:
        raise HTTPException(502, "the language model could not be reached") from error
