"""A small, safe expression language for chart rules.

Rules are written as expressions such as::

    house(jupiter, moon) in kendras and not debilitated(jupiter)
    count(h in kendras: any(p in occupants(h): benefic(p))) >= 3

Grammar::

    expr       := or_expr
    or_expr    := and_expr ("or" and_expr)*
    and_expr   := not_expr ("and" not_expr)*
    not_expr   := "not" not_expr | comparison
    comparison := term (("==" | "!=" | "<" | "<=" | ">" | ">=" | "in" | "not in") term)?
    term       := NUMBER | STRING | NAME | "(" expr ")" | "[" [expr ("," expr)*] "]"
                | NAME "(" [expr ("," expr)*] ")"
                | ("any" | "all" | "count" | "select") "(" NAME "in" expr ":" expr ")"

Names are planets (``sun`` ... ``ketu``), ``lagna``, signs (``aries`` ... ``pisces``),
groups (``benefics``, ``malefics``, ``seven``, ``grahas``, ``nodes``), house groups
(``kendras``, ``trikonas``, ``dusthanas``, ``upachayas``), variables bound by a
comprehension, and the functions in ``FUNCTIONS``. Nothing is evaluated with
Python's ``eval``: names, functions and their arities are checked when a rule is
compiled, and evaluation records the facts that made the rule true (its evidence).
"""

from __future__ import annotations

import fnmatch
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

from jyotish_engine.astro.bodies import GRAHAS, Body
from jyotish_engine.core.aspects import graha_aspected_signs
from jyotish_engine.core.dignity import DIGNITY_RULES, Relationship, natural_relationship
from jyotish_engine.core.zodiac import SIGN_LORDS, Sign
from jyotish_engine.rules.facts import (
    DUSTHANA,
    KENDRA,
    LAGNA,
    NODES,
    SEVEN,
    SIGN_NAMES,
    TRIKONA,
    UPACHAYA,
    ChartFacts,
)
from jyotish_engine.transit.gochara import NO_VEDHA, VEDHA


class RuleSyntaxError(ValueError):
    """An expression that cannot be parsed or refers to unknown names."""


class RuleTypeError(TypeError):
    """A function received a value of the wrong kind while a rule was evaluated."""


@dataclass(frozen=True, slots=True)
class SignValue:
    index: int

    def __str__(self) -> str:
        return Sign(self.index).name.lower()


class Counted(int):
    """The result of ``count(x in ...: ...)``: an int that remembers what it counted."""

    items: list[Any]

    def __new__(cls, items: list[Any]) -> Counted:
        value = super().__new__(cls, len(items))
        value.items = items
        return value


# --- Argument conversion ---------------------------------------------------------------

_PLANET_NAMES = {b.value for b in Body}


def _body(value: Any) -> Body:
    if isinstance(value, Body):
        return value
    if isinstance(value, str) and value in _PLANET_NAMES:
        return Body(value)
    raise RuleTypeError(f"expected a planet, got {value!r}")


def _point(value: Any) -> Body | str:
    """A planet or the lagna."""
    return LAGNA if value == LAGNA else _body(value)


def _sign(f: ChartFacts, value: Any) -> int:
    """A sign given directly, or the sign of a planet or of the lagna."""
    if isinstance(value, SignValue):
        return value.index
    return f.sign_of(_point(value))


def _int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuleTypeError(f"expected a number, got {value!r}")
    return int(value)


def _list(value: Any) -> list[Any]:
    if not isinstance(value, list):
        raise RuleTypeError(f"expected a list, got {value!r}")
    return value


def _bodies(value: Any) -> list[Body]:
    return [_body(v) for v in _list(value)]


def _houses(value: Any) -> set[int]:
    return {_int(v) for v in _list(value)}


# --- Function library ------------------------------------------------------------


def _house(f: ChartFacts, x: Any, ref: Any = LAGNA) -> int:
    return f.house(_point(x), _point(ref))


def _placed_in(f: ChartFacts, ps: Any, hs: Any, ref: Any = LAGNA) -> list[Body]:
    wanted = _houses(hs)
    return [p for p in _bodies(ps) if f.house(p, _point(ref)) in wanted]


def _arc(start: Any, length: Any) -> list[int]:
    return sorted((_int(start) - 1 + i) % 12 + 1 for i in range(_int(length)))


def _between_nodes(f: ChartFacts, ps: Any) -> bool:
    """All ``ps`` strictly on one side of the Rahu-Ketu axis (by longitude)."""
    rahu = f.positions[Body.RAHU]
    offsets = [(f.positions[p] - rahu) % 360.0 for p in _bodies(ps)]
    return all(0.0 < o < 180.0 for o in offsets) or all(o > 180.0 for o in offsets)


def _conjunct(f: ChartFacts, a: Any, b: Any) -> bool:
    x, y = _point(a), _point(b)
    return x != y and f.sign_of(x) == f.sign_of(y)


def _aspects(f: ChartFacts, a: Any, b: Any) -> bool:
    x, y = _body(a), _point(b)
    return x != y and f.aspects(x, y)


def _mutual_aspect(f: ChartFacts, a: Any, b: Any) -> bool:
    return _aspects(f, a, b) and _aspects(f, b, a)


def _exchange(f: ChartFacts, a: Any, b: Any) -> bool:
    x, y = _body(a), _body(b)
    return x != y and f.dispositor(x) == y and f.dispositor(y) == x


def _associated(f: ChartFacts, a: Any, b: Any) -> bool:
    """Parashari sambandha: conjunction, mutual aspect or exchange (two planets)."""
    return _conjunct(f, a, b) or _mutual_aspect(f, a, b) or _exchange(f, a, b)


def _influences(f: ChartFacts, a: Any, b: Any) -> bool:
    """``a`` joins (same sign) or aspects ``b``."""
    return _conjunct(f, a, b) or _aspects(f, a, b)


def _modality(f: ChartFacts, x: Any) -> int:
    return _sign(f, x) % 3


def _exalted_in(f: ChartFacts, sign: Any) -> list[Body]:
    index = _sign(f, sign)
    return [p for p in SEVEN if Sign(index) in DIGNITY_RULES[p].exaltation_signs]


def _navamsa_dignity(f: ChartFacts, p: Any, offset: int) -> bool:
    body = _body(p)
    return Sign((f.navamsa_sign(body) + offset) % 12) in DIGNITY_RULES[body].exaltation_signs


def _transit_influences(f: ChartFacts, p: Any, h: Any, ref: Any = LAGNA) -> bool:
    body = _body(p)
    target = f.sign_of_house(_int(h), _point(ref))
    sign = f.transit_sign(body)
    return target == sign or target in graha_aspected_signs(body, sign, f.node_aspects_5_9)


def _vedha(f: ChartFacts, p: Any) -> bool:
    """A favourable transit from the natal Moon obstructed by a graha in its vedha house."""
    body = _body(p)
    blocked = VEDHA[body].get(f.transit_house(body, Body.MOON))
    if blocked is None:
        return False
    return any(
        other is not body
        and frozenset({body, other}) not in NO_VEDHA
        and f.transit_house(other, Body.MOON) == blocked
        for other in f.transits or {}
    )


def _yogakaraka(f: ChartFacts, p: Any) -> bool:
    owned = {h for h in range(1, 13) if f.lord(h) is _body(p)}
    return bool(owned & {4, 7, 10}) and bool(owned & {5, 9})


def _fires(f: ChartFacts, pattern: Any) -> bool:
    return any(fired for rid, fired in f.results.items() if fnmatch.fnmatchcase(rid, pattern))


@dataclass(frozen=True, slots=True)
class Function:
    arities: tuple[int, ...]
    impl: Callable[..., Any]
    doc: str


def _fn(arities: tuple[int, ...], doc: str, impl: Callable[..., Any]) -> Function:
    return Function(arities, impl, doc)


#: The function library: name -> arities, implementation(facts, *args), description.
FUNCTIONS: dict[str, Function] = {
    # positions and houses
    "house": _fn((1, 2), "house of x counted from ref (default lagna)", _house),
    "sign": _fn((1,), "sign of x", lambda f, x: SignValue(_sign(f, x))),
    "navamsa": _fn(
        (1,), "navamsa (D9) sign of x", lambda f, x: SignValue(f.navamsa_sign(_point(x)))
    ),
    "vargottama": _fn(
        (1,),
        "x in the same sign in D1 and D9",
        lambda f, x: f.navamsa_sign(_point(x)) == _sign(f, x),
    ),
    "lord": _fn(
        (1, 2), "lord of house h counted from ref", lambda f, h, r=LAGNA: f.lord(_int(h), _point(r))
    ),
    "lord_of": _fn((1,), "lord of a sign", lambda f, s: SIGN_LORDS[Sign(_sign(f, s))]),
    "dispositor": _fn((1,), "lord of the sign occupied by x", lambda f, x: f.dispositor(_point(x))),
    "exaltation_lord": _fn(
        (1,), "lord of p's exaltation sign", lambda f, p: f.exaltation_lord(_body(p))
    ),
    "exalted_in": _fn((1,), "planets (of the seven) exalted in a sign", _exalted_in),
    "occupants": _fn(
        (1, 2), "grahas in house h from ref", lambda f, h, r=LAGNA: f.occupants(_int(h), _point(r))
    ),
    "companions": _fn(
        (1,),
        "other grahas in the sign of x",
        lambda f, x: [b for b in GRAHAS if b != x and f.signs[b] == _sign(f, x)],
    ),
    "empty": _fn(
        (1, 2),
        "no graha in house h from ref",
        lambda f, h, r=LAGNA: not f.occupants(_int(h), _point(r)),
    ),
    "placed_in": _fn((2, 3), "the planets of ps in houses hs from ref", _placed_in),
    "all_in_houses": _fn(
        (2, 3),
        "every planet of ps in houses hs from ref",
        lambda f, ps, hs, r=LAGNA: len(_placed_in(f, ps, hs, r)) == len(_list(ps)),
    ),
    "any_in_houses": _fn(
        (2, 3),
        "some planet of ps in houses hs from ref",
        lambda f, ps, hs, r=LAGNA: bool(_placed_in(f, ps, hs, r)),
    ),
    "count_in_houses": _fn(
        (2, 3),
        "number of planets of ps in houses hs from ref",
        lambda f, ps, hs, r=LAGNA: len(_placed_in(f, ps, hs, r)),
    ),
    "houses_of": _fn(
        (1, 2),
        "sorted houses occupied by ps, from ref",
        lambda f, ps, r=LAGNA: sorted({f.house(p, _point(r)) for p in _bodies(ps)}),
    ),
    "signs_occupied": _fn(
        (1,), "number of signs occupied by ps", lambda f, ps: len({f.signs[p] for p in _bodies(ps)})
    ),
    "arc": _fn(
        (2,), "sorted houses of the arc of n houses starting at house h", lambda f, h, n: _arc(h, n)
    ),
    "in_kendra": _fn(
        (1, 2), "x in house 1, 4, 7 or 10 from ref", lambda f, x, r=LAGNA: _house(f, x, r) in KENDRA
    ),
    "in_trikona": _fn(
        (1, 2), "x in house 1, 5 or 9 from ref", lambda f, x, r=LAGNA: _house(f, x, r) in TRIKONA
    ),
    "in_dusthana": _fn(
        (1, 2), "x in house 6, 8 or 12 from ref", lambda f, x, r=LAGNA: _house(f, x, r) in DUSTHANA
    ),
    "in_upachaya": _fn(
        (1, 2),
        "x in house 3, 6, 10 or 11 from ref",
        lambda f, x, r=LAGNA: _house(f, x, r) in UPACHAYA,
    ),
    "between_nodes": _fn((1,), "all ps on one side of the Rahu-Ketu axis", _between_nodes),
    # relations
    "conjunct": _fn((2,), "a and b (planet or lagna) in the same sign", _conjunct),
    "aspects": _fn((2,), "graha drishti of planet a on b (planet or lagna)", _aspects),
    "aspects_house": _fn(
        (2, 3),
        "graha drishti of a on house h from ref",
        lambda f, a, h, r=LAGNA: f.aspects_sign(_body(a), f.sign_of_house(_int(h), _point(r))),
    ),
    "aspecting": _fn(
        (1,),
        "grahas whose graha drishti falls on x",
        lambda f, x: [b for b in GRAHAS if _aspects(f, b, x)],
    ),
    "mutual_aspect": _fn((2,), "a and b aspect each other", _mutual_aspect),
    "exchange": _fn((2,), "a and b occupy each other's signs", _exchange),
    "associated": _fn((2,), "conjunction, mutual aspect or exchange of a and b", _associated),
    "influences": _fn((2,), "a joins or aspects b", _influences),
    # dignity and states
    "exalted": _fn((1,), "p in its exaltation sign", lambda f, p: f.exalted(_body(p))),
    "debilitated": _fn((1,), "p in its debilitation sign", lambda f, p: f.debilitated(_body(p))),
    "own_sign": _fn((1,), "p in a sign it owns", lambda f, p: f.own_sign(_body(p))),
    "moolatrikona": _fn((1,), "p in its moolatrikona range", lambda f, p: f.moolatrikona(_body(p))),
    "dignified": _fn(
        (1,), "p exalted, in moolatrikona or in its own sign", lambda f, p: f.dignified(_body(p))
    ),
    "friendly_sign": _fn(
        (1,), "p in its own or a friend's sign", lambda f, p: f.friendly_sign(_body(p))
    ),
    "enemy_sign": _fn((1,), "p in an enemy's sign", lambda f, p: f.enemy_sign(_body(p))),
    "exalted_navamsa": _fn(
        (1,), "p in its exaltation sign in D9", lambda f, p: _navamsa_dignity(f, p, 0)
    ),
    "debilitated_navamsa": _fn(
        (1,), "p in its debilitation sign in D9", lambda f, p: _navamsa_dignity(f, p, 6)
    ),
    "retrograde": _fn((1,), "p retrograde", lambda f, p: _body(p) in f.retrograde),
    "combust": _fn(
        (1,), "p within its combustion orb of the Sun", lambda f, p: f.combust(_body(p))
    ),
    "strong": _fn(
        (1,), "working strength test (ChartFacts.strong)", lambda f, p: f.strong(_body(p))
    ),
    "benefic": _fn((1,), "p a natural benefic here", lambda f, p: _body(p) in f.benefics),
    "malefic": _fn((1,), "p a natural malefic here", lambda f, p: _body(p) not in f.benefics),
    "gandanta": _fn(
        (1,), "x within a pada of a water-fire junction", lambda f, x: f.gandanta(_point(x))
    ),
    # sign qualities
    "movable": _fn((1,), "sign (or sign of x) is movable", lambda f, x: _modality(f, x) == 0),
    "fixed": _fn((1,), "sign (or sign of x) is fixed", lambda f, x: _modality(f, x) == 1),
    "dual": _fn((1,), "sign (or sign of x) is dual", lambda f, x: _modality(f, x) == 2),
    "odd_sign": _fn(
        (1,), "sign (or sign of x) is odd: Aries, Gemini, ...", lambda f, x: _sign(f, x) % 2 == 0
    ),
    # lunar day and mansions
    "waxing_moon": _fn((0,), "Moon in the bright half (Shukla paksha)", lambda f: f.waxing),
    "tithi": _fn((0,), "lunar day 1-30 (30 = Amavasya)", lambda f: f.tithi),
    "karana": _fn((0,), "karana name, such as 'vishti'", lambda f: f.karana),
    "nakshatra": _fn(
        (1,), "nakshatra of x, 1 (Ashwini) to 27 (Revati)", lambda f, x: f.nakshatra(_point(x))
    ),
    "pada": _fn((1,), "nakshatra pada (1-4) of x", lambda f, x: f.pada(_point(x))),
    "natural_friend": _fn(
        (2,),
        "a counts b as a natural friend (BPHS)",
        lambda f, a, b: natural_relationship(_body(a), _body(b)) is Relationship.FRIEND,
    ),
    "natural_enemy": _fn(
        (2,),
        "a counts b as a natural enemy (BPHS)",
        lambda f, a, b: natural_relationship(_body(a), _body(b)) is Relationship.ENEMY,
    ),
    "yogakaraka": _fn((1,), "p lords a kendra (4, 7, 10) and a trikona (5, 9)", _yogakaraka),
    # period: transits (dasha lords are the names md and ad)
    "transit_sign": _fn(
        (1,), "sign occupied by transiting p", lambda f, p: SignValue(f.transit_sign(_body(p)))
    ),
    "transit_house": _fn(
        (1, 2),
        "house of transiting p counted from natal ref (default lagna)",
        lambda f, p, r=LAGNA: f.transit_house(_body(p), _point(r)),
    ),
    "transit_influences": _fn(
        (2, 3),
        "transiting p occupies or aspects house h from natal ref",
        _transit_influences,
    ),
    "vedha": _fn((1,), "p's favourable transit from the Moon is obstructed (vedha)", _vedha),
    # birth facts
    "day_birth": _fn((0,), "born between sunrise and sunset", lambda f: f.require_day_birth()),
    "male": _fn((0,), "native is male", lambda f: f.require_gender() == "male"),
    "female": _fn((0,), "native is female", lambda f: f.require_gender() == "female"),
    # lists
    "count": _fn((1,), "length of a list", lambda f, xs: len(_list(xs))),
    "only": _fn(
        (2,),
        "items of xs that are in group",
        lambda f, xs, group: [x for x in _list(xs) if x in _list(group)],
    ),
    "without": _fn(
        (2,),
        "items of xs that are not in group",
        lambda f, xs, group: [x for x in _list(xs) if x not in _list(group)],
    ),
    # other rules
    "fires": _fn((1,), "a rule matching the quoted id pattern is present", _fires),
}

GROUPS: dict[str, Callable[[ChartFacts], list[Any]]] = {
    "benefics": lambda f: [b for b in SEVEN if b in f.benefics],
    "malefics": lambda f: [b for b in GRAHAS if b not in f.benefics],
    "seven": lambda f: list(SEVEN),
    "grahas": lambda f: list(GRAHAS),
    "nodes": lambda f: list(NODES),
    "kendras": lambda f: list(KENDRA),
    "trikonas": lambda f: list(TRIKONA),
    "dusthanas": lambda f: list(DUSTHANA),
    "upachayas": lambda f: list(UPACHAYA),
}

#: Names bound to the running period: the mahadasha and antardasha lords.
CONTEXT_NAMES: dict[str, Callable[[ChartFacts], Body]] = {
    "md": lambda f: f.dasha_lord(1),
    "ad": lambda f: f.dasha_lord(2),
}

CONSTANT_NAMES = (
    {b.value for b in GRAHAS} | {LAGNA} | set(SIGN_NAMES) | set(GROUPS) | set(CONTEXT_NAMES)
)
COMPREHENSIONS = ("any", "all", "count", "select")
KEYWORDS = {"and", "or", "not", "in"}


def _constant(name: str, facts: ChartFacts) -> Any:
    if name == LAGNA:
        return LAGNA
    if name in SIGN_NAMES:
        return SignValue(SIGN_NAMES[name])
    if name in GROUPS:
        return GROUPS[name](facts)
    if name in CONTEXT_NAMES:
        return CONTEXT_NAMES[name](facts)
    return Body(name)


def describe(value: Any) -> str:
    """A short human-readable rendering of a rule value."""
    if isinstance(value, Counted):
        return f"{int(value)}: " + describe(value.items)
    if isinstance(value, Body):
        return value.value
    if isinstance(value, list):
        return "[" + ", ".join(describe(v) for v in value) + "]"
    return str(value)


# --- AST ------------------------------------------------------------------------------

Env = dict[str, Any]


class Node:
    text: str

    def evaluate(self, facts: ChartFacts, env: Env, evidence: list[str]) -> Any:
        raise NotImplementedError

    def children(self) -> Iterator[Node]:
        return iter(())

    def walk(self) -> Iterator[Node]:
        yield self
        for child in self.children():
            yield from child.walk()


@dataclass(slots=True)
class Literal(Node):
    value: Any
    text: str

    def evaluate(self, facts: ChartFacts, env: Env, evidence: list[str]) -> Any:
        return self.value


@dataclass(slots=True)
class Name(Node):
    name: str
    text: str

    def evaluate(self, facts: ChartFacts, env: Env, evidence: list[str]) -> Any:
        return _constant(self.name, facts)


@dataclass(slots=True)
class Variable(Node):
    name: str
    text: str

    def evaluate(self, facts: ChartFacts, env: Env, evidence: list[str]) -> Any:
        return env[self.name]


@dataclass(slots=True)
class ListNode(Node):
    items: list[Node]
    text: str

    def evaluate(self, facts: ChartFacts, env: Env, evidence: list[str]) -> Any:
        return [item.evaluate(facts, env, []) for item in self.items]

    def children(self) -> Iterator[Node]:
        return iter(self.items)


def _derived(node: Node) -> bool:
    """Whether a node's value is worth showing next to its text in evidence."""
    if isinstance(node, Name):
        return node.name in CONTEXT_NAMES
    return isinstance(node, (Call, Variable, Comprehension))


@dataclass(slots=True)
class Call(Node):
    name: str
    args: list[Node]
    text: str

    def evaluate(self, facts: ChartFacts, env: Env, evidence: list[str]) -> Any:
        values = [arg.evaluate(facts, env, []) for arg in self.args]
        result = FUNCTIONS[self.name].impl(facts, *values)
        if result is True:
            derived = [v for a, v in zip(self.args, values, strict=True) if _derived(a)]
            suffix = f" [{', '.join(describe(v) for v in derived)}]" if derived else ""
            evidence.append(self.text + suffix)
        return result

    def children(self) -> Iterator[Node]:
        return iter(self.args)


@dataclass(slots=True)
class Comprehension(Node):
    kind: str  # any | all | count | select
    variable: str
    iterable: Node
    body: Node
    text: str

    def evaluate(self, facts: ChartFacts, env: Env, evidence: list[str]) -> Any:
        items = _list(self.iterable.evaluate(facts, env, []))
        matched = []
        for item in items:
            if self.body.evaluate(facts, {**env, self.variable: item}, []):
                matched.append(item)
            elif self.kind == "all":
                return False
        if self.kind == "select":
            return matched
        if self.kind == "count":
            return Counted(matched)
        result = bool(matched) if self.kind == "any" else True
        if result:
            shown = ", ".join(describe(m) for m in matched)
            evidence.append(f"{self.text} [{self.variable} = {shown}]" if shown else self.text)
        return result

    def children(self) -> Iterator[Node]:
        yield self.iterable
        yield self.body


def _number(value: Any) -> float:
    if isinstance(value, SignValue):
        return float(value.index)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuleTypeError(f"expected a number, got {value!r}")
    return float(value)


@dataclass(slots=True)
class Compare(Node):
    op: str
    left: Node
    right: Node
    text: str

    def evaluate(self, facts: ChartFacts, env: Env, evidence: list[str]) -> bool:
        a = self.left.evaluate(facts, env, [])
        b = self.right.evaluate(facts, env, [])
        if self.op in ("in", "not in"):
            inside = any(a == item for item in _list(b))
            result = inside if self.op == "in" else not inside
        elif self.op == "==":
            result = bool(a == b)
        elif self.op == "!=":
            result = bool(a != b)
        else:
            left, right = _number(a), _number(b)
            result = {
                "<": left < right,
                "<=": left <= right,
                ">": left > right,
                ">=": left >= right,
            }[self.op]
        if result:
            evidence.append(self._evidence(a, facts, env))
        return result

    def _evidence(self, value: Any, facts: ChartFacts, env: Env) -> str:
        if not (_derived(self.left) or isinstance(value, Counted)):
            return self.text
        shown = [describe(value)]
        if isinstance(self.left, Call):  # name the planets behind lord(...), etc.
            shown += [
                f"{arg.text} = {describe(arg.evaluate(facts, env, []))}"
                for arg in self.left.args
                if _derived(arg)
            ]
        return f"{self.text} ({'; '.join(shown)})"

    def children(self) -> Iterator[Node]:
        yield self.left
        yield self.right


@dataclass(slots=True)
class Not(Node):
    operand: Node
    text: str

    def evaluate(self, facts: ChartFacts, env: Env, evidence: list[str]) -> bool:
        result = not self.operand.evaluate(facts, env, [])
        if result:
            evidence.append(self.text)
        return result

    def children(self) -> Iterator[Node]:
        yield self.operand


@dataclass(slots=True)
class BoolOp(Node):
    op: str  # "and" | "or"
    operands: list[Node]
    text: str

    def evaluate(self, facts: ChartFacts, env: Env, evidence: list[str]) -> bool:
        if self.op == "and":
            collected: list[str] = []
            for operand in self.operands:
                if not operand.evaluate(facts, env, collected):
                    return False
            evidence.extend(collected)
            return True
        for operand in self.operands:
            collected = []
            if operand.evaluate(facts, env, collected):
                evidence.extend(collected)
                return True
        return False

    def children(self) -> Iterator[Node]:
        return iter(self.operands)


# --- Parser -------------------------------------------------------------------------------

_TOKEN = re.compile(
    r"\s*(?:(?P<num>\d+(?:\.\d+)?)|(?P<str>'[^']*'|\"[^\"]*\")|(?P<name>[a-z_][a-z0-9_]*)"
    r"|(?P<op>==|!=|<=|>=|<|>)|(?P<punct>[()\[\],:]))"
)
_IDENTIFIER = re.compile(r"[a-z_][a-z0-9_]*")

Token = tuple[str, str, int]


def _tokenize(text: str) -> list[Token]:
    tokens = []
    position = 0
    while text[position:].strip():
        match = _TOKEN.match(text, position)
        if not match:
            raise RuleSyntaxError(f"unexpected character at {position} in: {text!r}")
        kind = match.lastgroup or ""
        tokens.append((kind, match.group(kind), match.start(kind)))
        position = match.end()
    return tokens


class _Parser:
    def __init__(self, text: str) -> None:
        self.text = text
        self.tokens = _tokenize(text)
        self.index = 0
        self.scope: list[str] = []

    def peek(self, offset: int = 0) -> Token | None:
        i = self.index + offset
        return self.tokens[i] if i < len(self.tokens) else None

    def take(self, value: str | None = None) -> Token:
        token = self.peek()
        if token is None or (value is not None and token[1] != value):
            found = "the end" if token is None else repr(token[1])
            wanted = repr(value) if value else "more input"
            raise RuleSyntaxError(f"expected {wanted}, found {found} in: {self.text!r}")
        self.index += 1
        return token

    def span(self, start: int) -> str:
        end = self.tokens[self.index - 1]
        return self.text[start : end[2] + len(end[1])]

    def parse(self) -> Node:
        if not self.tokens:
            raise RuleSyntaxError("empty rule expression")
        node = self.or_expr()
        token = self.peek()
        if token is not None:
            raise RuleSyntaxError(f"unexpected {token[1]!r} in: {self.text!r}")
        return node

    def or_expr(self) -> Node:
        start = self._start()
        operands = [self.and_expr()]
        while self._is("or"):
            self.take()
            operands.append(self.and_expr())
        return operands[0] if len(operands) == 1 else BoolOp("or", operands, self.span(start))

    def and_expr(self) -> Node:
        start = self._start()
        operands = [self.not_expr()]
        while self._is("and"):
            self.take()
            operands.append(self.not_expr())
        return operands[0] if len(operands) == 1 else BoolOp("and", operands, self.span(start))

    def not_expr(self) -> Node:
        start = self._start()
        if self._is("not") and not self._is("in", 1):
            self.take()
            operand = self.not_expr()
            return Not(operand, self.span(start))
        return self.comparison()

    def comparison(self) -> Node:
        start = self._start()
        left = self.term()
        token = self.peek()
        if token is None:
            return left
        if token[0] == "op" or token[1] == "in":
            op = self.take()[1]
        elif token[1] == "not" and self._is("in", 1):
            self.take()
            self.take()
            op = "not in"
        else:
            return left
        right = self.term()
        return Compare(op, left, right, self.span(start))

    def sequence(self, close: str) -> list[Node]:
        items: list[Node] = []
        if not self._is(close):
            items.append(self.or_expr())
            while self._is(","):
                self.take()
                items.append(self.or_expr())
        self.take(close)
        return items

    def term(self) -> Node:
        start = self._start()
        kind, value, _ = self.take()
        if kind == "num":
            return Literal(float(value) if "." in value else int(value), value)
        if kind == "str":
            return Literal(value[1:-1], value)
        if value == "(":
            node = self.or_expr()
            self.take(")")
            return node
        if value == "[":
            return ListNode(self.sequence("]"), self.span(start))
        if kind != "name" or value in KEYWORDS:
            raise RuleSyntaxError(f"unexpected {value!r} in: {self.text!r}")
        if value in COMPREHENSIONS and self._is("(") and self._is("in", 2):
            return self.comprehension(value, start)
        if self._is("("):
            return self.call(value, start)
        if value in self.scope:
            return Variable(value, value)
        if value not in CONSTANT_NAMES:
            raise RuleSyntaxError(f"unknown name {value!r} in: {self.text!r}")
        return Name(value, value)

    def call(self, name: str, start: int) -> Node:
        if name not in FUNCTIONS:
            raise RuleSyntaxError(f"unknown function {name!r} in: {self.text!r}")
        self.take("(")
        args = self.sequence(")")
        arities = FUNCTIONS[name].arities
        if len(args) not in arities:
            counts = " or ".join(map(str, arities))
            raise RuleSyntaxError(f"{name}() takes {counts} arguments, got {len(args)}")
        if name == "fires" and not (
            isinstance(args[0], Literal) and isinstance(args[0].value, str)
        ):
            raise RuleSyntaxError("fires() takes a quoted rule id or pattern")
        return Call(name, args, self.span(start))

    def comprehension(self, kind: str, start: int) -> Node:
        self.take("(")
        variable = self.take()[1]
        reserved = CONSTANT_NAMES | set(FUNCTIONS) | KEYWORDS | set(COMPREHENSIONS)
        if not _IDENTIFIER.fullmatch(variable) or variable in reserved or variable in self.scope:
            raise RuleSyntaxError(f"bad variable name {variable!r} in: {self.text!r}")
        self.take("in")
        iterable = self.or_expr()
        self.take(":")
        self.scope.append(variable)
        body = self.or_expr()
        self.scope.pop()
        self.take(")")
        return Comprehension(kind, variable, iterable, body, self.span(start))

    def _start(self) -> int:
        token = self.peek()
        return token[2] if token else len(self.text)

    def _is(self, value: str, offset: int = 0) -> bool:
        token = self.peek(offset)
        return token is not None and token[1] == value


@dataclass(frozen=True, slots=True)
class Expression:
    """A compiled rule expression."""

    text: str
    root: Node

    def evaluate(self, facts: ChartFacts) -> tuple[bool, list[str]]:
        """Truth value plus evidence (empty when false)."""
        evidence: list[str] = []
        result = self.root.evaluate(facts, {}, evidence)
        if not isinstance(result, bool):
            raise RuleTypeError(f"{self.text!r} gave {describe(result)}, not true or false")
        return result, (evidence if result else [])

    def value(self, facts: ChartFacts) -> Any:
        return self.root.evaluate(facts, {}, [])

    def references(self) -> list[str]:
        """Rule ids or patterns this expression refers to with ``fires``."""
        return [
            str(node.args[0].value)  # type: ignore[attr-defined]
            for node in self.root.walk()
            if isinstance(node, Call) and node.name == "fires"
        ]


def compile_expression(text: str) -> Expression:
    """Parse and check an expression; whitespace (including newlines) is normalised."""
    text = " ".join(text.split())
    return Expression(text, _Parser(text).parse())
