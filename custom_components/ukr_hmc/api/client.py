"""Async HTTP client for public UkrHMC data."""

import asyncio
import json
import logging
import random
from collections.abc import Mapping
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from math import isclose
from time import monotonic
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession

from .const import (
    BASE_URL,
    CATALOG_CACHE_TTL,
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
    MAX_CONCURRENT_LOCATION_REQUESTS,
    QUERY_ACTION,
    QUERY_CITY,
    QUERY_LANGUAGE,
    QUERY_LOCATION,
    RADIATION_DATA_PATH,
    RADIATION_STATION_CATALOG_PATH,
    REGIONAL_FIRE_WARNINGS_PATH,
    REGIONAL_SNOW_WARNINGS_PATH,
    REGIONAL_WEATHER_WARNINGS_PATH,
    REQUEST_ATTEMPTS,
    REQUEST_HEADERS,
    REQUEST_TIMEOUT,
    RETRY_BASE_DELAY,
    RETRY_MAX_DELAY,
    RETRYABLE_HTTP_STATUSES,
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
from .telemetry import SchemaTelemetry

LOGGER = logging.getLogger(__name__)


def _retry_delay(exc: BaseException, attempt: int) -> float:
    """Return a bounded retry delay, honoring Retry-After when possible."""
    if isinstance(exc, ClientResponseError) and exc.headers:
        retry_after = exc.headers.get("Retry-After")
        if retry_after:
            try:
                return min(max(float(retry_after), 0), RETRY_MAX_DELAY)
            except ValueError:
                try:
                    retry_at = parsedate_to_datetime(retry_after)
                    seconds = (retry_at - datetime.now(UTC)).total_seconds()
                    return min(max(seconds, 0), RETRY_MAX_DELAY)
                except TypeError, ValueError:
                    pass
    exponential = RETRY_BASE_DELAY * (2**attempt)
    jitter = random.uniform(0, RETRY_BASE_DELAY)  # noqa: S311
    return min(exponential + jitter, RETRY_MAX_DELAY)


def _is_retryable(exc: BaseException) -> bool:
    """Return whether an idempotent provider GET should be retried."""
    return not isinstance(exc, ClientResponseError) or (
        exc.status in RETRYABLE_HTTP_STATUSES
    )


class UkrHMCClient:
    """Client for public UkrHMC endpoints."""

    def __init__(self, session: ClientSession, *, version: str | None = None) -> None:
        """Initialize the client with an injected HTTP session."""
        self._session = session
        self._request_headers = dict(REQUEST_HEADERS)
        if version:
            self._request_headers["User-Agent"] = (
                f"UkrHMC/{version} Home Assistant integration "
                "(+https://github.com/denysdovhan/ha-ukr-hmc)"
            )
        self.endpoint_availability: dict[str, bool] = {}
        self.endpoint_telemetry: dict[str, dict[str, Any]] = {}
        self.source_availability: dict[str, bool] = {}
        self.schema_telemetry = SchemaTelemetry()
        self._cache_updated_at: dict[str, float] = {}
        self._stations: dict[int, UkrHMCStation] | None = None
        self._radiation_stations: dict[int, UkrHMCRadiationStation] | None = None
        self._hydrology_posts: dict[int, UkrHMCHydrologyPost] | None = None
        self._snow_stations: dict[int, UkrHMCSnowStation] | None = None
        self._lookups: UkrHMCLookups | None = None
        self._region_geometries: dict[
            str, tuple[tuple[tuple[tuple[float, float], ...], ...], ...]
        ] = {}

    def _record_endpoint_result(  # noqa: PLR0913
        self,
        path: str,
        *,
        available: bool,
        started_at: float,
        attempts: int,
        status: int | None = None,
        error_category: str | None = None,
    ) -> None:
        """Record one privacy-safe request result and log state transitions."""
        previous = self.endpoint_availability.get(path)
        self.endpoint_availability[path] = available
        self.endpoint_telemetry[path] = {
            "available": available,
            "duration_ms": round((monotonic() - started_at) * 1000),
            "attempts": attempts,
            "status": status,
            "status_category": f"{status // 100}xx" if status else None,
            "error_category": error_category,
        }
        if previous is not False and not available:
            LOGGER.warning("Provider endpoint became unavailable: %s", path)
        elif previous is False and available:
            LOGGER.info("Provider endpoint recovered: %s", path)

    def _cache_is_fresh(self, key: str) -> bool:
        """Return whether a catalog or lookup cache is within its TTL."""
        updated_at = self._cache_updated_at.get(key)
        return updated_at is not None and (
            monotonic() - updated_at < CATALOG_CACHE_TTL.total_seconds()
        )

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
        geometry_results = await asyncio.gather(
            *(
                self._async_get_region_geometry(path)
                for path in geometry_paths.values()
            ),
            return_exceptions=True,
        )
        geometries = {}
        for (region_id, path), result in zip(
            geometry_paths.items(), geometry_results, strict=True
        ):
            if isinstance(result, (UkrHMCConnectionError, UkrHMCDataError)):
                LOGGER.warning("Cannot resolve warning region %s: %s", path, result)
                continue
            if isinstance(result, BaseException):
                raise result
            geometries[region_id] = result
        resolved = {}
        for point_id, (longitude, latitude) in points.items():
            for region_id, geometry in geometries.items():
                if point_in_region(longitude, latitude, geometry):
                    resolved[point_id] = region_id
                    break
        return resolved

    async def _get_text(self, path: str) -> str:
        """Fetch a text payload."""
        started_at = monotonic()
        for attempt in range(REQUEST_ATTEMPTS):
            try:
                async with asyncio.timeout(REQUEST_TIMEOUT):
                    response = await self._session.get(
                        f"{BASE_URL}{path}",
                        headers=self._request_headers,
                    )
                    response.raise_for_status()
                    text = await response.text()
                    self._record_endpoint_result(
                        path,
                        available=True,
                        started_at=started_at,
                        attempts=attempt + 1,
                        status=response.status,
                    )
                    return text
            except (TimeoutError, ClientError) as exc:
                if attempt + 1 < REQUEST_ATTEMPTS and _is_retryable(exc):
                    await asyncio.sleep(_retry_delay(exc, attempt))
                    continue
                self._record_endpoint_result(
                    path,
                    available=False,
                    started_at=started_at,
                    attempts=attempt + 1,
                    status=exc.status if isinstance(exc, ClientResponseError) else None,
                    error_category=(
                        "timeout" if isinstance(exc, TimeoutError) else "http"
                    ),
                )
                msg = f"Cannot fetch {path}"
                raise UkrHMCConnectionError(msg) from exc
        raise AssertionError

    async def _get_json(
        self,
        path: str,
        params: Mapping[str, str | int] | None = None,
    ) -> Mapping[str, Any]:
        """Fetch a JSON payload served with any content type."""
        started_at = monotonic()
        for attempt in range(REQUEST_ATTEMPTS):
            try:
                async with asyncio.timeout(REQUEST_TIMEOUT):
                    response = await self._session.get(
                        f"{BASE_URL}{path}",
                        headers=self._request_headers,
                        params=params,
                    )
                    response.raise_for_status()
                    payload = await response.json(content_type=None)
                break
            except (TimeoutError, ClientError) as exc:
                if attempt + 1 < REQUEST_ATTEMPTS and _is_retryable(exc):
                    await asyncio.sleep(_retry_delay(exc, attempt))
                    continue
                self._record_endpoint_result(
                    path,
                    available=False,
                    started_at=started_at,
                    attempts=attempt + 1,
                    status=exc.status if isinstance(exc, ClientResponseError) else None,
                    error_category=(
                        "timeout" if isinstance(exc, TimeoutError) else "http"
                    ),
                )
                msg = f"Cannot fetch {path}"
                raise UkrHMCConnectionError(msg) from exc
            except json.JSONDecodeError as exc:
                self._record_endpoint_result(
                    path,
                    available=False,
                    started_at=started_at,
                    attempts=attempt + 1,
                    status=response.status,
                    error_category="invalid_json",
                )
                msg = f"Invalid JSON payload from {path}"
                raise UkrHMCDataError(msg) from exc
        else:
            raise AssertionError

        if not isinstance(payload, Mapping):
            self._record_endpoint_result(
                path,
                available=False,
                started_at=started_at,
                attempts=attempt + 1,
                status=response.status,
                error_category="unexpected_payload_type",
            )
            msg = f"Unexpected payload from {path}"
            raise UkrHMCDataError(msg)
        self._record_endpoint_result(
            path,
            available=True,
            started_at=started_at,
            attempts=attempt + 1,
            status=response.status,
        )
        return payload

    async def async_get_stations(self) -> dict[int, UkrHMCStation]:
        """Return the physical station catalog."""
        if self._stations is None or not self._cache_is_fresh("stations"):
            try:
                stations = parse_station_catalog(
                    await self._get_text(STATION_CATALOG_PATH)
                )
            except UkrHMCConnectionError, UkrHMCDataError:
                if self._stations is None:
                    raise
                LOGGER.warning("Using cached station catalog after refresh failure")
            else:
                self._stations = stations
                self._cache_updated_at["stations"] = monotonic()
        return self._stations

    async def async_get_radiation_stations(
        self,
    ) -> dict[int, UkrHMCRadiationStation]:
        """Return the physical radiation station catalog."""
        if self._radiation_stations is None or not self._cache_is_fresh("radiation"):
            try:
                stations = parse_radiation_station_catalog(
                    await self._get_text(RADIATION_STATION_CATALOG_PATH)
                )
            except UkrHMCConnectionError, UkrHMCDataError:
                if self._radiation_stations is None:
                    raise
                LOGGER.warning("Using cached radiation catalog after refresh failure")
            else:
                self._radiation_stations = stations
                self._cache_updated_at["radiation"] = monotonic()
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
        return stations, parse_radiation_observations(payload, self.schema_telemetry)

    async def async_get_hydrology_posts(self) -> dict[int, UkrHMCHydrologyPost]:
        """Return the physical hydrology post catalog."""
        if self._hydrology_posts is None or not self._cache_is_fresh("hydrology"):
            try:
                posts = parse_hydrology_post_catalog(
                    await self._get_text(HYDROLOGY_POST_CATALOG_PATH)
                )
            except UkrHMCConnectionError, UkrHMCDataError:
                if self._hydrology_posts is None:
                    raise
                LOGGER.warning("Using cached hydrology catalog after refresh failure")
            else:
                self._hydrology_posts = posts
                self._cache_updated_at["hydrology"] = monotonic()
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
        return posts, parse_hydrology_observations(payload, self.schema_telemetry)

    async def async_get_snow_stations(self) -> dict[int, UkrHMCSnowStation]:
        """Return the snow and avalanche station catalog."""
        if self._snow_stations is None or not self._cache_is_fresh("snow"):
            try:
                stations = parse_snow_station_catalog(
                    await self._get_text(SNOW_STATION_CATALOG_PATH)
                )
            except UkrHMCConnectionError, UkrHMCDataError:
                if self._snow_stations is None:
                    raise
                LOGGER.warning("Using cached snow catalog after refresh failure")
            else:
                self._snow_stations = stations
                self._cache_updated_at["snow"] = monotonic()
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
        observations = parse_snow_observations(payload, lookups)
        self.schema_telemetry.accepted("snow_observations", len(observations))
        return stations, observations

    async def _async_get_lookups(self) -> UkrHMCLookups:
        """Return cached condition and wind lookup tables."""
        if self._lookups is None or not self._cache_is_fresh("lookups"):
            try:
                icon_script, wind_script = await asyncio.gather(
                    self._get_text(ICON_LOOKUP_PATH),
                    self._get_text(WIND_LOOKUP_PATH),
                )
                lookups = parse_lookups(icon_script, wind_script)
            except UkrHMCConnectionError, UkrHMCDataError:
                if self._lookups is None:
                    raise
                LOGGER.warning("Using cached provider lookups after refresh failure")
            else:
                self._lookups = lookups
                self._cache_updated_at["lookups"] = monotonic()
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

    async def _async_get_location_forecasts(
        self,
        requests: Mapping[str, UkrHMCLocationForecastRequest],
    ) -> dict[str, UkrHMCLocationForecast]:
        """Fetch location forecasts with bounded provider concurrency."""
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_LOCATION_REQUESTS)

        async def get_one(
            request: UkrHMCLocationForecastRequest,
        ) -> UkrHMCLocationForecast:
            async with semaphore:
                return await self._async_get_location_forecast(request)

        raw_results = await asyncio.gather(
            *(get_one(request) for request in requests.values()),
            return_exceptions=True,
        )
        results = {}
        for (request_id, _request), result in zip(
            requests.items(), raw_results, strict=True
        ):
            if isinstance(result, (UkrHMCConnectionError, UkrHMCDataError)):
                LOGGER.warning(
                    "Cannot update location forecast %s: %s", request_id, result
                )
                continue
            if isinstance(result, BaseException):
                raise result
            results[request_id] = result
        if requests and not results:
            msg = "Cannot update any configured location forecast"
            raise UkrHMCConnectionError(msg)
        return results

    async def async_get_data(  # noqa: C901, PLR0912, PLR0915
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
        self.source_availability = {}
        self.schema_telemetry = SchemaTelemetry()
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
        source_errors: list[UkrHMCConnectionError | UkrHMCDataError] = []
        successful_core_sources = 0
        configured_core_sources = sum(
            (
                include_station_data,
                include_radiation_data,
                include_hydrology_data,
                include_snow_data,
                bool(location_requests),
            )
        )
        radiation_task = (
            asyncio.create_task(self.async_get_radiation_data())
            if include_radiation_data
            else None
        )
        hydrology_task = (
            asyncio.create_task(self.async_get_hydrology_data())
            if include_hydrology_data
            else None
        )
        snow_task = (
            asyncio.create_task(self.async_get_snow_data())
            if include_snow_data
            else None
        )
        location_task = (
            asyncio.create_task(self._async_get_location_forecasts(location_requests))
            if location_requests
            else None
        )
        try:
            day_night = await self._get_json(DAY_NIGHT_PATH)
            alert_flags = parse_alert_flags(day_night)
        except (UkrHMCConnectionError, UkrHMCDataError) as exc:
            LOGGER.warning("Cannot update provider attention flags: %s", exc)
            self.source_availability["attention_flags"] = False
            day_night = {}
            alert_flags = {}
        else:
            self.source_availability["attention_flags"] = True
        if include_station_data:
            try:
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
                observations = parse_observations(
                    current, lookups, self.schema_telemetry
                )
                forecasts = parse_forecasts(forecast_payload, lookups)
                night_station_ids = (
                    parse_night_station_ids(day_night) if day_night else frozenset()
                )
            except (UkrHMCConnectionError, UkrHMCDataError) as exc:
                LOGGER.warning("Cannot update weather stations: %s", exc)
                self.source_availability["weather_stations"] = False
                source_errors.append(exc)
            else:
                self.source_availability["weather_stations"] = True
                successful_core_sources += 1
        elif location_requests:
            try:
                stations = await self.async_get_stations()
            except (UkrHMCConnectionError, UkrHMCDataError) as exc:
                LOGGER.warning("Cannot update station catalog: %s", exc)
        if include_station_data or location_requests:
            warning_results = await asyncio.gather(
                self._get_json(REGIONAL_WEATHER_WARNINGS_PATH),
                self._get_json(REGIONAL_FIRE_WARNINGS_PATH),
                self._get_json(REGIONAL_SNOW_WARNINGS_PATH),
                return_exceptions=True,
            )
            warning_parsers = (
                parse_regional_weather_warnings,
                parse_regional_hazard_warnings,
                parse_regional_hazard_warnings,
            )
            parsed_warnings = []
            for path, parser, result in zip(
                (
                    REGIONAL_WEATHER_WARNINGS_PATH,
                    REGIONAL_FIRE_WARNINGS_PATH,
                    REGIONAL_SNOW_WARNINGS_PATH,
                ),
                warning_parsers,
                warning_results,
                strict=True,
            ):
                try:
                    if isinstance(result, (UkrHMCConnectionError, UkrHMCDataError)):
                        raise result
                    if isinstance(result, BaseException):
                        raise result
                    parsed_warnings.append(parser(result))
                except (UkrHMCConnectionError, UkrHMCDataError) as exc:
                    self.endpoint_availability[path] = False
                    LOGGER.warning("Cannot update warning feed %s: %s", path, exc)
                    parsed_warnings.append((None, {}))
            (
                (weather_warnings_updated_at, regional_weather_warnings),
                (fire_warnings_updated_at, regional_fire_warnings),
                (snow_warnings_updated_at, regional_snow_warnings),
            ) = parsed_warnings
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
        if radiation_task is not None:
            try:
                radiation_stations, radiation_observations = await radiation_task
            except (UkrHMCConnectionError, UkrHMCDataError) as exc:
                LOGGER.warning("Cannot update radiation observations: %s", exc)
                self.source_availability["radiation"] = False
                source_errors.append(exc)
            else:
                self.source_availability["radiation"] = True
                successful_core_sources += 1
        if hydrology_task is not None:
            try:
                hydrology_posts, hydrology_observations = await hydrology_task
            except (UkrHMCConnectionError, UkrHMCDataError) as exc:
                LOGGER.warning("Cannot update hydrology observations: %s", exc)
                self.source_availability["hydrology"] = False
                source_errors.append(exc)
            else:
                self.source_availability["hydrology"] = True
                successful_core_sources += 1
        if include_hydrology_data and hydrology_posts:
            hydrology_warning_results = await asyncio.gather(
                self._get_json(HYDROLOGY_WARNINGS_PATH),
                self._get_text(HYDROLOGY_WARNING_LOOKUP_PATH),
                return_exceptions=True,
            )
            try:
                if any(
                    isinstance(result, (UkrHMCConnectionError, UkrHMCDataError))
                    for result in hydrology_warning_results
                ):
                    raise next(
                        result
                        for result in hydrology_warning_results
                        if isinstance(result, (UkrHMCConnectionError, UkrHMCDataError))
                    )
                if any(
                    isinstance(result, BaseException)
                    for result in hydrology_warning_results
                ):
                    raise next(
                        result
                        for result in hydrology_warning_results
                        if isinstance(result, BaseException)
                    )
                (
                    hydrology_warnings_updated_at,
                    regional_hydrology_warnings,
                ) = parse_regional_hydrology_warnings(
                    hydrology_warning_results[0], hydrology_warning_results[1]
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
            except (UkrHMCConnectionError, UkrHMCDataError) as exc:
                self.endpoint_availability[HYDROLOGY_WARNINGS_PATH] = False
                LOGGER.warning("Cannot update hydrology warning feed: %s", exc)
        if snow_task is not None:
            try:
                snow_stations, snow_observations = await snow_task
            except (UkrHMCConnectionError, UkrHMCDataError) as exc:
                LOGGER.warning("Cannot update snow observations: %s", exc)
                self.source_availability["snow"] = False
                source_errors.append(exc)
            else:
                self.source_availability["snow"] = True
                successful_core_sources += 1
        location_results = {}
        if location_task is not None:
            try:
                location_results = await location_task
            except (UkrHMCConnectionError, UkrHMCDataError) as exc:
                LOGGER.warning("Cannot update location forecasts: %s", exc)
                self.source_availability["locations"] = False
                source_errors.append(exc)
            else:
                self.source_availability["locations"] = len(location_results) == len(
                    location_requests
                )
                successful_core_sources += 1
        if configured_core_sources and not successful_core_sources:
            raise source_errors[0]
        return UkrHMCData.create(
            stations=stations,
            observations=observations,
            forecasts=forecasts,
            location_forecasts=location_results,
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
