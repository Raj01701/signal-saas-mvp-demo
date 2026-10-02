"""The five limbs of the panchanga and their names.

* **Vara**, the weekday, runs from one sunrise to the next.
* **Tithi**, the lunar day: each 12 degrees of the Moon's elongation from the Sun
  (30 per lunar month; 1-15 in the bright half, 16-30 in the dark half).
* **Nakshatra** of the Moon: each 13 degrees 20 minutes of its sidereal longitude.
* **Yoga** (nitya yoga): each 13 degrees 20 minutes of the sum of the sidereal
  longitudes of the Sun and the Moon.
* **Karana**, half a tithi: Kimstughna first, then Bava to Vishti eight times over,
  and Shakuni, Chatushpada and Naga at the end of the dark half.

The elongation, and so tithi and karana, does not depend on the ayanamsa; the
nakshatra and yoga do.
"""

from __future__ import annotations

from enum import StrEnum

import numpy as np
from numpy.typing import NDArray

from jyotish_engine.astro.bodies import Body
from jyotish_engine.core.nakshatra import NAKSHATRAS

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


class Limb(StrEnum):
    TITHI = "tithi"
    NAKSHATRA = "nakshatra"
    YOGA = "yoga"
    KARANA = "karana"


#: Degrees per unit of each limb, and how many units make the circle.
WIDTH = {Limb.TITHI: 12.0, Limb.NAKSHATRA: 360.0 / 27, Limb.YOGA: 360.0 / 27, Limb.KARANA: 6.0}
COUNT = {Limb.TITHI: 30, Limb.NAKSHATRA: 27, Limb.YOGA: 27, Limb.KARANA: 60}

_TITHI_NAMES = (
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi", "Saptami",
    "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi",
)  # fmt: skip
TITHIS = (*_TITHI_NAMES, "Purnima", *_TITHI_NAMES, "Amavasya")
YOGAS = (
    "Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana", "Atiganda", "Sukarma",
    "Dhriti", "Shula", "Ganda", "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra",
    "Siddhi", "Vyatipata", "Variyan", "Parigha", "Shiva", "Siddha", "Sadhya", "Shubha",
    "Shukla", "Brahma", "Indra", "Vaidhriti",
)  # fmt: skip
MOVABLE_KARANAS = ("Bava", "Balava", "Kaulava", "Taitila", "Garaja", "Vanija", "Vishti")
FIXED_KARANAS = {0: "Kimstughna", 57: "Shakuni", 58: "Chatushpada", 59: "Naga"}
VARAS = ("Ravivara", "Somavara", "Mangalavara", "Budhavara", "Guruvara", "Shukravara", "Shanivara")
#: Lords of the weekdays, Sunday first.
VARA_LORDS = (Body.SUN, Body.MOON, Body.MARS, Body.MERCURY, Body.JUPITER, Body.VENUS, Body.SATURN)


def karana_name(index: int) -> str:
    """Name of the karana with 0-based index 0-59 within the lunar month."""
    return FIXED_KARANAS.get(index) or MOVABLE_KARANAS[(index - 1) % 7]


def limb_name(limb: Limb, index: int) -> str:
    if limb is Limb.TITHI:
        return TITHIS[index]
    if limb is Limb.NAKSHATRA:
        return NAKSHATRAS[index].name
    if limb is Limb.YOGA:
        return YOGAS[index]
    return karana_name(index)


def paksha(tithi_index: int) -> str:
    """ "shukla" (bright half) for tithis 1-15, "krishna" (dark half) for 16-30."""
    return "shukla" if tithi_index < 15 else "krishna"


def limb_indices(limb: Limb, sun: FloatArray, moon: FloatArray) -> IntArray:
    """0-based limb index from sidereal longitudes of the Sun and the Moon."""
    if limb in (Limb.TITHI, Limb.KARANA):
        angle = (moon - sun) % 360.0
    elif limb is Limb.NAKSHATRA:
        angle = moon % 360.0
    else:
        angle = (sun + moon) % 360.0
    index = np.floor(angle / WIDTH[limb]).astype(np.int64)
    return np.minimum(index, COUNT[limb] - 1)
