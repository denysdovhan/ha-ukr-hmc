"""Tests for UkrHMC config and weather subentry flows."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_LATITUDE, CONF_LOCATION, CONF_LONGITUDE, CONF_NAME
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ukr_hmc.api import (
    UkrHMCConnectionError,
    UkrHMCDataError,
    UkrHMCLocationForecastRequest,
)
from custom_components.ukr_hmc.const import (
    CONF_STATION_ID,
    DOMAIN,
    SUBENTRY_TYPE_WEATHER_LOCATION,
    SUBENTRY_TYPE_WEATHER_STATION,
    WEATHER_SUBENTRY_TYPES,
)

from .fixtures import SECOND_STATION, STATION

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


async def _start_subentry_flow(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    subentry_type: str,
):
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, subentry_type),
        context={"source": SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    name_field = next(
        field for field in result["data_schema"].schema if field.schema == CONF_NAME
    )
    assert name_field.description["suggested_value"] == hass.config.location_name
    return result


@pytest.mark.parametrize("subentry_type", WEATHER_SUBENTRY_TYPES)
async def test_config_flow_opens_selected_weather_subentry(
    hass: HomeAssistant,
    subentry_type: str,
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    assert result["type"] is FlowResultType.MENU
    assert result["menu_options"] == WEATHER_SUBENTRY_TYPES

    get_stations = AsyncMock(return_value={STATION.station_id: STATION})
    with patch(
        "custom_components.ukr_hmc.config_flow.UkrHMCClient.async_get_stations",
        new=get_stations,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"next_step_id": subentry_type},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == DOMAIN
    assert result["next_flow"][0].value == "config_subentries_flow"
    subentry_result = hass.config_entries.subentries.async_get(result["next_flow"][1])
    assert subentry_result["handler"] == (result["result"].entry_id, subentry_type)
    assert get_stations.await_count == (
        1 if subentry_type == SUBENTRY_TYPE_WEATHER_STATION else 0
    )


async def test_config_flow_prevents_duplicate_service(
    hass: HomeAssistant,
) -> None:
    MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data={}).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_explicit_station_subentry(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data={})
    entry.add_to_hass(hass)

    with patch(
        "custom_components.ukr_hmc.config_flow.UkrHMCClient.async_get_stations",
        new=AsyncMock(
            return_value={
                STATION.station_id: STATION,
                SECOND_STATION.station_id: SECOND_STATION,
            }
        ),
    ):
        result = await _start_subentry_flow(
            hass,
            entry,
            SUBENTRY_TYPE_WEATHER_STATION,
        )
        assert result["type"] is FlowResultType.FORM
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "Kyiv",
                CONF_STATION_ID: str(STATION.station_id),
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_STATION_ID: STATION.station_id}
    assert result["unique_id"] == f"station:{STATION.station_id}"


async def test_location_subentry_creates_location_after_forecast_validation(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data={})
    entry.add_to_hass(hass)

    validate_forecast = AsyncMock()
    with patch(
        "custom_components.ukr_hmc.config_flow.UkrHMCClient.async_validate_location_forecast",
        new=validate_forecast,
    ):
        result = await _start_subentry_flow(
            hass,
            entry,
            SUBENTRY_TYPE_WEATHER_LOCATION,
        )
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "Home weather",
                CONF_LOCATION: {
                    CONF_LATITUDE: 50.4,
                    CONF_LONGITUDE: 30.5,
                },
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_NAME: "Home weather",
        CONF_LATITUDE: 50.4,
        CONF_LONGITUDE: 30.5,
    }
    assert result["unique_id"] == "location:50.400000:30.500000"
    validate_forecast.assert_awaited_once_with(
        UkrHMCLocationForecastRequest(
            name="Home weather",
            latitude=50.4,
            longitude=30.5,
        )
    )


async def test_duplicate_station_subentry_aborts(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        data={},
        subentries_data=[
            {
                "data": {CONF_STATION_ID: STATION.station_id},
                "subentry_type": SUBENTRY_TYPE_WEATHER_STATION,
                "title": STATION.name,
                "unique_id": f"station:{STATION.station_id}",
            }
        ],
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.ukr_hmc.config_flow.UkrHMCClient.async_get_stations",
        new=AsyncMock(return_value={STATION.station_id: STATION}),
    ):
        result = await _start_subentry_flow(
            hass,
            entry,
            SUBENTRY_TYPE_WEATHER_STATION,
        )
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "Duplicate",
                CONF_STATION_ID: str(STATION.station_id),
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_duplicate_location_subentry_aborts(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        data={},
        subentries_data=[
            {
                "data": {
                    CONF_NAME: "Home weather",
                    CONF_LATITUDE: 50.4,
                    CONF_LONGITUDE: 30.5,
                },
                "subentry_type": SUBENTRY_TYPE_WEATHER_LOCATION,
                "title": "Home weather",
                "unique_id": "location:50.400000:30.500000",
            }
        ],
    )
    entry.add_to_hass(hass)

    result = await _start_subentry_flow(
        hass,
        entry,
        SUBENTRY_TYPE_WEATHER_LOCATION,
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Duplicate",
            CONF_LOCATION: {
                CONF_LATITUDE: 50.4,
                CONF_LONGITUDE: 30.5,
            },
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_location_subentry_connection_error(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data={})
    entry.add_to_hass(hass)

    validate_forecast = AsyncMock(side_effect=[UkrHMCConnectionError, None])
    with patch(
        "custom_components.ukr_hmc.config_flow.UkrHMCClient.async_validate_location_forecast",
        new=validate_forecast,
    ):
        result = await _start_subentry_flow(
            hass,
            entry,
            SUBENTRY_TYPE_WEATHER_LOCATION,
        )
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "",
                CONF_LOCATION: {
                    CONF_LATITUDE: 50.4,
                    CONF_LONGITUDE: 30.5,
                },
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    with patch(
        "custom_components.ukr_hmc.config_flow.UkrHMCClient.async_validate_location_forecast",
        new=validate_forecast,
    ):
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "Home weather",
                CONF_LOCATION: {
                    CONF_LATITUDE: 50.4,
                    CONF_LONGITUDE: 30.5,
                },
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_location_subentry_rejects_missing_forecast(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data={})
    entry.add_to_hass(hass)

    with patch(
        "custom_components.ukr_hmc.config_flow.UkrHMCClient.async_validate_location_forecast",
        new=AsyncMock(side_effect=UkrHMCDataError),
    ):
        result = await _start_subentry_flow(
            hass,
            entry,
            SUBENTRY_TYPE_WEATHER_LOCATION,
        )
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "Home weather",
                CONF_LOCATION: {
                    CONF_LATITUDE: 50.4,
                    CONF_LONGITUDE: 30.5,
                },
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "no_forecast"}


async def test_station_subentry_connection_error(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data={})
    entry.add_to_hass(hass)

    with patch(
        "custom_components.ukr_hmc.config_flow.UkrHMCClient.async_get_stations",
        new=AsyncMock(side_effect=UkrHMCConnectionError),
    ):
        result = await _start_subentry_flow(
            hass,
            entry,
            SUBENTRY_TYPE_WEATHER_STATION,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_station_subentry_rejects_unknown_station(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data={})
    entry.add_to_hass(hass)

    get_stations = AsyncMock(
        side_effect=[
            {SECOND_STATION.station_id: SECOND_STATION},
            {STATION.station_id: STATION},
            {STATION.station_id: STATION},
        ]
    )
    with patch(
        "custom_components.ukr_hmc.config_flow.UkrHMCClient.async_get_stations",
        new=get_stations,
    ):
        result = await _start_subentry_flow(
            hass,
            entry,
            SUBENTRY_TYPE_WEATHER_STATION,
        )
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "",
                CONF_STATION_ID: str(SECOND_STATION.station_id),
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_station"}

    with patch(
        "custom_components.ukr_hmc.config_flow.UkrHMCClient.async_get_stations",
        new=get_stations,
    ):
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "Kyiv",
                CONF_STATION_ID: str(STATION.station_id),
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
