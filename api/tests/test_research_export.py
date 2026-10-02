"""The research export: consented adults only, without names or IDs."""

from __future__ import annotations

import importlib
import sys
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from jyotish_api.db import Base, LifeEvent, Person, User, make_engine

BIRTH = {
    "local_datetime": "1990-05-17T12:00:00",
    "place": {"name": "Delhi", "latitude": 28.6, "longitude": 77.2},
}


def test_only_consented_adults_are_exported(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        for user_id, consent in (("yes", True), ("no", False)):
            session.add(User(id=user_id, research_consent=consent))
            for minor in (False, True):
                person = Person(
                    owner_id=user_id,
                    name=f"{user_id}-{minor}",
                    birth=BIRTH,
                    is_minor=minor,
                    guardian_consent=minor,
                )
                person.events = [
                    LifeEvent(kind="marriage", date=date(2015, 2, 1)),
                    LifeEvent(kind="job", date=date(2012, 7, 1)),
                ]
                session.add(person)
        session.commit()
        monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
        try:
            cases = importlib.import_module("export_research_cases").export(session)
        finally:
            sys.modules.pop("export_research_cases", None)
    assert len(cases) == 1
    assert set(cases[0]) == {"birth", "gender", "events"}
    assert [e["kind"] for e in cases[0]["events"]] == ["marriage", "job"]
