"""Names of states and countries, so that a place typed as "Sirsa, Haryana" or
"Hamirpur, HP" finds the right town among several of the same name.

GeoNames identifies a state by its first-level administrative code: "IN.10" is
Haryana. The Indian codes below were checked against the gazetteer (the largest towns
under each code); United States codes are the two-letter postal codes.
"""

from __future__ import annotations

from functools import lru_cache

import geonamescache

from jyotish_engine.place.normalize import normalize

INDIA_STATES: dict[str, str] = {
    "01": "Andaman and Nicobar Islands",
    "02": "Andhra Pradesh",
    "03": "Assam",
    "05": "Chandigarh",
    "07": "Delhi",
    "09": "Gujarat",
    "10": "Haryana",
    "11": "Himachal Pradesh",
    "12": "Jammu and Kashmir",
    "13": "Kerala",
    "14": "Lakshadweep",
    "16": "Maharashtra",
    "17": "Manipur",
    "18": "Meghalaya",
    "19": "Karnataka",
    "20": "Nagaland",
    "21": "Odisha",
    "22": "Puducherry",
    "23": "Punjab",
    "24": "Rajasthan",
    "25": "Tamil Nadu",
    "26": "Tripura",
    "28": "West Bengal",
    "29": "Sikkim",
    "30": "Arunachal Pradesh",
    "31": "Mizoram",
    "33": "Goa",
    "34": "Bihar",
    "35": "Madhya Pradesh",
    "36": "Uttar Pradesh",
    "37": "Chhattisgarh",
    "38": "Jharkhand",
    "39": "Uttarakhand",
    "40": "Telangana",
    "41": "Ladakh",
    "52": "Dadra and Nagar Haveli and Daman and Diu",
}
#: Short forms and old names people write for Indian states.
INDIA_ALIASES: dict[str, str] = {
    "andaman": "01",
    "ap": "02",
    "andhra": "02",
    "as": "03",
    "dl": "07",
    "new delhi": "07",
    "ncr": "07",
    "nct": "07",
    "gj": "09",
    "hr": "10",
    "hp": "11",
    "himachal": "11",
    "j&k": "12",
    "j & k": "12",
    "jk": "12",
    "kashmir": "12",
    "kl": "13",
    "mh": "16",
    "ka": "19",
    "or": "21",
    "orissa": "21",
    "od": "21",
    "pondicherry": "22",
    "pondy": "22",
    "py": "22",
    "pb": "23",
    "rj": "24",
    "tn": "25",
    "wb": "28",
    "bengal": "28",
    "goa": "33",
    "br": "34",
    "mp": "35",
    "up": "36",
    "cg": "37",
    "chhatisgarh": "37",
    "chattisgarh": "37",
    "jh": "38",
    "uttaranchal": "39",
    "ts": "40",
    "telengana": "40",
    "daman": "52",
    "diu": "52",
    "dadra": "52",
    "silvassa": "52",
}
COUNTRY_ALIASES: dict[str, str] = {
    "usa": "US",
    "us": "US",
    "u.s.": "US",
    "u.s.a.": "US",
    "america": "US",
    "united states of america": "US",
    "uk": "GB",
    "u.k.": "GB",
    "britain": "GB",
    "great britain": "GB",
    "england": "GB",
    "scotland": "GB",
    "wales": "GB",
    "uae": "AE",
    "u.a.e.": "AE",
    "bharat": "IN",
    "hindustan": "IN",
}


@lru_cache(maxsize=1)
def _countries() -> dict[str, str]:
    """Country code to English name, from GeoNames."""
    countries = geonamescache.GeonamesCache().get_countries()
    return {code: str(info["name"]) for code, info in countries.items()}


@lru_cache(maxsize=1)
def _us_states() -> dict[str, str]:
    states = geonamescache.GeonamesCache().get_us_states()
    return {code: str(info["name"]) for code, info in states.items()}


def country_name(code: str) -> str:
    return _countries().get(code, code)


def region_name(country_code: str, admin1_code: str) -> str:
    """A state's name, or "" when it is not known."""
    if country_code == "IN":
        return INDIA_STATES.get(admin1_code, "")
    if country_code == "US":
        return _us_states().get(admin1_code, "")
    return ""


def match_country(text: str) -> str | None:
    """The country code a qualifier names ("India", "IN", "USA"), if any."""
    key = normalize(text)
    if key in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[key]
    for code, name in _countries().items():
        if key in (code.casefold(), normalize(name)):
            return code
    return None


def match_region(text: str) -> tuple[str, str] | None:
    """The (country code, state code) a qualifier names ("Haryana", "HP", "Texas")."""
    key = normalize(text).removesuffix(" state").strip()
    if key in INDIA_ALIASES:
        return "IN", INDIA_ALIASES[key]
    for code, name in INDIA_STATES.items():
        if key == normalize(name):
            return "IN", code
    for code, name in _us_states().items():
        if key in (normalize(name), code.casefold()) and len(key) > 2:
            return "US", code
    return None
