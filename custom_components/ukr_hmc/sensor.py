"""Current-condition sensors for UkrHMC."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import exp
from typing import TYPE_CHECKING, Any, override
from zoneinfo import ZoneInfo

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    EntityCategory,
    UnitOfLength,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .condition import hmc_condition_to_ha
from .const import (
    ATTRIBUTION,
    CONF_STATION_ID,
    CONFIGURATION_URL,
    DOMAIN,
    HYDROLOGY_CONFIGURATION_URL,
    MANUFACTURER,
    NAME,
    RADIATION_CONFIGURATION_URL,
    SNOW_CONFIGURATION_URL,
    SUBENTRY_TYPE_HYDROLOGY_POST,
    SUBENTRY_TYPE_RADIATION_STATION,
    SUBENTRY_TYPE_SNOW_STATION,
    SUBENTRY_TYPE_WEATHER_LOCATION,
    SUBENTRY_TYPE_WEATHER_STATION,
)
from .coordinator import UkrHMCCoordinator
from .entity import UkrHMCEntity

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import date, time

    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
    from homeassistant.helpers.typing import StateType

    from .api import (
        UkrHMCForecastDay,
        UkrHMCHourlyForecast,
        UkrHMCHydrologyObservation,
        UkrHMCHydrologyWarning,
        UkrHMCLocationForecast,
        UkrHMCObservation,
        UkrHMCRadiationObservation,
        UkrHMCSnowObservation,
    )
    from .data import UkrHMCConfigEntry


@dataclass(frozen=True, kw_only=True)
class UkrHMCSensorDescription(SensorEntityDescription):
    """Describe a current weather sensor."""

    station_value_fn: Callable[[UkrHMCObservation, bool], StateType | datetime | None]
    location_value_fn: Callable[[UkrHMCHourlyForecast], StateType | datetime | None]


@dataclass(frozen=True, kw_only=True)
class UkrHMCRadiationSensorDescription(SensorEntityDescription):
    """Describe a current radiation sensor."""

    value_fn: Callable[[UkrHMCRadiationObservation], StateType | datetime]


@dataclass(frozen=True, kw_only=True)
class UkrHMCHydrologySensorDescription(SensorEntityDescription):
    """Describe a current hydrology sensor."""

    value_fn: Callable[[UkrHMCHydrologyObservation], StateType | datetime]


@dataclass(frozen=True, kw_only=True)
class UkrHMCSnowSensorDescription(SensorEntityDescription):
    """Describe a snow-station sensor."""

    value_fn: Callable[[UkrHMCSnowObservation], StateType | date]


WARNING_LEVEL_OPTIONS = ("none", "yellow", "orange", "red")
MAX_RELATIVE_HUMIDITY = 100
WARNING_LEVEL_NAMES = {1: "yellow", 2: "orange", 3: "red"}
REGIONAL_WEATHER_WARNING_LEVEL_SENSOR = SensorEntityDescription(
    key="regional_weather_warning_level",
    translation_key="regional_weather_warning_level",
    device_class=SensorDeviceClass.ENUM,
    options=list(WARNING_LEVEL_OPTIONS),
)
FIRE_DANGER_OPTIONS = ("none", "extreme", "prolonged_extreme")
FIRE_DANGER_NAMES = {3: "extreme", 4: "prolonged_extreme"}
SNOW_DANGER_OPTIONS = (
    "none",
    "low",
    "moderate",
    "considerable",
    "high",
    "very_high",
)
SNOW_DANGER_NAMES = {
    1: "low",
    2: "moderate",
    3: "considerable",
    4: "high",
    5: "very_high",
}


class UkrHMCRegionalHazardLevelSensor(UkrHMCEntity, SensorEntity):
    """Expose the current fire or avalanche danger level."""

    def __init__(
        self,
        coordinator: UkrHMCCoordinator,
        subentry: ConfigSubentry,
        *,
        hazard: str,
    ) -> None:
        """Initialize a regional hazard sensor."""
        super().__init__(coordinator, subentry)
        self._hazard = hazard
        options = FIRE_DANGER_OPTIONS if hazard == "fire" else SNOW_DANGER_OPTIONS
        self.entity_description = SensorEntityDescription(
            key=f"regional_{hazard}_danger_level",
            translation_key=f"regional_{hazard}_danger_level",
            device_class=SensorDeviceClass.ENUM,
            options=list(options),
        )
        self._attr_unique_id = f"{subentry.subentry_id}-{self.entity_description.key}"

    @property
    @override
    def available(self) -> bool:
        """Return whether the source and latest snapshot are available."""
        return self.coordinator.last_update_success and (
            self._station_id is None
            or self.coordinator.data.stations.get(self._station_id) is not None
        )

    def _region_id(self) -> int | None:
        """Return the provider region containing this weather source."""
        if self._hazard == "fire":
            station = self.coordinator.data.stations.get(self._station_id)
            return (
                station.region_id
                if station is not None
                else self.coordinator.data.location_fire_region_ids.get(
                    self._subentry.subentry_id
                )
            )
        if self._station_id is not None:
            return self.coordinator.data.station_snow_region_ids.get(self._station_id)
        return self.coordinator.data.location_snow_region_ids.get(
            self._subentry.subentry_id
        )

    @property
    @override
    def native_value(self) -> str:
        """Return the highest currently active provider level."""
        warnings = (
            self.coordinator.data.regional_fire_warnings
            if self._hazard == "fire"
            else self.coordinator.data.regional_snow_warnings
        ).get(self._region_id(), ())
        level = max(
            (
                warning.danger_level
                for warning in warnings
                if warning.is_active(datetime.now(UTC))
            ),
            default=0,
        )
        names = FIRE_DANGER_NAMES if self._hazard == "fire" else SNOW_DANGER_NAMES
        return names.get(level, "none")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return direct provider validity details for automations."""
        region_id = self._region_id()
        warnings = (
            self.coordinator.data.regional_fire_warnings
            if self._hazard == "fire"
            else self.coordinator.data.regional_snow_warnings
        ).get(region_id, ())
        updated_at = (
            self.coordinator.data.fire_warnings_updated_at
            if self._hazard == "fire"
            else self.coordinator.data.snow_warnings_updated_at
        )
        return {
            "region_id": region_id,
            "updated_at": updated_at.isoformat() if updated_at else None,
            "warnings": [
                {
                    "level": warning.danger_level,
                    "description": warning.description,
                    "period": warning.period,
                    "starts_at": warning.starts_at.isoformat()
                    if warning.starts_at
                    else None,
                    "ends_at": warning.ends_at.isoformat() if warning.ends_at else None,
                }
                for warning in warnings
            ],
        }


class UkrHMCRegionalWeatherWarningLevelSensor(UkrHMCEntity, SensorEntity):
    """Expose the highest active regional weather-warning level."""

    entity_description = REGIONAL_WEATHER_WARNING_LEVEL_SENSOR

    def __init__(
        self,
        coordinator: UkrHMCCoordinator,
        subentry: ConfigSubentry,
    ) -> None:
        """Initialize the warning-level sensor."""
        super().__init__(coordinator, subentry)
        self._attr_unique_id = f"{subentry.subentry_id}-{self.entity_description.key}"

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
    def native_value(self) -> str:
        """Return the highest currently active warning level."""
        station = self.coordinator.data.stations.get(self._station_id)
        region_id = (
            station.region_id
            if station is not None
            else self.coordinator.data.location_region_ids.get(
                self._subentry.subentry_id
            )
        )
        if region_id is None:
            return "none"
        now = datetime.now(UTC)
        level = max(
            (
                warning.danger_level
                for warning in self.coordinator.data.regional_weather_warnings.get(
                    region_id, ()
                )
                if warning.is_active(now)
            ),
            default=0,
        )
        return WARNING_LEVEL_NAMES.get(level, "none")


@dataclass(frozen=True, kw_only=True)
class UkrHMCLocationSummarySensorDescription(SensorEntityDescription):
    """Describe a value derived directly from a location forecast series."""

    value_fn: Callable[[UkrHMCLocationForecast, datetime], StateType | datetime | None]


CONDITION_SENSOR = UkrHMCSensorDescription(
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
)
WEATHER_SENSOR = UkrHMCSensorDescription(
    key="weather",
    translation_key="weather",
    station_value_fn=lambda observation, _: observation.condition,
    location_value_fn=lambda forecast: forecast.weather,
)
TEMPERATURE_SENSOR = UkrHMCSensorDescription(
    key="temperature",
    translation_key="temperature",
    device_class=SensorDeviceClass.TEMPERATURE,
    native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    state_class=SensorStateClass.MEASUREMENT,
    suggested_display_precision=1,
    station_value_fn=lambda observation, _: observation.temperature,
    location_value_fn=lambda forecast: forecast.temperature,
)
HUMIDITY_SENSOR = UkrHMCSensorDescription(
    key="humidity",
    translation_key="humidity",
    device_class=SensorDeviceClass.HUMIDITY,
    native_unit_of_measurement=PERCENTAGE,
    state_class=SensorStateClass.MEASUREMENT,
    suggested_display_precision=0,
    station_value_fn=lambda observation, _: observation.humidity,
    location_value_fn=lambda forecast: forecast.humidity,
)
PRESSURE_SENSOR = UkrHMCSensorDescription(
    key="pressure",
    translation_key="pressure",
    device_class=SensorDeviceClass.PRESSURE,
    native_unit_of_measurement=UnitOfPressure.MMHG,
    state_class=SensorStateClass.MEASUREMENT,
    suggested_display_precision=0,
    station_value_fn=lambda observation, _: observation.pressure,
    location_value_fn=lambda forecast: forecast.pressure,
)
WIND_SPEED_SENSOR = UkrHMCSensorDescription(
    key="wind_speed",
    translation_key="wind_speed",
    device_class=SensorDeviceClass.WIND_SPEED,
    native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
    state_class=SensorStateClass.MEASUREMENT,
    station_value_fn=lambda observation, _: observation.wind_speed,
    location_value_fn=lambda forecast: forecast.wind_speed,
)
WIND_COMPASS_SENSOR = UkrHMCSensorDescription(
    key="wind_compass",
    translation_key="wind_compass",
    station_value_fn=lambda observation, _: observation.wind.abbreviation,
    location_value_fn=lambda forecast: forecast.wind_compass,
)
WIND_DIRECTION_SENSOR = UkrHMCSensorDescription(
    key="wind_direction",
    translation_key="wind_direction",
    device_class=SensorDeviceClass.WIND_DIRECTION,
    native_unit_of_measurement=DEGREE,
    state_class=SensorStateClass.MEASUREMENT_ANGLE,
    station_value_fn=lambda observation, _: observation.wind.bearing,
    location_value_fn=lambda forecast: forecast.wind_bearing,
)
DATA_TIME_SENSOR = UkrHMCSensorDescription(
    key="observation_time",
    translation_key="observation_time",
    device_class=SensorDeviceClass.TIMESTAMP,
    station_value_fn=lambda observation, _: observation.observed_at,
    location_value_fn=lambda forecast: forecast.forecast_at,
)


def apparent_temperature(
    temperature: float,
    humidity: float | None,
    wind_speed: float | None,
) -> float | None:
    """Return Steadman apparent temperature in shade, without solar radiation."""
    if (
        humidity is None
        or wind_speed is None
        or not 0 <= humidity <= MAX_RELATIVE_HUMIDITY
    ):
        return None
    vapour_pressure = (
        humidity / 100 * 6.105 * exp(17.27 * temperature / (237.7 + temperature))
    )
    return round(temperature + 0.33 * vapour_pressure - 0.7 * wind_speed - 4, 1)


APPARENT_TEMPERATURE_SENSOR = UkrHMCSensorDescription(
    key="apparent_temperature",
    translation_key="apparent_temperature",
    device_class=SensorDeviceClass.TEMPERATURE,
    native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    state_class=SensorStateClass.MEASUREMENT,
    suggested_display_precision=1,
    station_value_fn=lambda observation, _: apparent_temperature(
        observation.temperature,
        observation.humidity,
        observation.wind_speed,
    ),
    location_value_fn=lambda forecast: apparent_temperature(
        forecast.temperature,
        forecast.humidity,
        forecast.wind_speed,
    ),
)


def _observation_time_value(
    observation: UkrHMCObservation,
    value: time | None,
) -> datetime | None:
    """Combine a station observation date with a provider-local time."""
    if value is None:
        return None
    return datetime.combine(
        observation.observed_at.date(),
        value,
        observation.observed_at.tzinfo,
    )


SUNRISE_SENSOR = UkrHMCSensorDescription(
    key="sunrise",
    translation_key="sunrise",
    device_class=SensorDeviceClass.TIMESTAMP,
    station_value_fn=lambda observation, _: _observation_time_value(
        observation, observation.sunrise
    ),
    location_value_fn=lambda _: None,
)
SUNSET_SENSOR = UkrHMCSensorDescription(
    key="sunset",
    translation_key="sunset",
    device_class=SensorDeviceClass.TIMESTAMP,
    station_value_fn=lambda observation, _: _observation_time_value(
        observation, observation.sunset
    ),
    location_value_fn=lambda _: None,
)
PHENOMENON_CODE_SENSOR = UkrHMCSensorDescription(
    key="phenomenon_code",
    translation_key="phenomenon_code",
    entity_category=EntityCategory.DIAGNOSTIC,
    entity_registry_enabled_default=False,
    station_value_fn=lambda observation, _: observation.phenomenon_code,
    location_value_fn=lambda _: None,
)
INDICATOR_CODE_SENSOR = UkrHMCSensorDescription(
    key="indicator_code",
    translation_key="indicator_code",
    entity_category=EntityCategory.DIAGNOSTIC,
    entity_registry_enabled_default=False,
    station_value_fn=lambda observation, _: observation.indicator_code,
    location_value_fn=lambda _: None,
)
PRECIPITATION_SENSOR = UkrHMCSensorDescription(
    key="precipitation",
    translation_key="precipitation",
    device_class=SensorDeviceClass.PRECIPITATION,
    native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
    state_class=SensorStateClass.MEASUREMENT,
    station_value_fn=lambda *_: None,
    location_value_fn=lambda forecast: forecast.precipitation,
)

STATION_SENSORS: tuple[UkrHMCSensorDescription, ...] = (
    CONDITION_SENSOR,
    WEATHER_SENSOR,
    TEMPERATURE_SENSOR,
    APPARENT_TEMPERATURE_SENSOR,
    HUMIDITY_SENSOR,
    PRESSURE_SENSOR,
    WIND_SPEED_SENSOR,
    WIND_DIRECTION_SENSOR,
    DATA_TIME_SENSOR,
    SUNRISE_SENSOR,
    SUNSET_SENSOR,
    PHENOMENON_CODE_SENSOR,
    INDICATOR_CODE_SENSOR,
)

LOCATION_SENSORS: tuple[UkrHMCSensorDescription, ...] = (
    CONDITION_SENSOR,
    WEATHER_SENSOR,
    TEMPERATURE_SENSOR,
    APPARENT_TEMPERATURE_SENSOR,
    HUMIDITY_SENSOR,
    WIND_SPEED_SENSOR,
    WIND_COMPASS_SENSOR,
    WIND_DIRECTION_SENSOR,
    PRECIPITATION_SENSOR,
    DATA_TIME_SENSOR,
)


def _forecast_hours(
    forecast: UkrHMCLocationForecast,
    anchor: datetime,
    hours: int,
) -> tuple[UkrHMCHourlyForecast, ...]:
    """Return complete upcoming provider hours for a fixed horizon."""
    end = anchor + timedelta(hours=hours)
    values = tuple(
        item for item in forecast.hourly_forecasts if anchor < item.forecast_at <= end
    )
    return values if len(values) == hours else ()


def _precipitation_sum(
    forecast: UkrHMCLocationForecast,
    anchor: datetime,
    hours: int,
) -> float | None:
    """Sum precipitation only when every hour in the horizon is published."""
    values = _forecast_hours(forecast, anchor, hours)
    if not values or any(item.precipitation is None for item in values):
        return None
    return sum(item.precipitation for item in values if item.precipitation is not None)


def _next_precipitation(
    forecast: UkrHMCLocationForecast,
    anchor: datetime,
) -> datetime | None:
    """Return the first upcoming hour with published precipitation."""
    return next(
        (
            item.forecast_at
            for item in forecast.hourly_forecasts
            if item.forecast_at > anchor
            and item.precipitation is not None
            and item.precipitation > 0
        ),
        None,
    )


def _daily_temperature(
    forecast: UkrHMCLocationForecast,
    anchor: datetime,
    day_offset: int,
    *,
    high: bool,
) -> float | None:
    """Return the provider's direct daily low or high value."""
    target = anchor.astimezone(ZoneInfo("Europe/Kyiv")).date() + timedelta(
        days=day_offset
    )
    for item in forecast.daily_forecasts:
        if item.date == target:
            return item.temperature_day if high else item.temperature_night
    return None


def _maximum_gust(
    forecast: UkrHMCLocationForecast,
    anchor: datetime,
) -> UkrHMCHourlyForecast | None:
    """Return the hour with the largest published gust in the next 24 hours."""
    values = (
        item
        for item in _forecast_hours(forecast, anchor, 24)
        if item.wind_gust is not None
    )
    return max(values, key=lambda item: item.wind_gust or 0, default=None)


LOCATION_SUMMARY_SENSORS: tuple[UkrHMCLocationSummarySensorDescription, ...] = (
    *(
        UkrHMCLocationSummarySensorDescription(
            key=f"precipitation_next_{hours}h",
            translation_key=f"precipitation_next_{hours}h",
            device_class=SensorDeviceClass.PRECIPITATION,
            native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
            value_fn=lambda forecast, anchor, horizon=hours: _precipitation_sum(
                forecast, anchor, horizon
            ),
        )
        for hours in (1, 3, 6, 12, 24)
    ),
    UkrHMCLocationSummarySensorDescription(
        key="next_precipitation",
        translation_key="next_precipitation",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_next_precipitation,
    ),
    *(
        UkrHMCLocationSummarySensorDescription(
            key=f"temperature_{day}_{extreme}",
            translation_key=f"temperature_{day}_{extreme}",
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            value_fn=lambda forecast, anchor, offset=day_offset, is_high=high: (
                _daily_temperature(forecast, anchor, offset, high=is_high)
            ),
        )
        for day, day_offset in (("today", 0), ("tomorrow", 1))
        for extreme, high in (("min", False), ("max", True))
    ),
    UkrHMCLocationSummarySensorDescription(
        key="maximum_wind_gust_next_24h",
        translation_key="maximum_wind_gust_next_24h",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        value_fn=lambda forecast, anchor: (
            gust.wind_gust if (gust := _maximum_gust(forecast, anchor)) else None
        ),
    ),
    UkrHMCLocationSummarySensorDescription(
        key="maximum_wind_gust_time",
        translation_key="maximum_wind_gust_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda forecast, anchor: (
            gust.forecast_at if (gust := _maximum_gust(forecast, anchor)) else None
        ),
    ),
)

RADIATION_SENSORS: tuple[UkrHMCRadiationSensorDescription, ...] = (
    UkrHMCRadiationSensorDescription(
        key="exposure_dose_rate",
        translation_key="exposure_dose_rate",
        native_unit_of_measurement="µR/h",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda observation: observation.exposure_dose_rate,
    ),
    UkrHMCRadiationSensorDescription(
        key="dose_rate",
        translation_key="dose_rate",
        native_unit_of_measurement="nSv/h",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda observation: observation.dose_rate,
    ),
    UkrHMCRadiationSensorDescription(
        key="observation_time",
        translation_key="observation_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda observation: observation.observed_at,
    ),
)

SNOW_SENSORS: tuple[UkrHMCSnowSensorDescription, ...] = (
    UkrHMCSnowSensorDescription(
        key="snow_depth",
        translation_key="snow_depth",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda observation: observation.snow_depth,
    ),
    UkrHMCSnowSensorDescription(
        key="snow_depth_change",
        translation_key="snow_depth_change",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda observation: observation.snow_depth_change,
    ),
    UkrHMCSnowSensorDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda observation: observation.temperature,
    ),
    UkrHMCSnowSensorDescription(
        key="humidity",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda observation: observation.humidity,
    ),
    UkrHMCSnowSensorDescription(
        key="wind_speed",
        translation_key="wind_speed",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda observation: observation.wind_speed,
    ),
    UkrHMCSnowSensorDescription(
        key="wind_direction",
        translation_key="wind_direction",
        device_class=SensorDeviceClass.WIND_DIRECTION,
        native_unit_of_measurement=DEGREE,
        value_fn=lambda observation: observation.wind.bearing,
    ),
    UkrHMCSnowSensorDescription(
        key="cloudiness",
        translation_key="cloudiness",
        value_fn=lambda observation: observation.cloudiness or None,
    ),
    UkrHMCSnowSensorDescription(
        key="weather_phenomena",
        translation_key="weather_phenomena",
        value_fn=lambda observation: observation.phenomena or None,
    ),
    UkrHMCSnowSensorDescription(
        key="observation_date",
        translation_key="observation_date",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda observation: observation.observed_on,
    ),
)

HYDROLOGY_LEVEL_STATES = (
    "calm",
    "floodplain_flooding",
    "dangerous_high",
    "extreme_high",
    "dangerous_low",
)
HYDROLOGY_WARNING_LEVEL_STATES = (
    "none",
    "change_without_consequences",
    "danger_level_1",
    "danger_level_2",
    "danger_level_3",
    "danger_level_3_low_water",
)
HYDROLOGY_WARNING_LEVEL_NAMES = {
    0: "change_without_consequences",
    1: "danger_level_1",
    2: "danger_level_2",
    3: "danger_level_3",
    4: "danger_level_3_low_water",
}


def _hydrological_situation(observation: UkrHMCHydrologyObservation) -> str | None:
    """Return the provider's stable map-level state."""
    if 0 <= observation.level_class < len(HYDROLOGY_LEVEL_STATES):
        return HYDROLOGY_LEVEL_STATES[observation.level_class]
    return None


HYDROLOGY_SENSORS: tuple[UkrHMCHydrologySensorDescription, ...] = (
    UkrHMCHydrologySensorDescription(
        key="water_level",
        translation_key="water_level",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        suggested_unit_of_measurement=UnitOfLength.CENTIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda observation: observation.water_level,
    ),
    UkrHMCHydrologySensorDescription(
        key="water_level_altitude",
        translation_key="water_level_altitude",
        native_unit_of_measurement=UnitOfLength.METERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda observation: observation.water_level_altitude,
    ),
    UkrHMCHydrologySensorDescription(
        key="water_level_change",
        translation_key="water_level_change",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.METERS,
        suggested_unit_of_measurement=UnitOfLength.CENTIMETERS,
        suggested_display_precision=0,
        value_fn=lambda observation: observation.water_level_change,
    ),
    UkrHMCHydrologySensorDescription(
        key="water_temperature",
        translation_key="water_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda observation: observation.water_temperature,
    ),
    UkrHMCHydrologySensorDescription(
        key="hydrological_situation",
        translation_key="hydrological_situation",
        device_class=SensorDeviceClass.ENUM,
        options=list(HYDROLOGY_LEVEL_STATES),
        value_fn=_hydrological_situation,
    ),
    UkrHMCHydrologySensorDescription(
        key="observation_time",
        translation_key="observation_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda observation: observation.observed_at,
    ),
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


class UkrHMCLocationSummarySensor(UkrHMCEntity, SensorEntity):
    """Represent a summary of direct hourly or daily location forecasts."""

    entity_description: UkrHMCLocationSummarySensorDescription

    def __init__(
        self,
        coordinator: UkrHMCCoordinator,
        subentry: ConfigSubentry,
        description: UkrHMCLocationSummarySensorDescription,
    ) -> None:
        """Initialize a location forecast summary sensor."""
        super().__init__(coordinator, subentry)
        self.entity_description = description
        self._attr_unique_id = f"{subentry.subentry_id}-{description.key}"

    @property
    def location_forecast(self) -> UkrHMCLocationForecast | None:
        """Return the complete forecast for the configured point."""
        return self.coordinator.data.location_forecasts.get(self._subentry.subentry_id)

    @property
    @override
    def available(self) -> bool:
        """Return whether forecast data and a refresh timestamp are available."""
        return (
            super().available
            and self.location_forecast is not None
            and self.coordinator.last_successful_update is not None
        )

    @property
    @override
    def native_value(self) -> StateType | datetime | None:
        """Return the forecast summary value."""
        if (
            self.location_forecast is None
            or self.coordinator.last_successful_update is None
        ):
            return None
        return self.entity_description.value_fn(
            self.location_forecast,
            self.coordinator.last_successful_update,
        )


class UkrHMCForecastDetailsSensor(UkrHMCEntity, SensorEntity):
    """Expose direct provider station forecast details compactly."""

    _attr_translation_key = "forecast_details"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: UkrHMCCoordinator,
        subentry: ConfigSubentry,
    ) -> None:
        """Initialize the detailed forecast sensor."""
        super().__init__(coordinator, subentry)
        self._attr_unique_id = f"{subentry.subentry_id}-forecast_details"

    @property
    def station_forecasts(self) -> tuple[UkrHMCForecastDay, ...]:
        """Return direct forecasts for the configured station."""
        if self._station_id is None:
            return ()
        return self.coordinator.data.forecasts.get(self._station_id, ())

    @property
    @override
    def available(self) -> bool:
        """Return whether detailed forecasts are available."""
        return super().available and bool(self.station_forecasts)

    @property
    @override
    def native_value(self) -> str | None:
        """Return the first forecast date."""
        if not self.station_forecasts:
            return None
        return self.station_forecasts[0].date.isoformat()

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return direct day/night fields unsupported by HA weather forecasts."""
        return {
            "forecasts": [
                {
                    "date": forecast.date.isoformat(),
                    "temperature_night_min": forecast.temperature_night_from,
                    "temperature_night_max": forecast.temperature_night_to,
                    "temperature_day_min": forecast.temperature_day_from,
                    "temperature_day_max": forecast.temperature_day_to,
                    "cloudiness": forecast.cloudiness,
                    "precipitation_night": forecast.precipitation_night,
                    "precipitation_day": forecast.precipitation_day,
                    "wind_speed_night": forecast.wind_speed_night,
                    "wind_speed_day": forecast.wind_speed_day,
                    "sunrise": (
                        forecast.sunrise.isoformat() if forecast.sunrise else None
                    ),
                    "sunset": (
                        forecast.sunset.isoformat() if forecast.sunset else None
                    ),
                    "provider_code": forecast.provider_code,
                }
                for forecast in self.station_forecasts
            ]
        }


class UkrHMCLastSuccessfulUpdateSensor(
    CoordinatorEntity[UkrHMCCoordinator],
    SensorEntity,
):
    """Expose the time of the latest successful provider update."""

    _attr_attribution = ATTRIBUTION
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_translation_key = "last_successful_update"

    def __init__(self, coordinator: UkrHMCCoordinator, entry_id: str) -> None:
        """Initialize the last successful update sensor."""
        super().__init__(coordinator, context="diagnostic:last_successful_update")
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}-last_successful_update"

    @property
    @override
    def available(self) -> bool:
        """Keep the last known successful update visible during failures."""
        return self.coordinator.last_successful_update is not None

    @property
    @override
    def native_value(self) -> datetime | None:
        """Return the latest successful coordinator update time."""
        return self.coordinator.last_successful_update

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


class UkrHMCConsecutiveUpdateFailuresSensor(
    CoordinatorEntity[UkrHMCCoordinator],
    SensorEntity,
):
    """Expose the number of consecutive provider update failures."""

    _attr_attribution = ATTRIBUTION
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_icon = "mdi:counter"
    _attr_translation_key = "consecutive_update_failures"

    def __init__(self, coordinator: UkrHMCCoordinator, entry_id: str) -> None:
        """Initialize the consecutive failure counter."""
        super().__init__(coordinator, context="diagnostic:update_failures")
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}-consecutive_update_failures"

    @property
    @override
    def available(self) -> bool:
        """Keep the failure count visible during provider failures."""
        return True

    @property
    @override
    def native_value(self) -> int:
        """Return the current consecutive failure count."""
        return self.coordinator.consecutive_update_failures

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


class UkrHMCRadiationSensor(UkrHMCEntity, SensorEntity):
    """Represent one current radiation value."""

    entity_description: UkrHMCRadiationSensorDescription

    def __init__(
        self,
        coordinator: UkrHMCCoordinator,
        subentry: ConfigSubentry,
        description: UkrHMCRadiationSensorDescription,
    ) -> None:
        """Initialize a radiation sensor."""
        super().__init__(coordinator, subentry)
        self.entity_description = description
        self._radiation_station_id = int(subentry.data[CONF_STATION_ID])
        self._attr_unique_id = f"{subentry.subentry_id}-{description.key}"

    @property
    def radiation_observation(self) -> UkrHMCRadiationObservation | None:
        """Return the latest radiation observation."""
        return self.coordinator.data.radiation_observations.get(
            self._radiation_station_id
        )

    @property
    @override
    def available(self) -> bool:
        """Return whether current radiation data is available."""
        return (
            self.coordinator.last_update_success
            and self.radiation_observation is not None
        )

    @property
    @override
    def native_value(self) -> StateType | datetime | None:
        """Return the current provider value."""
        if (observation := self.radiation_observation) is None:
            return None
        return self.entity_description.value_fn(observation)

    @property
    @override
    def device_info(self) -> DeviceInfo:
        """Return service device information for this radiation station."""
        return DeviceInfo(
            configuration_url=RADIATION_CONFIGURATION_URL,
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._subentry.subentry_id)},
            manufacturer=MANUFACTURER,
            model=f"UkrHMC Radiation Station {self._radiation_station_id}",
            name=self._subentry.title,
        )


class UkrHMCHydrologySensor(UkrHMCEntity, SensorEntity):
    """Represent one current hydrology value."""

    entity_description: UkrHMCHydrologySensorDescription

    def __init__(
        self,
        coordinator: UkrHMCCoordinator,
        subentry: ConfigSubentry,
        description: UkrHMCHydrologySensorDescription,
    ) -> None:
        """Initialize a hydrology sensor."""
        super().__init__(coordinator, subentry)
        self.entity_description = description
        self._post_id = int(subentry.data[CONF_STATION_ID])
        self._attr_unique_id = f"{subentry.subentry_id}-{description.key}"

    @property
    def hydrology_observation(self) -> UkrHMCHydrologyObservation | None:
        """Return the latest hydrology observation."""
        return self.coordinator.data.hydrology_observations.get(self._post_id)

    @property
    @override
    def available(self) -> bool:
        """Return whether current hydrology data is available."""
        return (
            self.coordinator.last_update_success
            and self.hydrology_observation is not None
        )

    @property
    @override
    def native_value(self) -> StateType | datetime | None:
        """Return the current provider value."""
        if (observation := self.hydrology_observation) is None:
            return None
        return self.entity_description.value_fn(observation)

    @property
    @override
    def device_info(self) -> DeviceInfo:
        """Return service device information for this hydrology post."""
        return DeviceInfo(
            configuration_url=HYDROLOGY_CONFIGURATION_URL,
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._subentry.subentry_id)},
            manufacturer=MANUFACTURER,
            model=f"UkrHMC Hydrology Post {self._post_id}",
            name=self._subentry.title,
        )


class UkrHMCSnowSensor(UkrHMCEntity, SensorEntity):
    """Represent one snow or mountain-weather value."""

    entity_description: UkrHMCSnowSensorDescription

    def __init__(
        self,
        coordinator: UkrHMCCoordinator,
        subentry: ConfigSubentry,
        description: UkrHMCSnowSensorDescription,
    ) -> None:
        """Initialize a snow-station sensor."""
        super().__init__(coordinator, subentry)
        self.entity_description = description
        self._snow_station_id = int(subentry.data[CONF_STATION_ID])
        self._attr_unique_id = f"{subentry.subentry_id}-{description.key}"

    @property
    def snow_observation(self) -> UkrHMCSnowObservation | None:
        """Return the latest snow-station observation."""
        return self.coordinator.data.snow_observations.get(self._snow_station_id)

    @property
    @override
    def available(self) -> bool:
        """Return whether the station has a current provider record."""
        return (
            self.coordinator.last_update_success and self.snow_observation is not None
        )

    @property
    @override
    def native_value(self) -> StateType | date | None:
        """Return the current provider value."""
        if (observation := self.snow_observation) is None:
            return None
        return self.entity_description.value_fn(observation)

    @property
    @override
    def device_info(self) -> DeviceInfo:
        """Return device information for this snow station."""
        return DeviceInfo(
            configuration_url=SNOW_CONFIGURATION_URL,
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._subentry.subentry_id)},
            manufacturer=MANUFACTURER,
            model=f"UkrHMC Snow Station {self._snow_station_id}",
            name=self._subentry.title,
        )


class UkrHMCHydrologyWarningLevelSensor(UkrHMCHydrologySensor):
    """Expose hydrological warning level for the selected post."""

    def __init__(
        self,
        coordinator: UkrHMCCoordinator,
        subentry: ConfigSubentry,
    ) -> None:
        """Initialize the hydrological warning sensor."""
        super().__init__(
            coordinator,
            subentry,
            UkrHMCHydrologySensorDescription(
                key="hydrology_warning_level",
                translation_key="hydrology_warning_level",
                device_class=SensorDeviceClass.ENUM,
                options=list(HYDROLOGY_WARNING_LEVEL_STATES),
                value_fn=lambda _: None,
            ),
        )

    @property
    @override
    def available(self) -> bool:
        """Return whether the post and latest snapshot are available."""
        return self.coordinator.last_update_success and (
            self.coordinator.data.hydrology_posts.get(self._post_id) is not None
        )

    @property
    def warnings(self) -> tuple[UkrHMCHydrologyWarning, ...]:
        """Return warnings for the post's official basin polygon."""
        region_id = self.coordinator.data.hydrology_post_warning_region_ids.get(
            self._post_id
        )
        return self.coordinator.data.regional_hydrology_warnings.get(region_id, ())

    @property
    @override
    def native_value(self) -> str:
        """Return the highest active hydrological warning level."""
        level = max(
            (
                warning.danger_level
                for warning in self.warnings
                if warning.is_active(datetime.now(UTC))
            ),
            default=None,
        )
        return HYDROLOGY_WARNING_LEVEL_NAMES.get(level, "none")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return basin, river, warning text, and validity details."""
        post = self.coordinator.data.hydrology_posts.get(self._post_id)
        region_id = self.coordinator.data.hydrology_post_warning_region_ids.get(
            self._post_id
        )
        updated_at = self.coordinator.data.hydrology_warnings_updated_at
        return {
            "river": post.river if post else None,
            "basin": self.warnings[0].basin_name if self.warnings else None,
            "region_id": region_id,
            "updated_at": updated_at.isoformat() if updated_at else None,
            "warnings": [
                {
                    "level": warning.danger_level,
                    "phenomenon_code": warning.phenomenon_code,
                    "phenomenon": warning.phenomenon,
                    "text": warning.description,
                    "period": warning.period,
                    "starts_at": warning.starts_at.isoformat()
                    if warning.starts_at
                    else None,
                    "ends_at": warning.ends_at.isoformat() if warning.ends_at else None,
                }
                for warning in self.warnings
            ],
        }


SENSORS_BY_SUBENTRY_TYPE = {
    SUBENTRY_TYPE_WEATHER_STATION: (STATION_SENSORS, UkrHMCSensor),
    SUBENTRY_TYPE_WEATHER_LOCATION: (LOCATION_SENSORS, UkrHMCSensor),
    SUBENTRY_TYPE_RADIATION_STATION: (RADIATION_SENSORS, UkrHMCRadiationSensor),
    SUBENTRY_TYPE_HYDROLOGY_POST: (HYDROLOGY_SENSORS, UkrHMCHydrologySensor),
    SUBENTRY_TYPE_SNOW_STATION: (SNOW_SENSORS, UkrHMCSnowSensor),
}


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: UkrHMCConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up current sensors for each configured source."""
    coordinator = config_entry.runtime_data.coordinator
    async_add_entities(
        [
            UkrHMCLastSuccessfulUpdateSensor(coordinator, config_entry.entry_id),
            UkrHMCConsecutiveUpdateFailuresSensor(coordinator, config_entry.entry_id),
        ]
    )
    for subentry in config_entry.subentries.values():
        setup = SENSORS_BY_SUBENTRY_TYPE.get(subentry.subentry_type)
        if setup is None:
            continue
        descriptions, sensor_type = setup
        async_add_entities(
            [
                sensor_type(coordinator, subentry, description)
                for description in descriptions
            ],
            config_subentry_id=subentry.subentry_id,
        )
        if subentry.subentry_type == SUBENTRY_TYPE_WEATHER_STATION:
            async_add_entities(
                [
                    UkrHMCForecastDetailsSensor(coordinator, subentry),
                    UkrHMCRegionalWeatherWarningLevelSensor(coordinator, subentry),
                    UkrHMCRegionalHazardLevelSensor(
                        coordinator, subentry, hazard="fire"
                    ),
                    UkrHMCRegionalHazardLevelSensor(
                        coordinator, subentry, hazard="snow"
                    ),
                ],
                config_subentry_id=subentry.subentry_id,
            )
        elif subentry.subentry_type == SUBENTRY_TYPE_WEATHER_LOCATION:
            async_add_entities(
                [
                    UkrHMCLocationSummarySensor(coordinator, subentry, description)
                    for description in LOCATION_SUMMARY_SENSORS
                ],
                config_subentry_id=subentry.subentry_id,
            )
            async_add_entities(
                [
                    UkrHMCRegionalWeatherWarningLevelSensor(coordinator, subentry),
                    UkrHMCRegionalHazardLevelSensor(
                        coordinator, subentry, hazard="fire"
                    ),
                    UkrHMCRegionalHazardLevelSensor(
                        coordinator, subentry, hazard="snow"
                    ),
                ],
                config_subentry_id=subentry.subentry_id,
            )
        elif subentry.subentry_type == SUBENTRY_TYPE_HYDROLOGY_POST:
            async_add_entities(
                [UkrHMCHydrologyWarningLevelSensor(coordinator, subentry)],
                config_subentry_id=subentry.subentry_id,
            )
