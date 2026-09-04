"""Provider-global attention flags from UkrHMC."""

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
)
from .coordinator import UkrHMCCoordinator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

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
        return self.coordinator.data.alert_flags[self.entity_description.key]

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
