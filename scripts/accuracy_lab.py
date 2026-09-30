"""Run the Accuracy Lab on recorded cases, or on synthetic ones to check the pipeline.

    uv run python scripts/accuracy_lab.py --cases cases.jsonl --out docs/ACCURACY_LAB.md
    uv run python scripts/accuracy_lab.py --synthetic 12 --out docs/ACCURACY_LAB.md

A case file has one JSON object per line: {"birth": <BirthInput>, "events":
[{"kind": "marriage", "date": "2015-02-01"}, ...], "gender": "female"}.
``scripts/export_research_cases.py`` writes one from research-consented accounts.
Synthetic events are generated from the engine's own rules, so a synthetic run only
shows that the lab separates the true time from the controls; it says nothing about
predictive validity.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from jyotish_engine.chart import compute_chart
from jyotish_engine.lab import Case, backtest, render_markdown
from jyotish_engine.models import BirthInput, PlaceInput
from jyotish_engine.rectify import EventKind, LifeEvent
from jyotish_engine.rectify.synthetic import synthetic_events

CITIES = [
    ("New Delhi", 28.6139, 77.2090),
    ("Mumbai", 19.0760, 72.8777),
    ("Chennai", 13.0827, 80.2707),
    ("Kolkata", 22.5726, 88.3639),
    ("Bengaluru", 12.9716, 77.5946),
]
KINDS = [
    EventKind.MARRIAGE,
    EventKind.CHILD_BIRTH,
    EventKind.JOB,
    EventKind.PROMOTION,
    EventKind.PROPERTY,
]


def load_cases(path: Path) -> list[Case]:
    cases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        events = tuple(
            LifeEvent(EventKind(e["kind"]), date.fromisoformat(e["date"])) for e in data["events"]
        )
        cases.append(Case(BirthInput.model_validate(data["birth"]), events, data.get("gender")))
    return cases


def synthetic_cases(count: int, seed: int = 11) -> list[Case]:
    rng = random.Random(seed)
    cases = []
    for _ in range(count):
        name, lat, lon = rng.choice(CITIES)
        when = datetime(1950, 1, 1) + timedelta(minutes=rng.randrange(60 * 24 * 365 * 38))
        birth = BirthInput(
            local_datetime=when, place=PlaceInput(name=name, latitude=lat, longitude=lon)
        )
        cases.append(Case(birth, tuple(synthetic_events(compute_chart(birth), KINDS))))
    return cases


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--cases", type=Path, help="JSON-lines file of recorded cases")
    source.add_argument("--synthetic", type=int, help="number of synthetic cases")
    parser.add_argument("--replicates", type=int, default=5)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.cases:
        cases = load_cases(args.cases)
        title, note = "Accuracy Lab", f"Recorded cases from `{args.cases.name}`."
    else:
        cases = synthetic_cases(args.synthetic)
        title = "Accuracy Lab (synthetic check)"
        note = (
            "These events were generated from the engine's own rules, so this run only checks "
            "that the lab separates the true birth time from the controls. It says nothing about "
            "predictive validity; that needs recorded, consented events."
        )
    report = backtest(cases, args.replicates, args.seed)
    text = render_markdown(report, title, note)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
