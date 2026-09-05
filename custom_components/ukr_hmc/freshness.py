"""Provider timestamp freshness helpers."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .const import FUTURE_DATA_TOLERANCE

UKRAINE_TIME_ZONE = ZoneInfo("Europe/Kyiv")


def as_observation_datetime(value: datetime | date) -> datetime:
    """Normalize a provider observation timestamp to an aware datetime."""
    if isinstance(value, datetime):
        return value
    return datetime.combine(value, time.min, tzinfo=UKRAINE_TIME_ZONE)


def data_age(value: datetime | date, now: datetime | None = None) -> timedelta:
    """Return the age of a provider observation."""
    observed_at = as_observation_datetime(value).astimezone(UTC)
    current = now or datetime.now(UTC)
    return current.astimezone(UTC) - observed_at


def is_fresh(
    value: datetime | date,
    maximum_age: timedelta,
    now: datetime | None = None,
) -> bool:
    """Return whether provider data is neither stale nor implausibly future-dated."""
    age = data_age(value, now)
    return -FUTURE_DATA_TOLERANCE <= age <= maximum_age
