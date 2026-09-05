"""Provider diagnostics and weather warnings from UkrHMC."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, override

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    CONFIGURATION_URL,
    DOMAIN,
    MANUFACTURER,
    NAME,
    STALE_DATA_AFTER,
    SUBENTRY_TYPE_WEATHER_LOCATION,
    SUBENTRY_TYPE_WEATHER_STATION,
)
from .coordinator import UkrHMCCoordinator
from .entity import UkrHMCEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .api import UkrHMCWeatherWarning
    from .data import UkrHMCConfigEntry


ALERT_FLAGS: tuple[BinarySensorEntityDescription, ...] = tuple(
    BinarySensorEntityDescription(
        key=key,
        translation_key=f"global_{category}_attention",
        device_class=BinarySensorDeviceClass.PROBLEM,
    )
    for key, category in (
        ("attns_meteo", "weather"),
        ("attns_hydro", "hydrology"),
        ("attns_snigo", "snow"),
        ("attns_radio", "radiation"),
        ("attns_fire", "fire"),
    )
)

API_AVAILABLE_SENSOR = BinarySensorEntityDescription(
    key="api_available",
    translation_key="api_available",
    device_class=BinarySensorDeviceClass.CONNECTIVITY,
    entity_category=EntityCategory.DIAGNOSTIC,
)
DATA_STALE_SENSOR = BinarySensorEntityDescription(
    key="data_stale",
    translation_key="data_stale",
    device_class=BinarySensorDeviceClass.PROBLEM,
    entity_category=EntityCategory.DIAGNOSTIC,
)
REGIONAL_WEATHER_WARNING_SENSOR = BinarySensorEntityDescription(
    key="regional_weather_warning",
    translation_key="regional_weather_warning",
    device_class=BinarySensorDeviceClass.PROBLEM,
)
WARNING_LEVEL_NAMES = {1: "yellow", 2: "orange", 3: "red"}


class UkrHMCRegionalWeatherWarningBinarySensor(UkrHMCEntity, BinarySensorEntity):
    """Represent meteorological warnings for a station's region."""

    entity_description = REGIONAL_WEATHER_WARNING_SENSOR

    def __init__(
        self,
        coordinator: UkrHMCCoordinator,
        subentry: ConfigSubentry,
    ) -> None:
        """Initialize the regional warning entity."""
        super().__init__(coordinator, subentry)
        self._attr_unique_id = f"{subentry.subentry_id}-{self.entity_description.key}"

    @property
    def _warnings(self) -> tuple[UkrHMCWeatherWarning, ...]:
        region_id = self._region_id
        if region_id is None:
            return ()
        return self.coordinator.data.regional_weather_warnings.get(region_id, ())

    @property
    def _region_id(self) -> int | None:
        station = self.coordinator.data.stations.get(self._station_id)
        if station is not None:
            return station.region_id
        return self.coordinator.data.location_region_ids.get(self._subentry.subentry_id)

    @property
    @override
    def available(self) -> bool:
        """Return whether the station catalog and latest snapshot are available."""
        return self.coordinator.last_update_success and (
            self._station_id is None
            or self.coordinator.data.stations.get(self._station_id) is not None
        )

    @property
    @override
    def is_on(self) -> bool:
        """Return whether a regional warning is currently active."""
        now = datetime.now(UTC)
        return any(warning.is_active(now) for warning in self._warnings)

    @property
    @override
    def extra_state_attributes(self) -> dict[str, object]:
        """Return warning severity, text, codes, and validity intervals."""
        region_id = self._region_id
        station = next(
            (
                station
                for station in self.coordinator.data.stations.values()
                if station.region_id == region_id
            ),
            None,
        )
        warnings = self._warnings
        now = datetime.now(UTC)
        active_warnings = tuple(
            warning for warning in warnings if warning.is_active(now)
        )
        future_warnings = tuple(
            warning for warning in warnings if warning.is_future(now)
        )
        level = max((warning.danger_level for warning in active_warnings), default=0)
        next_start = min(
            (warning.starts_at for warning in future_warnings), default=None
        )
        next_end = min(
            (
                warning.ends_at
                for warning in warnings
                if warning.ends_at is not None and warning.ends_at > now
            ),
            default=None,
        )
        return {
            "region": station.region_name if station else None,
            "region_id": region_id,
            "level": level,
            "level_name": WARNING_LEVEL_NAMES.get(level, "none"),
            "active_count": len(active_warnings),
            "future_count": len(future_warnings),
            "next_start": next_start.isoformat() if next_start else None,
            "next_end": next_end.isoformat() if next_end else None,
            "updated_at": (
                self.coordinator.data.weather_warnings_updated_at.isoformat()
                if self.coordinator.data.weather_warnings_updated_at
                else None
            ),
            "warnings": [
                {
                    "description": warning.description,
                    "phenomenon_code": warning.phenomenon_code,
                    "level": warning.danger_level,
                    "level_name": WARNING_LEVEL_NAMES.get(
                        warning.danger_level, "unknown"
                    ),
                    "period": warning.period,
                    "starts_at": (
                        warning.starts_at.isoformat() if warning.starts_at else None
                    ),
                    "ends_at": warning.ends_at.isoformat() if warning.ends_at else None,
                    "status": (
                        "active"
                        if warning.is_active(now)
                        else "future"
                        if warning.is_future(now)
                        else "expired"
                    ),
                }
                for warning in warnings
            ],
        }


class UkrHMCAlertBinarySensor(
    CoordinatorEntity[UkrHMCCoordinator],
    BinarySensorEntity,
):
    """Represent one global provider attention flag."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: UkrHMCCoordinator,
        entry_id: str,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize a provider attention flag."""
        super().__init__(coordinator, context=f"alert:{description.key}")
        self.entity_description = description
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}-{description.key}"

    @property
    @override
    def is_on(self) -> bool:
        """Return the direct global provider flag."""
        return self.coordinator.data.alert_flags.get(self.entity_description.key, False)

    @property
    @override
    def available(self) -> bool:
        """Return whether the provider-global flag feed is available."""
        source_available = self.coordinator.source_availability.get(
            "attention_flags", True
        )
        return (
            self.coordinator.last_update_success
            and source_available
            and self.entity_description.key in self.coordinator.data.alert_flags
        )

    @property
    def extra_state_attributes(self) -> dict[str, str | bool]:
        """Describe the deliberately limited provider-global semantics."""
        return {
            "scope": "provider_global",
            "provider_key": self.entity_description.key,
            "has_regional_details": False,
        }

    @property
    @override
    def device_info(self) -> DeviceInfo:
        """Return the shared UkrHMC service device."""
        return DeviceInfo(
            configuration_url=CONFIGURATION_URL,
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._entry_id)},
            manufacturer=MANUFACTURER,
            model="UkrHMC Service",
            name=NAME,
        )


class UkrHMCApiAvailableBinarySensor(
    CoordinatorEntity[UkrHMCCoordinator],
    BinarySensorEntity,
):
    """Report whether the latest provider update succeeded."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(self, coordinator: UkrHMCCoordinator, entry_id: str) -> None:
        """Initialize the API availability sensor."""
        super().__init__(coordinator, context="diagnostic:api_available")
        self.entity_description = API_AVAILABLE_SENSOR
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}-api_available"

    @property
    @override
    def available(self) -> bool:
        """Keep the diagnostic entity available during provider failures."""
        return True

    @property
    @override
    def is_on(self) -> bool:
        """Return whether the latest coordinator update succeeded."""
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, bool]:
        """Expose product-level availability without endpoint implementation details."""
        return dict(sorted(self.coordinator.source_availability.items()))

    @property
    @override
    def device_info(self) -> DeviceInfo:
        """Return the shared UkrHMC service device."""
        return DeviceInfo(
            configuration_url=CONFIGURATION_URL,
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._entry_id)},
            manufacturer=MANUFACTURER,
            model="UkrHMC Service",
            name=NAME,
        )


class UkrHMCDataStaleBinarySensor(
    CoordinatorEntity[UkrHMCCoordinator],
    BinarySensorEntity,
):
    """Report whether the provider snapshot is older than the safe threshold."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(self, coordinator: UkrHMCCoordinator, entry_id: str) -> None:
        """Initialize the stale-data sensor."""
        super().__init__(coordinator, context="diagnostic:data_stale")
        self.entity_description = DATA_STALE_SENSOR
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}-data_stale"

    @property
    @override
    def available(self) -> bool:
        """Keep the stale-data status readable during provider failures."""
        return True

    @property
    @override
    def is_on(self) -> bool:
        """Return whether the last successful snapshot is older than 45 minutes."""
        if self.coordinator.last_successful_update is None:
            return True
        return datetime.now(UTC) - self.coordinator.last_successful_update > (
            STALE_DATA_AFTER
        )

    @property
    @override
    def device_info(self) -> DeviceInfo:
        """Return the shared UkrHMC service device."""
        return DeviceInfo(
            configuration_url=CONFIGURATION_URL,
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._entry_id)},
            manufacturer=MANUFACTURER,
            model="UkrHMC Service",
            name=NAME,
        )


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: UkrHMCConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up provider connectivity and global attention flags."""
    coordinator = config_entry.runtime_data.coordinator
    async_add_entities(
        [
            UkrHMCApiAvailableBinarySensor(coordinator, config_entry.entry_id),
            UkrHMCDataStaleBinarySensor(coordinator, config_entry.entry_id),
            *(
                UkrHMCAlertBinarySensor(coordinator, config_entry.entry_id, description)
                for description in ALERT_FLAGS
            ),
        ]
    )
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type not in (
            SUBENTRY_TYPE_WEATHER_STATION,
            SUBENTRY_TYPE_WEATHER_LOCATION,
        ):
            continue
        async_add_entities(
            [UkrHMCRegionalWeatherWarningBinarySensor(coordinator, subentry)],
            config_subentry_id=subentry.subentry_id,
        )
