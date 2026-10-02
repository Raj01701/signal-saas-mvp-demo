"""Web Push reminder routes: the public key, saving a browser's reminders, unsubscribing.

No account is needed and no birth data is sent: the browser posts its subscription and
the reminders it computed itself (see ``jyotish_api.push``).
"""

from __future__ import annotations

import hmac
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import AwareDatetime, BaseModel, Field
from sqlalchemy import delete, select

from jyotish_api.auth import SessionDep
from jyotish_api.db import PushReminder, PushSubscription
from jyotish_api.push import Vapid, allowed_endpoint, b64decode, browser_key

router = APIRouter(prefix="/v1/push", tags=["push"])
#: The furthest ahead a reminder may be scheduled.
HORIZON = timedelta(days=400)


class PushKeyOut(BaseModel):
    #: The application server key to subscribe with (base64url).
    public_key: str


class PushKeys(BaseModel):
    p256dh: str = Field(max_length=100)
    auth: str = Field(max_length=50)


class PushSubscriptionIn(BaseModel):
    """The browser's ``PushSubscription.toJSON()``."""

    endpoint: str = Field(max_length=2048)
    keys: PushKeys


class ReminderIn(BaseModel):
    at: AwareDatetime
    title: str = Field(min_length=1, max_length=120)
    body: str = Field(default="", max_length=300)


class RemindersIn(BaseModel):
    subscription: PushSubscriptionIn
    #: Replaces the reminders saved before; past ones are ignored.
    reminders: list[ReminderIn] = Field(max_length=60)


class UnsubscribeIn(BaseModel):
    endpoint: str = Field(max_length=2048)
    #: The subscription's authentication secret, proving it is the caller's.
    auth: str = Field(max_length=50)


def _vapid(request: Request) -> Vapid:
    vapid: Vapid | None = request.app.state.vapid
    if vapid is None:
        raise HTTPException(503, "push reminders are not configured")
    return vapid


def _check(subscription: PushSubscriptionIn) -> None:
    if not allowed_endpoint(subscription.endpoint):
        raise HTTPException(422, "the endpoint is not a browser push service")
    try:
        browser_key(subscription.keys.p256dh)
        auth = b64decode(subscription.keys.auth)
    except ValueError as error:
        raise HTTPException(422, "the subscription keys are not valid") from error
    if len(auth) != 16:
        raise HTTPException(422, "the subscription keys are not valid")


@router.get("/key")
def public_key(request: Request) -> PushKeyOut:
    """The key browsers subscribe with; 503 when push reminders are off."""
    return PushKeyOut(public_key=_vapid(request).public_key)


@router.put("/subscription", status_code=204)
def save_reminders(request: Request, body: RemindersIn, session: SessionDep) -> Response:
    """Save this browser's subscription and replace its pending reminders."""
    _vapid(request)
    _check(body.subscription)
    keys = body.subscription.keys
    saved = session.scalar(
        select(PushSubscription).where(PushSubscription.endpoint == body.subscription.endpoint)
    )
    if saved is not None and not hmac.compare_digest(saved.auth, keys.auth):
        raise HTTPException(409, "this endpoint is registered with other keys")
    now = datetime.now(UTC)
    moments = [reminder.at.astimezone(UTC) for reminder in body.reminders]
    if any(at > now + HORIZON for at in moments):
        raise HTTPException(422, "reminders can be set at most 400 days ahead")
    if saved is None:
        saved = PushSubscription(endpoint=body.subscription.endpoint, auth=keys.auth)
        session.add(saved)
    saved.p256dh = keys.p256dh
    saved.updated_at = now
    session.flush()
    session.execute(delete(PushReminder).where(PushReminder.subscription_id == saved.id))
    for reminder, at in zip(body.reminders, moments, strict=True):
        if at >= now:
            session.add(
                PushReminder(
                    subscription_id=saved.id, due_at=at, title=reminder.title, body=reminder.body
                )
            )
    return Response(status_code=204)


@router.post("/unsubscribe", status_code=204)
def unsubscribe(body: UnsubscribeIn, session: SessionDep) -> Response:
    """Forget a subscription and its reminders (idempotent)."""
    saved = session.scalar(
        select(PushSubscription).where(PushSubscription.endpoint == body.endpoint)
    )
    if saved is not None:
        if not hmac.compare_digest(saved.auth, body.auth):
            raise HTTPException(404, "no such subscription")
        session.delete(saved)
    return Response(status_code=204)
