"""Attributes of Moon signs and nakshatras used in marriage matching, and the points
tables of the eight kootas.

The groups (varna, vashya, yoni, gana, nadi, rajju, vedha) agree across the
references consulted. The points tables do not, so each disputed table is kept as a
named variant, and a :class:`KootaProfile` picks one of each:

* ``POPULAR``, the default, follows Indian matchmaking guides and apps: earth signs
  Vaishya and air signs Shudra, the Vashya table they print (as Astroyogi publishes
  it, the bride's group down the rows), and graha maitri on the 5-4-3-1-0.5-0 scale.
* ``MAITREYA`` reproduces the tables of the Maitreya program as documented on its
  companion site Saravali: air signs Vaishya, its own Vashya table, and graha
  maitri on a 5-4-3-2-1-0 scale.

Both profiles share Maitreya's Yoni and Gana tables. Astroyogi prints the same Gana
table, also with the bride's gana down the rows (a Deva bride with a Manushya groom
6, a Manushya bride with a Deva groom 5); ClickAstro likewise gives a Deva boy with
a Manushya girl 5, and PyJHora uses the table. Some guides print it the other way
round. The Yoni table is kept as published, including two cells that differ from
their mirror images (horse bride with deer groom 3, the reverse 1; lion bride with
buffalo groom 2, the reverse 1); PyJHora gives 1 both ways. ``docs/MATCHING.md``
sets out the evidence, and test pairs that tell the readings apart in any app.

Two-dimensional tables are indexed ``[bride][groom]``, as the sources print them.
Nakshatras are 0-based from Ashwini, signs 0-based from Mesha.
"""

from __future__ import annotations

from enum import IntEnum, StrEnum

from jyotish_engine.rules.schema import Citation


class KootaProfile(StrEnum):
    POPULAR = "popular"
    MAITREYA = "maitreya"


class Varna(IntEnum):
    """Lower is higher in rank."""

    BRAHMIN = 0
    KSHATRIYA = 1
    VAISHYA = 2
    SHUDRA = 3


class Vashya(IntEnum):
    CHATUSHPADA = 0  # quadruped
    MANAVA = 1  # human
    JALACHARA = 2  # aquatic
    VANACHARA = 3  # wild (Leo)
    KEETA = 4  # insect (Scorpio)


class Gana(IntEnum):
    DEVA = 0
    MANUSHYA = 1
    RAKSHASA = 2


class Nadi(IntEnum):
    ADI = 0  # vata
    MADHYA = 1  # pitta
    ANTYA = 2  # kapha


class Rajju(IntEnum):
    PADA = 0  # foot
    KATI = 1  # waist
    NABHI = 2  # navel
    KANTHA = 3  # neck
    SIRA = 4  # head


YONI_ANIMALS = (
    "horse", "elephant", "sheep", "serpent", "dog", "cat", "rat",
    "cow", "buffalo", "tiger", "deer", "monkey", "mongoose", "lion",
)  # fmt: skip

#: (animal index, male) for each nakshatra. Abhijit, the female mongoose, is not
#: used: matching takes the 27 nakshatras.
NAKSHATRA_YONI: tuple[tuple[int, bool], ...] = (
    (0, True), (1, True), (2, False), (3, True), (3, False), (4, False), (5, False),
    (2, True), (5, True), (6, True), (6, False), (7, True), (8, False), (9, False),
    (8, True), (9, True), (10, False), (10, True), (4, True), (11, True), (12, True),
    (11, False), (13, False), (0, False), (13, True), (7, False), (1, False),
)  # fmt: skip

#: Pairs of animals that are sworn enemies (0 points; a failed yoni porutham).
YONI_ENEMIES = frozenset(
    frozenset(pair) for pair in ((0, 8), (1, 13), (2, 11), (3, 12), (4, 10), (5, 6), (7, 9))
)

NAKSHATRA_GANA: tuple[Gana, ...] = tuple(
    Gana(g)
    for g in (0, 1, 2, 1, 0, 1, 0, 0, 2, 2, 1, 1, 0, 2, 0, 2, 0, 2, 2, 1, 1, 0, 2, 2, 1, 1, 0)
)

#: Nadi runs Adi, Madhya, Antya, Antya, Madhya, Adi through each group of six.
NAKSHATRA_NADI: tuple[Nadi, ...] = tuple(Nadi((0, 1, 2, 2, 1, 0)[i % 6]) for i in range(27))

#: Rajju climbs from foot to head and back down in each group of nine.
NAKSHATRA_RAJJU: tuple[Rajju, ...] = tuple(
    Rajju((0, 1, 2, 3, 4, 3, 2, 1, 0)[i % 9]) for i in range(27)
)

#: Nakshatra pairs that obstruct each other (vedha).
VEDHA_PAIRS = frozenset(
    frozenset(pair)
    for pair in (
        (0, 17), (1, 16), (2, 15), (3, 14), (4, 22), (5, 21), (6, 20),
        (7, 19), (8, 18), (9, 26), (10, 25), (11, 24), (12, 23),
    )
)  # fmt: skip

#: Varna of each sign by its element (fire, earth, air, water in turn from Mesha).
VARNA_BY_ELEMENT: dict[KootaProfile, tuple[Varna, Varna, Varna, Varna]] = {
    KootaProfile.POPULAR: (Varna.KSHATRIYA, Varna.VAISHYA, Varna.SHUDRA, Varna.BRAHMIN),
    KootaProfile.MAITREYA: (Varna.KSHATRIYA, Varna.SHUDRA, Varna.VAISHYA, Varna.BRAHMIN),
}

#: Vashya group of each sign; Dhanu and Makara are split at 15 degrees (first half, second half).
_VASHYA_BY_SIGN: tuple[Vashya | tuple[Vashya, Vashya], ...] = (
    Vashya.CHATUSHPADA,
    Vashya.CHATUSHPADA,
    Vashya.MANAVA,
    Vashya.JALACHARA,
    Vashya.VANACHARA,
    Vashya.MANAVA,
    Vashya.MANAVA,
    Vashya.KEETA,
    (Vashya.MANAVA, Vashya.CHATUSHPADA),
    (Vashya.CHATUSHPADA, Vashya.JALACHARA),
    Vashya.MANAVA,
    Vashya.JALACHARA,
)

VASHYA_POINTS: dict[KootaProfile, tuple[tuple[float, ...], ...]] = {
    KootaProfile.POPULAR: (
        (2.0, 1.0, 1.0, 1.5, 1.0),
        (1.0, 2.0, 1.5, 0.0, 1.0),
        (1.0, 1.5, 2.0, 1.0, 1.0),
        (0.0, 0.0, 0.0, 2.0, 0.0),
        (1.0, 1.0, 1.0, 0.0, 2.0),
    ),
    KootaProfile.MAITREYA: (
        (2.0, 0.0, 0.0, 0.5, 0.0),
        (1.0, 2.0, 1.0, 0.5, 1.0),
        (0.5, 1.0, 2.0, 1.0, 1.0),
        (0.0, 0.0, 0.0, 2.0, 0.0),
        (1.0, 1.0, 1.0, 0.0, 2.0),
    ),
}

YONI_POINTS: tuple[tuple[int, ...], ...] = (
    (4, 2, 2, 3, 2, 2, 2, 1, 0, 1, 3, 3, 2, 1),
    (2, 4, 3, 3, 2, 2, 2, 2, 3, 1, 2, 3, 2, 0),
    (2, 3, 4, 2, 1, 2, 1, 3, 3, 1, 2, 0, 3, 1),
    (3, 3, 2, 4, 2, 1, 1, 1, 1, 2, 2, 2, 0, 2),
    (2, 2, 1, 2, 4, 2, 1, 2, 2, 1, 0, 2, 1, 1),
    (2, 2, 2, 1, 2, 4, 0, 2, 2, 1, 3, 3, 2, 1),
    (2, 2, 1, 1, 1, 0, 4, 2, 2, 2, 2, 2, 1, 2),
    (1, 2, 3, 1, 2, 2, 2, 4, 3, 0, 3, 2, 2, 1),
    (0, 3, 3, 1, 2, 2, 2, 3, 4, 1, 2, 2, 2, 1),
    (1, 1, 1, 2, 1, 1, 2, 0, 1, 4, 1, 1, 2, 1),
    (1, 2, 2, 2, 0, 3, 2, 3, 2, 1, 4, 2, 2, 1),
    (3, 3, 0, 2, 2, 3, 2, 2, 2, 1, 2, 4, 3, 2),
    (2, 2, 3, 0, 1, 2, 1, 2, 2, 2, 2, 3, 4, 2),
    (1, 0, 1, 2, 1, 1, 2, 1, 2, 1, 1, 2, 2, 4),
)

GANA_POINTS: tuple[tuple[int, ...], ...] = ((6, 6, 0), (5, 6, 0), (1, 0, 6))

#: Graha maitri points for (friend, neutral, enemy) counts of the two Moon-sign lords'
#: natural views of each other: 2 friends, friend and neutral, 2 neutral, friend and
#: enemy, neutral and enemy, 2 enemies.
MAITRI_POINTS: dict[KootaProfile, dict[tuple[int, int, int], float]] = {
    KootaProfile.POPULAR: {
        (2, 0, 0): 5.0, (1, 1, 0): 4.0, (0, 2, 0): 3.0,
        (1, 0, 1): 1.0, (0, 1, 1): 0.5, (0, 0, 2): 0.0,
    },
    KootaProfile.MAITREYA: {
        (2, 0, 0): 5.0, (1, 1, 0): 4.0, (0, 2, 0): 3.0,
        (1, 0, 1): 2.0, (0, 1, 1): 1.0, (0, 0, 2): 0.0,
    },
}  # fmt: skip

#: Sign distances (counted from either partner, 1 = same sign) that break Bhakoot.
BHAKOOT_DOSHA_DISTANCES = frozenset({2, 12, 5, 9, 6, 8})

#: Signs amenable (vashya) to each sign, for the South Indian Vasya porutham.
VASYA_SIGNS: tuple[frozenset[int], ...] = tuple(
    frozenset(s)
    for s in (
        {4, 7}, {3, 6}, {5}, {7, 8}, {6}, {11, 2},
        {9, 5}, {3}, {11}, {0, 10}, {0}, {9},
    )
)  # fmt: skip

MAHENDRA_COUNTS = frozenset({4, 7, 10, 13, 16, 19, 22, 25})
DINA_GOOD_REMAINDERS = frozenset({2, 4, 6, 8, 0})
TARA_BAD_REMAINDERS = frozenset({3, 5, 7})

MAITREYA = Citation(text="maitreya", locator="Asta Koota pages of its documentation")
RAMAN = Citation(text="raman_muhurtha", locator="Marriage: agreement of horoscopes (kutas)")


def _popular(locator: str) -> Citation:
    return Citation(text="popular_practice", locator=locator)


SOURCES: dict[str, dict[KootaProfile, tuple[Citation, ...]]] = {
    "varna": {
        KootaProfile.POPULAR: (_popular("Varna koota: earth signs Vaishya, air signs Shudra"),),
        KootaProfile.MAITREYA: (MAITREYA,),
    },
    "vashya": {
        KootaProfile.POPULAR: (_popular("Vashya koota points table of matchmaking guides"),),
        KootaProfile.MAITREYA: (MAITREYA,),
    },
    "tara": dict.fromkeys(KootaProfile, (MAITREYA, _popular("Tara (dina) koota"))),
    "yoni": dict.fromkeys(KootaProfile, (MAITREYA,)),
    "graha_maitri": {
        KootaProfile.POPULAR: (
            Citation(text="bphs", edition="santhanam", chapter=3, locator="natural friendships"),
            _popular("Graha maitri points scale"),
        ),
        KootaProfile.MAITREYA: (
            Citation(text="bphs", edition="santhanam", chapter=3, locator="natural friendships"),
            MAITREYA,
        ),
    },
    "gana": {
        KootaProfile.POPULAR: (
            MAITREYA,
            _popular("Gana koota table of matchmaking guides, the bride's gana down the rows"),
        ),
        KootaProfile.MAITREYA: (MAITREYA,),
    },
    "bhakoot": dict.fromkeys(KootaProfile, (MAITREYA, _popular("Bhakoot (rasi) koota"))),
    "nadi": dict.fromkeys(KootaProfile, (MAITREYA, _popular("Nadi koota"))),
}


def varna(sign: int, profile: KootaProfile) -> Varna:
    return VARNA_BY_ELEMENT[profile][sign % 4]


def vashya(sign: int, degrees_in_sign: float) -> Vashya:
    group = _VASHYA_BY_SIGN[sign]
    if isinstance(group, tuple):
        return group[1] if degrees_in_sign >= 15.0 else group[0]
    return group
