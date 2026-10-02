"""Catalogue-wide invariants on random charts, and second implementations of some rules.

The second implementations use plain sign arithmetic and small tables, independent of
the rule language, so a mistake in either shows up as a disagreement.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from jyotish_engine.astro.bodies import GRAHAS, Body
from jyotish_engine.rules.catalogue import RuleResult, default_catalogue
from jyotish_engine.rules.facts import SIGN_NAMES, ChartFacts
from jyotish_engine.rules.schema import PERIOD_CATEGORIES, READING_CATEGORIES
from jyotish_engine.rules.yogas import YOGA_CATEGORIES

CATALOGUE = default_catalogue()
NATAL = YOGA_CATEGORIES | READING_CATEGORIES
SIGNS = list(SIGN_NAMES)
SEVEN = ("sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn")
LORDS = [
    "mars", "venus", "mercury", "moon", "sun", "mercury",
    "venus", "mars", "jupiter", "saturn", "saturn", "jupiter",
]  # fmt: skip
OWN = {"mars": {0, 7}, "mercury": {2, 5}, "jupiter": {8, 11}, "venus": {1, 6}, "saturn": {9, 10}}
EXALTED = {"mars": 9, "mercury": 5, "jupiter": 3, "venus": 11, "saturn": 6}
MAHAPURUSHA = {
    "mars": "ruchaka",
    "mercury": "bhadra",
    "jupiter": "hamsa",
    "venus": "malavya",
    "saturn": "sasa",
}

position = st.builds(
    lambda sign, degrees: f"{sign} {degrees:.2f}",
    st.sampled_from(SIGNS),
    st.floats(min_value=0.0, max_value=29.99, allow_nan=False),
)
charts = st.fixed_dictionaries(
    {
        "lagna": position,
        **{planet: position for planet in SEVEN},
        "rahu": position,
        "day_birth": st.booleans(),
        "gender": st.sampled_from(["male", "female"]),
    }
)


def _evaluate(spec: dict[str, Any]) -> tuple[ChartFacts, dict[str, RuleResult]]:
    facts = ChartFacts.from_spec(spec)
    return facts, {r.rule.id: r for r in CATALOGUE.evaluate(facts, NATAL)}


def _holds(result: RuleResult) -> bool:
    """The rule's condition is true (present, or present but cancelled)."""
    return result.present or result.cancelled


def _present(results: dict[str, RuleResult], prefix: str) -> list[str]:
    return [rid for rid, r in results.items() if rid.startswith(prefix) and r.present]


@settings(max_examples=60, deadline=None)
@given(charts)
def test_period_rules_are_decided(spec: dict[str, Any]) -> None:
    """With a dasha and transits, every period rule is decided, and each graha's transit
    from the Moon matches exactly one gochara rule (present, or cancelled by vedha)."""
    natal = ChartFacts.from_spec(spec)
    facts = natal.with_period(dasha=(Body.SATURN, Body.MERCURY), transits=natal.positions)
    results = {r.rule.id: r for r in CATALOGUE.evaluate(facts, PERIOD_CATEGORIES)}
    assert all(r.missing is None for r in results.values())
    for body in GRAHAS:
        prefix = f"transit.{body.value}_h"
        assert sum(_holds(r) for rid, r in results.items() if rid.startswith(prefix)) == 1


@settings(max_examples=150, deadline=None)
@given(charts)
def test_catalogue_invariants(spec: dict[str, Any]) -> None:
    facts, results = _evaluate(spec)
    assert all(r.missing is None for r in results.values())

    lunar = ["chandra.sunapha", "chandra.anapha", "chandra.durudhura", "chandra.kemadruma"]
    assert sum(_holds(results[rid]) for rid in lunar) == 1
    from_sun = [f"chandra.moon_{k}_from_sun" for k in ("kendra", "panaphara", "apoklima")]
    assert sum(results[rid].present for rid in from_sun) == 1
    assert sum(results[f"surya.{k}"].present for k in ("vesi", "vasi", "ubhayachari")) <= 1

    assert len(_present(results, "nabhasa.ashraya.")) <= 1
    akriti = _present(results, "nabhasa.akriti.")
    assert len(akriti) <= 1
    blocked = bool(akriti or _present(results, "nabhasa.dala."))
    assert len(_present(results, "nabhasa.sankhya.")) == (0 if blocked else 1)

    malika = _present(results, "malika.")
    assert len(malika) <= 1
    if malika:  # a Malika chain is always one of the seven-house Nabhasa shapes
        assert akriti and akriti[0] in {
            "nabhasa.akriti.nauka",
            "nabhasa.akriti.kuta",
            "nabhasa.akriti.chatra",
            "nabhasa.akriti.chapa",
            "nabhasa.akriti.ardha_chandra",
        }

    named_types = _present(results, "dosha.kala_sarpa_")
    assert len(named_types) == (1 if results["dosha.kala_sarpa"].present else 0)

    counts = Counter(facts.signs[b] for b in facts.signs if b.value in SEVEN)
    pairs = sum(1 for n in counts.values() if n == 2)
    triples = sum(1 for n in counts.values() if n == 3)
    assert len(_present(results, "conjunction.dwigraha_")) == pairs
    assert len(_present(results, "conjunction.trigraha_")) == triples


@settings(max_examples=150, deadline=None)
@given(charts)
def test_rules_agree_with_plain_python(spec: dict[str, Any]) -> None:
    facts, results = _evaluate(spec)
    signs = {b.value: s for b, s in facts.signs.items()}
    lagna = facts.lagna_sign

    def house(planet: str, ref: int) -> int:
        return (signs[planet] - ref) % 12 + 1

    for planet, yoga in MAHAPURUSHA.items():
        dignified = signs[planet] in OWN[planet] or signs[planet] == EXALTED[planet]
        expected = dignified and house(planet, lagna) in (1, 4, 7, 10)
        assert results[f"mahapurusha.{yoga}"].present == expected, (yoga, spec)

    exchanges = 0
    for a in range(1, 13):
        for b in range(a + 1, 13):
            x, y = LORDS[(lagna + a - 1) % 12], LORDS[(lagna + b - 1) % 12]
            if x != y and LORDS[signs[x]] == y and LORDS[signs[y]] == x:
                exchanges += 1
    assert len(_present(results, "parivartana.")) == exchanges

    gaja = house("jupiter", signs["moon"]) in (1, 4, 7, 10)
    assert _holds(results["chandra.gajakesari"]) == gaja

    rahu = facts.positions[Body.RAHU]
    offsets = [(facts.positions[Body(p)] - rahu) % 360.0 for p in SEVEN]
    sides = {o < 180.0 for o in offsets}
    on_axis = any(o % 180.0 == 0.0 for o in offsets)
    assert results["dosha.kala_sarpa"].present == (len(sides) == 1 and not on_axis)

    star = ("mars", "mercury", "jupiter", "venus", "saturn")
    second = any(house(p, signs["moon"]) == 2 for p in star)
    twelfth = any(house(p, signs["moon"]) == 12 for p in star)
    assert _holds(results["chandra.durudhura"]) == (second and twelfth)
    assert _holds(results["chandra.kemadruma"]) == (not second and not twelfth)
