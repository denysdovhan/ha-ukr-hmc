"""Tests for Ukrhydrometcenter config and station subentry flows."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_LATITUDE, CONF_LOCATION, CONF_LONGITUDE, CONF_NAME
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ukr_hmc.api import UkrHMCConnectionError
from custom_components.ukr_hmc.const import (
    CONF_STATION_ID,
    CONF_STATION_TYPE,
    DOMAIN,
    STATION_TYPE_DYNAMIC,
    STATION_TYPE_STATIC,
    SUBENTRY_TYPE_STATION,
)

from .fixtures import SECOND_STATION, STATION

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


async def _start_subentry_flow(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    step_id: str,
):
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE_STATION),
        context={"source": SOURCE_USER},
    )
    assert result["type"] is FlowResultType.MENU
    return await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {"next_step_id": step_id},
    )


async def test_config_flow_tests_connection_and_starts_station_flow(
    hass: HomeAssistant,
) -> None:
    with patch(
        "custom_components.ukr_hmc.config_flow.UkrHMCClient.async_get_stations",
        new=AsyncMock(return_value={STATION.station_id: STATION}),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == DOMAIN
    assert result["next_flow"][0].value == "config_subentries_flow"


async def test_config_flow_connection_error_and_retry(hass: HomeAssistant) -> None:
    with patch(
        "custom_components.ukr_hmc.config_flow.UkrHMCClient.async_get_stations",
        new=AsyncMock(side_effect=UkrHMCConnectionError),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    with patch(
        "custom_components.ukr_hmc.config_flow.UkrHMCClient.async_get_stations",
        new=AsyncMock(return_value={STATION.station_id: STATION}),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_config_flow_rejects_empty_station_catalog(
    hass: HomeAssistant,
) -> None:
    with patch(
        "custom_components.ukr_hmc.config_flow.UkrHMCClient.async_get_stations",
        new=AsyncMock(return_value={}),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "no_stations"}


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
        result = await _start_subentry_flow(hass, entry, "station")
        assert result["type"] is FlowResultType.FORM
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "Kyiv",
                CONF_STATION_ID: str(STATION.station_id),
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_STATION_TYPE: STATION_TYPE_STATIC,
        CONF_STATION_ID: STATION.station_id,
    }
    assert result["unique_id"] == f"station:{STATION.station_id}"


async def test_nearest_station_subentry(hass: HomeAssistant) -> None:
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
        result = await _start_subentry_flow(hass, entry, "map")
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
        CONF_STATION_TYPE: STATION_TYPE_DYNAMIC,
        CONF_LATITUDE: 50.4,
        CONF_LONGITUDE: 30.5,
    }
    assert result["unique_id"] == "location:50.400000:30.500000"


async def test_duplicate_station_subentry_aborts(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        data={},
        subentries_data=[
            {
                "data": {
                    CONF_STATION_TYPE: STATION_TYPE_STATIC,
                    CONF_STATION_ID: STATION.station_id,
                },
                "subentry_type": SUBENTRY_TYPE_STATION,
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
        result = await _start_subentry_flow(hass, entry, "station")
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "Duplicate",
                CONF_STATION_ID: str(STATION.station_id),
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_duplicate_map_subentry_aborts(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        data={},
        subentries_data=[
            {
                "data": {
                    CONF_STATION_TYPE: STATION_TYPE_DYNAMIC,
                    CONF_LATITUDE: 50.4,
                    CONF_LONGITUDE: 30.5,
                },
                "subentry_type": SUBENTRY_TYPE_STATION,
                "title": "Home weather",
                "unique_id": "location:50.400000:30.500000",
            }
        ],
    )
    entry.add_to_hass(hass)

    result = await _start_subentry_flow(hass, entry, "map")
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


@pytest.mark.parametrize(
    ("stations_result", "expected_error"),
    [
        (UkrHMCConnectionError(), "cannot_connect"),
        ({}, "no_stations"),
    ],
)
async def test_map_subentry_errors(
    hass: HomeAssistant,
    stations_result,
    expected_error: str,
) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data={})
    entry.add_to_hass(hass)

    if isinstance(stations_result, Exception):
        mock = AsyncMock(side_effect=stations_result)
    else:
        mock = AsyncMock(return_value=stations_result)

    with patch(
        "custom_components.ukr_hmc.config_flow.UkrHMCClient.async_get_stations",
        new=mock,
    ):
        result = await _start_subentry_flow(hass, entry, "map")
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
    assert result["errors"] == {"base": expected_error}


async def test_station_subentry_connection_error(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data={})
    entry.add_to_hass(hass)

    with patch(
        "custom_components.ukr_hmc.config_flow.UkrHMCClient.async_get_stations",
        new=AsyncMock(side_effect=UkrHMCConnectionError),
    ):
        result = await _start_subentry_flow(hass, entry, "station")

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_station_subentry_rejects_unknown_station(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data={})
    entry.add_to_hass(hass)

    with patch(
        "custom_components.ukr_hmc.config_flow.UkrHMCClient.async_get_stations",
        new=AsyncMock(
            side_effect=[
                {SECOND_STATION.station_id: SECOND_STATION},
                {STATION.station_id: STATION},
            ]
        ),
    ):
        result = await _start_subentry_flow(hass, entry, "station")
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "",
                CONF_STATION_ID: str(SECOND_STATION.station_id),
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_station"}
