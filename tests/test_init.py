"""Tests for Ukrhydrometcenter setup and unload."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ukr_hmc.const import DOMAIN
from custom_components.ukr_hmc.data import UkrHMCRuntimeData

from .fixtures import DATA, STATIC_SUBENTRY_DATA

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


async def test_setup_creates_weather_and_current_sensors(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Ukrhydrometcenter",
        unique_id=DOMAIN,
        data={},
        subentries_data=[STATIC_SUBENTRY_DATA],
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
    weather_entity_id = registry.async_get_entity_id(
        "weather",
        DOMAIN,
        "station-subentry",
    )
    temperature_entity_id = registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        "station-subentry-temperature",
    )
    condition_entity_id = registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        "station-subentry-condition",
    )

    assert weather_entity_id is not None
    assert temperature_entity_id is not None
    assert condition_entity_id is not None
    assert hass.states.get(weather_entity_id).state == "partlycloudy"
    assert hass.states.get(temperature_entity_id).state == "25.9"
    assert hass.states.get(condition_entity_id).state == "Хмарно з проясненнями"

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
