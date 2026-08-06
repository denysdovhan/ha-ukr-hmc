"""Tests for UkrHMC setup and unload."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ukr_hmc.const import DOMAIN, NAME
from custom_components.ukr_hmc.data import UkrHMCRuntimeData

from .fixtures import (
    DATA,
    HYDROLOGY_SUBENTRY_DATA,
    LOCATION_SUBENTRY_DATA,
    RADIATION_SUBENTRY_DATA,
    STATION_SUBENTRY_DATA,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


def _entity_id(
    registry: er.EntityRegistry,
    unique_id: str,
    platform: str = "sensor",
) -> str:
    """Return the registered entity ID for a tested entity."""
    entity_id = registry.async_get_entity_id(platform, DOMAIN, unique_id)
    assert entity_id is not None
    return entity_id


async def test_setup_creates_weather_and_current_sensors(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=NAME,
        unique_id=DOMAIN,
        data={},
        subentries_data=[
            STATION_SUBENTRY_DATA,
            LOCATION_SUBENTRY_DATA,
            RADIATION_SUBENTRY_DATA,
            HYDROLOGY_SUBENTRY_DATA,
        ],
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.ukr_hmc.api.UkrHMCClient.async_get_data",
        new=AsyncMock(return_value=DATA),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert isinstance(entry.runtime_data, UkrHMCRuntimeData)

    registry = er.async_get(hass)
    weather_entity_id = _entity_id(registry, "station-subentry", "weather")
    temperature_entity_id = _entity_id(registry, "station-subentry-temperature")
    condition_entity_id = _entity_id(registry, "station-subentry-condition")
    weather_description_entity_id = _entity_id(registry, "station-subentry-weather")
    location_weather_entity_id = _entity_id(registry, "location-subentry", "weather")
    location_temperature_entity_id = _entity_id(
        registry, "location-subentry-temperature"
    )
    location_condition_entity_id = _entity_id(registry, "location-subentry-condition")
    location_weather_description_entity_id = _entity_id(
        registry, "location-subentry-weather"
    )
    location_wind_compass_entity_id = _entity_id(
        registry, "location-subentry-wind_compass"
    )
    location_wind_direction_entity_id = _entity_id(
        registry, "location-subentry-wind_direction"
    )
    radiation_exposure_dose_rate_entity_id = _entity_id(
        registry,
        "radiation-subentry-exposure_dose_rate",
    )
    radiation_dose_rate_entity_id = _entity_id(
        registry,
        "radiation-subentry-dose_rate",
    )
    _entity_id(registry, "radiation-subentry-observation_time")
    hydrology_water_level_entity_id = _entity_id(
        registry,
        "hydrology-subentry-water_level",
    )
    hydrology_water_level_change_entity_id = _entity_id(
        registry,
        "hydrology-subentry-water_level_change",
    )
    hydrology_water_temperature_entity_id = _entity_id(
        registry,
        "hydrology-subentry-water_temperature",
    )
    hydrology_situation_entity_id = _entity_id(
        registry,
        "hydrology-subentry-hydrological_situation",
    )
    _entity_id(registry, "hydrology-subentry-water_level_altitude")
    _entity_id(registry, "hydrology-subentry-observation_time")
    assert (
        registry.async_get_entity_id(
            "sensor",
            DOMAIN,
            "location-subentry-pressure",
        )
        is None
    )
    assert (
        registry.async_get_entity_id(
            "sensor",
            DOMAIN,
            "station-subentry-wind_compass",
        )
        is None
    )
    assert registry.async_get_entity_id("weather", DOMAIN, "radiation-subentry") is None
    assert registry.async_get_entity_id("weather", DOMAIN, "hydrology-subentry") is None
    assert (
        registry.async_get_entity_id("sensor", DOMAIN, "radiation-subentry-dose_level")
        is None
    )
    assert hass.states.get(weather_entity_id).state == "partlycloudy"
    assert hass.states.get(temperature_entity_id).state == "25.9"
    assert hass.states.get(condition_entity_id).state == "partlycloudy"
    assert hass.states.get(weather_description_entity_id).state == (
        "Хмарно з проясненнями"
    )
    assert hass.states.get(location_weather_entity_id).state == "clear-night"
    assert hass.states.get(location_temperature_entity_id).state == "20"
    assert hass.states.get(location_condition_entity_id).state == "clear-night"
    assert hass.states.get(location_weather_description_entity_id).state == "Ясно"
    assert hass.states.get(location_wind_compass_entity_id).state == "NW"
    assert hass.states.get(location_wind_direction_entity_id).state == "315.0"
    assert hass.states.get(radiation_exposure_dose_rate_entity_id).state == "11"
    assert hass.states.get(radiation_dose_rate_entity_id).state == "96"
    assert hass.states.get(hydrology_water_level_entity_id).state == "444.0"
    assert hass.states.get(hydrology_water_level_change_entity_id).state == "-1.0"
    assert hass.states.get(hydrology_water_temperature_entity_id).state == "25.0"
    assert hass.states.get(hydrology_situation_entity_id).state == (
        "floodplain_flooding"
    )
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
