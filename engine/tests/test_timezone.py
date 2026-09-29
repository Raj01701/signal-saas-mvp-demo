from datetime import UTC, datetime, timedelta

import pytest

from jyotish_engine.place.timezone import (
    Confidence,
    TimeStandard,
    resolve_local_time,
    timezone_for,
)

DELHI = (28.6139, 77.2090)
MUMBAI = (19.0760, 72.8777)
KOLKATA = (22.5726, 88.3639)
VARANASI = (25.3176, 82.9739)
NEW_YORK = (40.7128, -74.0060)


def test_timezone_lookup_is_offline_and_correct() -> None:
    assert timezone_for(*DELHI) == "Asia/Kolkata"
    assert timezone_for(*NEW_YORK) == "America/New_York"


def test_modern_indian_birth_is_high_confidence_ist() -> None:
    result = resolve_local_time(datetime(1990, 5, 17, 12, 0), *DELHI)
    assert result.chosen.standard is TimeStandard.ZONE
    assert result.chosen.utc == datetime(1990, 5, 17, 6, 30, tzinfo=UTC)
    assert result.confidence is Confidence.HIGH
    assert not result.ambiguous


def test_bombay_before_1955_defaults_to_bombay_time_and_offers_ist() -> None:
    result = resolve_local_time(datetime(1950, 6, 15, 7, 0), *MUMBAI)
    assert result.chosen.standard is TimeStandard.BOMBAY_TIME
    assert result.chosen.utc == datetime(1950, 6, 15, 2, 8, 50, tzinfo=UTC)
    assert result.ambiguous
    ist = [a for a in result.alternatives if a.standard is TimeStandard.ZONE]
    assert ist and ist[0].utc == datetime(1950, 6, 15, 1, 30, tzinfo=UTC)


def test_calcutta_time_before_1948() -> None:
    result = resolve_local_time(datetime(1940, 1, 10, 6, 0), *KOLKATA)
    assert result.chosen.standard is TimeStandard.CALCUTTA_TIME
    assert result.chosen.utc_offset_seconds == 5 * 3600 + 53 * 60 + 20


def test_bombay_after_1955_is_ist() -> None:
    result = resolve_local_time(datetime(1960, 1, 1, 12, 0), *MUMBAI)
    assert result.chosen.standard is TimeStandard.ZONE
    assert result.chosen.utc_offset_seconds == 5.5 * 3600


def test_world_war_ii_war_time_is_applied_and_flagged() -> None:
    result = resolve_local_time(datetime(1943, 7, 1, 10, 0), *DELHI)
    assert result.chosen.utc_offset_seconds == 6.5 * 3600
    assert result.ambiguous
    assert any("war time" in w for w in result.warnings)


def test_1962_war_offers_ist_plus_one_without_applying_it() -> None:
    result = resolve_local_time(datetime(1962, 11, 1, 9, 0), *DELHI)
    assert result.chosen.utc_offset_seconds == 5.5 * 3600
    assert result.ambiguous
    assert any(a.utc_offset_seconds == 6.5 * 3600 for a in result.alternatives)


def test_pre_1906_india_uses_local_mean_time() -> None:
    result = resolve_local_time(datetime(1890, 3, 1, 5, 0), *VARANASI)
    assert result.chosen.standard is TimeStandard.LMT
    assert result.chosen.utc_offset_seconds == pytest.approx(VARANASI[1] * 240.0)
    assert result.confidence is Confidence.LOW


def test_dst_fold_returns_both_occurrences() -> None:
    result = resolve_local_time(datetime(2021, 11, 7, 1, 30), *NEW_YORK)
    assert result.ambiguous
    utcs = {result.chosen.utc, *(a.utc for a in result.alternatives)}
    assert utcs == {
        datetime(2021, 11, 7, 5, 30, tzinfo=UTC),
        datetime(2021, 11, 7, 6, 30, tzinfo=UTC),
    }


def test_dst_gap_is_reported() -> None:
    result = resolve_local_time(datetime(2021, 3, 14, 2, 30), *NEW_YORK)
    assert result.ambiguous
    assert any("did not exist" in w for w in result.warnings)


def test_forced_standards() -> None:
    fixed = resolve_local_time(
        datetime(1950, 6, 15, 7, 0),
        *MUMBAI,
        standard=TimeStandard.FIXED_OFFSET,
        utc_offset_seconds=19800,
    )
    assert fixed.chosen.utc == datetime(1950, 6, 15, 1, 30, tzinfo=UTC)
    lmt = resolve_local_time(datetime(2000, 1, 1, 12, 0), *DELHI, standard=TimeStandard.LMT)
    assert lmt.chosen.utc == datetime(2000, 1, 1, 12, 0, tzinfo=UTC) - timedelta(
        seconds=DELHI[1] * 240.0
    )


def test_aware_datetimes_are_rejected() -> None:
    with pytest.raises(ValueError, match="without a timezone"):
        resolve_local_time(datetime(2000, 1, 1, tzinfo=UTC), *DELHI)
