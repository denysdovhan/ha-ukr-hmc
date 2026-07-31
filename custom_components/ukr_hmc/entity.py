"""Base entity for UkrHMC station data."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, CONFIGURATION_URL, DOMAIN, MANUFACTURER
from .coordinator import UkrHMCCoordinator
from .helpers import resolve_station_id

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigSubentry

    from .api import UkrHMCObservation, UkrHMCStation


class UkrHMCStationEntityMixin:
    """Resolve the station represented by a config subentry."""

    coordinator: UkrHMCCoordinator
    _subentry: ConfigSubentry
    _station_id: int | None

    @property
    def station(self) -> UkrHMCStation | None:
        """Return the currently resolved station."""
        if self._station_id is None:
            return None
        return self.coordinator.data.stations.get(self._station_id)

    @property
    def observation(self) -> UkrHMCObservation | None:
        """Return the latest observation for the resolved station."""
        if self._station_id is None:
            return None
        return self.coordinator.data.observations.get(self._station_id)

    @property
    def available(self) -> bool:
        """Return whether current station data is available."""
        return self.coordinator.last_update_success and self.observation is not None

    @property
    def device_info(self) -> DeviceInfo:
        """Return service device information for this station selection."""
        station = self.station
        return DeviceInfo(
            configuration_url=CONFIGURATION_URL,
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._subentry.subentry_id)},
            manufacturer=MANUFACTURER,
            model=(f"Meteorological station {station.station_id}" if station else None),
            name=self._subentry.title,
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Resolve dynamic stations again after a catalog update."""
        self._station_id = resolve_station_id(self.coordinator.data, self._subentry)
        super()._handle_coordinator_update()  # type: ignore[misc]


class UkrHMCEntity(
    UkrHMCStationEntityMixin,
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
        self._subentry = subentry
        self._station_id = resolve_station_id(self.coordinator.data, subentry)
