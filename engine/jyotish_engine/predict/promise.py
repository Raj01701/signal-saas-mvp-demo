"""The natal promise of each life domain: how strongly the birth chart supports it.

Every factor is a score from -1 (afflicts the domain) to +1 (supports it) with a
weight and a readable label. The promise is ``0.5 + 0.5 * weighted mean``, so 0.5 is
neutral. The factors follow Parashari practice: the dignity, placement and
Shadbala of the domain houses' lords, the houses' Ashtakavarga bindus, occupants
and aspects, the karakas, the lord's sign in the domain's divisional chart, and the
yogas and readings of the knowledge base. The weights are working values to be
calibrated by the Accuracy Lab (milestone M12).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from jyotish_engine.astro.bodies import GRAHAS, Body
from jyotish_engine.core.dignity import DIGNITY_RULES, Relationship, natural_relationship
from jyotish_engine.core.varga import varga_sign
from jyotish_engine.core.zodiac import SIGN_LORDS, Sign
from jyotish_engine.predict.domains import DomainSpec, karakas
from jyotish_engine.rules.catalogue import RuleResult
from jyotish_engine.rules.facts import DUSTHANA, KENDRA, TRIKONA, UPACHAYA, ChartFacts
from jyotish_engine.rules.schema import Polarity, Strength
from jyotish_engine.rules.schema import ordinal as ordinal_text

RELATION_SCORES = {
    "own": 0.7,
    "great_friend": 0.5,
    "friend": 0.3,
    "neutral": 0.0,
    "enemy": -0.3,
    "great_enemy": -0.5,
}
RULE_WEIGHTS = {Strength.MINOR: 0.1, Strength.MODERATE: 0.2, Strength.MAJOR: 0.35}
POLARITY_SIGN = {Polarity.POSITIVE: 1.0, Polarity.NEGATIVE: -1.0, Polarity.MIXED: 0.0}


@dataclass(frozen=True, slots=True)
class Factor:
    """One scored input to a prediction, with the reason in words."""

    kind: str  # promise | period | trigger | convergence
    label: str
    score: float
    weight: float
    rules: tuple[str, ...] = ()


def clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def name(body: Body) -> str:
    return body.value.title()


def dignity(facts: ChartFacts, body: Body) -> tuple[float, str]:
    """Score (-1 to 1) and description of a graha's sign dignity."""
    if facts.exalted(body):
        score, label = 1.0, "exalted"
    elif facts.debilitated(body):
        score, label = -1.0, "debilitated"
    elif facts.moolatrikona(body):
        score, label = 0.8, "in moolatrikona"
    else:
        relation = facts.relation_to_dispositor(body)
        score = RELATION_SCORES[relation]
        label = (
            "in its own sign" if relation == "own" else f"in a {relation.replace('_', ' ')}'s sign"
        )
    if body not in (Body.SUN, Body.RAHU, Body.KETU) and facts.combust(body):
        score, label = score - 0.4, f"{label}, combust"
    return clamp(score), label


def placement(facts: ChartFacts, body: Body) -> tuple[float, str]:
    """Score of a graha's house from the lagna: kendras and trikonas help, dusthanas hurt."""
    house = facts.house(body)
    if house in KENDRA or house in TRIKONA:
        score = 0.6 if house == 1 else 0.5
    elif house == 11:
        score = 0.3
    elif house == 2:
        score = 0.1
    elif house in DUSTHANA:
        owns_dusthana = any(facts.lord(h) is body for h in DUSTHANA)
        score = 0.2 if owns_dusthana else -0.5  # a dusthana lord in a dusthana: Viparita
    else:
        score = 0.0
    return score, f"in the {ordinal_text(house)} house"


def functional_tone(facts: ChartFacts, body: Body) -> float:
    """How well a graha's period tends to go: dignity, placement and the houses it owns."""
    owned = {h for h in range(1, 13) if facts.lord(h) is body}
    score = dignity(facts, body)[0] + 0.5 * placement(facts, body)[0]
    if owned & {5, 9}:
        score += 0.3
    if owned & set(DUSTHANA) and not owned & (set(KENDRA) | set(TRIKONA)):
        score -= 0.3
    return clamp(score)


def varga_dignity(longitude: float, body: Body, division: int) -> tuple[float, Sign]:
    """A graha's dignity in a divisional chart, judged by sign and natural friendship."""
    sign = varga_sign(longitude, division)
    rule = DIGNITY_RULES[body]
    if sign in rule.exaltation_signs:
        return 1.0, sign
    if Sign((sign + 6) % 12) in rule.exaltation_signs:
        return -1.0, sign
    if sign in rule.own_signs:
        return 0.7, sign
    relation = natural_relationship(body, SIGN_LORDS[sign])
    return {Relationship.FRIEND: 0.3, Relationship.ENEMY: -0.3}.get(relation, 0.0), sign


def domain_promise(
    spec: DomainSpec,
    facts: ChartFacts,
    sav: Sequence[int],
    shadbala_ratio: Mapping[Body, float],
    rules: Sequence[RuleResult],
    gender: str | None = None,
) -> tuple[float, list[Factor]]:
    """The promise (0-1, 0.5 neutral) of ``spec``'s domain and the factors behind it."""
    factors: list[Factor] = []
    for houses, weight in ((spec.primary, 1.0), (spec.secondary, 0.5)):
        for house in houses:
            factors.extend(_house_factors(facts, house, weight, sav, shadbala_ratio))
    for karaka in karakas(spec, gender):
        d, d_label = dignity(facts, karaka)
        p, p_label = placement(facts, karaka)
        label = f"karaka {name(karaka)} {d_label}, {p_label}"
        factors.append(Factor("promise", label, clamp((d + p) / 1.5), 0.6))
    if spec.varga is not None:
        house = spec.primary[0]
        lord = facts.lord(house)
        score, sign = varga_dignity(facts.longitude(lord), lord, spec.varga)
        where = f"{sign.name.title()} in D{spec.varga}"
        label = f"{ordinal_text(house)} lord {name(lord)} in {where}"
        factors.append(Factor("promise", label, score, 0.5))
    related = [r for r in rules if r.present and spec.domain in r.rule.effects.domains]
    if related:
        total = sum(
            POLARITY_SIGN[r.rule.effects.polarity] * RULE_WEIGHTS[r.rule.effects.strength]
            for r in related
        )
        ids = tuple(r.rule.id for r in related)
        factors.append(
            Factor("promise", f"{len(related)} yogas and readings", clamp(total / 1.5), 1.0, ids)
        )
    weight = sum(f.weight for f in factors)
    mean = sum(f.score * f.weight for f in factors) / weight if weight else 0.0
    return 0.5 + 0.5 * mean, factors


def _house_factors(
    facts: ChartFacts,
    house: int,
    weight: float,
    sav: Sequence[int],
    shadbala_ratio: Mapping[Body, float],
) -> list[Factor]:
    lord = facts.lord(house)
    nth = ordinal_text(house)
    d, d_label = dignity(facts, lord)
    p, p_label = placement(facts, lord)
    out = [
        Factor("promise", f"{nth} lord {name(lord)} {d_label}", d, weight),
        Factor("promise", f"{nth} lord {name(lord)} {p_label}", p, 0.8 * weight),
    ]
    if lord in shadbala_ratio:
        ratio = shadbala_ratio[lord]
        label = f"{nth} lord {name(lord)} has {ratio:.2f} of its required Shadbala"
        out.append(Factor("promise", label, clamp(ratio - 1.0), 0.6 * weight))
    sign = facts.sign_of_house(house)
    bindus = sav[sign]
    out.append(
        Factor(
            "promise",
            f"{nth} house has {bindus} Ashtakavarga bindus",
            clamp((bindus - 28) / 8),
            0.8 * weight,
        )
    )
    occupants = facts.occupants(house)
    if occupants:
        malefic_ok = house in UPACHAYA
        score = sum(
            0.3 if b in facts.benefics else (0.15 if malefic_ok else -0.3) for b in occupants
        )
        names = ", ".join(name(b) for b in occupants)
        out.append(Factor("promise", f"{nth} house holds {names}", clamp(score), 0.6 * weight))
    aspecting = [b for b in GRAHAS if b not in occupants and facts.aspects_sign(b, sign)]
    if aspecting:
        score = sum(0.2 if b in facts.benefics else -0.2 for b in aspecting)
        names = ", ".join(name(b) for b in aspecting)
        out.append(
            Factor("promise", f"{nth} house aspected by {names}", clamp(score), 0.5 * weight)
        )
    return out
