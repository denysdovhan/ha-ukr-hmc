"""Provider-global attention flags from UkrHMC."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, CONFIGURATION_URL, DOMAIN, MANUFACTURER, NAME
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
            model="UkrHMC Global Alerts",
            name=NAME,
        )


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: UkrHMCConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up global provider attention flags."""
    coordinator = config_entry.runtime_data.coordinator
    async_add_entities(
        UkrHMCAlertBinarySensor(coordinator, config_entry.entry_id, description)
        for description in ALERT_FLAGS
    )
