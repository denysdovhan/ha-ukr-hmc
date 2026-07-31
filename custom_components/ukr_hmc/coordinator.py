"""Data update coordinator for Ukrhydrometcenter."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, override

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import UkrHMCClient, UkrHMCData, UkrHMCError
from .const import DOMAIN, UPDATE_INTERVAL

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import UkrHMCConfigEntry

LOGGER = logging.getLogger(__name__)


class UkrHMCCoordinator(DataUpdateCoordinator[UkrHMCData]):
    """Coordinate one shared provider snapshot for all station subentries."""

    config_entry: UkrHMCConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: UkrHMCConfigEntry,
        api: UkrHMCClient,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self._api = api

    @override
    async def _async_update_data(self) -> UkrHMCData:
        """Fetch one complete snapshot."""
        try:
            return await self._api.async_get_data()
        except UkrHMCError as exc:
            raise UpdateFailed(str(exc)) from exc
