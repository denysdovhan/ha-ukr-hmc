"""Base entity for UkrHMC weather data."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    CONF_STATION_ID,
    CONFIGURATION_URL,
    DOMAIN,
    MANUFACTURER,
    SUBENTRY_TYPE_WEATHER_STATION,
)
from .coordinator import UkrHMCCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigSubentry

    from .api import UkrHMCHourlyForecast, UkrHMCObservation


class UkrHMCWeatherEntityMixin:
    """Expose data for a configured weather source."""

    coordinator: UkrHMCCoordinator
    _subentry: ConfigSubentry
    _station_id: int | None

    def _initialize_weather_source(self, subentry: ConfigSubentry) -> None:
        """Initialize the configured weather source."""
        self._subentry = subentry
        self._station_id = (
            int(subentry.data[CONF_STATION_ID])
            if subentry.subentry_type == SUBENTRY_TYPE_WEATHER_STATION
            else None
        )

    @property
    def observation(self) -> UkrHMCObservation | None:
        """Return the latest observation for the selected station."""
        if self._station_id is None:
            return None
        return self.coordinator.data.observations.get(self._station_id)

    @property
    def current_forecast(self) -> UkrHMCHourlyForecast | None:
        """Return the location forecast for the current provider hour."""
        if self._station_id is not None:
            return None
        forecast = self.coordinator.data.location_forecasts.get(
            self._subentry.subentry_id
        )
        return forecast.current if forecast else None

    @property
    def available(self) -> bool:
        """Return whether current weather data is available."""
        current_data = (
            self.observation if self._station_id is not None else self.current_forecast
        )
        return self.coordinator.last_update_success and current_data is not None

    @property
    def device_info(self) -> DeviceInfo:
        """Return service device information for this weather location."""
        if self._station_id is None:
            model = "UkrHMC Location Forecast"
        else:
            model = f"UkrHMC Station {self._station_id}"
        return DeviceInfo(
            configuration_url=CONFIGURATION_URL,
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._subentry.subentry_id)},
            manufacturer=MANUFACTURER,
            model=model,
            name=self._subentry.title,
        )


class UkrHMCEntity(
    UkrHMCWeatherEntityMixin,
    CoordinatorEntity[UkrHMCCoordinator],
):
    """Base class for coordinator-backed UkrHMC entities."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: UkrHMCCoordinator,
        subentry: ConfigSubentry,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, context=subentry.subentry_id)
        self._initialize_weather_source(subentry)
