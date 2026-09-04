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
    HYDROLOGY_WARNING_LOOKUP_PATH,
    HYDROLOGY_WARNINGS_PATH,
    ICON_LOOKUP_PATH,
    LOCATION_MATCH_TOLERANCE,
    QUERY_ACTION,
    QUERY_CITY,
    QUERY_LANGUAGE,
    QUERY_LOCATION,
    RADIATION_DATA_PATH,
    RADIATION_STATION_CATALOG_PATH,
    REGIONAL_FIRE_WARNINGS_PATH,
    REGIONAL_SNOW_WARNINGS_PATH,
    REGIONAL_WEATHER_WARNINGS_PATH,
    REQUEST_HEADERS,
    REQUEST_TIMEOUT,
    SNOW_DATA_PATH,
    SNOW_STATION_CATALOG_PATH,
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
    UkrHMCSnowObservation,
    UkrHMCSnowStation,
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
    parse_region_geometry,
    parse_regional_hazard_warnings,
    parse_regional_hydrology_warnings,
    parse_regional_weather_warnings,
    parse_snow_observations,
    parse_snow_station_catalog,
    parse_station_catalog,
    point_in_region,
)


class UkrHMCClient:
    """Client for public UkrHMC endpoints."""

    def __init__(self, session: ClientSession) -> None:
        """Initialize the client with an injected HTTP session."""
        self._session = session
        self.endpoint_availability: dict[str, bool] = {}
        self._stations: dict[int, UkrHMCStation] | None = None
        self._radiation_stations: dict[int, UkrHMCRadiationStation] | None = None
        self._hydrology_posts: dict[int, UkrHMCHydrologyPost] | None = None
        self._snow_stations: dict[int, UkrHMCSnowStation] | None = None
        self._lookups: UkrHMCLookups | None = None
        self._region_geometries: dict[
            str, tuple[tuple[tuple[tuple[float, float], ...], ...], ...]
        ] = {}

    async def _async_get_region_geometry(
        self, path: str
    ) -> tuple[tuple[tuple[tuple[float, float], ...], ...], ...]:
        """Return a cached provider region geometry."""
        if path not in self._region_geometries:
            self._region_geometries[path] = parse_region_geometry(
                await self._get_json(path)
            )
        return self._region_geometries[path]

    async def _async_resolve_warning_regions(
        self,
        warnings: Mapping[int, tuple[Any, ...]],
        points: Mapping[str | int, tuple[float, float]],
    ) -> dict[str | int, int]:
        """Resolve points against polygons referenced by one warning feed."""
        if not warnings or not points:
            return {}
        geometry_paths = {
            region_id: region_warnings[0].geometry_path
            for region_id, region_warnings in warnings.items()
        }
        geometries = await asyncio.gather(
            *(self._async_get_region_geometry(path) for path in geometry_paths.values())
        )
        resolved = {}
        for point_id, (longitude, latitude) in points.items():
            for region_id, geometry in zip(geometry_paths, geometries, strict=True):
                if point_in_region(longitude, latitude, geometry):
                    resolved[point_id] = region_id
                    break
        return resolved

    async def _get_text(self, path: str) -> str:
        """Fetch a text payload."""
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                response = await self._session.get(
                    f"{BASE_URL}{path}",
                    headers=REQUEST_HEADERS,
                )
                response.raise_for_status()
                text = await response.text()
                self.endpoint_availability[path] = True
                return text
        except (TimeoutError, ClientError) as exc:
            self.endpoint_availability[path] = False
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
            self.endpoint_availability[path] = False
            msg = f"Cannot fetch {path}"
            raise UkrHMCConnectionError(msg) from exc
        except json.JSONDecodeError as exc:
            self.endpoint_availability[path] = False
            msg = f"Invalid JSON payload from {path}"
            raise UkrHMCDataError(msg) from exc

        if not isinstance(payload, Mapping):
            self.endpoint_availability[path] = False
            msg = f"Unexpected payload from {path}"
            raise UkrHMCDataError(msg)
        self.endpoint_availability[path] = True
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

    async def async_get_snow_stations(self) -> dict[int, UkrHMCSnowStation]:
        """Return the snow and avalanche station catalog."""
        if self._snow_stations is None:
            self._snow_stations = parse_snow_station_catalog(
                await self._get_text(SNOW_STATION_CATALOG_PATH)
            )
        return self._snow_stations

    async def async_get_snow_data(
        self,
    ) -> tuple[dict[int, UkrHMCSnowStation], dict[int, UkrHMCSnowObservation]]:
        """Return mountain stations and their latest observations."""
        stations, lookups, payload = await asyncio.gather(
            self.async_get_snow_stations(),
            self._async_get_lookups(),
            self._get_json(SNOW_DATA_PATH),
        )
        return stations, parse_snow_observations(payload, lookups)

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

    async def async_get_data(  # noqa: PLR0915
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
        include_snow_data: bool = False,
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
        snow_stations = {}
        snow_observations = {}
        weather_warnings_updated_at = None
        regional_weather_warnings = {}
        location_region_ids = {}
        fire_warnings_updated_at = None
        regional_fire_warnings = {}
        location_fire_region_ids = {}
        snow_warnings_updated_at = None
        regional_snow_warnings = {}
        location_snow_region_ids = {}
        station_snow_region_ids = {}
        hydrology_warnings_updated_at = None
        regional_hydrology_warnings = {}
        hydrology_post_warning_region_ids = {}
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
        elif location_requests:
            stations = await self.async_get_stations()
        if include_station_data or location_requests:
            warning_payload, fire_payload, snow_payload = await asyncio.gather(
                self._get_json(REGIONAL_WEATHER_WARNINGS_PATH),
                self._get_json(REGIONAL_FIRE_WARNINGS_PATH),
                self._get_json(REGIONAL_SNOW_WARNINGS_PATH),
            )
            (
                weather_warnings_updated_at,
                regional_weather_warnings,
            ) = parse_regional_weather_warnings(warning_payload)
            fire_warnings_updated_at, regional_fire_warnings = (
                parse_regional_hazard_warnings(fire_payload)
            )
            snow_warnings_updated_at, regional_snow_warnings = (
                parse_regional_hazard_warnings(snow_payload)
            )
        location_points = {
            location_id: (request.longitude, request.latitude)
            for location_id, request in location_requests.items()
        }
        location_region_ids = await self._async_resolve_warning_regions(
            regional_weather_warnings, location_points
        )
        location_fire_region_ids = await self._async_resolve_warning_regions(
            regional_fire_warnings, location_points
        )
        location_snow_region_ids = await self._async_resolve_warning_regions(
            regional_snow_warnings, location_points
        )
        station_snow_region_ids = await self._async_resolve_warning_regions(
            regional_snow_warnings,
            {
                station_id: (station.longitude, station.latitude)
                for station_id, station in stations.items()
            },
        )
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
            hydrology_warning_payload, hydrology_warning_lookup = await asyncio.gather(
                self._get_json(HYDROLOGY_WARNINGS_PATH),
                self._get_text(HYDROLOGY_WARNING_LOOKUP_PATH),
            )
            (
                hydrology_warnings_updated_at,
                regional_hydrology_warnings,
            ) = parse_regional_hydrology_warnings(
                hydrology_warning_payload, hydrology_warning_lookup
            )
            hydrology_post_warning_region_ids = (
                await self._async_resolve_warning_regions(
                    regional_hydrology_warnings,
                    {
                        post_id: (post.longitude, post.latitude)
                        for post_id, post in hydrology_posts.items()
                    },
                )
            )
        if include_snow_data:
            snow_stations, snow_observations = await self.async_get_snow_data()
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
            snow_stations=snow_stations,
            snow_observations=snow_observations,
            alert_flags=alert_flags,
            weather_warnings_updated_at=weather_warnings_updated_at,
            regional_weather_warnings=regional_weather_warnings,
            location_region_ids=location_region_ids,
            fire_warnings_updated_at=fire_warnings_updated_at,
            regional_fire_warnings=regional_fire_warnings,
            location_fire_region_ids=location_fire_region_ids,
            snow_warnings_updated_at=snow_warnings_updated_at,
            regional_snow_warnings=regional_snow_warnings,
            location_snow_region_ids=location_snow_region_ids,
            station_snow_region_ids=station_snow_region_ids,
            hydrology_warnings_updated_at=hydrology_warnings_updated_at,
            regional_hydrology_warnings=regional_hydrology_warnings,
            hydrology_post_warning_region_ids=hydrology_post_warning_region_ids,
        )
