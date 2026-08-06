"""Current-condition sensors for UkrHMC."""

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
    DEGREE,
    PERCENTAGE,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)

from .condition import hmc_condition_to_ha
from .const import WEATHER_SUBENTRY_TYPES
from .entity import UkrHMCEntity

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
    from homeassistant.helpers.typing import StateType

    from .api import UkrHMCHourlyForecast, UkrHMCObservation
    from .coordinator import UkrHMCCoordinator
    from .data import UkrHMCConfigEntry


@dataclass(frozen=True, kw_only=True)
class UkrHMCSensorDescription(SensorEntityDescription):
    """Describe a current weather sensor."""

    station_value_fn: Callable[[UkrHMCObservation, bool], StateType | datetime]
    location_value_fn: Callable[[UkrHMCHourlyForecast], StateType | datetime]


SENSORS: tuple[UkrHMCSensorDescription, ...] = (
    UkrHMCSensorDescription(
        key="condition",
        translation_key="condition",
        station_value_fn=lambda observation, is_night: hmc_condition_to_ha(
            observation.condition,
            is_night=is_night,
        ),
        location_value_fn=lambda forecast: hmc_condition_to_ha(
            forecast.condition,
            is_night=forecast.is_night,
        ),
    ),
    UkrHMCSensorDescription(
        key="weather",
        translation_key="weather",
        station_value_fn=lambda observation, _: observation.condition,
        location_value_fn=lambda forecast: forecast.weather,
    ),
    UkrHMCSensorDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        station_value_fn=lambda observation, _: observation.temperature,
        location_value_fn=lambda forecast: forecast.temperature,
    ),
    UkrHMCSensorDescription(
        key="humidity",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        station_value_fn=lambda observation, _: observation.humidity,
        location_value_fn=lambda forecast: forecast.humidity,
    ),
    UkrHMCSensorDescription(
        key="pressure",
        translation_key="pressure",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.MMHG,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        station_value_fn=lambda observation, _: observation.pressure,
        location_value_fn=lambda forecast: forecast.pressure,
    ),
    UkrHMCSensorDescription(
        key="wind_speed",
        translation_key="wind_speed",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        station_value_fn=lambda observation, _: observation.wind_speed,
        location_value_fn=lambda forecast: forecast.wind_speed,
    ),
    UkrHMCSensorDescription(
        key="wind_direction",
        translation_key="wind_direction",
        device_class=SensorDeviceClass.WIND_DIRECTION,
        native_unit_of_measurement=DEGREE,
        state_class=SensorStateClass.MEASUREMENT_ANGLE,
        station_value_fn=lambda observation, _: observation.wind.bearing,
        location_value_fn=lambda forecast: forecast.wind_direction,
    ),
    UkrHMCSensorDescription(
        key="observation_time",
        translation_key="observation_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        station_value_fn=lambda observation, _: observation.observed_at,
        location_value_fn=lambda forecast: forecast.forecast_at,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: UkrHMCConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up current weather sensors for each configured location."""
    coordinator = config_entry.runtime_data.coordinator
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type not in WEATHER_SUBENTRY_TYPES:
            continue
        async_add_entities(
            [
                UkrHMCSensor(coordinator, subentry, description)
                for description in SENSORS
            ],
            config_subentry_id=subentry.subentry_id,
        )


class UkrHMCSensor(UkrHMCEntity, SensorEntity):
    """Represent one current weather value."""

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
        # Location forecasts report pressure in hPa; station observations use mmHg.
        if self._station_id is None and description.key == "pressure":
            self._attr_native_unit_of_measurement = UnitOfPressure.HPA
        self._attr_unique_id = f"{subentry.subentry_id}-{description.key}"

    @property
    @override
    def native_value(self) -> StateType | datetime | None:
        """Return the current provider value."""
        if self.current_forecast is not None:
            return self.entity_description.location_value_fn(self.current_forecast)
        if self.observation is None:
            return None
        return self.entity_description.station_value_fn(
            self.observation,
            self._station_id in self.coordinator.data.night_station_ids,
        )
