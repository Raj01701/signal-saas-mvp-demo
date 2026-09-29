from jyotish_engine.place.geocode import normalize, search_places


def test_normalize_ignores_case_and_accents() -> None:
    assert normalize("Bengalūru") == normalize("BENGALURU") == "bengaluru"


def test_search_finds_major_city_first() -> None:
    results = search_places("Mumbai")
    assert results[0].name == "Mumbai"
    assert results[0].country_code == "IN"
    assert results[0].timezone == "Asia/Kolkata"


def test_search_by_historical_name() -> None:
    assert search_places("Bombay", country_code="IN")[0].name == "Mumbai"
    assert search_places("Benares")[0].name == "Varanasi"


def test_search_by_devanagari_name() -> None:
    assert search_places("वाराणसी")[0].name == "Varanasi"


def test_prefix_search_and_country_filter() -> None:
    results = search_places("Tirupat", country_code="IN")
    assert any(p.name == "Tirupati" for p in results)
    assert all(p.country_code == "IN" for p in results)


def test_empty_query_returns_nothing() -> None:
    assert search_places("   ") == []
