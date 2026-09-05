"""Tests for the shared data coordinator."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ukr_hmc.api import UkrHMCConnectionError
from custom_components.ukr_hmc.const import (
    CONF_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    UPDATE_INTERVAL,
)
from custom_components.ukr_hmc.coordinator import UkrHMCCoordinator

from .fixtures import (
    DATA,
    HYDROLOGY_SUBENTRY_DATA,
    LOCATION_FORECAST_REQUEST,
    LOCATION_SUBENTRY_DATA,
    RADIATION_SUBENTRY_DATA,
    SNOW_SUBENTRY_DATA,
    STATION_SUBENTRY_DATA,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def test_coordinator_returns_provider_snapshot(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        subentries_data=[
            STATION_SUBENTRY_DATA,
            LOCATION_SUBENTRY_DATA,
            RADIATION_SUBENTRY_DATA,
            HYDROLOGY_SUBENTRY_DATA,
            SNOW_SUBENTRY_DATA,
        ],
    )
    api = AsyncMock()
    api.async_get_data.return_value = DATA
    coordinator = UkrHMCCoordinator(hass, entry, api)

    assert await coordinator._async_update_data() is DATA
    assert coordinator.last_successful_update is not None
    assert coordinator.last_successful_update.tzinfo is not None
    assert coordinator.update_interval == UPDATE_INTERVAL
    assert not coordinator.always_update
    api.async_get_data.assert_awaited_once_with(
        {"location-subentry": LOCATION_FORECAST_REQUEST},
        include_station_data=True,
        include_radiation_data=True,
        include_hydrology_data=True,
        include_snow_data=True,
    )


async def test_location_only_coordinator_skips_station_data(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        subentries_data=[LOCATION_SUBENTRY_DATA],
    )
    api = AsyncMock()
    api.async_get_data.return_value = DATA
    coordinator = UkrHMCCoordinator(hass, entry, api)

    assert await coordinator._async_update_data() is DATA
    api.async_get_data.assert_awaited_once_with(
        {"location-subentry": LOCATION_FORECAST_REQUEST},
        include_station_data=False,
        include_radiation_data=False,
        include_hydrology_data=False,
        include_snow_data=False,
    )


async def test_station_only_coordinator_includes_station_data(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        subentries_data=[STATION_SUBENTRY_DATA],
    )
    api = AsyncMock()
    api.async_get_data.return_value = DATA
    coordinator = UkrHMCCoordinator(hass, entry, api)

    assert await coordinator._async_update_data() is DATA
    api.async_get_data.assert_awaited_once_with(
        {},
        include_station_data=True,
        include_radiation_data=False,
        include_hydrology_data=False,
        include_snow_data=False,
    )


async def test_radiation_only_coordinator_skips_weather_data(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        subentries_data=[RADIATION_SUBENTRY_DATA],
    )
    api = AsyncMock()
    api.async_get_data.return_value = DATA
    coordinator = UkrHMCCoordinator(hass, entry, api)

    assert await coordinator._async_update_data() is DATA
    api.async_get_data.assert_awaited_once_with(
        {},
        include_station_data=False,
        include_radiation_data=True,
        include_hydrology_data=False,
        include_snow_data=False,
    )


async def test_hydrology_only_coordinator_skips_other_data(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        subentries_data=[HYDROLOGY_SUBENTRY_DATA],
    )
    api = AsyncMock()
    api.async_get_data.return_value = DATA
    coordinator = UkrHMCCoordinator(hass, entry, api)

    assert await coordinator._async_update_data() is DATA
    api.async_get_data.assert_awaited_once_with(
        {},
        include_station_data=False,
        include_radiation_data=False,
        include_hydrology_data=True,
        include_snow_data=False,
    )


async def test_coordinator_wraps_api_error(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={})
    api = AsyncMock()
    api.async_get_data.side_effect = UkrHMCConnectionError("offline")
    coordinator = UkrHMCCoordinator(hass, entry, api)

    with pytest.raises(UpdateFailed, match="offline"):
        await coordinator._async_update_data()
    assert coordinator.consecutive_update_failures == 1


async def test_coordinator_suppresses_equal_snapshots_but_dispatches_warning_change(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={})
    api = AsyncMock()
    api.async_get_data.side_effect = (
        DATA,
        DATA,
        replace(
            DATA,
            active_warning_keys=frozenset({("meteorological", 1, 0)}),
        ),
    )
    coordinator = UkrHMCCoordinator(hass, entry, api)
    listener = Mock()
    remove_listener = coordinator.async_add_listener(listener)

    await coordinator.async_refresh()
    await coordinator.async_refresh()
    assert listener.call_count == 1

    await coordinator.async_refresh()
    assert listener.call_count == 2
    remove_listener()


async def test_coordinator_uses_configured_polling_interval(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={CONF_UPDATE_INTERVAL_MINUTES: 30},
    )

    coordinator = UkrHMCCoordinator(hass, entry, AsyncMock())

    assert coordinator.update_interval == timedelta(minutes=30)
