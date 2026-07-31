"""Tests for the shared data coordinator."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ukr_hmc.api import UkrHMCConnectionError
from custom_components.ukr_hmc.const import DOMAIN
from custom_components.ukr_hmc.coordinator import UkrHMCCoordinator

from .fixtures import DATA

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def test_coordinator_returns_provider_snapshot(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={})
    api = AsyncMock()
    api.async_get_data.return_value = DATA
    coordinator = UkrHMCCoordinator(hass, entry, api)

    assert await coordinator._async_update_data() is DATA


async def test_coordinator_wraps_api_error(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={})
    api = AsyncMock()
    api.async_get_data.side_effect = UkrHMCConnectionError("offline")
    coordinator = UkrHMCCoordinator(hass, entry, api)

    with pytest.raises(UpdateFailed, match="offline"):
        await coordinator._async_update_data()
