"""Tests for UkrHMC warning calendars."""

from dataclasses import replace
from datetime import datetime, timedelta
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ukr_hmc.calendar import (
    UkrHMCHydrologyWarningCalendar,
    UkrHMCWarningCalendar,
)
from custom_components.ukr_hmc.const import DOMAIN
from custom_components.ukr_hmc.coordinator import UkrHMCCoordinator

from .fixtures import DATA, HYDROLOGY_SUBENTRY_DATA, STATION_SUBENTRY_DATA


async def test_warning_calendar_returns_only_timed_overlapping_events(hass) -> None:
    """Calendar exposes provider warning periods from coordinator memory."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={}, subentries_data=[STATION_SUBENTRY_DATA]
    )
    zone = ZoneInfo("Europe/Kyiv")
    start = datetime(2026, 9, 5, 0, tzinfo=zone)
    warning = replace(
        DATA.regional_weather_warnings[1][0],
        starts_at=start + timedelta(hours=9),
        ends_at=start + timedelta(hours=21),
    )
    coordinator = UkrHMCCoordinator(hass, entry, AsyncMock())
    coordinator.async_set_updated_data(
        replace(
            DATA,
            regional_weather_warnings={1: (warning,)},
            regional_fire_warnings={},
        )
    )
    calendar = UkrHMCWarningCalendar(coordinator, next(iter(entry.subentries.values())))

    events = await calendar.async_get_events(
        hass, start + timedelta(hours=8), start + timedelta(hours=10)
    )

    assert len(events) == 1
    assert events[0].start == warning.starts_at
    assert events[0].end == warning.ends_at
    assert events[0].location == "Kyiv weather"
    assert "Метеорологічне попередження" in events[0].summary


async def test_hydrology_warning_calendar_uses_basin_as_location(hass) -> None:
    """Hydrology calendar exposes a selected post's timed basin warnings."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={}, subentries_data=[HYDROLOGY_SUBENTRY_DATA]
    )
    zone = ZoneInfo("Europe/Kyiv")
    start = datetime(2026, 9, 4, 0, tzinfo=zone)
    warning = replace(
        DATA.regional_hydrology_warnings[61][0],
        starts_at=start,
        ends_at=start + timedelta(days=1),
    )
    coordinator = UkrHMCCoordinator(hass, entry, AsyncMock())
    coordinator.async_set_updated_data(
        replace(DATA, regional_hydrology_warnings={61: (warning,)})
    )
    calendar = UkrHMCHydrologyWarningCalendar(
        coordinator, next(iter(entry.subentries.values()))
    )

    events = await calendar.async_get_events(
        hass, start - timedelta(hours=1), start + timedelta(hours=1)
    )

    assert len(events) == 1
    assert events[0].summary == "Підвищення рівнів води"
    assert "Середнього Дніпра" in events[0].location
    assert "Річка поста: Дніпро" in events[0].description
