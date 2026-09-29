"""The 27 nakshatras (lunar mansions), their padas and Vimshottari lords."""

from __future__ import annotations

from dataclasses import dataclass

from jyotish_engine.astro.bodies import Body

NAKSHATRA_SPAN = 360.0 / 27.0  # 13 deg 20 min
PADA_SPAN = NAKSHATRA_SPAN / 4.0  # 3 deg 20 min

#: Vimshottari dasha lords and their periods in years, in sequence from Ashwini.
VIMSHOTTARI_SEQUENCE: tuple[tuple[Body, int], ...] = (
    (Body.KETU, 7),
    (Body.VENUS, 20),
    (Body.SUN, 6),
    (Body.MOON, 10),
    (Body.MARS, 7),
    (Body.RAHU, 18),
    (Body.JUPITER, 16),
    (Body.SATURN, 19),
    (Body.MERCURY, 17),
)
VIMSHOTTARI_TOTAL_YEARS = 120


@dataclass(frozen=True, slots=True)
class NakshatraInfo:
    index: int  # 0 = Ashwini
    name: str
    deity: str

    @property
    def lord(self) -> Body:
        return VIMSHOTTARI_SEQUENCE[self.index % 9][0]

    @property
    def start(self) -> float:
        return self.index * NAKSHATRA_SPAN


NAKSHATRAS: tuple[NakshatraInfo, ...] = tuple(
    NakshatraInfo(i, name, deity)
    for i, (name, deity) in enumerate(
        (
            ("Ashwini", "Ashwini Kumaras"),
            ("Bharani", "Yama"),
            ("Krittika", "Agni"),
            ("Rohini", "Prajapati (Brahma)"),
            ("Mrigashira", "Soma"),
            ("Ardra", "Rudra"),
            ("Punarvasu", "Aditi"),
            ("Pushya", "Brihaspati"),
            ("Ashlesha", "Sarpas (Nagas)"),
            ("Magha", "Pitris"),
            ("Purva Phalguni", "Bhaga"),
            ("Uttara Phalguni", "Aryaman"),
            ("Hasta", "Savitr"),
            ("Chitra", "Tvashtr (Vishwakarma)"),
            ("Swati", "Vayu"),
            ("Vishakha", "Indra and Agni"),
            ("Anuradha", "Mitra"),
            ("Jyeshtha", "Indra"),
            ("Mula", "Nirriti"),
            ("Purva Ashadha", "Apas"),
            ("Uttara Ashadha", "Vishvedevas"),
            ("Shravana", "Vishnu"),
            ("Dhanishta", "Vasus"),
            ("Shatabhisha", "Varuna"),
            ("Purva Bhadrapada", "Aja Ekapada"),
            ("Uttara Bhadrapada", "Ahir Budhnya"),
            ("Revati", "Pushan"),
        )
    )
)


@dataclass(frozen=True, slots=True)
class NakshatraPosition:
    nakshatra: NakshatraInfo
    pada: int  # 1..4
    degrees_in_nakshatra: float
    #: Fraction of the nakshatra already traversed (0..1); drives the dasha balance.
    fraction_elapsed: float

    @property
    def fraction_remaining(self) -> float:
        return 1.0 - self.fraction_elapsed


def nakshatra_of(longitude: float) -> NakshatraPosition:
    """Nakshatra, pada and traversal of a sidereal longitude."""
    longitude %= 360.0
    index = min(int(longitude / NAKSHATRA_SPAN), 26)
    within = longitude - index * NAKSHATRA_SPAN
    pada = min(int(within / PADA_SPAN), 3) + 1
    return NakshatraPosition(
        nakshatra=NAKSHATRAS[index],
        pada=pada,
        degrees_in_nakshatra=within,
        fraction_elapsed=within / NAKSHATRA_SPAN,
    )
