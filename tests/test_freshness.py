"""Tests for provider timestamp freshness rules."""

from datetime import UTC, date, datetime, timedelta

from custom_components.ukr_hmc.const import WEATHER_OBSERVATION_MAX_AGE
from custom_components.ukr_hmc.freshness import data_age, is_fresh


def test_freshness_accepts_recent_and_rejects_stale_data() -> None:
    now = datetime(2026, 9, 4, 12, tzinfo=UTC)

    assert is_fresh(now - WEATHER_OBSERVATION_MAX_AGE, WEATHER_OBSERVATION_MAX_AGE, now)
    assert not is_fresh(
        now - WEATHER_OBSERVATION_MAX_AGE - timedelta(seconds=1),
        WEATHER_OBSERVATION_MAX_AGE,
        now,
    )


def test_freshness_rejects_implausible_future_timestamp() -> None:
    now = datetime(2026, 9, 4, 12, tzinfo=UTC)

    assert is_fresh(now + timedelta(hours=2), WEATHER_OBSERVATION_MAX_AGE, now)
    assert not is_fresh(
        now + timedelta(hours=2, seconds=1), WEATHER_OBSERVATION_MAX_AGE, now
    )


def test_date_age_uses_ukraine_local_midnight() -> None:
    now = datetime(2026, 9, 4, 21, tzinfo=UTC)

    assert data_age(date(2026, 9, 5), now) == timedelta(0)
