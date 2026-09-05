"""Tests for warning transition event entities."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ukr_hmc.const import DOMAIN
from custom_components.ukr_hmc.coordinator import UkrHMCCoordinator
from custom_components.ukr_hmc.event import (
    EVENT_TYPES,
    UkrHMCHydrologyWarningEvent,
    UkrHMCWarningEvent,
)

from .fixtures import (
    DATA,
    HYDROLOGY_SUBENTRY_DATA,
    HYDROLOGY_WARNING,
    STATION_SUBENTRY_DATA,
    WEATHER_WARNING,
)


def _active_warning(warning, level: int):
    now = datetime.now(UTC)
    return replace(
        warning,
        danger_level=level,
        starts_at=now - timedelta(minutes=5),
        ends_at=now + timedelta(hours=1),
    )


async def test_weather_warning_event_transitions(hass) -> None:
    """Weather event emits start, escalation, and end transitions."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={}, subentries_data=[STATION_SUBENTRY_DATA]
    )
    coordinator = UkrHMCCoordinator(hass, entry, AsyncMock())
    coordinator.async_set_updated_data(replace(DATA, regional_weather_warnings={}))
    entity = UkrHMCWarningEvent(
        coordinator, next(iter(entry.subentries.values())), "meteorological"
    )
    entity.async_write_ha_state = Mock()

    assert entity.event_types == EVENT_TYPES
    assert entity.state is None

    warning = _active_warning(WEATHER_WARNING, 1)
    coordinator.data = replace(DATA, regional_weather_warnings={1: (warning,)})
    entity._handle_coordinator_update()
    assert entity.state_attributes["event_type"] == "started"
    assert entity.state_attributes["level"] == 1
    assert entity.state_attributes["territory"] == "Київська"

    warning = _active_warning(WEATHER_WARNING, 2)
    coordinator.data = replace(DATA, regional_weather_warnings={1: (warning,)})
    entity._handle_coordinator_update()
    assert entity.state_attributes["event_type"] == "level_increased"
    assert entity.state_attributes["previous_level"] == 1
    assert entity.state_attributes["level"] == 2

    coordinator.data = replace(DATA, regional_weather_warnings={})
    entity._handle_coordinator_update()
    assert entity.state_attributes["event_type"] == "ended"
    assert entity.state_attributes["previous_level"] == 2
    assert entity.state_attributes["level"] == 0
    assert entity.state_attributes["text"] == WEATHER_WARNING.description


async def test_initial_active_warning_is_only_a_baseline(hass) -> None:
    """Creating an entity during an alert does not produce a false start."""
    warning = _active_warning(WEATHER_WARNING, 1)
    entry = MockConfigEntry(
        domain=DOMAIN, data={}, subentries_data=[STATION_SUBENTRY_DATA]
    )
    coordinator = UkrHMCCoordinator(hass, entry, AsyncMock())
    coordinator.async_set_updated_data(
        replace(DATA, regional_weather_warnings={1: (warning,)})
    )

    entity = UkrHMCWarningEvent(
        coordinator, next(iter(entry.subentries.values())), "meteorological"
    )
    entity.async_write_ha_state = Mock()

    assert entity.state is None
    entity._handle_coordinator_update()
    assert entity.state is None


async def test_hydrology_warning_event_uses_basin(hass) -> None:
    """Hydrology transitions expose the matched basin as territory."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={}, subentries_data=[HYDROLOGY_SUBENTRY_DATA]
    )
    coordinator = UkrHMCCoordinator(hass, entry, AsyncMock())
    coordinator.async_set_updated_data(replace(DATA, regional_hydrology_warnings={}))
    entity = UkrHMCHydrologyWarningEvent(
        coordinator, next(iter(entry.subentries.values()))
    )
    entity.async_write_ha_state = Mock()

    warning = _active_warning(HYDROLOGY_WARNING, 2)
    coordinator.data = replace(DATA, regional_hydrology_warnings={61: (warning,)})
    entity._handle_coordinator_update()

    assert entity.state_attributes["event_type"] == "started"
    assert entity.state_attributes["warning_type"] == "hydrology"
    assert entity.state_attributes["territory"] == HYDROLOGY_WARNING.basin_name
