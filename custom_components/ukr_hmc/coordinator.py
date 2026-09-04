"""Data update coordinator for UkrHMC."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, override

from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    UkrHMCClient,
    UkrHMCData,
    UkrHMCError,
    UkrHMCLocationForecastRequest,
)
from .const import (
    DOMAIN,
    SUBENTRY_TYPE_HYDROLOGY_POST,
    SUBENTRY_TYPE_RADIATION_STATION,
    SUBENTRY_TYPE_SNOW_STATION,
    SUBENTRY_TYPE_WEATHER_LOCATION,
    SUBENTRY_TYPE_WEATHER_STATION,
    UPDATE_INTERVAL,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import UkrHMCConfigEntry

LOGGER = logging.getLogger(__name__)


class UkrHMCCoordinator(DataUpdateCoordinator[UkrHMCData]):
    """Manage one shared provider snapshot for all weather subentries."""

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
        self.last_successful_update: datetime | None = None
        self.consecutive_update_failures = 0

    @override
    async def _async_update_data(self) -> UkrHMCData:
        """Fetch one complete snapshot."""
        try:
            location_forecasts = {
                subentry.subentry_id: UkrHMCLocationForecastRequest(
                    name=str(subentry.data[CONF_NAME]),
                    latitude=float(subentry.data[CONF_LATITUDE]),
                    longitude=float(subentry.data[CONF_LONGITUDE]),
                )
                for subentry in self.config_entry.subentries.values()
                if subentry.subentry_type == SUBENTRY_TYPE_WEATHER_LOCATION
            }
            include_station_data = any(
                subentry.subentry_type == SUBENTRY_TYPE_WEATHER_STATION
                for subentry in self.config_entry.subentries.values()
            )
            include_radiation_data = any(
                subentry.subentry_type == SUBENTRY_TYPE_RADIATION_STATION
                for subentry in self.config_entry.subentries.values()
            )
            include_hydrology_data = any(
                subentry.subentry_type == SUBENTRY_TYPE_HYDROLOGY_POST
                for subentry in self.config_entry.subentries.values()
            )
            include_snow_data = any(
                subentry.subentry_type == SUBENTRY_TYPE_SNOW_STATION
                for subentry in self.config_entry.subentries.values()
            )
            data = await self._api.async_get_data(
                location_forecasts,
                include_station_data=include_station_data,
                include_radiation_data=include_radiation_data,
                include_hydrology_data=include_hydrology_data,
                include_snow_data=include_snow_data,
            )
        except UkrHMCError as exc:
            self.consecutive_update_failures += 1
            raise UpdateFailed(str(exc)) from exc
        else:
            self.last_successful_update = datetime.now(UTC)
            self.consecutive_update_failures = 0
            return data
