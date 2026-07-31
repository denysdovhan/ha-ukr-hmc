"""Async HTTP client for public UkrHMC data."""

import asyncio
import json
from collections.abc import Mapping
from typing import Any

from aiohttp import ClientError, ClientSession

from .const import (
    BASE_URL,
    CURRENT_PATH,
    DAY_NIGHT_PATH,
    FORECAST_PATH,
    ICON_LOOKUP_PATH,
    REQUEST_HEADERS,
    REQUEST_TIMEOUT,
    STATION_CATALOG_PATH,
    WIND_LOOKUP_PATH,
)
from .errors import UkrHMCConnectionError, UkrHMCDataError
from .models import UkrHMCData, UkrHMCLookups, UkrHMCStation
from .parsers import (
    parse_forecasts,
    parse_lookups,
    parse_night_station_ids,
    parse_observations,
    parse_station_catalog,
)


class UkrHMCClient:
    """Client for public UkrHMC endpoints."""

    def __init__(self, session: ClientSession) -> None:
        """Initialize the client with an injected HTTP session."""
        self._session = session
        self._stations: dict[int, UkrHMCStation] | None = None
        self._lookups: UkrHMCLookups | None = None

    async def _get_text(self, path: str) -> str:
        """Fetch a text payload."""
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                response = await self._session.get(
                    f"{BASE_URL}{path}",
                    headers=REQUEST_HEADERS,
                )
                response.raise_for_status()
                return await response.text()
        except (TimeoutError, ClientError) as exc:
            msg = f"Cannot fetch {path}"
            raise UkrHMCConnectionError(msg) from exc

    async def _get_json(self, path: str) -> Mapping[str, Any]:
        """Fetch a JSON payload served with any content type."""
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                response = await self._session.get(
                    f"{BASE_URL}{path}",
                    headers=REQUEST_HEADERS,
                )
                response.raise_for_status()
                payload = await response.json(content_type=None)
        except (TimeoutError, ClientError) as exc:
            msg = f"Cannot fetch {path}"
            raise UkrHMCConnectionError(msg) from exc
        except json.JSONDecodeError as exc:
            msg = f"Invalid JSON payload from {path}"
            raise UkrHMCDataError(msg) from exc

        if not isinstance(payload, Mapping):
            msg = f"Unexpected payload from {path}"
            raise UkrHMCDataError(msg)
        return payload

    async def async_get_stations(self) -> dict[int, UkrHMCStation]:
        """Return the physical station catalog."""
        if self._stations is None:
            self._stations = parse_station_catalog(
                await self._get_text(STATION_CATALOG_PATH)
            )
        return self._stations

    async def _async_get_lookups(self) -> UkrHMCLookups:
        """Return cached condition and wind lookup tables."""
        if self._lookups is None:
            icon_script, wind_script = await asyncio.gather(
                self._get_text(ICON_LOOKUP_PATH),
                self._get_text(WIND_LOOKUP_PATH),
            )
            self._lookups = parse_lookups(icon_script, wind_script)
        return self._lookups

    async def async_get_data(self) -> UkrHMCData:
        """Fetch one complete provider snapshot."""
        stations, lookups, current, forecasts, day_night = await asyncio.gather(
            self.async_get_stations(),
            self._async_get_lookups(),
            self._get_json(CURRENT_PATH),
            self._get_json(FORECAST_PATH),
            self._get_json(DAY_NIGHT_PATH),
        )
        return UkrHMCData.create(
            stations=stations,
            observations=parse_observations(current, lookups),
            forecasts=parse_forecasts(forecasts, lookups),
            night_station_ids=parse_night_station_ids(day_night),
        )
