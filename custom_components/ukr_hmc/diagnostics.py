"""Diagnostics support for UkrHMC."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import UkrHMCConfigEntry


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
