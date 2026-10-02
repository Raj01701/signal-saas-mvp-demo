"""Account routes (sign-in required): profile and consent, saved people, life events,
data export and deletion."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select

from jyotish_api.auth import CurrentUser, SessionDep
from jyotish_api.charts import ChartCache, resolve_settings
from jyotish_api.db import LifeEvent, Person
from jyotish_api.schemas import RectifyOptions
from jyotish_engine.models import BirthInput, ChartResult, RectificationOut
from jyotish_engine.rectify import EventKind, rectify
from jyotish_engine.rectify import LifeEvent as DatedEvent
from jyotish_engine.settings import Preset, Settings

router = APIRouter(prefix="/v1")

EVENT_KINDS = (
    "marriage", "divorce", "child_birth", "education", "job", "promotion", "job_loss",
    "business", "relocation", "foreign_travel", "property", "illness", "surgery",
    "accident", "parent_death", "spouse_death", "other",
)  # fmt: skip


class Me(BaseModel):
    id: str
    email: str | None
    research_consent: bool
    people: int


class MeUpdate(BaseModel):
    research_consent: bool


class PersonIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    birth: BirthInput
    gender: Literal["male", "female"] | None = None
    is_minor: bool = False
    #: Required for a minor: the account holder confirms they are the guardian.
    guardian_consent: bool = False
    notes: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def _guardian(self) -> PersonIn:
        if self.is_minor and not self.guardian_consent:
            raise ValueError("a minor's data needs the guardian's consent")
        return self


class PersonOut(PersonIn):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class EventIn(BaseModel):
    kind: Literal[EVENT_KINDS]  # type: ignore[valid-type]
    date: date
    precision: Literal["day", "month", "year"] = "day"
    description: str | None = Field(default=None, max_length=2000)


class EventOut(EventIn):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime


class ChartOptions(BaseModel):
    settings: Settings | None = None
    preset: Preset | None = None


class Export(BaseModel):
    me: Me
    people: list[PersonOut]
    events: dict[str, list[EventOut]]


def _person(session: SessionDep, user: CurrentUser, person_id: str) -> Person:
    person = session.get(Person, person_id)
    if person is None or person.owner_id != user.id:
        raise HTTPException(status_code=404, detail="no such person")
    return person


def _me(user: CurrentUser) -> Me:
    return Me(
        id=user.id,
        email=user.email,
        research_consent=user.research_consent,
        people=len(user.people),
    )


@router.get("/me")
def me(user: CurrentUser) -> Me:
    return _me(user)


@router.put("/me")
def update_me(body: MeUpdate, user: CurrentUser) -> Me:
    user.research_consent = body.research_consent
    return _me(user)


@router.get("/me/export")
def export(user: CurrentUser) -> Export:
    """Everything stored for this account, in one document."""
    return Export(
        me=_me(user),
        people=[PersonOut.model_validate(p) for p in user.people],
        events={p.id: [EventOut.model_validate(e) for e in p.events] for p in user.people},
    )


@router.delete("/me", status_code=204)
def delete_me(user: CurrentUser, session: SessionDep) -> Response:
    """Delete the account and everything saved with it."""
    session.delete(user)
    return Response(status_code=204)


@router.get("/people")
def list_people(user: CurrentUser, session: SessionDep) -> list[PersonOut]:
    rows = session.scalars(
        select(Person).where(Person.owner_id == user.id).order_by(Person.created_at)
    )
    return [PersonOut.model_validate(p) for p in rows]


@router.post("/people", status_code=201)
def create_person(body: PersonIn, user: CurrentUser, session: SessionDep) -> PersonOut:
    person = Person(owner_id=user.id, **body.model_dump(mode="json"))
    session.add(person)
    session.flush()
    return PersonOut.model_validate(person)


@router.get("/people/{person_id}")
def get_person(person_id: str, user: CurrentUser, session: SessionDep) -> PersonOut:
    return PersonOut.model_validate(_person(session, user, person_id))


@router.put("/people/{person_id}")
def update_person(
    person_id: str, body: PersonIn, user: CurrentUser, session: SessionDep
) -> PersonOut:
    person = _person(session, user, person_id)
    for key, value in body.model_dump(mode="json").items():
        setattr(person, key, value)
    session.flush()
    return PersonOut.model_validate(person)


@router.delete("/people/{person_id}", status_code=204)
def delete_person(person_id: str, user: CurrentUser, session: SessionDep) -> Response:
    session.delete(_person(session, user, person_id))
    return Response(status_code=204)


@router.post("/people/{person_id}/chart")
def person_chart(
    person_id: str, body: ChartOptions, request: Request, user: CurrentUser, session: SessionDep
) -> ChartResult:
    person = _person(session, user, person_id)
    cache: ChartCache = request.app.state.charts
    return cache.chart(
        BirthInput.model_validate(person.birth), resolve_settings(body.settings, body.preset)
    )


class PersonRectifyRequest(ChartOptions, RectifyOptions):
    pass


@router.post("/people/{person_id}/rectify")
def person_rectify(
    person_id: str,
    body: PersonRectifyRequest,
    request: Request,
    user: CurrentUser,
    session: SessionDep,
) -> RectificationOut:
    """Rectify a saved person's birth time from their saved life events."""
    person = _person(session, user, person_id)
    cache: ChartCache = request.app.state.charts
    chart = cache.chart(
        BirthInput.model_validate(person.birth), resolve_settings(body.settings, body.preset)
    )
    events = [DatedEvent(EventKind(e.kind), e.date) for e in person.events]
    gender = person.gender if person.gender in ("male", "female") else None
    try:
        return rectify(
            chart,
            events,
            uncertainty_minutes=body.uncertainty_minutes,
            step_seconds=body.step_seconds,
            gender=gender,
            priors=body.priors,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/people/{person_id}/events")
def list_events(person_id: str, user: CurrentUser, session: SessionDep) -> list[EventOut]:
    person = _person(session, user, person_id)
    return [EventOut.model_validate(e) for e in sorted(person.events, key=lambda e: e.date)]


@router.post("/people/{person_id}/events", status_code=201)
def create_event(person_id: str, body: EventIn, user: CurrentUser, session: SessionDep) -> EventOut:
    person = _person(session, user, person_id)
    event = LifeEvent(person_id=person.id, **body.model_dump())
    session.add(event)
    session.flush()
    return EventOut.model_validate(event)


@router.delete("/people/{person_id}/events/{event_id}", status_code=204)
def delete_event(person_id: str, event_id: str, user: CurrentUser, session: SessionDep) -> Response:
    person = _person(session, user, person_id)
    event = session.get(LifeEvent, event_id)
    if event is None or event.person_id != person.id:
        raise HTTPException(status_code=404, detail="no such event")
    session.delete(event)
    return Response(status_code=204)
