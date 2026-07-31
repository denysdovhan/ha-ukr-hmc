"""Tests for UkrHMC weather and sensor entities."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ukr_hmc.const import DOMAIN
from custom_components.ukr_hmc.coordinator import UkrHMCCoordinator
from custom_components.ukr_hmc.sensor import SENSORS, UkrHMCSensor
from custom_components.ukr_hmc.weather import UkrHMCWeather

from .fixtures import DATA, STATIC_SUBENTRY_DATA

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


def _entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        data={},
        subentries_data=[STATIC_SUBENTRY_DATA],
    )


async def test_weather_current_and_native_forecasts(hass: HomeAssistant) -> None:
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


async def test_current_sensors_use_provider_values(hass: HomeAssistant) -> None:
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

    assert values["condition"] == "Хмарно з проясненнями"
    assert values["temperature"] == 25.9
    assert values["humidity"] == 38
    assert values["pressure"] == 750
    assert values["wind_speed"] == 3
    assert values["wind_direction"] == "Північно-Західний"
    assert values["observation_time"].isoformat() == "2026-07-30T15:00:00+03:00"
