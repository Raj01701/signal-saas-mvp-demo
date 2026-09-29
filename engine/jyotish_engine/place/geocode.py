"""Offline place search over GeoNames (CC BY 4.0), via the ``geonamescache`` package.

The gazetteer covers about 235,000 populated places with at least 500 inhabitants,
including Hindi and regional-script alternate names. Places missing from it can be
entered with a map pin (explicit coordinates).
"""

from __future__ import annotations

import unicodedata
from bisect import bisect_left
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import geonamescache

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


def normalize(text: str) -> str:
    """Case- and accent-insensitive key: 'Bengaluru', 'bengaluru' and 'Bengalūru' match."""
    decomposed = unicodedata.normalize("NFKD", text.casefold().strip())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


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
