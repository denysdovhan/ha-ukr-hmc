"""Diagnostics support for UkrHMC."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import UkrHMCConfigEntry

from .const import (
    HYDROLOGY_OBSERVATION_MAX_AGE,
    LOCATION_FORECAST_MAX_AGE,
    RADIATION_OBSERVATION_MAX_AGE,
    SNOW_OBSERVATION_MAX_AGE,
    WEATHER_OBSERVATION_MAX_AGE,
)
from .freshness import as_observation_datetime, data_age, is_fresh


def _freshness_summary(
    timestamps: list[datetime | date], maximum_age: timedelta
) -> dict[str, Any]:
    """Return privacy-safe freshness details for one product family."""
    if not timestamps:
        return {
            "record_count": 0,
            "latest_observation": None,
            "age_seconds": None,
            "maximum_age_seconds": int(maximum_age.total_seconds()),
            "stale": None,
        }
    latest = max(as_observation_datetime(value) for value in timestamps)
    age = data_age(latest, datetime.now(UTC))
    return {
        "record_count": len(timestamps),
        "latest_observation": latest.isoformat(),
        "age_seconds": round(age.total_seconds()),
        "maximum_age_seconds": int(maximum_age.total_seconds()),
        "stale": not is_fresh(latest, maximum_age),
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,  # noqa: ARG001
    entry: UkrHMCConfigEntry,
) -> dict[str, Any]:
    """Return privacy-safe diagnostics for a config entry."""
    coordinator = entry.runtime_data.coordinator
    data = coordinator.data
    subentry_counts = Counter(
        subentry.subentry_type for subentry in entry.subentries.values()
    )

    return {
        "config_entry": {
            "version": entry.version,
            "minor_version": entry.minor_version,
            "subentry_counts": dict(sorted(subentry_counts.items())),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_successful_update": (
                coordinator.last_successful_update.isoformat()
                if coordinator.last_successful_update
                else None
            ),
            "consecutive_update_failures": coordinator.consecutive_update_failures,
        },
        "endpoints": dict(sorted(entry.runtime_data.api.endpoint_availability.items())),
        "endpoint_telemetry": dict(
            sorted(getattr(entry.runtime_data.api, "endpoint_telemetry", {}).items())
        ),
        "sources": dict(
            sorted(getattr(entry.runtime_data.api, "source_availability", {}).items())
        ),
        "schema": (
            telemetry.snapshot()
            if (telemetry := getattr(entry.runtime_data.api, "schema_telemetry", None))
            else {}
        ),
        "freshness": {
            "weather_stations": _freshness_summary(
                [item.observed_at for item in data.observations.values()],
                WEATHER_OBSERVATION_MAX_AGE,
            ),
            "weather_locations": _freshness_summary(
                [
                    forecast.current.forecast_at
                    for forecast in data.location_forecasts.values()
                    if forecast.current is not None
                ],
                LOCATION_FORECAST_MAX_AGE,
            ),
            "radiation": _freshness_summary(
                [item.observed_at for item in data.radiation_observations.values()],
                RADIATION_OBSERVATION_MAX_AGE,
            ),
            "hydrology": _freshness_summary(
                [item.observed_at for item in data.hydrology_observations.values()],
                HYDROLOGY_OBSERVATION_MAX_AGE,
            ),
            "snow": _freshness_summary(
                [item.observed_on for item in data.snow_observations.values()],
                SNOW_OBSERVATION_MAX_AGE,
            ),
        },
        "record_counts": {
            "stations": len(data.stations),
            "observations": len(data.observations),
            "forecasts": sum(len(records) for records in data.forecasts.values()),
            "location_forecasts": len(data.location_forecasts),
            "hourly_forecasts": sum(
                len(forecast.hourly_forecasts)
                for forecast in data.location_forecasts.values()
            ),
            "radiation_stations": len(data.radiation_stations),
            "radiation_observations": len(data.radiation_observations),
            "hydrology_posts": len(data.hydrology_posts),
            "hydrology_observations": len(data.hydrology_observations),
            "snow_stations": len(data.snow_stations),
            "snow_observations": len(data.snow_observations),
            "regional_weather_warnings": sum(
                len(warnings) for warnings in data.regional_weather_warnings.values()
            ),
            "regional_fire_warnings": sum(
                len(warnings) for warnings in data.regional_fire_warnings.values()
            ),
            "regional_snow_warnings": sum(
                len(warnings) for warnings in data.regional_snow_warnings.values()
            ),
            "regional_hydrology_warnings": sum(
                len(warnings) for warnings in data.regional_hydrology_warnings.values()
            ),
        },
    }
