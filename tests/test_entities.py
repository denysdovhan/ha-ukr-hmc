"""Tests for UkrHMC weather and sensor entities."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.components.weather import WeatherEntityFeature
from homeassistant.const import DEGREE, UnitOfPressure
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ukr_hmc.const import CONFIGURATION_URL, DOMAIN
from custom_components.ukr_hmc.coordinator import UkrHMCCoordinator
from custom_components.ukr_hmc.sensor import SENSORS, UkrHMCSensor
from custom_components.ukr_hmc.weather import UkrHMCWeather, _single_wind_speed

from .fixtures import (
    DATA,
    LOCATION_SUBENTRY_DATA,
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
    assert weather.native_pressure == 1017
    assert weather.native_wind_speed == 2
    assert weather.native_wind_gust_speed == 5
    assert weather.native_dew_point == 10
    assert weather.wind_bearing == 315
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
        for description in SENSORS
    }

    assert values["condition"] == "partlycloudy"
    assert values["weather"] == "Хмарно з проясненнями"
    assert values["temperature"] == 25.9
    assert values["humidity"] == 38
    assert values["pressure"] == 750
    assert values["wind_speed"] == 3
    assert values["wind_direction"] == 315
    assert values["observation_time"].isoformat() == "2026-07-30T15:00:00+03:00"

    wind_direction = next(
        description for description in SENSORS if description.key == "wind_direction"
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
        for description in SENSORS
    }

    assert sensors["condition"].native_value == "clear-night"
    assert sensors["weather"].native_value == "Ясно"
    assert sensors["temperature"].native_value == 20
    assert sensors["humidity"].native_value == 52
    assert sensors["pressure"].native_value == 1017
    assert sensors["wind_speed"].native_value == 2
    assert sensors["wind_direction"].native_value == 315
    assert (
        sensors["observation_time"].native_value.isoformat()
        == "2026-07-30T22:00:00+03:00"
    )
    assert sensors["pressure"].native_unit_of_measurement == UnitOfPressure.HPA
