"""Dasha and transit rules for ``knowledge/dasha/`` and ``knowledge/transit/``.

Used by ``scripts/generate_readings.py``. As with the natal readings, every result
is our own wording of the cited chapters and stays a draft until reviewed. The
test charts carry the period: ``dasha`` (running lords) and ``transit`` (positions
of the transiting grahas).
"""

from __future__ import annotations

from typing import Any

from generate_rule_families import HOUSE_MATTERS, LORDS, SIGNS, citation, ordinal, sign_of_house

#: House matters for double-transit texts (the 8th read as obstacles, not longevity).
MATTERS = {**HOUSE_MATTERS, 8: "obstacles, research and hidden matters"}

GRAHAS = ("sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu", "ketu")
SEVEN = GRAHAS[:7]
POLARITY = {"+": "positive", "-": "negative", "~": "mixed"}
EXALTED = {"sun": 0, "moon": 1, "mars": 9, "mercury": 5, "jupiter": 3, "venus": 11, "saturn": 6}
#: Life domains each graha's periods speak for.
PLANET_DOMAINS = {
    "sun": ["status", "parents"],
    "moon": ["character", "parents"],
    "mars": ["conflict", "property"],
    "mercury": ["intellect", "education"],
    "jupiter": ["fortune", "children"],
    "venus": ["marriage", "wealth"],
    "saturn": ["career"],
    "rahu": ["travel", "career"],
    "ketu": ["spirituality"],
}
DOMAINS = {
    1: ["self", "health"],
    2: ["wealth"],
    3: ["siblings", "character"],
    4: ["property", "parents"],
    5: ["children", "intellect"],
    6: ["conflict", "health"],
    7: ["marriage"],
    8: ["health", "spirituality"],
    9: ["fortune", "parents"],
    10: ["career", "status"],
    11: ["wealth"],
    12: ["wealth", "spirituality", "travel"],
}
BPHS_DASHA = citation("bphs", edition="santhanam", locator="Effects of the dashas")
BPHS_ANTARDASHA = citation("bphs", edition="santhanam", locator="Effects of the antardashas")
PD_DASHA = citation("phaladeepika", edition="sastri", chapter=19)
PD_ANTARDASHA = citation("phaladeepika", edition="sastri", chapter=20)
PD_GOCHARA = citation("phaladeepika", edition="sastri", chapter=26)

# --- Texts ------------------------------------------------------------------------

#: The mahadasha of the lord of each house.
MD_LORDSHIP = {
    1: ("+", "Health, confidence and personal initiative come to the fore; new beginnings."),
    2: (
        "~",
        "Wealth, family affairs and speech come to the fore; savings grow if the lord is strong.",
    ),
    3: ("~", "Initiative, siblings, short journeys and communication; results follow effort."),
    4: ("+", "Home, property, vehicles, mother and education come to the fore."),
    5: ("+", "Children, learning, creativity and merit come to the fore; good for study."),
    6: ("-", "Competition, debts, disputes and health matters; service and hard work succeed."),
    7: ("~", "Marriage, partnerships, business and travel come to the fore."),
    8: ("-", "Obstacles, sudden changes, research and inheritance come to the fore."),
    9: ("+", "Fortune, dharma, teachers, father and long journeys; a favourable period."),
    10: (
        "+",
        "Career, status and public deeds come to the fore; advancement if the lord is strong.",
    ),
    11: ("+", "Gains, income, friends and fulfilled desires come to the fore."),
    12: ("-", "Expenses, travel abroad, retreat and spiritual pursuits; losses need watching."),
}
#: The mahadasha lord's house.
MD_PLACEMENT = {
    1: ("+", "Personal matters, health and self-expression flourish."),
    2: ("+", "Wealth, family and speech are active."),
    3: ("~", "Effort, courage and communication; results come through initiative."),
    4: ("+", "Home, comforts and property are active."),
    5: ("+", "Learning, children and creative work flourish."),
    6: ("-", "Disputes, debts or health matters, with success in competition."),
    7: ("~", "Relationships, partnerships and travel are active."),
    8: ("-", "Obstacles, sudden events and hidden matters."),
    9: ("+", "Fortune, dharma and long journeys."),
    10: ("+", "Career and public life are active."),
    11: ("+", "Gains and the fulfilment of desires."),
    12: ("-", "Expenses, distance from home and retreat."),
}
#: Each graha's mahadasha when strong, then when weak.
PLANET_DASHA = {
    "sun": (
        "Honours, authority and gains through government or father; vigour and fame.",
        "Friction with authority or father, low vitality and loss of position.",
    ),
    "moon": (
        "Comforts, popularity and gains through the public; peace of mind.",
        "Emotional unrest, changes of residence and strain concerning mother.",
    ),
    "mars": (
        "Gains through land, courage, command and competition; victory over rivals.",
        "Quarrels, accidents, property disputes and friction with siblings.",
    ),
    "mercury": (
        "Learning, trade, writing and communication prosper; new friendships.",
        "Nervous strain, mistakes in trade or documents, and disputes.",
    ),
    "jupiter": (
        "Wisdom, children, wealth, honour and religious merit increase.",
        "Loss of respect or wealth; trouble concerning children or teachers.",
    ),
    "venus": (
        "Marriage, comforts, vehicles, arts and luxuries; a pleasant period.",
        "Disappointments in relationships and overspending on pleasures.",
    ),
    "saturn": (
        "A steady rise through discipline and service; property and followers.",
        "Hardship, delays, fatigue and losses; heavy burdens of work.",
    ),
}
#: Results of an antardasha in the mahadasha of the first graha (general tenor).
PAIRS: dict[str, dict[str, tuple[str, str]]] = {
    "sun": {
        "sun": ("~", "Honours and gains from authority, with friction with superiors."),
        "moon": ("+", "Gains through government and the public; new comforts; ease of mind."),
        "mars": ("+", "Gains of land, courage and success in disputes; a heated temper."),
        "rahu": ("-", "Strain, anxiety, friction with authority and unexpected losses."),
        "jupiter": ("+", "Honours, religious merit, children and success through advice."),
        "saturn": ("-", "Friction with father or superiors, delays and burdens at work."),
        "mercury": ("~", "Gains through learning, trade and communication; nervous strain."),
        "ketu": ("-", "Anxiety, separation and pressure; a turn towards the spiritual."),
        "venus": ("~", "Comforts and the arts, but friction with authority."),
    },
    "moon": {
        "moon": ("+", "Comforts, popularity and emotional fulfilment."),
        "mars": ("~", "Energy and gains through property, with emotional friction."),
        "rahu": ("-", "Anxiety, confusion and restlessness; unusual contacts."),
        "jupiter": ("+", "Wisdom, children, comforts and honours."),
        "saturn": ("-", "Sadness, fatigue and delays; strain concerning mother."),
        "mercury": ("+", "Learning, trade and communication flourish."),
        "ketu": ("-", "Emotional detachment, loss and anxiety."),
        "venus": ("+", "Comforts, arts, vehicles and pleasant relationships."),
        "sun": ("~", "Honours with emotional strain; dealings with authority."),
    },
    "mars": {
        "mars": ("~", "Courage and gains through land, with quarrels and accidents to avoid."),
        "rahu": ("-", "Conflicts, accidents and disputes; unusual risks."),
        "jupiter": ("+", "Gains of land, honours and success in ventures."),
        "saturn": ("-", "Hardship, disputes and fatigue; obstacles."),
        "mercury": ("~", "Gains through trade and skill, with friction and anxiety."),
        "ketu": ("-", "Sudden setbacks, injuries or disputes; restlessness."),
        "venus": ("~", "Passion, comforts and relationships; overspending."),
        "sun": ("+", "Authority, courage and victory; gains through government."),
        "moon": ("+", "Gains through property and the public; comforts."),
    },
    "rahu": {
        "rahu": ("~", "Ambition and unconventional gains amid confusion and anxiety."),
        "jupiter": ("+", "Honours, learning and gains; ethical growth."),
        "saturn": ("-", "Hardship, delays, disputes and burdens."),
        "mercury": ("+", "Gains through intellect, trade and technology."),
        "ketu": ("-", "Confusion, anxiety and sudden changes."),
        "venus": ("~", "Comforts and relationships with unconventional turns; indulgence."),
        "sun": ("-", "Friction with authority, strain and loss of position."),
        "moon": ("-", "Emotional unrest, anxiety and changes of residence."),
        "mars": ("-", "Conflicts, accidents and disputes over property."),
    },
    "jupiter": {
        "jupiter": ("+", "Wisdom, children, honours and prosperity."),
        "saturn": ("~", "Steady progress with burdens and delays; service."),
        "mercury": ("~", "Learning and trade, with differences of opinion."),
        "ketu": ("~", "Spiritual growth with material detachment."),
        "venus": ("~", "Comforts and the arts, but differing values."),
        "sun": ("+", "Honours, authority and religious merit."),
        "moon": ("+", "Comforts, popularity and prosperity."),
        "mars": ("+", "Gains of land, courage and success."),
        "rahu": ("-", "Confusion, ethical dilemmas and obstacles."),
    },
    "saturn": {
        "saturn": ("~", "Discipline, hard work and slow gains; burdens."),
        "mercury": ("+", "Gains through trade, skill and service."),
        "ketu": ("-", "Isolation, loss and anxiety."),
        "venus": ("+", "Comforts, property and success through partners."),
        "sun": ("-", "Friction with authority or father; strain."),
        "moon": ("-", "Emotional strain and fatigue; changes of residence."),
        "mars": ("-", "Disputes, accidents and hardship."),
        "rahu": ("-", "Confusion, obstacles and anxiety."),
        "jupiter": ("+", "Relief, honours and religious merit."),
    },
    "mercury": {
        "mercury": ("+", "Learning, trade and communication flourish."),
        "ketu": ("-", "Anxiety, losses and confusion in dealings."),
        "venus": ("+", "Comforts, arts, wealth and pleasant relationships."),
        "sun": ("~", "Recognition with friction; dealings with authority."),
        "moon": ("~", "Emotional ups and downs; public dealings."),
        "mars": ("~", "Energy in trade, with disputes."),
        "rahu": ("~", "Clever gains, with deception to guard against."),
        "jupiter": ("+", "Learning, honours and wise counsel."),
        "saturn": ("+", "Steady gains through work and service."),
    },
    "ketu": {
        "ketu": ("-", "Detachment, loss and anxiety; spiritual inclinations."),
        "venus": ("~", "Comforts with detachment; changes in relationships."),
        "sun": ("-", "Friction with authority; strain on vitality."),
        "moon": ("-", "Emotional unrest and separation."),
        "mars": ("-", "Conflicts, accidents or disputes."),
        "rahu": ("-", "Confusion and sudden changes."),
        "jupiter": ("+", "Spiritual growth, learning and relief."),
        "saturn": ("-", "Hardship, isolation and delays."),
        "mercury": ("~", "Learning with anxiety; changes in dealings."),
    },
    "venus": {
        "venus": ("+", "Comforts, the arts, marriage and luxuries."),
        "sun": ("~", "Honours with friction; strained relationships."),
        "moon": ("~", "Comforts with emotional fluctuations."),
        "mars": ("~", "Passion and gains of property; quarrels."),
        "rahu": ("~", "Luxuries and unconventional pleasures; confusion."),
        "jupiter": ("~", "Honours and learning with differing values."),
        "saturn": ("+", "Prosperity, property and stable relationships."),
        "mercury": ("+", "Wealth, the arts and pleasant dealings."),
        "ketu": ("-", "Disappointments, detachment and losses."),
    },
}
#: Gochara from the natal Moon (Phaladeepika 26): GOCHARA[graha][house - 1].
GOCHARA: dict[str, list[tuple[str, str]]] = {
    "sun": [
        ("-", "Fatigue, irritability and wasted journeys; care with superiors."),
        ("-", "Loss of money, deception and strain in the family."),
        ("+", "A new position, wealth and good health; success over rivals."),
        ("-", "Disturbance at home and obstacles to comfort."),
        ("-", "Mental unrest, confusion and worry over children."),
        ("+", "Freedom from rivals, illness and anxiety; success in competition."),
        ("-", "Tiring travel, digestive strain and friction with the spouse."),
        ("-", "Fear, quarrels and trouble with authorities."),
        ("-", "Setbacks and friction with elders or father."),
        ("+", "Success in undertakings, recognition and promotion."),
        ("+", "Gains, honours, a new position and good health."),
        ("-", "Expenses, losses and quarrels with friends."),
    ],
    "moon": [
        ("+", "Comfort, good food and happiness."),
        ("-", "Loss of money and obstacles."),
        ("+", "Gains, success and good company."),
        ("-", "Anxiety, distrust and disturbed sleep."),
        ("-", "Sorrow, obstacles to plans and indigestion."),
        ("+", "Health, wealth and victory over rivals."),
        ("+", "Comforts, honours and pleasant company."),
        ("-", "Anxiety and fear; health needs care."),
        ("-", "Obstacles, fatigue and mental strain."),
        ("+", "Success at work and the favour of superiors."),
        ("+", "Gains, happiness and meetings with friends."),
        ("-", "Expenses and restlessness."),
    ],
    "mars": [
        ("-", "Anger, accidents and quarrels."),
        ("-", "Loss of money, harsh words and family disputes."),
        ("+", "Gains, courage and victory; success in ventures."),
        ("-", "Trouble at home, property disputes and restlessness."),
        ("-", "Worries concerning children, anger and misjudgement."),
        ("+", "Victory over rivals, gains and relief from debts."),
        ("-", "Quarrels with the spouse or partners; tiring travel."),
        ("-", "Injury, fever or conflict; avoid risks."),
        ("-", "Loss, weakness and setbacks to plans."),
        ("-", "Obstacles and strain at work."),
        ("+", "Gains of land or money, good health and success."),
        ("-", "Expenses, losses and quarrels; disturbed sleep."),
    ],
    "mercury": [
        ("-", "Loss through harsh words or bad company; confusion."),
        ("+", "Gains of money and learning; pleasing speech."),
        ("-", "Fear of rivals and friction with friends."),
        ("+", "Gains, harmony at home and support of relatives."),
        ("-", "Quarrels with children or the spouse; anxiety."),
        ("+", "Success, recognition and victory over rivals."),
        ("-", "Friction in relationships; tiring journeys."),
        ("+", "Gains, success and cheerful news."),
        ("-", "Obstacles to plans and quarrels."),
        ("+", "Success at work, gains and happiness."),
        ("+", "Gains, comforts, good news and friendships."),
        ("-", "Losses, insult and anxiety."),
    ],
    "jupiter": [
        ("-", "Loss of money or position, restlessness and unwanted travel."),
        ("+", "Gains of wealth, harmony in the family and success."),
        ("-", "Obstacles, loss of position and separation from close ones."),
        ("-", "Grief, trouble from relatives and domestic unrest."),
        ("+", "Happiness through children, learning and good counsel."),
        ("-", "Trouble from rivals, anxiety and strain."),
        ("+", "Marriage or harmony with the spouse; good company and gains."),
        ("-", "Sorrow, losses, fatigue and obstacles."),
        ("+", "Good fortune, success, religious merit and prosperity."),
        ("-", "Obstacles at work and loss of position or wealth."),
        ("+", "Gains, recovery of position and good health."),
        ("-", "Grief, expenses and travel."),
    ],
    "venus": [
        ("+", "Comforts, pleasures and good health."),
        ("+", "Wealth, a pleasant family life and gifts."),
        ("+", "Prosperity, honour and success over rivals."),
        ("+", "Gains, happiness and the help of friends."),
        ("+", "Happiness through children and friends; gains."),
        ("-", "Trouble through rivals or indulgence; strain."),
        ("-", "Trouble through the spouse or relationships."),
        ("+", "Gains, comforts and property."),
        ("+", "Religious merit, happiness and fine things."),
        ("-", "Quarrels and loss of face at work."),
        ("+", "Gains, good health and prosperity."),
        ("+", "Gains of money and comforts."),
    ],
    "saturn": [
        ("-", "Part of Sade Sati: fatigue, obstacles and separation from comforts."),
        ("-", "Part of Sade Sati: loss of money and strain in the family."),
        ("+", "Gains, success over rivals, property and good health."),
        ("-", "Ardhashtama Shani: separation from home, relatives or comforts."),
        ("-", "Worries concerning children and mental strain."),
        ("+", "Victory over rivals and illness; gains."),
        ("-", "Tiring journeys and strain in marriage."),
        ("-", "Ashtama Shani: obstacles, loss of face and ill health."),
        ("-", "Setbacks, hostility and strain with father."),
        ("-", "Loss of position or wealth; burdens at work."),
        ("+", "Gains, honour and prosperity."),
        ("-", "Part of Sade Sati: expenses, losses and sleeplessness."),
    ],
    "rahu": [
        ("-", "Anxiety, illness and confusion."),
        ("-", "Loss of money and family discord."),
        ("+", "Gains, success and courage."),
        ("-", "Trouble at home and anxiety."),
        ("-", "Confusion and worries over children."),
        ("+", "Victory over rivals and relief from illness."),
        ("-", "Friction in relationships."),
        ("-", "Sudden obstacles and fear."),
        ("-", "Obstacles to fortune; conflict with elders."),
        ("~", "Unusual opportunities at work, with instability."),
        ("+", "Gains and fulfilled desires."),
        ("-", "Expenses, losses and foreign travel."),
    ],
    "ketu": [
        ("-", "Anxiety and detachment; health needs care."),
        ("-", "Loss of money and harsh speech."),
        ("+", "Courage and success."),
        ("-", "Unrest at home."),
        ("-", "Confusion and worries over children."),
        ("+", "Victory over rivals."),
        ("-", "Detachment in relationships."),
        ("-", "Sudden setbacks."),
        ("-", "Obstacles to fortune; doubts in faith."),
        ("~", "Changes and detachment at work."),
        ("+", "Gains and fulfilled desires."),
        ("~", "Expenses and spiritual retreat."),
    ],
}
#: Favourable houses from the Moon and their vedha houses (as transit/gochara.py).
VEDHA = {
    "sun": {3: 9, 6: 12, 10: 4, 11: 5},
    "moon": {1: 5, 3: 9, 6: 12, 7: 2, 10: 4, 11: 8},
    "mars": {3: 12, 6: 9, 11: 5},
    "mercury": {2: 5, 4: 3, 6: 9, 8: 1, 10: 8, 11: 12},
    "jupiter": {2: 12, 5: 4, 7: 3, 9: 10, 11: 8},
    "venus": {1: 8, 2: 7, 3: 1, 4: 10, 5: 9, 8: 5, 9: 11, 11: 6, 12: 3},
    "saturn": {3: 12, 6: 9, 11: 5},
    "rahu": {3: 12, 6: 9, 11: 5},
    "ketu": {3: 12, 6: 9, 11: 5},
}
NO_VEDHA = ({"sun", "saturn"}, {"moon", "mercury"})
#: Jupiter's and Saturn's transits over each natal graha.
OVER_NATAL: dict[str, dict[str, tuple[str, str]]] = {
    "jupiter": {
        "sun": ("+", "Recognition and support from superiors and father; confidence."),
        "moon": ("~", "A change of place or role; growth with restlessness."),
        "mars": ("+", "Energy directed to worthwhile goals; property matters."),
        "mercury": ("+", "Learning, writing and trade expand."),
        "jupiter": ("+", "Jupiter's return: renewal of faith, learning and fortune."),
        "venus": ("+", "Relationships, comforts and the arts flourish."),
        "saturn": ("~", "Responsibilities grow along with their rewards."),
        "rahu": ("~", "Ambitions expand; guard against excess and shortcuts."),
        "ketu": ("~", "Spiritual insight; detachment from material growth."),
    },
    "saturn": {
        "sun": ("-", "Pressure from authority; strain on vitality and on father; hard work."),
        "moon": ("-", "The peak of Sade Sati: emotional weight, responsibility and maturity."),
        "mars": ("-", "Frustrated energy; disputes and accidents to guard against."),
        "mercury": ("~", "Serious study and careful communication; delays in trade."),
        "jupiter": ("~", "Faith and teachers are tested; slow but lasting growth."),
        "venus": ("-", "Relationships and finances are tested; commitments harden or end."),
        "saturn": ("~", "Saturn's return: maturity, restructuring and new responsibilities."),
        "rahu": ("-", "Confusion and pressure; obligations come due."),
        "ketu": ("~", "Detachment and discipline; endings that clear the way."),
    },
}

# --- Helpers ----------------------------------------------------------------------


def _effects(domains: list[str], entry: tuple[str, str], strength: str) -> dict[str, Any]:
    polarity, summary = entry
    return {
        "domains": list(dict.fromkeys(domains)),
        "polarity": POLARITY[polarity],
        "strength": strength,
        "summary": summary,
    }


def _spec(
    lagna: int, rest: int, placements: dict[str, int] | None = None, **extra: Any
) -> dict[str, Any]:
    out: dict[str, Any] = {"lagna": SIGNS[lagna]}
    for planet, sign in (placements or {}).items():
        out[planet] = SIGNS[sign]
    out["rest"] = SIGNS[rest]
    out.update(extra)
    return out


def _other(*avoid: str) -> str:
    return next(p for p in GRAHAS if p not in avoid)


def _instance(
    params: dict[str, Any], effects: dict[str, Any], positive: Any, negative: Any, **more: Any
) -> dict[str, Any]:
    tests: dict[str, Any] = {"positive": [positive], "negative": [negative]}
    if "cancelled" in more:
        tests["cancelled"] = [more.pop("cancelled")]
    overrides = {"effects": effects, **more}
    return {"params": params, "overrides": overrides, "tests": tests}


def _document(
    category: str, provenance: str, families: list[Any], rules: list[Any] | None = None
) -> dict[str, Any]:
    document: dict[str, Any] = {
        "defaults": {"category": category, "school": "parashari", "provenance": provenance}
    }
    if rules:
        document["rules"] = rules
    if families:
        document["families"] = families
    return document


# --- Dasha rules --------------------------------------------------------------------


def dasha_houses() -> dict[str, Any]:
    """Mahadasha and antardasha lords by the houses they own and occupy."""
    md_lord, ad_lord, md_in, ad_in = [], [], [], []
    for house in range(1, 13):
        lagna = house % 12
        lord = LORDS[sign_of_house(lagna, house)]
        other = _other(lord)
        md_lord.append(
            _instance(
                {"house": house},
                _effects(DOMAINS[house], MD_LORDSHIP[house], "moderate"),
                _spec(lagna, 5, dasha=[lord]),
                _spec(lagna, 5, dasha=[other]),
            )
        )
        second = _other(lord, other)
        ad_lord.append(
            _instance(
                {"house": house},
                _effects(DOMAINS[house], MD_LORDSHIP[house], "minor"),
                _spec(lagna, 5, dasha=[other, lord]),
                _spec(lagna, 5, dasha=[other, second]),
            )
        )
        rest = sign_of_house(lagna, house % 12 + 2)
        md_in.append(
            _instance(
                {"house": house},
                _effects(DOMAINS[house], MD_PLACEMENT[house], "moderate"),
                _spec(lagna, rest, {"jupiter": sign_of_house(lagna, house)}, dasha=["jupiter"]),
                _spec(
                    lagna,
                    rest,
                    {"jupiter": sign_of_house(lagna, house % 12 + 1)},
                    dasha=["jupiter"],
                ),
            )
        )
        ad_in.append(
            _instance(
                {"house": house},
                _effects(DOMAINS[house], MD_PLACEMENT[house], "minor"),
                _spec(
                    lagna, rest, {"jupiter": sign_of_house(lagna, house)}, dasha=["sun", "jupiter"]
                ),
                _spec(
                    lagna,
                    rest,
                    {"jupiter": sign_of_house(lagna, house % 12 + 1)},
                    dasha=["sun", "jupiter"],
                ),
            )
        )
    sources = [BPHS_DASHA, PD_DASHA]
    sub_sources = [BPHS_ANTARDASHA, PD_ANTARDASHA]
    return _document(
        "dasha",
        "classical",
        [
            {
                "template": {
                    "id": "dasha.md_lord_of_{house}",
                    "name": "Mahadasha of the {house|ord} lord",
                    "description": "The mahadasha lord owns the {house|ord} house.",
                    "when": "md == lord({house})",
                    "participants": "[md]",
                    "sources": sources,
                },
                "instances": md_lord,
            },
            {
                "template": {
                    "id": "dasha.ad_lord_of_{house}",
                    "name": "Antardasha of the {house|ord} lord",
                    "description": "The antardasha lord, another graha than the mahadasha lord, owns the {house|ord} house.",
                    "when": "ad != md and ad == lord({house})",
                    "participants": "[ad]",
                    "sources": sub_sources,
                },
                "instances": ad_lord,
            },
            {
                "template": {
                    "id": "dasha.md_in_{house}",
                    "name": "Mahadasha lord in the {house|ord} house",
                    "description": "The mahadasha lord occupies the {house|ord} house from the lagna.",
                    "when": "house(md) == {house}",
                    "participants": "[md]",
                    "sources": sources,
                },
                "instances": md_in,
            },
            {
                "template": {
                    "id": "dasha.ad_in_{house}",
                    "name": "Antardasha lord in the {house|ord} house",
                    "description": "The antardasha lord, another graha than the mahadasha lord, occupies the {house|ord} house.",
                    "when": "ad != md and house(ad) == {house}",
                    "participants": "[ad]",
                    "sources": sub_sources,
                },
                "instances": ad_in,
            },
        ],
    )


WEAK = "debilitated({planet}) or combust({planet}) or (in_dusthana({planet}) and not dignified({planet}))"


def dasha_planets() -> dict[str, Any]:
    """Each graha's mahadasha when strong or weak, the nodes by house, and special lords."""
    strong, weak = [], []
    for planet, (good, bad) in PLANET_DASHA.items():
        exalted, debilitated = EXALTED[planet], (EXALTED[planet] + 6) % 12
        rest = (exalted + 4) % 12
        strong.append(
            _instance(
                {"planet": planet},
                _effects(PLANET_DOMAINS[planet], ("+", good), "moderate"),
                _spec(exalted, rest, {planet: exalted}, dasha=[planet]),
                _spec(exalted, rest, {planet: debilitated}, dasha=[planet]),
            )
        )
        weak.append(
            _instance(
                {"planet": planet},
                _effects(PLANET_DOMAINS[planet], ("-", bad), "moderate"),
                _spec(exalted, rest, {planet: debilitated}, dasha=[planet]),
                _spec(exalted, rest, {planet: exalted}, dasha=[planet]),
            )
        )
    nodes = [
        (
            "rahu",
            "kendra_trikona",
            "a kendra or trikona",
            "[1, 4, 5, 7, 9, 10]",
            4,
            8,
            ("+", "Ambition, sudden rises and gains through foreign or unusual channels."),
        ),
        (
            "rahu",
            "upachaya",
            "an upachaya (3rd, 6th, 10th or 11th)",
            "upachayas",
            3,
            2,
            ("+", "Success over rivals, courage and material gains."),
        ),
        (
            "rahu",
            "dusthana",
            "the 8th or 12th",
            "[8, 12]",
            8,
            9,
            ("-", "Confusion, losses, anxiety and trouble through foreign dealings."),
        ),
        (
            "ketu",
            "upachaya",
            "an upachaya (3rd, 6th, 10th or 11th)",
            "upachayas",
            6,
            5,
            ("+", "Courage, success over rivals and spiritual progress."),
        ),
        (
            "ketu",
            "dusthana",
            "the 8th or 12th",
            "[8, 12]",
            12,
            11,
            ("~", "Detachment and spiritual progress, with losses and isolation."),
        ),
    ]
    node_instances = [
        _instance(
            {"node": node, "group": group, "where": where, "houses": houses},
            _effects(PLANET_DOMAINS[node], entry, "moderate"),
            _spec(0, 1, {node: sign_of_house(0, yes)}, dasha=[node]),
            _spec(0, 1, {node: sign_of_house(0, no)}, dasha=[node]),
        )
        for node, group, where, houses, yes, no, entry in nodes
    ]
    rules = [
        {
            "id": "dasha.yogakaraka",
            "name": "Mahadasha of the yogakaraka",
            "description": "The mahadasha lord owns both a kendra (4th, 7th or 10th) and a trikona (5th or 9th).",
            "when": "yogakaraka(md)",
            "participants": "[md]",
            "effects": _effects(
                ["status", "career", "fortune"],
                ("+", "One of the most productive periods for status, career and fortune."),
                "major",
            ),
            "sources": [
                BPHS_DASHA,
                citation("laghu_parashari", edition="raman", locator="Yogakaraka"),
            ],
            "tests": {
                "positive": [_spec(1, 5, dasha=["saturn"])],
                "negative": [_spec(0, 5, dasha=["saturn"])],
            },
        },
        {
            "id": "dasha.maraka",
            "name": "Mahadasha of a maraka lord",
            "description": "The mahadasha lord owns the 2nd or 7th house (a maraka, killer, house).",
            "when": "md in [lord(2), lord(7)]",
            "participants": "[md]",
            "sensitive": True,
            "effects": _effects(
                ["longevity", "health"],
                (
                    "-",
                    "Texts associate maraka periods with health crises, above all late in life; judged only with longevity.",
                ),
                "moderate",
            ),
            "sources": [
                citation("laghu_parashari", edition="raman", locator="Maraka lords"),
                BPHS_DASHA,
            ],
            "tests": {
                "positive": [_spec(0, 5, dasha=["venus"])],
                "negative": [_spec(0, 5, dasha=["jupiter"])],
            },
        },
        {
            "id": "dasha.retrograde_lord",
            "name": "Retrograde mahadasha lord",
            "description": "The mahadasha lord (Mars to Saturn) was retrograde at birth.",
            "when": "md in [mars, mercury, jupiter, venus, saturn] and retrograde(md)",
            "participants": "[md]",
            "provenance": "traditional",
            "effects": _effects(
                ["character"],
                ("~", "Results come with delays, reversals or a return to unfinished matters."),
                "minor",
            ),
            "sources": [citation("popular_practice", locator="Dashas of retrograde planets")],
            "tests": {
                "positive": [_spec(0, 5, dasha=["saturn"], retrograde=["saturn"])],
                "negative": [_spec(0, 5, dasha=["saturn"])],
            },
        },
    ]
    return _document(
        "dasha",
        "classical",
        [
            {
                "template": {
                    "id": "dasha.{planet}_strong",
                    "name": "Mahadasha of a strong {planet|title}",
                    "description": "{planet|title} runs the mahadasha and is strong (the working test of strong()).",
                    "when": "md == {planet} and strong({planet})",
                    "participants": "[{planet}]",
                    "sources": [PD_DASHA, BPHS_DASHA],
                },
                "instances": strong,
            },
            {
                "template": {
                    "id": "dasha.{planet}_weak",
                    "name": "Mahadasha of a weak {planet|title}",
                    "description": "{planet|title} runs the mahadasha and is debilitated, combust, or in a dusthana outside its own dignity.",
                    "when": "md == {planet} and (" + WEAK + ")",
                    "participants": "[{planet}]",
                    "sources": [PD_DASHA, BPHS_DASHA],
                },
                "instances": weak,
            },
            {
                "template": {
                    "id": "dasha.{node}_{group}",
                    "name": "Mahadasha of {node|title} in {where}",
                    "description": (
                        "{node|title} runs the mahadasha from {where} house; the nodes also give "
                        "the results of their dispositors."
                    ),
                    "when": "md == {node} and house({node}) in {houses}",
                    "participants": "[{node}, dispositor({node})]",
                    "sources": [BPHS_DASHA],
                },
                "instances": node_instances,
            },
        ],
        rules,
    )


def dasha_antardasha() -> dict[str, Any]:
    """The antardasha lord's relation to the mahadasha lord, and each pair's tenor."""
    relations = [
        {
            "id": "dasha.ad_dusthana_from_md",
            "name": "Antardasha lord in a dusthana from the mahadasha lord",
            "description": "The antardasha lord is 6th, 8th or 12th from the mahadasha lord.",
            "when": "ad != md and house(ad, md) in dusthanas",
            "effects": _effects(
                ["fortune"],
                ("-", "Friction, obstacles or expenses within the main period."),
                "minor",
            ),
            "tests": {
                "positive": [_spec(0, 5, {"sun": 0, "moon": 7}, dasha=["sun", "moon"])],
                "negative": [_spec(0, 5, {"sun": 0, "moon": 4}, dasha=["sun", "moon"])],
            },
        },
        {
            "id": "dasha.ad_kendra_trikona_from_md",
            "name": "Antardasha lord in a kendra or trikona from the mahadasha lord",
            "description": "The antardasha lord is 1st, 4th, 5th, 7th, 9th or 10th from the mahadasha lord.",
            "when": "ad != md and house(ad, md) in [1, 4, 5, 7, 9, 10]",
            "effects": _effects(
                ["fortune"], ("+", "The sub-period supports the main period's promise."), "minor"
            ),
            "tests": {
                "positive": [_spec(0, 5, {"sun": 0, "moon": 4}, dasha=["sun", "moon"])],
                "negative": [_spec(0, 5, {"sun": 0, "moon": 7}, dasha=["sun", "moon"])],
            },
        },
        {
            "id": "dasha.ad_md_friends",
            "name": "Mahadasha and antardasha lords are mutual friends",
            "description": "The two lords count each other as natural friends.",
            "when": "ad != md and natural_friend(md, ad) and natural_friend(ad, md)",
            "effects": _effects(
                ["fortune"], ("+", "Harmonious results; the two lords cooperate."), "minor"
            ),
            "tests": {
                "positive": [_spec(0, 5, dasha=["sun", "moon"])],
                "negative": [_spec(0, 5, dasha=["sun", "saturn"])],
            },
        },
        {
            "id": "dasha.ad_md_enemies",
            "name": "Mahadasha and antardasha lords are enemies",
            "description": "One of the two lords counts the other as a natural enemy.",
            "when": "ad != md and (natural_enemy(md, ad) or natural_enemy(ad, md))",
            "effects": _effects(
                ["fortune"],
                ("~", "Mixed results and friction between the two lords' matters."),
                "minor",
            ),
            "tests": {
                "positive": [_spec(0, 5, dasha=["sun", "saturn"])],
                "negative": [_spec(0, 5, dasha=["sun", "moon"])],
            },
        },
    ]
    for rule in relations:
        rule["participants"] = "[md, ad]"
        rule["sources"] = [BPHS_ANTARDASHA]
    pairs = []
    for md, row in PAIRS.items():
        for ad, entry in row.items():
            pairs.append(
                _instance(
                    {"md": md, "ad": ad},
                    _effects(PLANET_DOMAINS[md][:1] + PLANET_DOMAINS[ad][:1], entry, "minor"),
                    _spec(0, 5, dasha=[md, ad]),
                    _spec(0, 5, dasha=[md, _other(ad)]),
                )
            )
    return _document(
        "dasha",
        "classical",
        [
            {
                "template": {
                    "id": "dasha.pair_{md}_{ad}",
                    "name": "{ad|title} antardasha in the {md|title} mahadasha",
                    "description": "The antardasha of {ad|title} runs within the mahadasha of {md|title}.",
                    "when": "md == {md} and ad == {ad}",
                    "participants": "[{md}, {ad}]",
                    "notes": "The texts make each result depend on the strength and placement of both lords; this is its general tenor.",
                    "sources": [BPHS_ANTARDASHA, PD_ANTARDASHA],
                },
                "instances": pairs,
            }
        ],
        relations,
    )


# --- Transit rules ------------------------------------------------------------------


def _obstructor(planet: str) -> str:
    return next(
        p
        for p in ("jupiter", "mars", "venus", "mercury")
        if p != planet and {p, planet} not in NO_VEDHA
    )


def gochara() -> dict[str, Any]:
    instances = []
    for planet, row in GOCHARA.items():
        for house, entry in enumerate(row, start=1):
            moon = (GRAHAS.index(planet) * 5 + house) % 12
            natal = {"moon": moon}
            here = SIGNS[(moon + house - 1) % 12]
            elsewhere = SIGNS[(moon + house) % 12]
            strength = "moderate" if planet in ("jupiter", "saturn", "rahu", "ketu") else "minor"
            more: dict[str, Any] = {}
            if house in VEDHA[planet]:
                blocked = SIGNS[(moon + VEDHA[planet][house] - 1) % 12]
                more["cancel_when"] = f"vedha({planet})"
                more["cancelled"] = _spec(
                    0, (moon + 6) % 12, natal, transit={planet: here, _obstructor(planet): blocked}
                )
            if planet in ("rahu", "ketu"):
                more["provenance"] = "traditional"
                more["sources"] = [
                    citation("popular_practice", locator="Rahu and Ketu in transit from the Moon")
                ]
            instances.append(
                _instance(
                    {"planet": planet, "house": house},
                    _effects(DOMAINS[house], entry, strength),
                    _spec(0, (moon + 6) % 12, natal, transit={planet: here}),
                    _spec(0, (moon + 6) % 12, natal, transit={planet: elsewhere}),
                    **more,
                )
            )
    return _document(
        "transit",
        "classical",
        [
            {
                "template": {
                    "id": "transit.{planet}_h{house}",
                    "name": "{planet|title} transiting the {house|ord} from the Moon",
                    "description": "Transiting {planet|title} occupies the {house|ord} house from the natal Moon.",
                    "when": "transit_house({planet}, moon) == {house}",
                    "participants": "[{planet}]",
                    "notes": "A favourable transit is cancelled by vedha: another graha transiting its paired house (the Sun and Saturn, and the Moon and Mercury, do not obstruct each other).",
                    "sources": [PD_GOCHARA],
                },
                "instances": instances,
            }
        ],
    )


def slow_transits() -> dict[str, Any]:
    """Sade Sati, Kantaka Shani, double transit, and Jupiter and Saturn over natal grahas."""
    rules = [
        {
            "id": "transit.sade_sati",
            "name": "Sade Sati",
            "description": "Saturn transits the 12th, 1st or 2nd house from the natal Moon (about seven and a half years).",
            "when": "transit_house(saturn, moon) in [12, 1, 2]",
            "participants": "[saturn, moon]",
            "effects": _effects(
                ["career", "wealth", "health"],
                ("-", "Pressure, responsibility and restructuring; effort matures slowly."),
                "major",
            ),
            "sources": [citation("popular_practice", locator="Sade Sati")],
            "tests": {
                "positive": [_spec(0, 6, {"moon": 3}, transit={"saturn": SIGNS[2]})],
                "negative": [_spec(0, 6, {"moon": 3}, transit={"saturn": SIGNS[5]})],
            },
        },
        {
            "id": "transit.kantaka_shani",
            "name": "Kantaka Shani",
            "description": "Saturn transits the 4th, 7th or 10th house from the natal Moon.",
            "when": "transit_house(saturn, moon) in [4, 7, 10]",
            "participants": "[saturn, moon]",
            "effects": _effects(
                ["career", "property", "marriage"],
                ("-", "Obstacles in work, home or relationships; patience is needed."),
                "moderate",
            ),
            "sources": [citation("popular_practice", locator="Kantaka Shani")],
            "tests": {
                "positive": [_spec(0, 6, {"moon": 3}, transit={"saturn": SIGNS[6]})],
                "negative": [_spec(0, 6, {"moon": 3}, transit={"saturn": SIGNS[7]})],
            },
        },
    ]
    for rule in rules:
        rule["provenance"] = "traditional"
    double = [
        _instance(
            {"house": house},
            _effects(
                DOMAINS[house],
                ("~", f"The {ordinal(house)} house ({MATTERS[house]}) is ripe for events."),
                "moderate",
            ),
            _spec(0, 5, transit={"jupiter": SIGNS[house - 1], "saturn": SIGNS[house - 1]}),
            _spec(0, 5, transit={"jupiter": SIGNS[house - 1], "saturn": SIGNS[(house + 1) % 12]}),
        )
        for house in range(1, 13)
    ]
    over = []
    for transiting, row in OVER_NATAL.items():
        for natal, entry in row.items():
            sign = (GRAHAS.index(natal) * 3 + 1) % 12
            base = {natal: sign}
            rest = (sign + 5) % 12
            over.append(
                _instance(
                    {"transiting": transiting, "natal": natal},
                    _effects(PLANET_DOMAINS[natal], entry, "moderate"),
                    _spec(0, rest, base, transit={transiting: SIGNS[sign]}),
                    _spec(0, rest, base, transit={transiting: SIGNS[(sign + 1) % 12]}),
                )
            )
    return _document(
        "transit",
        "modern",
        [
            {
                "template": {
                    "id": "transit.double_h{house}",
                    "name": "Double transit on the {house|ord} house",
                    "description": "Transiting Jupiter and Saturn both occupy or aspect the {house|ord} house from the lagna.",
                    "when": "transit_influences(jupiter, {house}) and transit_influences(saturn, {house})",
                    "participants": "[jupiter, saturn]",
                    "sources": [
                        citation(
                            "popular_practice",
                            locator="Double transit of Jupiter and Saturn (K.N. Rao)",
                        )
                    ],
                },
                "instances": double,
            },
            {
                "template": {
                    "id": "transit.{transiting}_over_{natal}",
                    "name": "{transiting|title} transiting natal {natal|title}",
                    "description": "Transiting {transiting|title} occupies the sign of natal {natal|title}.",
                    "when": "transit_sign({transiting}) == sign({natal})",
                    "participants": "[{transiting}, {natal}]",
                    "provenance": "traditional",
                    "sources": [citation("popular_practice", locator="Transits over natal grahas")],
                },
                "instances": over,
            },
        ],
        rules,
    )
