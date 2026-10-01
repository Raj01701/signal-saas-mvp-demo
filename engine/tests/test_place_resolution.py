"""Birthplaces: the state after a comma picks among towns of the same name, same-name
places are flagged, and coordinates pasted from a map are read as they are."""

from __future__ import annotations

import pytest

from jyotish_engine.place.geocode import (
    dms,
    parse_coordinates,
    resolve_place,
    search_places,
    seconds_per_km,
)
from jyotish_engine.place.regions import match_country, match_region


def test_the_state_after_a_comma_picks_the_town() -> None:
    sirsa = resolve_place("sirsa, haryana")
    assert sirsa.label == "Sirsa, Haryana, India" and not sirsa.ambiguous
    assert sirsa.latitude == pytest.approx(29.535, abs=0.01)
    hamirpur = resolve_place("Hamirpur, HP")
    assert "Himachal Pradesh" in hamirpur.label and hamirpur.latitude > 31
    aurangabad = resolve_place("aurangabad, bihar")
    assert "Bihar" in aurangabad.label and aurangabad.longitude > 84


def test_same_name_places_are_flagged() -> None:
    hamirpur = resolve_place("hamirpur")
    assert hamirpur.ambiguous and "are called" in hamirpur.how
    assert any("Himachal Pradesh" in p.label for p in hamirpur.alternatives)
    rampur = resolve_place("rampur, UP")
    assert rampur.ambiguous and "share the name" in rampur.how


def test_countries_and_unknown_states() -> None:
    assert resolve_place("london, uk").label == "London, United Kingdom"
    assert "Switzerland" in resolve_place("zurich, ch").label
    assert "Pakistan" in resolve_place("hyderabad, pakistan").label
    assert "closest match" in resolve_place("sirsa, kerala").how
    with pytest.raises(ValueError, match="coordinates"):
        resolve_place("xyzzyq")


def test_coordinates_from_a_map() -> None:
    assert parse_coordinates("29.5321, 75.0318") == (29.5321, 75.0318)
    assert parse_coordinates("33.86 S 151.21 E") == (-33.86, 151.21)
    lat, lon = parse_coordinates("29°32′06″N 75°01′44″E") or (0.0, 0.0)
    assert lat == pytest.approx(29.535, abs=1e-3) and lon == pytest.approx(75.0289, abs=1e-3)
    assert parse_coordinates("Sirsa") is None and parse_coordinates("95, 75") is None
    pasted = resolve_place("29.5321, 75.0318")
    assert pasted.place is None and pasted.how == "coordinates as entered"


def test_formats_and_precision() -> None:
    assert dms(29.53489, 75.02898) == "29°32′06″ N, 75°01′44″ E"
    assert dms(-33.86, -70.5) == "33°51′36″ S, 70°30′00″ W"
    assert seconds_per_km(0.0) == pytest.approx(2.156, abs=0.01)
    assert seconds_per_km(29.5) == pytest.approx(2.48, abs=0.02)


def test_regions_and_search_carry_state_names() -> None:
    assert match_region("Haryana") == ("IN", "10") and match_region("U.P.") is None
    assert match_region("up") == ("IN", "36") and match_region("Texas") == ("US", "TX")
    assert match_country("India") == "IN" and match_country("USA") == "US"
    assert search_places("Sirsa", limit=1)[0].admin1_name == "Haryana"
