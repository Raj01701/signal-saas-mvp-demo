from datetime import datetime

import pytest
from pydantic import ValidationError

from jyotish_engine.astro.ayanamsa import Ayanamsa
from jyotish_engine.astro.bodies import GRAHAS, Body
from jyotish_engine.astro.houses import HouseSystem
from jyotish_engine.chart import compute_chart
from jyotish_engine.models import BirthInput, BirthTimeSource, PlaceInput
from jyotish_engine.place.timezone import TimeStandard
from jyotish_engine.settings import PRESETS, Preset, Settings

DELHI = PlaceInput(name="New Delhi", latitude=28.6139, longitude=77.2090, elevation_m=216)


def _birth(**overrides: object) -> BirthInput:
    fields: dict[str, object] = {
        "local_datetime": datetime(1990, 5, 17, 12, 0),
        "place": DELHI,
        "time_source": BirthTimeSource.BIRTH_CERTIFICATE,
    }
    fields.update(overrides)
    return BirthInput.model_validate(fields)


def test_chart_contains_all_grahas_and_houses() -> None:
    chart = compute_chart(_birth())
    assert [g.body for g in chart.grahas] == list(GRAHAS)
    assert len(chart.houses.whole_sign) == 12
    assert chart.houses.whole_sign[0] == chart.ascendant.sign
    assert chart.houses.system is HouseSystem.SRIPATI
    assert chart.rodden_rating == "AA"
    assert chart.time.interpretation.standard is TimeStandard.ZONE
    assert chart.ephemeris.name in {"DE421", "DE440"}


def test_sidereal_equals_tropical_minus_true_ayanamsa() -> None:
    chart = compute_chart(_birth())
    for graha in chart.grahas:
        expected = (graha.tropical_longitude - chart.ayanamsa.true) % 360.0
        assert graha.sidereal_longitude == pytest.approx(expected, abs=1e-9)
    # Lahiri in mid-1990 is about 23 deg 43 min.
    assert chart.ayanamsa.true == pytest.approx(23.72, abs=0.01)


def test_ketu_is_opposite_rahu_and_nodes_are_retrograde() -> None:
    chart = compute_chart(_birth())
    by_body = {g.body: g for g in chart.grahas}
    rahu, ketu = by_body[Body.RAHU], by_body[Body.KETU]
    assert (ketu.sidereal_longitude - rahu.sidereal_longitude) % 360.0 == pytest.approx(180.0)
    assert rahu.retrograde and ketu.retrograde


def test_sun_position_for_known_date() -> None:
    # 17 May 1990: tropical Sun near 26 deg Taurus, so sidereal Sun near 2 deg Taurus.
    chart = compute_chart(_birth())
    sun = next(g for g in chart.grahas if g.body is Body.SUN)
    assert sun.sign_name == "Vrishabha"
    assert 2.0 < sun.degrees_in_sign < 3.0


def test_birth_day_sunrise_brackets_the_birth() -> None:
    chart = compute_chart(_birth())
    assert chart.day.sunrise is not None
    assert chart.day.next_sunrise is not None
    assert chart.day.sunrise < chart.time.interpretation.utc < chart.day.next_sunrise
    assert chart.day.born_during_day is True
    assert chart.day.weekday == 4  # 17 May 1990 was a Thursday


def test_m2_quantities_are_present_and_consistent() -> None:
    chart = compute_chart(_birth())
    assert {v.division for v in chart.vargas} >= {1, 2, 3, 9, 10, 12, 30, 60, 144}
    d1 = next(v for v in chart.vargas if v.division == 1)
    assert d1.ascendant.sign == chart.ascendant.sign
    assert len(chart.special.karakas) == 8
    assert len(chart.special.arudhas) == 12
    assert chart.special.bhava_lagna is not None
    assert len(chart.special.upagrahas) == 11
    sun = next(g for g in chart.grahas if g.body is Body.SUN)
    assert sun.nakshatra.name == "Krittika"
    assert sun.house == (sun.sign - chart.ascendant.sign) % 12 + 1
    assert all(g.dignity is not None for g in chart.grahas)


def test_chart_serialises_to_json() -> None:
    chart = compute_chart(_birth())
    text = chart.model_dump_json()
    assert '"karakas"' in text and "NaN" not in text


def test_settings_hash_is_stable_and_sensitive() -> None:
    a = compute_chart(_birth()).settings_hash
    b = compute_chart(_birth()).settings_hash
    c = compute_chart(_birth(), Settings(ayanamsa=Ayanamsa.RAMAN)).settings_hash
    assert a == b != c


def test_presets_change_the_chart_as_expected() -> None:
    kp = compute_chart(_birth(), PRESETS[Preset.KP])
    classic = compute_chart(_birth(), PRESETS[Preset.CLASSIC_PARASHARI])
    assert kp.houses.system is HouseSystem.PLACIDUS
    assert kp.ayanamsa.true < classic.ayanamsa.true  # KP ayanamsa is ~6' smaller


def test_outer_planets_are_optional() -> None:
    chart = compute_chart(_birth(), Settings(include_outer_planets=True))
    assert {g.body for g in chart.grahas} >= {Body.URANUS, Body.NEPTUNE, Body.PLUTO}


def test_invalid_settings_are_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(ayanamsa=Ayanamsa.USER)
    with pytest.raises(ValidationError):
        Settings(bhava_system=HouseSystem.WHOLE_SIGN)


def test_bombay_birth_reports_ambiguity() -> None:
    mumbai = PlaceInput(name="Mumbai", latitude=19.0760, longitude=72.8777)
    chart = compute_chart(_birth(local_datetime=datetime(1950, 6, 15, 7, 0), place=mumbai))
    assert chart.time.ambiguous
    assert chart.time.interpretation.standard is TimeStandard.BOMBAY_TIME
    assert chart.time.alternatives
