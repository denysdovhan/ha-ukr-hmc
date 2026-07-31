"""Current-condition sensors for Ukrhydrometcenter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)

from .entity import UkrHMCEntity

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
    from homeassistant.helpers.typing import StateType

    from .api import UkrHMCObservation
    from .coordinator import UkrHMCCoordinator
    from .data import UkrHMCConfigEntry


@dataclass(frozen=True, kw_only=True)
class UkrHMCSensorDescription(SensorEntityDescription):
    """Describe a current observation sensor."""

    value_fn: Callable[[UkrHMCObservation], StateType | datetime]


SENSORS: tuple[UkrHMCSensorDescription, ...] = (
    UkrHMCSensorDescription(
        key="condition",
        translation_key="condition",
        value_fn=lambda observation: observation.condition,
    ),
    UkrHMCSensorDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda observation: observation.temperature,
    ),
    UkrHMCSensorDescription(
        key="humidity",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda observation: observation.humidity,
    ),
    UkrHMCSensorDescription(
        key="pressure",
        translation_key="pressure",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.MMHG,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda observation: observation.pressure,
    ),
    UkrHMCSensorDescription(
        key="wind_speed",
        translation_key="wind_speed",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda observation: observation.wind_speed,
    ),
    UkrHMCSensorDescription(
        key="wind_direction",
        translation_key="wind_direction",
        value_fn=lambda observation: (
            observation.wind.name or observation.wind.abbreviation
        ),
    ),
    UkrHMCSensorDescription(
        key="observation_time",
        translation_key="observation_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda observation: observation.observed_at,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: UkrHMCConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors for each station subentry."""
    coordinator = config_entry.runtime_data.coordinator
    for subentry in config_entry.subentries.values():
        async_add_entities(
            [
                UkrHMCSensor(coordinator, subentry, description)
                for description in SENSORS
            ],
            config_subentry_id=subentry.subentry_id,
        )


class UkrHMCSensor(UkrHMCEntity, SensorEntity):
    """Represent one current observation value."""

    entity_description: UkrHMCSensorDescription

    def __init__(
        self,
        coordinator: UkrHMCCoordinator,
        subentry: ConfigSubentry,
        description: UkrHMCSensorDescription,
    ) -> None:
        """Initialize a sensor."""
        super().__init__(coordinator, subentry)
        self.entity_description = description
        self._attr_unique_id = f"{subentry.subentry_id}-{description.key}"

    @property
    @override
    def native_value(self) -> StateType | datetime | None:
        """Return the current provider value."""
        if self.observation is None:
            return None
        return self.entity_description.value_fn(self.observation)
