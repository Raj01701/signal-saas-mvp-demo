"""The rule expression language: parsing, every library function, evidence, errors."""

from __future__ import annotations

import re

import pytest

from jyotish_engine.rules.catalogue import default_knowledge_dir
from jyotish_engine.rules.dsl import (
    FUNCTIONS,
    Counted,
    RuleSyntaxError,
    RuleTypeError,
    compile_expression,
    describe,
)
from jyotish_engine.rules.facts import ChartFacts, MissingFactError

# Aries lagna; Moon Aries, Mars Capricorn, Jupiter Cancer; Sun, Mercury, Venus, Saturn
# and Rahu in Gemini (all at 15 degrees), Ketu in Sagittarius. The Moon is waning
# (elongation 300 degrees) and Mercury, among malefics, is itself a malefic.
SPEC = {
    "lagna": "aries",
    "moon": "aries",
    "mars": "capricorn",
    "jupiter": "cancer",
    "rest": "gemini",
}


@pytest.fixture(scope="module")
def facts() -> ChartFacts:
    return ChartFacts.from_spec(SPEC)


def _eval(text: str, facts: ChartFacts) -> tuple[bool, list[str]]:
    return compile_expression(text).evaluate(facts)


# Every expression below is true for SPEC; worked out by hand.
TRUE_EXPRESSIONS = [
    # positions and houses
    "house(mars) == 10",
    "house(jupiter, moon) == 4",
    "sign(mars) == capricorn",
    "sign(lagna) == aries",
    "navamsa(mars) == taurus",
    "not vargottama(mars)",
    "lord(10) == saturn",
    "lord(1, moon) == mars",
    "lord_of(sign(jupiter)) == moon",
    "dispositor(mars) == saturn",
    "dispositor(lagna) == mars",
    "exaltation_lord(jupiter) == moon",
    "exalted_in(capricorn) == [mars]",
    "occupants(3) == [sun, mercury, venus, saturn, rahu]",
    "companions(sun) == [mercury, venus, saturn, rahu]",
    "empty(2)",
    "placed_in(seven, kendras) == [moon, mars, jupiter]",
    "all_in_houses([moon, mars], kendras)",
    "any_in_houses([sun, venus], [3])",
    "count_in_houses(seven, [3]) == 4",
    "houses_of(seven) == [1, 3, 4, 10]",
    "houses_of([ketu], moon) == [9]",
    "signs_occupied(seven) == 4",
    "arc(11, 4) == [1, 2, 11, 12]",
    "in_kendra(jupiter)",
    "in_trikona(ketu)",
    "not in_dusthana(mars)",
    "in_upachaya(sun)",
    "between_nodes([moon, mars])",
    "not between_nodes([moon, jupiter])",
    # relations
    "conjunct(sun, venus)",
    "not conjunct(sun, sun)",
    "conjunct(moon, lagna)",
    "aspects(mars, lagna)",
    "aspects(mars, jupiter)",
    "aspects_house(jupiter, 12)",
    "aspecting(jupiter) == [mars]",
    "mutual_aspect(mars, jupiter)",
    "not exchange(mars, saturn)",
    "associated(mars, jupiter)",
    "influences(mars, lagna)",
    # dignity and states
    "exalted(mars) and exalted(jupiter)",
    "not debilitated(mars)",
    "own_sign(mercury) and dignified(mercury) and not moolatrikona(mercury)",
    "friendly_sign(jupiter)",
    # Sun in Mercury's sign: natural neutral plus temporary enemy (same sign) = enemy.
    # Saturn there: natural friend plus temporary enemy = neutral.
    "enemy_sign(sun) and not enemy_sign(saturn)",
    "not exalted_navamsa(mars) and not debilitated_navamsa(mars)",
    "not retrograde(saturn)",
    "combust(mercury) and not combust(mars)",
    "strong(mars) and strong(jupiter) and not strong(venus)",
    "benefic(jupiter) and benefic(venus) and malefic(mercury) and malefic(moon)",
    "not gandanta(moon)",
    # sign qualities
    "movable(lagna) and movable(jupiter) and dual(sun)",
    "fixed(taurus) and not fixed(aries)",
    "odd_sign(sun) and not odd_sign(jupiter) and odd_sign(sagittarius)",
    # lunar day and mansions
    "not waxing_moon()",
    "tithi() == 26",
    "karana() == 'bava'",
    'karana() == "bava"',
    "nakshatra(moon) == 2 and pada(moon) == 1",
    # lists and groups
    "count(seven) == 7",
    "only(seven, benefics) == [jupiter, venus]",
    "without(benefics, [venus]) == [jupiter]",
    "benefics == [jupiter, venus]",
    "malefics == [sun, moon, mars, mercury, saturn, rahu, ketu]",
    "nodes == [rahu, ketu] and grahas != seven",
    "kendras == [1, 4, 7, 10] and trikonas == [1, 5, 9]",
    "dusthanas == [6, 8, 12] and upachayas == [3, 6, 10, 11]",
    "not fires('mahapurusha.*')",
    # comprehensions
    "any(p in [mars, jupiter]: exalted(p))",
    "all(p in [mars, jupiter]: exalted(p))",
    "not all(p in seven: exalted(p))",
    "count(p in seven: exalted(p)) == 2",
    "select(p in seven: exalted(p)) == [mars, jupiter]",
    "any(h in kendras: any(p in occupants(h): exalted(p)))",
    "all(p in []: exalted(p))",
    # operators
    "house(mars) >= 10 and house(mars) > 9 and house(mars) <= 10 and house(mars) < 11",
    "sign(mars) > sign(jupiter)",
    "mars not in [sun, moon] and mars in seven",
    "not mars in [sun, moon]",
    "house(mars) != 4",
]


@pytest.mark.parametrize("text", TRUE_EXPRESSIONS)
def test_library_on_a_known_chart(text: str, facts: ChartFacts) -> None:
    result, evidence = _eval(text, facts)
    assert result is True, text
    assert evidence


#: Functions exercised with a running dasha and transits in test_periods.py.
PERIOD_TESTED = {
    "natural_friend",
    "natural_enemy",
    "yogakaraka",
    "transit_sign",
    "transit_house",
    "transit_influences",
    "vedha",
}


def test_every_function_is_documented_and_used_in_the_table() -> None:
    used = " ".join(TRUE_EXPRESSIONS)
    for name, function in FUNCTIONS.items():
        assert function.doc, name
        assert function.arities, name
        assert f"{name}(" in used or name in {"day_birth", "male", "female"} | PERIOD_TESTED, name


def test_knowledge_guide_lists_every_function() -> None:
    """knowledge/README.md carries the table written by scripts/rules_reference.py."""
    guide = (default_knowledge_dir() / "README.md").read_text(encoding="utf-8")
    for name, function in FUNCTIONS.items():
        assert f"| `{name}` |" in guide and function.doc in guide, (
            f"re-run rules_reference ({name})"
        )


def test_precedence_not_and_or(facts: ChartFacts) -> None:
    assert _eval("not exalted(mars) or exalted(jupiter)", facts)[0] is True
    assert _eval("not (exalted(mars) or exalted(jupiter))", facts)[0] is False
    assert _eval("exalted(saturn) and exalted(mars) or exalted(jupiter)", facts)[0] is True
    assert _eval("exalted(saturn) and (exalted(mars) or exalted(jupiter))", facts)[0] is False


def test_evidence_names_the_facts_that_decided(facts: ChartFacts) -> None:
    result, evidence = _eval("exalted(mars) and not debilitated(jupiter)", facts)
    assert result and evidence == ["exalted(mars)", "not debilitated(jupiter)"]
    _, evidence = _eval("house(jupiter, moon) in kendras", facts)
    assert evidence == ["house(jupiter, moon) in kendras (4)"]
    _, evidence = _eval("exalted(saturn) or exalted(jupiter)", facts)
    assert evidence == ["exalted(jupiter)"]
    _, evidence = _eval("exchange(lord(10), mars) or associated(lord(10), sun)", facts)
    assert evidence == ["associated(lord(10), sun) [saturn]"]
    _, evidence = _eval("any(p in seven: exalted(p))", facts)
    assert evidence == ["any(p in seven: exalted(p)) [p = mars, jupiter]"]
    _, evidence = _eval("count(p in seven: exalted(p)) >= 2", facts)
    assert evidence == ["count(p in seven: exalted(p)) >= 2 (2: [mars, jupiter])"]


def test_false_expressions_give_no_evidence(facts: ChartFacts) -> None:
    assert _eval("exalted(mars) and exalted(saturn)", facts) == (False, [])


def test_whitespace_and_newlines_are_normalised(facts: ChartFacts) -> None:
    expression = compile_expression("exalted(mars)\n   and\texalted(jupiter)  ")
    assert expression.text == "exalted(mars) and exalted(jupiter)"
    assert expression.evaluate(facts)[1] == ["exalted(mars)", "exalted(jupiter)"]


def test_references_lists_fires_patterns() -> None:
    expression = compile_expression("fires('nabhasa.akriti.*') or fires(\"chandra.adhi\")")
    assert expression.references() == ["nabhasa.akriti.*", "chandra.adhi"]


def test_fires_reads_the_results_of_earlier_rules() -> None:
    facts = ChartFacts.from_spec(SPEC)
    expression = compile_expression("fires('family.*')")
    assert expression.evaluate(facts)[0] is False
    facts.results["family.one"] = False
    facts.results["family.two"] = True
    assert expression.evaluate(facts)[0] is True
    assert compile_expression("fires('family.one')").evaluate(facts)[0] is False


def test_missing_birth_facts_raise(facts: ChartFacts) -> None:
    with pytest.raises(MissingFactError):
        _eval("day_birth()", facts)
    with pytest.raises(MissingFactError):
        _eval("male()", facts)
    known = ChartFacts.from_spec({**SPEC, "day_birth": False, "gender": "female"})
    assert _eval("not day_birth() and female() and not male()", known)[0] is True


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("", "empty"),
        ("   ", "empty"),
        ("house(mars) @ 3", "unexpected character"),
        ("exalted(mars) exalted(jupiter)", "unexpected"),
        ("(exalted(mars)", "expected ')'"),
        ("in_kendra(mars) ==", "more input"),
        ("and exalted(mars)", "unexpected 'and'"),
        ("foo(mars)", "unknown function"),
        ("exalted(pluto)", "unknown name"),
        ("house()", "takes 1 or 2 arguments"),
        ("house(mars, moon, sun)", "takes 1 or 2 arguments"),
        ("fires(mars)", "quoted rule id"),
        ("any(p in seven: exalted(p)) and exalted(p)", "unknown name 'p'"),
        ("any(p in seven: any(p in seven: exalted(p)))", "bad variable name"),
        ("any(mars in seven: exalted(mars))", "bad variable name"),
        ("any(p in seven exalted(p))", "expected ':'"),
    ],
)
def test_syntax_errors(text: str, message: str) -> None:
    with pytest.raises(RuleSyntaxError, match=re.escape(message)):
        compile_expression(text)


@pytest.mark.parametrize(
    "text",
    [
        "house(1) == 1",
        "count(mars) == 1",
        "sign(mars) < mars",
        "house(mars)",
        "lord(mars) == sun",
    ],
)
def test_type_errors_surface_at_evaluation(text: str, facts: ChartFacts) -> None:
    with pytest.raises(RuleTypeError):
        _eval(text, facts)


def test_value_returns_non_boolean_results(facts: ChartFacts) -> None:
    assert compile_expression("placed_in(seven, kendras)").value(facts) == [
        "moon",
        "mars",
        "jupiter",
    ]


def test_describe() -> None:
    assert describe(Counted(["mars", 3])) == "2: [mars, 3]"
    assert describe([1, [2, 3]]) == "[1, [2, 3]]"
