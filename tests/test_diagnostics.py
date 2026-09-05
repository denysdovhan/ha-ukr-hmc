"""Tests for privacy-safe integration diagnostics."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ukr_hmc.api.telemetry import SchemaTelemetry
from custom_components.ukr_hmc.const import DOMAIN
from custom_components.ukr_hmc.coordinator import UkrHMCCoordinator
from custom_components.ukr_hmc.data import UkrHMCRuntimeData
from custom_components.ukr_hmc.diagnostics import async_get_config_entry_diagnostics

from .fixtures import DATA, LOCATION_SUBENTRY_DATA, SNOW_SUBENTRY_DATA


async def test_config_entry_diagnostics_are_aggregated_and_private(hass) -> None:
    """Diagnostics include health and counts without configured location data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        version=1,
        minor_version=2,
        subentries_data=[LOCATION_SUBENTRY_DATA, SNOW_SUBENTRY_DATA],
    )
    schema_telemetry = SchemaTelemetry()
    schema_telemetry.accepted("snow_observations", 1)
    api = SimpleNamespace(
        endpoint_availability={"/_/m/snigost.js": True, "/fmi.json": False},
        endpoint_telemetry={
            "/fmi.json": {
                "available": False,
                "duration_ms": 1500,
                "attempts": 3,
                "status": 503,
                "status_category": "5xx",
                "error_category": "http",
            }
        },
        source_availability={"locations": False, "snow": True},
        schema_telemetry=schema_telemetry,
    )
    coordinator = UkrHMCCoordinator(hass, entry, AsyncMock())
    coordinator.async_set_updated_data(DATA)
    coordinator.last_successful_update = datetime(2026, 9, 4, 12, tzinfo=UTC)
    coordinator.consecutive_update_failures = 1
    entry.runtime_data = UkrHMCRuntimeData(api=api, coordinator=coordinator)

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["config_entry"] == {
        "version": 1,
        "minor_version": 2,
        "subentry_counts": {"snow_station": 1, "weather_location": 1},
    }
    assert diagnostics["coordinator"]["last_update_success"]
    assert diagnostics["coordinator"]["last_successful_update"] == (
        "2026-09-04T12:00:00+00:00"
    )
    assert diagnostics["coordinator"]["consecutive_update_failures"] == 1
    assert diagnostics["endpoints"] == {
        "/_/m/snigost.js": True,
        "/fmi.json": False,
    }
    assert diagnostics["sources"] == {"locations": False, "snow": True}
    assert diagnostics["endpoint_telemetry"]["/fmi.json"]["status_category"] == "5xx"
    assert diagnostics["schema"]["snow_observations"]["accepted"] == 1
    assert diagnostics["schema"]["_meta"]["telemetry_schema_version"] == 1
    assert diagnostics["freshness"]["hydrology"]["record_count"] == 1
    assert diagnostics["freshness"]["hydrology"]["maximum_age_seconds"] == 172800
    assert diagnostics["freshness"]["hydrology"]["stale"]
    assert diagnostics["freshness"]["weather_locations"]["record_count"] == 1
    assert diagnostics["record_counts"]["snow_observations"] == 1
    assert diagnostics["record_counts"]["hourly_forecasts"] == 1
    rendered = repr(diagnostics)
    assert "50.4501" not in rendered
    assert "30.5234" not in rendered
    assert "Home" not in rendered
