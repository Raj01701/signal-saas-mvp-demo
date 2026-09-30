"""Dasha tables, running periods, dasha years and applicability rules."""

from __future__ import annotations

from datetime import UTC, datetime
from itertools import pairwise

import pytest

from jyotish_engine.astro.bodies import Body
from jyotish_engine.astro.time import jd_to_datetime
from jyotish_engine.core.nakshatra import NAKSHATRA_SPAN
from jyotish_engine.dasha.base import SubPeriodRule
from jyotish_engine.dasha.conditions import applicability, in_sun_hora, shukla_paksha
from jyotish_engine.dasha.nakshatra import DEFINITIONS, NakshatraDasha, mahadashas
from jyotish_engine.dasha.tables import SPAN_YEARS, nakshatra_dasha_table
from jyotish_engine.dasha.years import dasha_year_days, true_sidereal_year_days
from jyotish_engine.settings import DASHA_YEAR_DAYS, DashaYear, Settings

BIRTH = 2448029.5  # 1990-05-18 00:00 UT
YEAR = DASHA_YEAR_DAYS[DashaYear.SIDEREAL]


def test_birth_balance_follows_the_moon_through_its_nakshatra() -> None:
    at_start = nakshatra_dasha_table(NakshatraDasha.VIMSHOTTARI, BIRTH, 0.0, YEAR)
    assert at_start.birth_lord is Body.KETU
    assert at_start.balance_years == pytest.approx(7.0)
    halfway = nakshatra_dasha_table(NakshatraDasha.VIMSHOTTARI, BIRTH, NAKSHATRA_SPAN / 2, YEAR)
    assert halfway.balance_years == pytest.approx(3.5)
    # Bharani (the second nakshatra) is ruled by Venus, 20 years.
    bharani = nakshatra_dasha_table(NakshatraDasha.VIMSHOTTARI, BIRTH, NAKSHATRA_SPAN * 1.25, YEAR)
    assert bharani.birth_lord is Body.VENUS
    assert bharani.balance_years == pytest.approx(15.0)


def test_table_rows_are_depth_first_and_contiguous() -> None:
    table = nakshatra_dasha_table(NakshatraDasha.VIMSHOTTARI, BIRTH, 123.4, YEAR, depth=2)
    mahas = [p for p in table.periods if len(p.lords) == 1]
    assert table.periods[0].lords == [mahas[0].lords[0]]
    assert [len(p.lords) for p in table.periods[1:10]] == [2] * 9
    for first, second in pairwise(mahas):
        assert first.end_jd_ut == pytest.approx(second.start_jd_ut)
    antars = [p for p in table.periods if len(p.lords) == 2]
    assert len(antars) == 9 * len(mahas)
    # The mahadasha table reaches the end of a human lifespan.
    assert mahas[0].start_jd_ut <= BIRTH < mahas[0].end_jd_ut
    assert mahas[-1].end_jd_ut >= BIRTH + SPAN_YEARS * YEAR
    assert mahas[-1].start_jd_ut < BIRTH + SPAN_YEARS * YEAR


def test_short_cycles_repeat_to_cover_a_lifespan() -> None:
    table = nakshatra_dasha_table(NakshatraDasha.YOGINI, BIRTH, 200.0, YEAR, depth=1)
    assert DEFINITIONS[NakshatraDasha.YOGINI].total_years == 36
    assert len(table.periods) > 3 * 8
    assert table.periods[-1].end_jd_ut >= BIRTH + SPAN_YEARS * YEAR


def test_table_depth_is_limited() -> None:
    for depth in (0, 4):
        with pytest.raises(ValueError, match="depth"):
            nakshatra_dasha_table(NakshatraDasha.VIMSHOTTARI, BIRTH, 10.0, YEAR, depth=depth)


def test_equal_and_proportional_sub_periods() -> None:
    proportional = nakshatra_dasha_table(NakshatraDasha.YOGINI, BIRTH, 50.0, YEAR, depth=2)
    equal = nakshatra_dasha_table(
        NakshatraDasha.YOGINI, BIRTH, 50.0, YEAR, depth=2, rule=SubPeriodRule.EQUAL
    )
    first_p = [p for p in proportional.periods[1:9]]
    first_e = [p for p in equal.periods[1:9]]
    lengths_e = {round(p.end_jd_ut - p.start_jd_ut, 6) for p in first_e}
    assert len(lengths_e) == 1
    assert len({round(p.end_jd_ut - p.start_jd_ut, 6) for p in first_p}) > 1


def test_sub_periods_start_from_the_period_lord() -> None:
    periods = mahadashas(NakshatraDasha.VIMSHOTTARI, BIRTH, 250.0, YEAR)
    table = nakshatra_dasha_table(NakshatraDasha.VIMSHOTTARI, BIRTH, 250.0, YEAR, depth=3)
    assert table.periods[1].lords == [periods[0].lord, periods[0].lord]
    assert table.periods[2].lords == [periods[0].lord] * 3


def test_jd_to_datetime() -> None:
    assert jd_to_datetime(2451545.0) == datetime(2000, 1, 1, 12, 0, tzinfo=UTC)
    assert jd_to_datetime(2451545.5) == datetime(2000, 1, 2, 0, 0, tzinfo=UTC)
    assert jd_to_datetime(BIRTH + 0.25) == datetime(1990, 5, 18, 6, 0, tzinfo=UTC)


def test_dasha_year_options() -> None:
    assert dasha_year_days(Settings(), BIRTH) == YEAR
    assert dasha_year_days(Settings(dasha_year=DashaYear.SAVANA), BIRTH) == 360.0
    true_year = dasha_year_days(Settings(dasha_year=DashaYear.TRUE_SIDEREAL), BIRTH)
    assert true_year == pytest.approx(YEAR, abs=0.01)
    assert true_year != YEAR


def test_true_sidereal_year_near_the_start_of_the_ephemeris() -> None:
    """Before 1900-07 the previous sankranti may be out of range; the next year is used."""
    assert true_sidereal_year_days(2415000.0) == pytest.approx(YEAR, abs=0.01)


def test_horas_and_pakshas() -> None:
    assert in_sun_hora(5.0) and not in_sun_hora(20.0)  # Aries: Sun's hora first
    assert not in_sun_hora(35.0) and in_sun_hora(50.0)  # Taurus: Moon's hora first
    assert shukla_paksha(10.0, 100.0)
    assert not shukla_paksha(10.0, 200.0)
    assert shukla_paksha(350.0, 20.0)


def _verdicts(
    ascendant: float, born_during_day: bool | None, **longitudes: float
) -> dict[NakshatraDasha, bool | None]:
    sidereal = {
        body: 0.0
        for body in Body
        if body.value
        in {"sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu", "ketu"}
    }
    sidereal.update({Body(name): value for name, value in longitudes.items()})
    return {a.system: a.applicable for a in applicability(ascendant, sidereal, born_during_day)}


def test_shattrimsha_sama_needs_day_and_sun_hora_or_night_and_moon_hora() -> None:
    assert _verdicts(5.0, True)[NakshatraDasha.SHATTRIMSHA_SAMA] is True
    assert _verdicts(20.0, False)[NakshatraDasha.SHATTRIMSHA_SAMA] is True
    assert _verdicts(20.0, True)[NakshatraDasha.SHATTRIMSHA_SAMA] is False
    assert _verdicts(5.0, None)[NakshatraDasha.SHATTRIMSHA_SAMA] is None


def test_shodashottari_pairs_paksha_with_hora() -> None:
    # Sun's hora (5 deg Aries) in Shukla paksha (Moon 90 deg ahead of the Sun).
    assert _verdicts(5.0, True, sun=0.0, moon=90.0)[NakshatraDasha.SHODASHOTTARI] is True
    assert _verdicts(5.0, True, sun=0.0, moon=270.0)[NakshatraDasha.SHODASHOTTARI] is False
    assert _verdicts(20.0, True, sun=0.0, moon=270.0)[NakshatraDasha.SHODASHOTTARI] is True


def test_universal_dashas_always_apply() -> None:
    verdicts = _verdicts(123.0, None, moon=77.0)
    assert verdicts[NakshatraDasha.VIMSHOTTARI] is True
    assert verdicts[NakshatraDasha.YOGINI] is True
