"""Offline place search over GeoNames (CC BY 4.0), via the ``geonamescache`` package.

The gazetteer covers about 235,000 populated places with at least 500 inhabitants,
including Hindi and regional-script alternate names. Places missing from it can be
entered with a map pin (explicit coordinates).
"""

from __future__ import annotations

import math
import re
from bisect import bisect_left
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import geonamescache

from jyotish_engine.place.normalize import normalize
from jyotish_engine.place.regions import country_name, match_country, match_region, region_name

#: Alternate names are indexed only for places at least this populous, which keeps
#: memory in check while still covering every district town.
ALTERNATE_NAME_MIN_POPULATION = 1000
MAX_NAME_LENGTH = 60


@dataclass(frozen=True, slots=True)
class Place:
    geonames_id: int
    name: str
    country_code: str
    admin1_code: str
    latitude: float
    longitude: float
    timezone: str
    population: int
    #: The state's name ("Haryana"), when known.
    admin1_name: str = ""

    @property
    def label(self) -> str:
        """ "Sirsa, Haryana, India"."""
        parts = [self.name, self.admin1_name, country_name(self.country_code)]
        return ", ".join(p for p in parts if p)


__all__ = ["Place", "Resolution", "normalize", "resolve_place", "search_places"]


class Gazetteer:
    def __init__(self, cities: dict[str, dict[str, Any]]) -> None:
        self._places: dict[int, Place] = {}
        self._index: dict[str, list[int]] = defaultdict(list)
        for raw in cities.values():
            place = Place(
                geonames_id=int(raw["geonameid"]),
                name=str(raw["name"]),
                country_code=str(raw["countrycode"]),
                admin1_code=str(raw.get("admin1code") or ""),
                latitude=float(raw["latitude"]),
                longitude=float(raw["longitude"]),
                timezone=str(raw["timezone"]),
                population=int(raw.get("population") or 0),
                admin1_name=region_name(str(raw["countrycode"]), str(raw.get("admin1code") or "")),
            )
            self._places[place.geonames_id] = place
            keys = {normalize(place.name)}
            if place.population >= ALTERNATE_NAME_MIN_POPULATION:
                keys.update(
                    normalize(alt)
                    for alt in raw.get("alternatenames") or []
                    if 0 < len(alt) <= MAX_NAME_LENGTH
                )
            for key in keys:
                self._index[key].append(place.geonames_id)
        self._sorted_keys = sorted(self._index)

    def __len__(self) -> int:
        return len(self._places)

    def get(self, geonames_id: int) -> Place | None:
        return self._places.get(geonames_id)

    def matches(self, query: str) -> tuple[list[Place], list[Place]]:
        """Places whose name (or an alternate name) is the query, and those it begins."""
        key = normalize(query)
        if not key:
            return [], []
        exact = set(self._index.get(key, ()))
        prefix: set[int] = set()
        start = bisect_left(self._sorted_keys, key)
        for candidate in self._sorted_keys[start : start + 2000]:
            if not candidate.startswith(key):
                break
            prefix.update(self._index[candidate])
        prefix -= exact
        return [self._places[i] for i in exact], [self._places[i] for i in prefix]

    def search(self, query: str, country_code: str | None = None, limit: int = 10) -> list[Place]:
        """Exact-name matches first, then prefix matches, each ranked by population."""
        key = normalize(query)
        if not key:
            return []
        exact = set(self._index.get(key, ()))
        prefix: set[int] = set()
        start = bisect_left(self._sorted_keys, key)
        for candidate in self._sorted_keys[start : start + 2000]:
            if not candidate.startswith(key):
                break
            prefix.update(self._index[candidate])
        prefix -= exact

        def ranked(ids: set[int]) -> list[Place]:
            places = [self._places[i] for i in ids]
            if country_code:
                places = [p for p in places if p.country_code == country_code.upper()]
            return sorted(places, key=lambda p: -p.population)

        return (ranked(exact) + ranked(prefix))[:limit]


@lru_cache(maxsize=1)
def gazetteer() -> Gazetteer:
    """Load the gazetteer once (about 1.5 s)."""
    cache = geonamescache.GeonamesCache(min_city_population=500)
    return Gazetteer(cache.get_cities())


def search_places(query: str, country_code: str | None = None, limit: int = 10) -> list[Place]:
    return gazetteer().search(query, country_code=country_code, limit=limit)


#: Decimal coordinates as copied from a map: "29.5321, 75.0318" or "29.5321 N 75.0318 E".
DECIMAL = re.compile(
    r"^\s*([+-]?\d{1,2}(?:\.\d+)?)\s*°?\s*([NS])?\s*[,;\s]\s*"
    r"([+-]?\d{1,3}(?:\.\d+)?)\s*°?\s*([EW])?\s*$",
    re.IGNORECASE,
)
#: Degrees and minutes (and seconds): "29°32′N 75°01′E", "29 32 06 N, 75 01 44 E".
DMS = re.compile(
    r"^\s*(\d{1,2})\s*[°\s]\s*(\d{1,2})\s*['′\s]?\s*(?:(\d{1,2}(?:\.\d+)?)\s*[\"″]?)?\s*([NS])"
    r"\s*[,;\s]\s*(\d{1,3})\s*[°\s]\s*(\d{1,2})\s*['′\s]?\s*(?:(\d{1,2}(?:\.\d+)?)\s*[\"″]?)?\s*"
    r"([EW])\s*$",
    re.IGNORECASE,
)


def parse_coordinates(text: str) -> tuple[float, float] | None:
    """Latitude and longitude written as decimals or as degrees and minutes, if valid."""
    match = DECIMAL.match(text)
    if match:
        lat, ns, lon, ew = match.groups()
        latitude = float(lat) * (-1 if (ns or "").upper() == "S" else 1)
        longitude = float(lon) * (-1 if (ew or "").upper() == "W" else 1)
    else:
        match = DMS.match(text)
        if not match:
            return None
        d1, m1, s1, ns, d2, m2, s2, ew = match.groups()
        latitude = (int(d1) + int(m1) / 60 + float(s1 or 0) / 3600) * (
            -1 if ns.upper() == "S" else 1
        )
        longitude = (int(d2) + int(m2) / 60 + float(s2 or 0) / 3600) * (
            -1 if ew.upper() == "W" else 1
        )
    if abs(latitude) > 90 or abs(longitude) > 180:
        return None
    return latitude, longitude


@dataclass(frozen=True, slots=True)
class Resolution:
    """Where a birthplace was found, how, and what else it could have been."""

    latitude: float
    longitude: float
    label: str
    #: How the place was chosen, in a sentence.
    how: str
    place: Place | None = None
    alternatives: tuple[Place, ...] = ()
    #: Several places share the name and nothing typed told them apart.
    ambiguous: bool = False


def _in_region(region: tuple[str, str]) -> Callable[[Place], bool]:
    return lambda p: (p.country_code, p.admin1_code) == region


def _in_country(country: str) -> Callable[[Place], bool]:
    return lambda p: p.country_code == country


def resolve_place(text: str) -> Resolution:
    """A birthplace from what someone typed: coordinates, or "town, state, country".

    The state or country after a comma narrows the search; without one, Indian places
    come first and the most populous wins, and the result says when other places share
    the name. Raises ``ValueError`` when nothing is found.
    """
    coordinates = parse_coordinates(text)
    if coordinates is not None:
        lat, lon = coordinates
        return Resolution(lat, lon, f"{lat:.5f}, {lon:.5f}", "coordinates as entered")
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if not parts:
        raise ValueError("enter a place name or its coordinates")
    head, qualifiers = parts[0], parts[1:]
    regions = [r for q in qualifiers if (r := match_region(q)) is not None]
    countries = [c for q in qualifiers if (c := match_country(q)) is not None]
    exact, prefix = gazetteer().matches(head)
    if not exact and not prefix:
        raise ValueError(f'no place called "{head}" was found; enter its coordinates instead')
    # The narrowest qualifier that finds the place wins: a state, then a country.
    filters: list[tuple[str, Callable[[Place], bool]]] = []
    for r in regions:
        filters.append((region_name(*r) or r[1], _in_region(r)))
    for c in countries:
        filters.append((country_name(c), _in_country(c)))
    pool: list[Place] = []
    where = ""
    for label, keep in filters:
        pool = [p for p in exact if keep(p)] or [p for p in prefix if keep(p)]
        if pool:
            where = label
            break
    unmatched = bool(filters) and not pool
    if not pool:
        pool = exact or prefix
    ranked = sorted(pool, key=lambda p: (p.country_code != "IN" and not where, -p.population))
    best = ranked[0]
    others = sorted(
        (p for p in (exact or prefix) if p is not best),
        key=lambda p: (p.country_code != "IN", -p.population),
    )
    groups = {(p.country_code, p.admin1_code) for p in (pool if where else exact)}
    same_name = [p for p in pool if normalize(p.name) == normalize(best.name)]
    ambiguous = (not where and len(groups) > 1) or len(same_name) > 1
    if unmatched:
        how = (
            f'no "{head}" was found in {", ".join(qualifiers)}; the closest match is used, '
            "so please check it or enter coordinates"
        )
    elif where and len(same_name) > 1:
        how = (
            f"matched in {where}, as entered; {len(same_name)} places there share the name and "
            "the largest is used, so check it or enter coordinates if you meant another"
        )
    elif where:
        how = f"matched in {where}, as entered"
    elif ambiguous:
        how = (
            f"{len(groups)} places in the gazetteer are called {best.name}; the largest is "
            "used. Add the state after a comma, or enter coordinates, if you meant another"
        )
    else:
        how = f'best match for "{text.strip()}" (population {best.population:,})'
    return Resolution(
        best.latitude,
        best.longitude,
        best.label,
        how,
        best,
        tuple(others[:5]),
        ambiguous,
    )


def dms(latitude: float, longitude: float) -> str:
    """Degrees, minutes and seconds with hemispheres: "29°32′06″ N, 75°01′44″ E"."""

    def one(value: float, positive: str, negative: str) -> str:
        sign = positive if value >= 0 else negative
        seconds = round(abs(value) * 3600)
        degrees, rest = divmod(seconds, 3600)
        minutes, secs = divmod(rest, 60)
        return f"{degrees}°{minutes:02d}′{secs:02d}″ {sign}"

    return f"{one(latitude, 'N', 'S')}, {one(longitude, 'E', 'W')}"


def seconds_per_km(latitude: float) -> float:
    """Clock seconds that one kilometre east or west moves a chart (4 minutes a degree)."""
    km_per_degree = 111.32 * max(math.cos(math.radians(latitude)), 0.01)
    return 240.0 / km_per_degree
