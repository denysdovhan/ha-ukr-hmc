"""Warning transition event entities for UkrHMC."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, override

from homeassistant.components.event import EventEntity
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    CONF_STATION_ID,
    DOMAIN,
    HYDROLOGY_CONFIGURATION_URL,
    MANUFACTURER,
    SUBENTRY_TYPE_HYDROLOGY_POST,
    SUBENTRY_TYPE_WEATHER_LOCATION,
    SUBENTRY_TYPE_WEATHER_STATION,
)
from .coordinator import UkrHMCCoordinator
from .entity import UkrHMCEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .api import UkrHMCHydrologyWarning, UkrHMCWeatherWarning
    from .data import UkrHMCConfigEntry

EVENT_TYPES = ["started", "level_increased", "ended"]
WEATHER_WARNING_KINDS = ("meteorological", "fire", "avalanche")


def _highest_active(
    warnings: tuple[UkrHMCWeatherWarning | UkrHMCHydrologyWarning, ...],
) -> UkrHMCWeatherWarning | UkrHMCHydrologyWarning | None:
    """Return the highest currently active warning."""
    now = datetime.now(UTC)
    return max(
        (warning for warning in warnings if warning.is_active(now)),
        key=lambda warning: warning.danger_level,
        default=None,
    )


def _warning_attributes(
    warning: UkrHMCWeatherWarning | UkrHMCHydrologyWarning | None,
    *,
    warning_type: str,
    territory: str,
    previous_level: int,
    level: int,
) -> dict[str, Any]:
    """Return automation-friendly event attributes."""
    return {
        "warning_type": warning_type,
        "previous_level": previous_level,
        "level": level,
        "territory": territory,
        "region_id": warning.region_id if warning else None,
        "text": warning.description if warning else None,
        "period": warning.period if warning else None,
        "starts_at": warning.starts_at.isoformat()
        if warning and warning.starts_at
        else None,
        "ends_at": warning.ends_at.isoformat() if warning and warning.ends_at else None,
    }


class UkrHMCWarningEvent(UkrHMCEntity, EventEntity):
    """Emit transitions for one weather-source warning kind."""

    _attr_event_types = EVENT_TYPES

    def __init__(
        self,
        coordinator: UkrHMCCoordinator,
        subentry: ConfigSubentry,
        warning_type: str,
    ) -> None:
        """Initialize the warning event entity with the current level baseline."""
        super().__init__(coordinator, subentry)
        self._warning_type = warning_type
        self._attr_translation_key = f"{warning_type}_warning_event"
        self._attr_unique_id = f"{subentry.subentry_id}-{warning_type}-warning-event"
        self._previous_warning = _highest_active(self._warnings())
        self._previous_level = (
            self._previous_warning.danger_level if self._previous_warning else 0
        )

    def _region_id(self) -> int | None:
        """Return the warning region matched to this weather source."""
        station = self.coordinator.data.stations.get(self._station_id)
        if self._warning_type == "meteorological":
            return (
                station.region_id
                if station
                else self.coordinator.data.location_region_ids.get(
                    self._subentry.subentry_id
                )
            )
        if self._warning_type == "fire":
            return (
                station.region_id
                if station
                else self.coordinator.data.location_fire_region_ids.get(
                    self._subentry.subentry_id
                )
            )
        return (
            self.coordinator.data.station_snow_region_ids.get(self._station_id)
            if station
            else self.coordinator.data.location_snow_region_ids.get(
                self._subentry.subentry_id
            )
        )

    def _warnings(self) -> tuple[UkrHMCWeatherWarning, ...]:
        """Return current warnings for this entity's kind and region."""
        region_id = self._region_id()
        source = {
            "meteorological": self.coordinator.data.regional_weather_warnings,
            "fire": self.coordinator.data.regional_fire_warnings,
            "avalanche": self.coordinator.data.regional_snow_warnings,
        }[self._warning_type]
        return source.get(region_id, ())

    def _current_level(self) -> int:
        """Return the highest active warning level."""
        warning = _highest_active(self._warnings())
        return warning.danger_level if warning else 0

    @override
    def _handle_coordinator_update(self) -> None:
        """Emit an event when the active warning level changes."""
        warning = _highest_active(self._warnings())
        level = warning.danger_level if warning else 0
        event_type = None
        if self._previous_level == 0 and level > 0:
            event_type = "started"
        elif level > self._previous_level:
            event_type = "level_increased"
        elif self._previous_level > 0 and level == 0:
            event_type = "ended"
        if event_type:
            station = self.coordinator.data.stations.get(self._station_id)
            territory = station.region_name if station else self._subentry.title
            event_warning = self._previous_warning if event_type == "ended" else warning
            self._trigger_event(
                event_type,
                _warning_attributes(
                    event_warning,
                    warning_type=self._warning_type,
                    territory=territory,
                    previous_level=self._previous_level,
                    level=level,
                ),
            )
        self._previous_level = level
        self._previous_warning = warning
        super()._handle_coordinator_update()


class UkrHMCHydrologyWarningEvent(CoordinatorEntity[UkrHMCCoordinator], EventEntity):
    """Emit warning transitions for one hydrology post."""

    _attr_attribution = ATTRIBUTION
    _attr_event_types = EVENT_TYPES
    _attr_has_entity_name = True
    _attr_translation_key = "hydrology_warning_event"

    def __init__(
        self, coordinator: UkrHMCCoordinator, subentry: ConfigSubentry
    ) -> None:
        """Initialize with the current warning level baseline."""
        super().__init__(coordinator, context=subentry.subentry_id)
        self._subentry = subentry
        self._post_id = int(subentry.data[CONF_STATION_ID])
        self._attr_unique_id = f"{subentry.subentry_id}-hydrology-warning-event"
        self._previous_warning = _highest_active(self._warnings())
        self._previous_level = (
            self._previous_warning.danger_level if self._previous_warning else 0
        )

    def _warnings(self) -> tuple[UkrHMCHydrologyWarning, ...]:
        region_id = self.coordinator.data.hydrology_post_warning_region_ids.get(
            self._post_id
        )
        return self.coordinator.data.regional_hydrology_warnings.get(region_id, ())

    def _current_level(self) -> int:
        warning = _highest_active(self._warnings())
        return warning.danger_level if warning else 0

    @property
    @override
    def device_info(self) -> DeviceInfo:
        """Return the hydrology post device metadata."""
        return DeviceInfo(
            configuration_url=HYDROLOGY_CONFIGURATION_URL,
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._subentry.subentry_id)},
            manufacturer=MANUFACTURER,
            model=f"UkrHMC Hydrology Post {self._post_id}",
            name=self._subentry.title,
        )

    @override
    def _handle_coordinator_update(self) -> None:
        """Emit an event when the active hydrological level changes."""
        warning = _highest_active(self._warnings())
        level = warning.danger_level if warning else 0
        event_type = None
        if self._previous_level == 0 and level > 0:
            event_type = "started"
        elif level > self._previous_level:
            event_type = "level_increased"
        elif self._previous_level > 0 and level == 0:
            event_type = "ended"
        if event_type:
            post = self.coordinator.data.hydrology_posts.get(self._post_id)
            territory = warning.basin_name if warning else (post.name if post else "")
            event_warning = self._previous_warning if event_type == "ended" else warning
            self._trigger_event(
                event_type,
                _warning_attributes(
                    event_warning,
                    warning_type="hydrology",
                    territory=territory,
                    previous_level=self._previous_level,
                    level=level,
                ),
            )
        self._previous_level = level
        self._previous_warning = warning
        super()._handle_coordinator_update()


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: UkrHMCConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up warning transition event entities."""
    coordinator = config_entry.runtime_data.coordinator
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type == SUBENTRY_TYPE_HYDROLOGY_POST:
            async_add_entities(
                [UkrHMCHydrologyWarningEvent(coordinator, subentry)],
                config_subentry_id=subentry.subentry_id,
            )
        elif subentry.subentry_type in (
            SUBENTRY_TYPE_WEATHER_STATION,
            SUBENTRY_TYPE_WEATHER_LOCATION,
        ):
            async_add_entities(
                [
                    UkrHMCWarningEvent(coordinator, subentry, warning_type)
                    for warning_type in WEATHER_WARNING_KINDS
                ],
                config_subentry_id=subentry.subentry_id,
            )
