"""Database: SQLAlchemy 2 models of accounts, saved people and their life events.

The schema is managed by Alembic (``api/migrations``). SQLite serves development and
tests; production uses Postgres through the pg8000 driver
(``postgresql+pg8000://...``). Deleting a user deletes everything they saved.
"""

from __future__ import annotations

import ssl
import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, String, Text, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool


def _now() -> datetime:
    return datetime.now(UTC)


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    #: The Supabase user id (the token's ``sub``).
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str | None] = mapped_column(String(320))
    #: Opt-in consent to use this account's data, anonymised, for accuracy research.
    research_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    people: Mapped[list[Person]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", passive_deletes=True
    )


class Person(Base):
    """Someone whose chart the account holder keeps (themselves, family, clients)."""

    __tablename__ = "people"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    #: A ``BirthInput`` as JSON.
    birth: Mapped[dict[str, Any]] = mapped_column(JSON)
    gender: Mapped[str | None] = mapped_column(String(10))
    #: Under 18: saved only with the account holder's consent as guardian (DPDP Act).
    is_minor: Mapped[bool] = mapped_column(Boolean, default=False)
    guardian_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
    owner: Mapped[User] = relationship(back_populates="people")
    events: Mapped[list[LifeEvent]] = relationship(
        back_populates="person", cascade="all, delete-orphan", passive_deletes=True
    )


class LifeEvent(Base):
    """A dated event in a person's life, for rectification and backtesting."""

    __tablename__ = "life_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    person_id: Mapped[str] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    date: Mapped[date] = mapped_column(Date)
    #: "day", "month" or "year": how exactly the date is known.
    precision: Mapped[str] = mapped_column(String(5), default="day")
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    person: Mapped[Person] = relationship(back_populates="events")


def tls_connect_args(url: str, tls: str = "prefer", ca_file: str | None = None) -> dict[str, Any]:
    """pg8000 arguments for "verify-full": TLS required, certificate and host name checked.

    Without an SSL context pg8000 encrypts only when the server offers TLS and does not
    check the certificate (libpq's "prefer").
    """
    if tls != "verify-full" or url.startswith("sqlite"):
        return {}
    return {"ssl_context": ssl.create_default_context(cafile=ca_file)}


def make_engine(url: str, tls: str = "prefer", ca_file: str | None = None) -> Engine:
    if url.startswith("sqlite"):
        options: dict[str, Any] = {"connect_args": {"check_same_thread": False}}
        if ":memory:" in url or url.rstrip("/").endswith("sqlite:"):
            options["poolclass"] = StaticPool
        engine = create_engine(url, **options)

        @event.listens_for(engine, "connect")
        def _foreign_keys(connection: Any, _: Any) -> None:
            connection.execute("PRAGMA foreign_keys=ON")

        return engine
    return create_engine(url, pool_pre_ping=True, connect_args=tls_connect_args(url, tls, ca_file))


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)


def sessions(factory: sessionmaker[Session]) -> Iterator[Session]:
    with factory() as session, session.begin():
        yield session
