"""Export research-consented cases for the Accuracy Lab (no names or IDs).

    JYOTISH_API_DATABASE_URL=... uv run python scripts/export_research_cases.py cases.jsonl

Only people saved by accounts that opted in to research, and never minors, are
exported: birth data, gender and dated events.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from jyotish_api.config import ApiSettings
from jyotish_api.db import Person, User, make_engine


def export(session: Session) -> list[dict[str, object]]:
    rows = session.scalars(
        select(Person).join(User).where(User.research_consent.is_(True), Person.is_minor.is_(False))
    )
    out = []
    for person in rows:
        events = [
            {"kind": e.kind, "date": e.date.isoformat()} for e in person.events if e.kind != "other"
        ]
        if len(events) >= 2:
            out.append({"birth": person.birth, "gender": person.gender, "events": events})
    return out


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    engine = make_engine(ApiSettings().database_url)
    with Session(engine) as session:
        cases = export(session)
    Path(sys.argv[1]).write_text("".join(json.dumps(c) + "\n" for c in cases), encoding="utf-8")
    print(f"exported {len(cases)} cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
