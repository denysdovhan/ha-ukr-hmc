"""Tests for UkrHMC weather and sensor entities."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.components.weather import WeatherEntityFeature
from homeassistant.const import (
    DEGREE,
    EntityCategory,
    UnitOfLength,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfTemperature,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ukr_hmc.binary_sensor import (
    ALERT_FLAGS,
    UkrHMCAlertBinarySensor,
    UkrHMCApiAvailableBinarySensor,
    UkrHMCDataStaleBinarySensor,
)
from custom_components.ukr_hmc.const import (
    CONFIGURATION_URL,
    DOMAIN,
    HYDROLOGY_CONFIGURATION_URL,
    RADIATION_CONFIGURATION_URL,
)
from custom_components.ukr_hmc.coordinator import UkrHMCCoordinator
from custom_components.ukr_hmc.sensor import (
    HYDROLOGY_SENSORS,
    LOCATION_SENSORS,
    LOCATION_SUMMARY_SENSORS,
    RADIATION_SENSORS,
    STATION_SENSORS,
    UkrHMCConsecutiveUpdateFailuresSensor,
    UkrHMCForecastDetailsSensor,
    UkrHMCHydrologySensor,
    UkrHMCLastSuccessfulUpdateSensor,
    UkrHMCLocationSummarySensor,
    UkrHMCRadiationSensor,
    UkrHMCSensor,
    _daily_temperature,
    _maximum_gust,
    _next_precipitation,
    _precipitation_sum,
)
from custom_components.ukr_hmc.weather import UkrHMCWeather, _single_wind_speed

from .fixtures import (
    DATA,
    HYDROLOGY_OBSERVATION,
    HYDROLOGY_POST,
    HYDROLOGY_SUBENTRY_DATA,
    LOCATION_SUBENTRY_DATA,
    RADIATION_STATION,
    RADIATION_SUBENTRY_DATA,
    STATION,
    STATION_SUBENTRY_DATA,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


def _entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        data={},
        subentries_data=[STATION_SUBENTRY_DATA],
    )


def _location_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        data={},
        subentries_data=[LOCATION_SUBENTRY_DATA],
    )


def _radiation_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        data={},
        subentries_data=[RADIATION_SUBENTRY_DATA],
    )


def _hydrology_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        data={},
        subentries_data=[HYDROLOGY_SUBENTRY_DATA],
    )


async def test_station_weather_current_and_native_forecasts(
    hass: HomeAssistant,
) -> None:
    entry = _entry()
    coordinator = UkrHMCCoordinator(hass, entry, AsyncMock())
    coordinator.async_set_updated_data(DATA)
    subentry = next(iter(entry.subentries.values()))
    weather = UkrHMCWeather(coordinator, subentry)

    assert weather.available
    assert weather.condition == "partlycloudy"
    assert weather.native_temperature == 25.9
    assert weather.humidity == 38
    assert weather.native_pressure == 750
    assert weather.native_wind_speed == 3
    assert weather.wind_bearing == "NW"
    assert weather.device_info["configuration_url"] == CONFIGURATION_URL
    assert weather.device_info["model"] == f"UkrHMC Station {STATION.station_id}"
    assert weather.supported_features == (
        WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_TWICE_DAILY
    )
    assert weather._async_forecast_hourly() is None

    daily = weather._async_forecast_daily()
    assert daily == [
        {
            "datetime": "2026-07-29T21:00:00+00:00",
            "condition": "partlycloudy",
            "native_temperature": 26,
            "native_templow": 14,
            "native_wind_speed": None,
            "wind_bearing": "NW",
        }
    ]

    twice_daily = weather._async_forecast_twice_daily()
    assert twice_daily is not None
    assert [item["is_daytime"] for item in twice_daily] == [True, False]
    assert [item["native_temperature"] for item in twice_daily] == [26, 14]
    assert [item["datetime"] for item in twice_daily] == [
        "2026-07-30T02:22:00+00:00",
        "2026-07-30T17:46:00+00:00",
    ]


async def test_location_weather_uses_point_current_and_native_forecasts(
    hass: HomeAssistant,
) -> None:
    entry = _location_entry()
    coordinator = UkrHMCCoordinator(hass, entry, AsyncMock())
    coordinator.async_set_updated_data(DATA)
    subentry = next(iter(entry.subentries.values()))
    weather = UkrHMCWeather(coordinator, subentry)

    assert weather.available
    assert weather.condition == "clear-night"
    assert weather.native_temperature == 20
    assert weather.humidity == 52
    assert weather.native_pressure is None
    assert weather.native_wind_speed == 2
    assert weather.native_wind_gust_speed is None
    assert weather.native_dew_point is None
    assert weather.wind_bearing == "NW"
    assert weather.native_pressure_unit == UnitOfPressure.HPA
    assert weather.supported_features == (
        WeatherEntityFeature.FORECAST_HOURLY | WeatherEntityFeature.FORECAST_DAILY
    )
    assert weather.device_info["model"] == "UkrHMC Location Forecast"
    assert weather._async_forecast_twice_daily() is None
    assert weather._async_forecast_hourly() == [
        {
            "datetime": "2026-07-30T19:00:00+00:00",
            "condition": "clear-night",
            "native_temperature": 20,
            "native_precipitation": 0,
            "native_pressure": 1017,
            "humidity": 52,
            "native_dew_point": 10,
            "native_wind_speed": 2,
            "native_wind_gust_speed": 5,
            "wind_bearing": 315,
        }
    ]
    assert weather._async_forecast_daily() == [
        {
            "datetime": "2026-07-29T21:00:00+00:00",
            "condition": "sunny",
            "native_temperature": 26,
            "native_templow": 14,
        }
    ]


def test_single_wind_speed_requires_one_numeric_value() -> None:
    assert _single_wind_speed("5") == 5
    assert _single_wind_speed("5-10") is None
    assert _single_wind_speed("") is None
    assert _single_wind_speed("calm") is None


async def test_station_current_sensors_use_observation_values(
    hass: HomeAssistant,
) -> None:
    entry = _entry()
    coordinator = UkrHMCCoordinator(hass, entry, AsyncMock())
    coordinator.async_set_updated_data(DATA)
    subentry = next(iter(entry.subentries.values()))

    values = {
        description.key: UkrHMCSensor(
            coordinator,
            subentry,
            description,
        ).native_value
        for description in STATION_SENSORS
    }

    assert values["condition"] == "partlycloudy"
    assert values["weather"] == "Хмарно з проясненнями"
    assert values["temperature"] == 25.9
    assert values["humidity"] == 38
    assert values["pressure"] == 750
    assert values["wind_speed"] == 3
    assert values["wind_direction"] == 315
    assert values["observation_time"].isoformat() == "2026-07-30T15:00:00+03:00"
    assert values["sunrise"].isoformat() == "2026-07-30T05:22:00+03:00"
    assert values["sunset"].isoformat() == "2026-07-30T20:46:00+03:00"
    assert values["phenomenon_code"] == 6
    assert values["indicator_code"] == 0
    assert "wind_compass" not in values

    wind_direction = next(
        description
        for description in STATION_SENSORS
        if description.key == "wind_direction"
    )
    assert wind_direction.device_class is SensorDeviceClass.WIND_DIRECTION
    assert wind_direction.native_unit_of_measurement == DEGREE
    assert wind_direction.state_class is SensorStateClass.MEASUREMENT_ANGLE


async def test_location_current_sensors_use_point_forecast_values(
    hass: HomeAssistant,
) -> None:
    entry = _location_entry()
    coordinator = UkrHMCCoordinator(hass, entry, AsyncMock())
    coordinator.async_set_updated_data(DATA)
    subentry = next(iter(entry.subentries.values()))

    sensors = {
        description.key: UkrHMCSensor(
            coordinator,
            subentry,
            description,
        )
        for description in LOCATION_SENSORS
    }

    assert sensors["condition"].native_value == "clear-night"
    assert sensors["weather"].native_value == "Ясно"
    assert sensors["temperature"].native_value == 20
    assert sensors["humidity"].native_value == 52
    assert sensors["wind_speed"].native_value == 2
    assert sensors["wind_compass"].native_value == "NW"
    assert sensors["wind_direction"].native_value == 315
    assert sensors["precipitation"].native_value == 0
    assert sensors["precipitation"].native_unit_of_measurement == (
        UnitOfPrecipitationDepth.MILLIMETERS
    )
    assert (
        sensors["observation_time"].native_value.isoformat()
        == "2026-07-30T22:00:00+03:00"
    )
    assert "pressure" not in sensors

    wind_compass = next(
        description
        for description in LOCATION_SENSORS
        if description.key == "wind_compass"
    )
    assert wind_compass.device_class is None
    assert wind_compass.native_unit_of_measurement is None
    assert wind_compass.state_class is None


async def test_station_detailed_forecast_sensor(hass: HomeAssistant) -> None:
    entry = _entry()
    coordinator = UkrHMCCoordinator(hass, entry, AsyncMock())
    coordinator.async_set_updated_data(DATA)
    subentry = next(iter(entry.subentries.values()))
    sensor = UkrHMCForecastDetailsSensor(coordinator, subentry)

    assert sensor.native_value == "2026-07-30"
    assert sensor.entity_category is EntityCategory.DIAGNOSTIC
    assert sensor.extra_state_attributes == {
        "forecasts": [
            {
                "date": "2026-07-30",
                "temperature_night_min": 13,
                "temperature_night_max": 15,
                "temperature_day_min": 25,
                "temperature_day_max": 27,
                "cloudiness": "невелика хмарність",
                "precipitation_night": "без опадів",
                "precipitation_day": "без опадів",
                "wind_speed_night": "3-8",
                "wind_speed_day": "5-10",
                "sunrise": "05:22:00",
                "sunset": "20:46:00",
                "provider_code": 16,
            }
        ]
    }


async def test_global_attention_binary_sensors(hass: HomeAssistant) -> None:
    entry = _entry()
    coordinator = UkrHMCCoordinator(hass, entry, AsyncMock())
    coordinator.async_set_updated_data(DATA)
    sensors = {
        description.key: UkrHMCAlertBinarySensor(
            coordinator, entry.entry_id, description
        )
        for description in ALERT_FLAGS
    }

    assert sensors["attns_meteo"].is_on
    assert not sensors["attns_hydro"].is_on
    assert sensors["attns_fire"].is_on
    assert sensors["attns_meteo"].device_info["model"] == "UkrHMC Service"


async def test_api_diagnostic_entities(hass: HomeAssistant) -> None:
    entry = _entry()
    coordinator = UkrHMCCoordinator(hass, entry, AsyncMock())
    coordinator.async_set_updated_data(DATA)
    updated_at = datetime(2026, 9, 4, 8, 30, tzinfo=UTC)
    coordinator.last_successful_update = updated_at

    availability = UkrHMCApiAvailableBinarySensor(coordinator, entry.entry_id)
    last_update = UkrHMCLastSuccessfulUpdateSensor(coordinator, entry.entry_id)

    assert availability.available
    assert availability.is_on
    assert availability.entity_category is EntityCategory.DIAGNOSTIC
    assert availability.device_info["model"] == "UkrHMC Service"
    assert last_update.available
    assert last_update.native_value == updated_at
    assert last_update.device_class is SensorDeviceClass.TIMESTAMP
    assert last_update.entity_category is EntityCategory.DIAGNOSTIC

    failures = UkrHMCConsecutiveUpdateFailuresSensor(coordinator, entry.entry_id)
    stale = UkrHMCDataStaleBinarySensor(coordinator, entry.entry_id)
    assert failures.native_value == 0
    assert not stale.is_on

    coordinator.last_update_success = False
    coordinator.consecutive_update_failures = 2
    assert availability.available
    assert not availability.is_on
    assert last_update.available
    assert last_update.native_value == updated_at
    assert failures.native_value == 2

    coordinator.last_successful_update = datetime.now(UTC) - timedelta(minutes=46)
    assert stale.is_on


async def test_location_forecast_summary_sensors(hass: HomeAssistant) -> None:
    entry = _location_entry()
    coordinator = UkrHMCCoordinator(hass, entry, AsyncMock())
    anchor = datetime(2026, 7, 30, 18, tzinfo=UTC)
    original = DATA.location_forecasts["location-subentry"]
    hourly = tuple(
        replace(
            original.hourly_forecasts[0],
            forecast_at=anchor + timedelta(hours=hour),
            precipitation=0.5 if hour in (2, 4) else 0,
            wind_gust=float(hour),
        )
        for hour in range(1, 25)
    )
    forecast = replace(original, hourly_forecasts=hourly)
    coordinator.async_set_updated_data(
        replace(DATA, location_forecasts={"location-subentry": forecast})
    )
    coordinator.last_successful_update = anchor
    subentry = next(iter(entry.subentries.values()))

    assert _precipitation_sum(forecast, anchor, 1) == 0
    assert _precipitation_sum(forecast, anchor, 3) == 0.5
    assert _precipitation_sum(forecast, anchor, 24) == 1
    assert _next_precipitation(forecast, anchor) == anchor + timedelta(hours=2)
    assert _daily_temperature(forecast, anchor, 0, high=False) == 14
    assert _daily_temperature(forecast, anchor, 0, high=True) == 26
    assert _maximum_gust(forecast, anchor) == hourly[-1]

    sensors = {
        description.key: UkrHMCLocationSummarySensor(coordinator, subentry, description)
        for description in LOCATION_SUMMARY_SENSORS
    }
    assert sensors["precipitation_next_24h"].native_value == 1
    assert sensors["next_precipitation"].native_value == anchor + timedelta(hours=2)
    assert sensors["temperature_today_min"].native_value == 14
    assert sensors["temperature_today_max"].native_value == 26
    assert sensors["maximum_wind_gust_next_24h"].native_value == 24
    assert sensors["maximum_wind_gust_time"].native_value == hourly[-1].forecast_at


async def test_radiation_sensors_use_direct_provider_values(
    hass: HomeAssistant,
) -> None:
    entry = _radiation_entry()
    coordinator = UkrHMCCoordinator(hass, entry, AsyncMock())
    coordinator.async_set_updated_data(DATA)
    subentry = next(iter(entry.subentries.values()))
    sensors = {
        description.key: UkrHMCRadiationSensor(
            coordinator,
            subentry,
            description,
        )
        for description in RADIATION_SENSORS
    }

    assert sensors["exposure_dose_rate"].native_value == 11
    assert sensors["dose_rate"].native_value == 96
    assert (
        sensors["observation_time"].native_value.isoformat()
        == "2026-08-06T12:00:00+03:00"
    )
    assert sensors["exposure_dose_rate"].available
    assert sensors["exposure_dose_rate"].native_unit_of_measurement == "µR/h"
    assert sensors["dose_rate"].native_unit_of_measurement == "nSv/h"
    assert sensors["dose_rate"].state_class is SensorStateClass.MEASUREMENT
    assert sensors["observation_time"].device_class is SensorDeviceClass.TIMESTAMP
    assert sensors["observation_time"].device_info["model"] == (
        f"UkrHMC Radiation Station {RADIATION_STATION.station_id}"
    )
    assert (
        sensors["observation_time"].device_info["configuration_url"]
        == RADIATION_CONFIGURATION_URL
    )

    coordinator.async_set_updated_data(replace(DATA, radiation_observations={}))
    assert not sensors["exposure_dose_rate"].available
    assert sensors["exposure_dose_rate"].native_value is None


async def test_hydrology_sensors_use_direct_provider_values(
    hass: HomeAssistant,
) -> None:
    entry = _hydrology_entry()
    coordinator = UkrHMCCoordinator(hass, entry, AsyncMock())
    coordinator.async_set_updated_data(DATA)
    subentry = next(iter(entry.subentries.values()))
    sensors = {
        description.key: UkrHMCHydrologySensor(
            coordinator,
            subentry,
            description,
        )
        for description in HYDROLOGY_SENSORS
    }

    assert sensors["water_level"].native_value == 444
    assert sensors["water_level_altitude"].native_value == 91.44
    assert sensors["water_level_change"].native_value == -0.01
    assert sensors["water_temperature"].native_value == 25
    assert sensors["hydrological_situation"].native_value == "floodplain_flooding"
    assert (
        sensors["observation_time"].native_value.isoformat()
        == "2026-08-06T08:00:00+03:00"
    )
    assert sensors["water_level"].native_unit_of_measurement == (
        UnitOfLength.CENTIMETERS
    )
    assert sensors["water_level"].suggested_unit_of_measurement == (
        UnitOfLength.CENTIMETERS
    )
    assert sensors["water_level"].suggested_display_precision == 0
    assert sensors["water_level_altitude"].native_unit_of_measurement == (
        UnitOfLength.METERS
    )
    assert sensors["water_level_altitude"].suggested_display_precision == 1
    assert sensors["water_level"].device_class is None
    assert sensors["water_level_altitude"].device_class is None
    assert sensors["water_level_change"].suggested_unit_of_measurement == (
        UnitOfLength.CENTIMETERS
    )
    assert sensors["water_level_change"].suggested_display_precision == 0
    assert sensors["water_level_change"].state_class is None
    assert sensors["water_temperature"].native_unit_of_measurement == (
        UnitOfTemperature.CELSIUS
    )
    assert sensors["hydrological_situation"].device_class is SensorDeviceClass.ENUM
    assert sensors["observation_time"].device_info["model"] == (
        f"UkrHMC Hydrology Post {HYDROLOGY_POST.post_id}"
    )
    assert (
        sensors["observation_time"].device_info["configuration_url"]
        == HYDROLOGY_CONFIGURATION_URL
    )

    coordinator.async_set_updated_data(replace(DATA, hydrology_observations={}))
    assert not sensors["water_level"].available
    assert sensors["water_level"].native_value is None

    coordinator.async_set_updated_data(
        replace(
            DATA,
            hydrology_observations={
                HYDROLOGY_POST.post_id: replace(
                    HYDROLOGY_OBSERVATION,
                    level_class=9,
                )
            },
        )
    )
    assert sensors["hydrological_situation"].native_value is None
