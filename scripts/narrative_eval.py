"""Evaluate narratives on evidence bundles: valid evidence IDs and no banned claims.

    uv run python scripts/narrative_eval.py            # offline template narrator
    uv run python scripts/narrative_eval.py --claude   # needs JYOTISH_API_ANTHROPIC_API_KEY

Plan acceptance (M10): 100 % valid evidence IDs and 0 banned-claim hits on 50 bundles.
With Claude it also reports token use and an estimated cost at the plan's prices.
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from jyotish_api.narrative.evidence import build_bundle
from jyotish_api.narrative.narrators import ClaudeNarrator, Narrator, TemplateNarrator
from jyotish_api.narrative.report import check
from jyotish_engine.chart import compute_chart
from jyotish_engine.models import BirthInput, PlaceInput

CITIES = [
    ("New Delhi", 28.6139, 77.2090),
    ("Mumbai", 19.0760, 72.8777),
    ("Chennai", 13.0827, 80.2707),
    ("Kolkata", 22.5726, 88.3639),
    ("London", 51.5074, -0.1278),
]
#: US dollars per million tokens (plan section 4): input, output, cache reads.
PRICES = {"input_tokens": 4.0, "output_tokens": 20.0, "cache_read_input_tokens": 0.2}


@dataclass
class Result:
    cases: int = 0
    passed: int = 0
    tokens: dict[str, int] | None = None


def births(count: int, seed: int = 7) -> list[BirthInput]:
    rng = random.Random(seed)
    out = []
    for _ in range(count):
        name, lat, lon = rng.choice(CITIES)
        when = datetime(1950, 1, 1) + timedelta(minutes=rng.randrange(0, 60 * 24 * 365 * 55))
        out.append(
            BirthInput(
                local_datetime=when, place=PlaceInput(name=name, latitude=lat, longitude=lon)
            )
        )
    return out


def evaluate(narrator: Narrator, count: int, today: date, verbose: bool = False) -> Result:
    result = Result(tokens={})
    for birth in births(count):
        bundle = build_bundle(compute_chart(birth), today=today)
        report, usage = narrator.write(bundle, "en")
        problems = check(report, bundle)
        result.cases += 1
        result.passed += not problems
        for key, value in (usage or {}).items():
            result.tokens[key] = result.tokens.get(key, 0) + value  # type: ignore[index]
        if problems and verbose:
            print(f"{birth.local_datetime} {birth.place.name}: {problems}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--claude", action="store_true", help="evaluate Claude instead of the template"
    )
    parser.add_argument("--count", type=int, default=50)
    args = parser.parse_args()
    narrator: Narrator = TemplateNarrator()
    if args.claude:
        key = os.environ.get("JYOTISH_API_ANTHROPIC_API_KEY")
        if not key:
            print("set JYOTISH_API_ANTHROPIC_API_KEY to evaluate Claude")
            return 2
        narrator = ClaudeNarrator(
            key, os.environ.get("JYOTISH_API_NARRATIVE_MODEL", "claude-opus-5-5")
        )
    result = evaluate(narrator, args.count, date(2026, 9, 30), verbose=True)
    passed = f"{result.passed}/{result.cases}"
    print(f"{narrator.name}: {passed} reports passed (valid IDs, no banned claims)")
    if result.tokens:
        cost = sum(PRICES.get(k, 0.0) * v / 1e6 for k, v in result.tokens.items())
        print(f"tokens {result.tokens}; estimated cost ${cost:.2f}")
    return 0 if result.passed == result.cases else 1


if __name__ == "__main__":
    sys.exit(main())
