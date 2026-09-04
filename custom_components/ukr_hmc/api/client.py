"""Async HTTP client for public UkrHMC data."""

import asyncio
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from math import isclose
from typing import Any

from aiohttp import ClientError, ClientSession

from .const import (
    BASE_URL,
    CITY_API_PATH,
    CITY_LANGUAGE,
    CITY_WEATHER_ACTION,
    CURRENT_PATH,
    DAY_NIGHT_PATH,
    FORECAST_PATH,
    HYDROLOGY_DATA_PATH,
    HYDROLOGY_POST_CATALOG_PATH,
    ICON_LOOKUP_PATH,
    LOCATION_MATCH_TOLERANCE,
    QUERY_ACTION,
    QUERY_CITY,
    QUERY_LANGUAGE,
    QUERY_LOCATION,
    RADIATION_DATA_PATH,
    RADIATION_STATION_CATALOG_PATH,
    REQUEST_HEADERS,
    REQUEST_TIMEOUT,
    STATION_CATALOG_PATH,
    WIND_LOOKUP_PATH,
)
from .errors import UkrHMCConnectionError, UkrHMCDataError
from .models import (
    UkrHMCData,
    UkrHMCHydrologyObservation,
    UkrHMCHydrologyPost,
    UkrHMCLocationForecast,
    UkrHMCLocationForecastRequest,
    UkrHMCLookups,
    UkrHMCRadiationObservation,
    UkrHMCRadiationStation,
    UkrHMCStation,
)
from .parsers import (
    parse_alert_flags,
    parse_current_location_forecast,
    parse_forecasts,
    parse_hourly_forecasts,
    parse_hydrology_observations,
    parse_hydrology_post_catalog,
    parse_location_daily_forecasts,
    parse_location_forecast_point,
    parse_lookups,
    parse_night_station_ids,
    parse_observations,
    parse_radiation_observations,
    parse_radiation_station_catalog,
    parse_station_catalog,
)


class UkrHMCClient:
    """Client for public UkrHMC endpoints."""

    def __init__(self, session: ClientSession) -> None:
        """Initialize the client with an injected HTTP session."""
        self._session = session
        self._stations: dict[int, UkrHMCStation] | None = None
        self._radiation_stations: dict[int, UkrHMCRadiationStation] | None = None
        self._hydrology_posts: dict[int, UkrHMCHydrologyPost] | None = None
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

    async def _get_json(
        self,
        path: str,
        params: Mapping[str, str | int] | None = None,
    ) -> Mapping[str, Any]:
        """Fetch a JSON payload served with any content type."""
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                response = await self._session.get(
                    f"{BASE_URL}{path}",
                    headers=REQUEST_HEADERS,
                    params=params,
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

    async def async_get_radiation_stations(
        self,
    ) -> dict[int, UkrHMCRadiationStation]:
        """Return the physical radiation station catalog."""
        if self._radiation_stations is None:
            self._radiation_stations = parse_radiation_station_catalog(
                await self._get_text(RADIATION_STATION_CATALOG_PATH)
            )
        return self._radiation_stations

    async def async_get_radiation_data(
        self,
    ) -> tuple[
        dict[int, UkrHMCRadiationStation],
        dict[int, UkrHMCRadiationObservation],
    ]:
        """Return the radiation station catalog and current observations."""
        stations, payload = await asyncio.gather(
            self.async_get_radiation_stations(),
            self._get_json(RADIATION_DATA_PATH),
        )
        return stations, parse_radiation_observations(payload)

    async def async_get_hydrology_posts(self) -> dict[int, UkrHMCHydrologyPost]:
        """Return the physical hydrology post catalog."""
        if self._hydrology_posts is None:
            self._hydrology_posts = parse_hydrology_post_catalog(
                await self._get_text(HYDROLOGY_POST_CATALOG_PATH)
            )
        return self._hydrology_posts

    async def async_get_hydrology_data(
        self,
    ) -> tuple[
        dict[int, UkrHMCHydrologyPost],
        dict[int, UkrHMCHydrologyObservation],
    ]:
        """Return the hydrology post catalog and current observations."""
        posts, payload = await asyncio.gather(
            self.async_get_hydrology_posts(),
            self._get_json(HYDROLOGY_DATA_PATH),
        )
        return posts, parse_hydrology_observations(payload)

    async def _async_get_lookups(self) -> UkrHMCLookups:
        """Return cached condition and wind lookup tables."""
        if self._lookups is None:
            icon_script, wind_script = await asyncio.gather(
                self._get_text(ICON_LOOKUP_PATH),
                self._get_text(WIND_LOOKUP_PATH),
            )
            self._lookups = parse_lookups(icon_script, wind_script)
        return self._lookups

    async def _async_get_location_forecast(
        self,
        request: UkrHMCLocationForecastRequest,
    ) -> UkrHMCLocationForecast:
        """Return the provider's forecast for an explicit location."""
        city = request.name.strip()
        if not city:
            msg = "Location forecast city label is required"
            raise UkrHMCDataError(msg)
        payload = await self._get_json(
            CITY_API_PATH,
            params={
                QUERY_ACTION: CITY_WEATHER_ACTION,
                QUERY_CITY: city,
                QUERY_LOCATION: f"{request.latitude},{request.longitude}",
                QUERY_LANGUAGE: CITY_LANGUAGE,
            },
        )
        latitude, longitude = parse_location_forecast_point(payload)
        if not (
            isclose(
                latitude,
                request.latitude,
                abs_tol=LOCATION_MATCH_TOLERANCE,
            )
            and isclose(
                longitude,
                request.longitude,
                abs_tol=LOCATION_MATCH_TOLERANCE,
            )
        ):
            msg = "Provider forecast location does not match the requested point"
            raise UkrHMCDataError(msg)
        return UkrHMCLocationForecast(
            current=parse_current_location_forecast(payload, datetime.now(UTC)),
            hourly_forecasts=parse_hourly_forecasts(payload),
            daily_forecasts=parse_location_daily_forecasts(payload),
        )

    async def async_validate_location_forecast(
        self,
        request: UkrHMCLocationForecastRequest,
    ) -> UkrHMCLocationForecast:
        """Return a validated, non-empty location forecast."""
        forecast = await self._async_get_location_forecast(request)
        if not forecast.hourly_forecasts:
            msg = "No hourly forecast data for the requested location"
            raise UkrHMCDataError(msg)
        return forecast

    async def async_get_data(
        self,
        location_forecasts: Mapping[
            str,
            UkrHMCLocationForecastRequest,
        ]
        | None = None,
        *,
        include_station_data: bool = True,
        include_radiation_data: bool = False,
        include_hydrology_data: bool = False,
    ) -> UkrHMCData:
        """Fetch one complete provider snapshot."""
        location_requests = location_forecasts or {}
        stations = {}
        observations = {}
        forecasts = {}
        night_station_ids = frozenset()
        radiation_stations = {}
        radiation_observations = {}
        hydrology_posts = {}
        hydrology_observations = {}
        day_night = await self._get_json(DAY_NIGHT_PATH)
        alert_flags = parse_alert_flags(day_night)
        if include_station_data:
            (
                stations,
                lookups,
                current,
                forecast_payload,
            ) = await asyncio.gather(
                self.async_get_stations(),
                self._async_get_lookups(),
                self._get_json(CURRENT_PATH),
                self._get_json(FORECAST_PATH),
            )
            observations = parse_observations(current, lookups)
            forecasts = parse_forecasts(forecast_payload, lookups)
            night_station_ids = parse_night_station_ids(day_night)
        if include_radiation_data:
            (
                radiation_stations,
                radiation_observations,
            ) = await self.async_get_radiation_data()
        if include_hydrology_data:
            (
                hydrology_posts,
                hydrology_observations,
            ) = await self.async_get_hydrology_data()
        location_results = await asyncio.gather(
            *(
                self._async_get_location_forecast(request)
                for request in location_requests.values()
            )
        )
        return UkrHMCData.create(
            stations=stations,
            observations=observations,
            forecasts=forecasts,
            location_forecasts=dict(
                zip(location_requests, location_results, strict=True)
            ),
            night_station_ids=night_station_ids,
            radiation_stations=radiation_stations,
            radiation_observations=radiation_observations,
            hydrology_posts=hydrology_posts,
            hydrology_observations=hydrology_observations,
            alert_flags=alert_flags,
        )
