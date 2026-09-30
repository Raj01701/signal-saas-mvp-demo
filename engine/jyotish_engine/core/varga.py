"""Divisional charts (vargas).

Each sign is split into ``n`` parts (unequal for the Trimsamsa, D30), and each part
maps to a sign. The traditional Parashara rules (BPHS, *Vargavivekadhyaya*) are the
default. Alternative schools are selectable:

* **Parivritti cyclic**: parts are numbered continuously from Aries around the zodiac.
* **Parivritti even-reverse**: as cyclic, but even signs run their parts backwards.
* **Parivritti alternate** (Somanatha): odd signs count forward from Aries, even signs
  backward from Pisces.
* **Jagannatha** drekkana (D3) and **Raman** ekadashamsha (D11).
* **Parashara even-reverse** for the vargas where some authorities reverse even signs.

The longitude inside a divisional sign is ``(degrees in sign x n) mod 30``, the usual
convention (also for the unequal D30).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from jyotish_engine.core.zodiac import Sign


class VargaMethod(StrEnum):
    PARASHARA = "parashara"
    PARASHARA_EVEN_REVERSE = "parashara_even_reverse"
    PARIVRITTI_CYCLIC = "parivritti_cyclic"
    PARIVRITTI_EVEN_REVERSE = "parivritti_even_reverse"
    PARIVRITTI_ALTERNATE = "parivritti_alternate"
    JAGANNATHA = "jagannatha"
    RAMAN = "raman"
    #: Siddhamsa (D24) with both odd and even signs counted from Leo.
    SIDDHAMSA_FROM_LEO = "siddhamsa_from_leo"


@dataclass(frozen=True, slots=True)
class VargaSpec:
    division: int
    name: str
    signification: str


VARGAS: dict[int, VargaSpec] = {
    spec.division: spec
    for spec in (
        VargaSpec(1, "Rashi", "the body and life as a whole"),
        VargaSpec(2, "Hora", "wealth and sustenance"),
        VargaSpec(3, "Drekkana", "siblings, courage, initiative"),
        VargaSpec(4, "Chaturthamsha", "home, property, fortune"),
        VargaSpec(5, "Panchamsha", "fame, authority, merit"),
        VargaSpec(6, "Shashthamsha", "health, disease, conflict"),
        VargaSpec(7, "Saptamsha", "children and progeny"),
        VargaSpec(8, "Ashtamsha", "sudden events and longevity"),
        VargaSpec(9, "Navamsha", "spouse, dharma, inner strength of planets"),
        VargaSpec(10, "Dashamsha", "career and status"),
        VargaSpec(11, "Rudramsha", "destruction, gains and losses"),
        VargaSpec(12, "Dwadashamsha", "parents and lineage"),
        VargaSpec(16, "Shodashamsha", "vehicles, comforts, happiness"),
        VargaSpec(20, "Vimshamsha", "spiritual practice and worship"),
        VargaSpec(24, "Chaturvimshamsha", "education and learning"),
        VargaSpec(27, "Saptavimshamsha", "strengths and weaknesses"),
        VargaSpec(30, "Trimshamsha", "misfortunes, character, evils"),
        VargaSpec(40, "Khavedamsha", "auspicious and inauspicious effects (maternal)"),
        VargaSpec(45, "Akshavedamsha", "character and conduct (paternal)"),
        VargaSpec(60, "Shashtiamsha", "past karma; all matters"),
        VargaSpec(81, "Navanavamsha", "subtle refinement of the navamsha"),
        VargaSpec(108, "Ashtottaramsha", "subtle karmic results"),
        VargaSpec(144, "Dwadash-dwadashamsha", "subtle refinement of the dwadashamsha"),
    )
}

#: The sixteen Shodashavarga divisions of BPHS.
SHODASHAVARGA: tuple[int, ...] = (1, 2, 3, 4, 7, 9, 10, 12, 16, 20, 24, 27, 30, 40, 45, 60)

# Trimsamsa: (upper bound in degrees, sign) for odd and even signs.
_D30_ODD = (
    (5.0, Sign.ARIES),
    (10.0, Sign.AQUARIUS),
    (18.0, Sign.SAGITTARIUS),
    (25.0, Sign.GEMINI),
    (30.0, Sign.LIBRA),
)
_D30_EVEN = (
    (5.0, Sign.TAURUS),
    (12.0, Sign.VIRGO),
    (20.0, Sign.PISCES),
    (25.0, Sign.CAPRICORN),
    (30.0, Sign.SCORPIO),
)

#: Vargas whose even-sign reversal counts backwards from the usual starting sign
#: (the others reverse the order of the parts).
_COUNT_BACKWARD_FROM_START = frozenset({12, 24})

_D5_ODD = (Sign.ARIES, Sign.AQUARIUS, Sign.SAGITTARIUS, Sign.GEMINI, Sign.LIBRA)
_D5_EVEN = (Sign.TAURUS, Sign.VIRGO, Sign.PISCES, Sign.CAPRICORN, Sign.SCORPIO)


def _is_odd(sign: int) -> bool:
    return sign % 2 == 0  # Aries (0), Gemini (2), ... are odd signs


def _modality(sign: int) -> int:
    return sign % 3  # 0 movable, 1 fixed, 2 dual


def _parashara_start(division: int, sign: int) -> int | None:
    """Starting sign for vargas whose parts run forward from one sign, else None."""
    odd = _is_odd(sign)
    mode = _modality(sign)
    if division == 3:
        return sign  # parts step by 4, handled separately
    if division in (4, 12, 60):
        return sign
    if division in {6, 40}:
        return 0 if odd else 6
    if division == 7:
        return sign if odd else sign + 6
    if division == 8:
        return (0, 8, 4)[mode]
    if division in (9, 81):
        return 9 * sign
    if division == 10:
        return sign if odd else sign + 8
    if division in (16, 45):
        return (0, 4, 8)[mode]
    if division == 20:
        return (0, 8, 4)[mode]
    if division == 24:
        return 4 if odd else 3
    if division == 27:
        return (0, 3, 6, 9)[sign % 4]
    return None


def part_index(degrees_in_sign: float, division: int) -> int:
    return min(int(degrees_in_sign * division / 30.0), division - 1)


def varga_sign_index(
    sign: int, degrees_in_sign: float, division: int, method: VargaMethod = VargaMethod.PARASHARA
) -> int:
    """Sign index (0 = Aries) of a position in a divisional chart."""
    if division == 1:
        return sign
    n = division
    p = part_index(degrees_in_sign, n)

    if method is VargaMethod.PARIVRITTI_CYCLIC:
        return (n * sign + p) % 12
    if method is VargaMethod.PARIVRITTI_EVEN_REVERSE:
        return (n * sign + (p if _is_odd(sign) else n - 1 - p)) % 12
    if method is VargaMethod.PARIVRITTI_ALTERNATE:
        k = sign // 2
        return (n * k + p) % 12 if _is_odd(sign) else (-n * k - 1 - p) % 12
    if method is VargaMethod.JAGANNATHA:
        if n != 3:
            raise ValueError("the Jagannatha method applies to the drekkana (D3) only")
        movable_of_element = (0, 9, 6, 3)[sign % 4]
        return (movable_of_element + 4 * p) % 12
    if method is VargaMethod.RAMAN:
        if n != 11:
            raise ValueError("the Raman method applies to the ekadashamsha (D11) only")
        return (sign - 1 - p) % 12

    if method is VargaMethod.SIDDHAMSA_FROM_LEO:
        if n != 24:
            raise ValueError("the Siddhamsa-from-Leo method applies to D24 only")
        return (Sign.LEO + p) % 12

    # Parashara (optionally with even signs reversed).
    reverse = method is VargaMethod.PARASHARA_EVEN_REVERSE and not _is_odd(sign)
    if reverse and n in _COUNT_BACKWARD_FROM_START:
        start = _parashara_start(n, sign)
        if start is None:
            raise ValueError(f"D{n} has no Parashara starting sign")
        return (start - p) % 12
    q = n - 1 - p if reverse else p
    if n == 2:
        sun_half = (q == 0) == _is_odd(sign)
        return Sign.LEO if sun_half else Sign.CANCER
    if n == 3:
        return (sign + 4 * q) % 12
    if n == 4:
        return (sign + 3 * q) % 12
    if n == 5:
        return (_D5_ODD if _is_odd(sign) else _D5_EVEN)[q]
    if n == 11:
        return (q - sign) % 12
    if n == 30:
        table = _D30_ODD if _is_odd(sign) else _D30_EVEN
        for upper, target in table:
            if degrees_in_sign < upper:
                return int(target)
        return int(table[-1][1])
    if n == 108:
        navamsa = (9 * sign + q // 12) % 12
        return (navamsa + q % 12) % 12
    if n == 144:
        dwadashamsa = (sign + q // 12) % 12
        return (dwadashamsa + q % 12) % 12
    start = _parashara_start(n, sign)
    if start is None:
        raise ValueError(f"no Parashara rule for D{n}; use a parivritti method")
    return (start + q) % 12


def varga_longitude(
    longitude: float, division: int, method: VargaMethod = VargaMethod.PARASHARA
) -> float:
    """Longitude in the divisional chart: its sign plus (degrees in sign x n) mod 30."""
    longitude %= 360.0
    sign = int(longitude // 30.0)
    degrees = longitude - 30.0 * sign
    target = varga_sign_index(sign, degrees, division, method)
    return 30.0 * target + (degrees * division) % 30.0


def varga_sign(
    longitude: float, division: int, method: VargaMethod = VargaMethod.PARASHARA
) -> Sign:
    return Sign(int(varga_longitude(longitude, division, method) // 30.0))
