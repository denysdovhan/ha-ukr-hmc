"""Set up the UkrHMC integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import UkrHMCClient
from .coordinator import UkrHMCCoordinator
from .data import UkrHMCConfigEntry, UkrHMCRuntimeData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

PLATFORMS = (Platform.BINARY_SENSOR, Platform.SENSOR, Platform.WEATHER)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: UkrHMCConfigEntry,
) -> bool:
    """Set up UkrHMC from a config entry."""
    api = UkrHMCClient(async_get_clientsession(hass))
    coordinator = UkrHMCCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = UkrHMCRuntimeData(api=api, coordinator=coordinator)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: UkrHMCConfigEntry,
) -> bool:
    """Unload a UkrHMC config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(
    hass: HomeAssistant,
    entry: UkrHMCConfigEntry,
) -> None:
    """Reload when weather subentries change."""
    await hass.config_entries.async_reload(entry.entry_id)
