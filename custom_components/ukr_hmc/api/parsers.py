"""Parsers for UkrHMC JSON and JavaScript data payloads."""

import json
import re
from collections.abc import Mapping
from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from .const import (
    ALERT_FLAG_KEYS,
    CLOUD_CONDITION_SELECTOR,
    CLOUD_TITLES_VARIABLE,
    CONDITION_TITLES_VARIABLE,
    DAY_NIGHT_STATIONS_KEY,
    DEFAULT_WIND_DIRECTION_CODE,
    FORECAST_CLOUDINESS_ENGLISH_KEY,
    FORECAST_CLOUDINESS_KEY,
    FORECAST_DAY_ICON_KEY,
    FORECAST_DAY_PRECIPITATION_ENGLISH_KEY,
    FORECAST_DAY_PRECIPITATION_KEY,
    FORECAST_DAY_TEMPERATURE_FROM_KEY,
    FORECAST_DAY_TEMPERATURE_KEY,
    FORECAST_DAY_TEMPERATURE_TO_KEY,
    FORECAST_DAY_WIND_DIRECTION_KEY,
    FORECAST_DAY_WIND_SPEED_KEY,
    FORECAST_NIGHT_ICON_KEY,
    FORECAST_NIGHT_PRECIPITATION_ENGLISH_KEY,
    FORECAST_NIGHT_PRECIPITATION_KEY,
    FORECAST_NIGHT_TEMPERATURE_FROM_KEY,
    FORECAST_NIGHT_TEMPERATURE_KEY,
    FORECAST_NIGHT_TEMPERATURE_TO_KEY,
    FORECAST_NIGHT_WIND_DIRECTION_KEY,
    FORECAST_NIGHT_WIND_SPEED_KEY,
    FORECAST_PROVIDER_CODE_KEY,
    HOURLY_CONDITION_KEY,
    HOURLY_DEW_POINT_KEY,
    HOURLY_FORECASTS_KEY,
    HOURLY_HUMIDITY_KEY,
    HOURLY_IS_NIGHT_KEY,
    HOURLY_MAXIMUM_TEMPERATURE_KEY,
    HOURLY_METADATA_KEY,
    HOURLY_PRECIPITATION_KEY,
    HOURLY_PRESSURE_KEY,
    HOURLY_TEMPERATURE_KEY,
    HOURLY_TIME_KEY,
    HOURLY_WEATHER_KEY,
    HOURLY_WIND_COMPASS_KEY,
    HOURLY_WIND_DIRECTION_KEY,
    HOURLY_WIND_GUST_KEY,
    HOURLY_WIND_SPEED_KEY,
    HYDROLOGY_DATE_KEY,
    HYDROLOGY_LEVEL_CLASS_KEY,
    HYDROLOGY_OBSERVATION_HOUR,
    HYDROLOGY_POST_LATITUDE_KEY,
    HYDROLOGY_POST_LONGITUDE_KEY,
    HYDROLOGY_POST_NAME_KEY,
    HYDROLOGY_POST_RIVER_KEY,
    HYDROLOGY_POSTS_VARIABLE,
    HYDROLOGY_WATER_LEVEL_ALTITUDE_KEY,
    HYDROLOGY_WATER_LEVEL_CHANGE_KEY,
    HYDROLOGY_WATER_LEVEL_KEY,
    HYDROLOGY_WATER_TEMPERATURE_KEY,
    LOCATION_DAY_FORECAST_HOUR,
    LOCATION_FORECAST_RECORDS_KEY,
    LOCATION_NIGHT_FORECAST_HOUR,
    LOCATION_POINT_COMPONENT_COUNT,
    LOCATION_POINT_KEY,
    MISSING_VALUE_MARKERS,
    NIGHT_VALUE,
    OBSERVATION_CONDITION_CODE_KEY,
    OBSERVATION_CONDITION_SELECTOR_KEY,
    OBSERVATION_DATE_KEY,
    OBSERVATION_DAY_ICON_KEY,
    OBSERVATION_HOUR_KEY,
    OBSERVATION_HUMIDITY_KEY,
    OBSERVATION_INDICATOR_CODE_KEY,
    OBSERVATION_NIGHT_ICON_KEY,
    OBSERVATION_PHENOMENON_CODE_KEY,
    OBSERVATION_PRESSURE_KEY,
    OBSERVATION_TEMPERATURE_KEY,
    OBSERVATION_WIND_DIRECTION_KEY,
    OBSERVATION_WIND_SPEED_KEY,
    RADIATION_DATE_KEY,
    RADIATION_DOSE_RATE_KEY,
    RADIATION_EXPOSURE_DOSE_RATE_KEY,
    RADIATION_STATION_ALTITUDE_KEY,
    RADIATION_STATION_LATITUDE_KEY,
    RADIATION_STATION_LONGITUDE_KEY,
    RADIATION_STATION_NAME_KEY,
    RADIATION_STATIONS_VARIABLE,
    RADIATION_TIME_KEY,
    REGIONS_VARIABLE,
    STATION_ALTITUDE_KEY,
    STATION_ID_KEY,
    STATION_LATITUDE_KEY,
    STATION_LONGITUDE_KEY,
    STATION_NAME_KEY,
    STATION_REGION_ID_KEY,
    STATIONS_VARIABLE,
    SUNRISE_KEY,
    SUNSET_KEY,
    WIND_ABBREVIATION_KEY,
    WIND_NAME_KEY,
    WINDS_VARIABLE,
)
from .errors import UkrHMCDataError
from .models import (
    UkrHMCForecastDay,
    UkrHMCHourlyForecast,
    UkrHMCHydrologyObservation,
    UkrHMCHydrologyPost,
    UkrHMCLocationForecastDay,
    UkrHMCLookups,
    UkrHMCObservation,
    UkrHMCRadiationObservation,
    UkrHMCRadiationStation,
    UkrHMCStation,
    UkrHMCWind,
)

UKRAINE_TIME_ZONE = ZoneInfo("Europe/Kyiv")
STATION_CATALOG_PATTERN = re.compile(
    rf"const {REGIONS_VARIABLE}\s*=\s*(\{{.*?\}});\s*"
    rf"const {STATIONS_VARIABLE}\s*=\s*(\{{.*\}});?\s*$",
    re.DOTALL,
)


def _parse_js_assignment(script: str, variable: str) -> Any:
    """Parse one JSON-compatible JavaScript const assignment."""
    match = re.search(
        rf"const\s+{re.escape(variable)}\s*=\s*(.*?);\s*(?:const|\Z)",
        script,
        re.DOTALL,
    )
    if match is None:
        msg = f"Missing {variable} assignment"
        raise UkrHMCDataError(msg)

    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        msg = f"Invalid {variable} assignment"
        raise UkrHMCDataError(msg) from exc


def _parse_time(value: object) -> time | None:
    """Parse a provider time in HMM, HHMM, or H:MM format."""
    if value in (None, ""):
        return None

    digits = str(value).replace(":", "").zfill(4)
    try:
        return time(hour=int(digits[:2]), minute=int(digits[2:]))
    except (ValueError, TypeError) as exc:
        msg = f"Invalid provider time: {value}"
        raise UkrHMCDataError(msg) from exc


def _optional_float(record: Mapping[str, Any], key: str) -> float | None:
    """Return an optional numeric provider field."""
    value = record.get(key)
    if value in MISSING_VALUE_MARKERS:
        return None
    return float(value)


def _optional_int(record: Mapping[str, Any], key: str) -> int | None:
    """Return an optional integer provider field."""
    value = record.get(key)
    if value in MISSING_VALUE_MARKERS:
        return None
    return int(value)


def _optional_str(record: Mapping[str, Any], key: str) -> str | None:
    """Return an optional string provider field."""
    value = record.get(key)
    if value in MISSING_VALUE_MARKERS:
        return None
    return str(value)


def _wind(lookups: UkrHMCLookups, code: object) -> UkrHMCWind:
    """Return a provider wind lookup value."""
    index = int(code)
    if 0 <= index < len(lookups.winds):
        return lookups.winds[index]
    return UkrHMCWind(code=index, abbreviation=None, name=None)


def _condition_title(
    lookups: UkrHMCLookups,
    selector: object,
    code: object,
) -> str:
    """Return a provider condition title."""
    titles = lookups.condition_titles
    if int(selector) == CLOUD_CONDITION_SELECTOR:
        titles = lookups.cloud_titles
    index = int(code)
    if 0 <= index < len(titles):
        return titles[index]
    return ""


def _parse_wind(index: int, record: object) -> UkrHMCWind:
    """Parse one provider wind lookup record."""
    if not isinstance(record, Mapping):
        return UkrHMCWind(code=index, abbreviation=None, name=None)
    return UkrHMCWind(
        code=index,
        abbreviation=record.get(WIND_ABBREVIATION_KEY),
        name=record.get(WIND_NAME_KEY),
    )


def parse_station_catalog(script: str) -> dict[int, UkrHMCStation]:
    """Parse physical stations from the provider JavaScript catalog."""
    match = STATION_CATALOG_PATTERN.fullmatch(script.strip())
    if match is None:
        msg = "Invalid station catalog"
        raise UkrHMCDataError(msg)

    try:
        regions = json.loads(match.group(1))
        station_records = json.loads(match.group(2))
        return {
            int(record[STATION_ID_KEY]): UkrHMCStation(
                station_id=int(record[STATION_ID_KEY]),
                region_id=int(record[STATION_REGION_ID_KEY]),
                region_name=str(regions[str(record[STATION_REGION_ID_KEY])]),
                name=str(record[STATION_NAME_KEY]),
                latitude=float(record[STATION_LATITUDE_KEY]),
                longitude=float(record[STATION_LONGITUDE_KEY]),
                altitude=int(record[STATION_ALTITUDE_KEY]),
            )
            for record in station_records.values()
        }
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        msg = "Invalid station catalog data"
        raise UkrHMCDataError(msg) from exc


def parse_radiation_station_catalog(
    script: str,
) -> dict[int, UkrHMCRadiationStation]:
    """Parse physical radiation stations from provider JavaScript."""
    records = _parse_js_assignment(script, RADIATION_STATIONS_VARIABLE)
    if not isinstance(records, Mapping):
        msg = "Invalid radiation station catalog"
        raise UkrHMCDataError(msg)

    try:
        return {
            int(station_id): UkrHMCRadiationStation(
                station_id=int(station_id),
                name=str(record[RADIATION_STATION_NAME_KEY]),
                latitude=float(record[RADIATION_STATION_LATITUDE_KEY]),
                longitude=float(record[RADIATION_STATION_LONGITUDE_KEY]),
                altitude=int(record[RADIATION_STATION_ALTITUDE_KEY]),
            )
            for station_id, record in records.items()
            if isinstance(record, Mapping)
        }
    except (KeyError, TypeError, ValueError) as exc:
        msg = "Invalid radiation station catalog data"
        raise UkrHMCDataError(msg) from exc


def parse_radiation_observations(
    payload: Mapping[str, Any],
) -> dict[int, UkrHMCRadiationObservation]:
    """Parse current radiation observations."""
    observations: dict[int, UkrHMCRadiationObservation] = {}
    try:
        for station_id, record in payload.items():
            if station_id == "0" or not isinstance(record, Mapping):
                continue
            exposure_dose_rate = float(record[RADIATION_EXPOSURE_DOSE_RATE_KEY])
            dose_rate = float(record[RADIATION_DOSE_RATE_KEY])
            if exposure_dose_rate < 0 or dose_rate < 0:
                continue
            observations[int(station_id)] = UkrHMCRadiationObservation(
                observed_at=datetime.strptime(
                    f"{record[RADIATION_DATE_KEY]} {record[RADIATION_TIME_KEY]}",
                    "%d.%m.%Y %H:%M:%S",
                ).replace(tzinfo=UKRAINE_TIME_ZONE),
                exposure_dose_rate=exposure_dose_rate,
                dose_rate=dose_rate,
            )
    except (KeyError, TypeError, ValueError) as exc:
        msg = "Invalid radiation observation data"
        raise UkrHMCDataError(msg) from exc
    return observations


def parse_hydrology_post_catalog(script: str) -> dict[int, UkrHMCHydrologyPost]:
    """Parse physical hydrology posts from provider JavaScript."""
    records = _parse_js_assignment(script, HYDROLOGY_POSTS_VARIABLE)
    if not isinstance(records, Mapping):
        msg = "Invalid hydrology post catalog"
        raise UkrHMCDataError(msg)

    try:
        return {
            int(post_id): UkrHMCHydrologyPost(
                post_id=int(post_id),
                river=str(record[HYDROLOGY_POST_RIVER_KEY]),
                name=str(record[HYDROLOGY_POST_NAME_KEY]),
                latitude=float(record[HYDROLOGY_POST_LATITUDE_KEY]),
                longitude=float(record[HYDROLOGY_POST_LONGITUDE_KEY]),
            )
            for post_id, record in records.items()
            if isinstance(record, Mapping)
        }
    except (KeyError, TypeError, ValueError) as exc:
        msg = "Invalid hydrology post catalog data"
        raise UkrHMCDataError(msg) from exc


def parse_hydrology_observations(
    payload: Mapping[str, Any],
) -> dict[int, UkrHMCHydrologyObservation]:
    """Parse current daily hydrology observations."""
    observations: dict[int, UkrHMCHydrologyObservation] = {}
    try:
        for post_id, record in payload.items():
            if post_id == "0" or not isinstance(record, Mapping):
                continue
            water_level_altitude = float(record[HYDROLOGY_WATER_LEVEL_ALTITUDE_KEY])
            if water_level_altitude == 0:
                continue
            observations[int(post_id)] = UkrHMCHydrologyObservation(
                observed_at=datetime.strptime(
                    str(record[HYDROLOGY_DATE_KEY]),
                    "%d.%m.%Y",
                ).replace(
                    hour=HYDROLOGY_OBSERVATION_HOUR,
                    tzinfo=UKRAINE_TIME_ZONE,
                ),
                water_level=float(record[HYDROLOGY_WATER_LEVEL_KEY]),
                water_level_altitude=water_level_altitude,
                water_level_change=float(record[HYDROLOGY_WATER_LEVEL_CHANGE_KEY]),
                water_temperature=float(record[HYDROLOGY_WATER_TEMPERATURE_KEY]),
                level_class=int(record[HYDROLOGY_LEVEL_CLASS_KEY]),
            )
    except (KeyError, TypeError, ValueError) as exc:
        msg = "Invalid hydrology observation data"
        raise UkrHMCDataError(msg) from exc
    return observations


def parse_lookups(icon_script: str, wind_script: str) -> UkrHMCLookups:
    """Parse provider condition and wind lookup tables."""
    condition_titles = _parse_js_assignment(icon_script, CONDITION_TITLES_VARIABLE)
    cloud_titles = _parse_js_assignment(icon_script, CLOUD_TITLES_VARIABLE)
    wind_records = _parse_js_assignment(wind_script, WINDS_VARIABLE)

    if not all(
        isinstance(value, list)
        for value in (condition_titles, cloud_titles, wind_records)
    ):
        msg = "Invalid provider lookup data"
        raise UkrHMCDataError(msg)

    try:
        winds = tuple(
            _parse_wind(index, record) for index, record in enumerate(wind_records)
        )
        return UkrHMCLookups(
            condition_titles=tuple(str(value) for value in condition_titles),
            cloud_titles=tuple(str(value) for value in cloud_titles),
            winds=winds,
        )
    except (TypeError, ValueError) as exc:
        msg = "Invalid provider lookup data"
        raise UkrHMCDataError(msg) from exc


def parse_observations(
    payload: Mapping[str, Any],
    lookups: UkrHMCLookups,
) -> dict[int, UkrHMCObservation]:
    """Parse latest observations for all stations."""
    observations: dict[int, UkrHMCObservation] = {}
    try:
        for station_id, value in payload.items():
            if not isinstance(value, Mapping):
                continue
            observed_at = datetime.strptime(
                f"{value[OBSERVATION_DATE_KEY]} {int(value[OBSERVATION_HOUR_KEY]):02d}",
                "%Y-%m-%d %H",
            ).replace(tzinfo=UKRAINE_TIME_ZONE)
            observations[int(station_id)] = UkrHMCObservation(
                observed_at=observed_at,
                temperature=float(value[OBSERVATION_TEMPERATURE_KEY]),
                humidity=float(value[OBSERVATION_HUMIDITY_KEY]),
                pressure=float(value[OBSERVATION_PRESSURE_KEY]),
                wind_speed=float(value[OBSERVATION_WIND_SPEED_KEY]),
                wind=_wind(lookups, value[OBSERVATION_WIND_DIRECTION_KEY]),
                condition=_condition_title(
                    lookups,
                    value[OBSERVATION_CONDITION_SELECTOR_KEY],
                    value[OBSERVATION_CONDITION_CODE_KEY],
                ),
                icon_code_day=int(value[OBSERVATION_DAY_ICON_KEY]),
                icon_code_night=int(value[OBSERVATION_NIGHT_ICON_KEY]),
                phenomenon_code=int(value[OBSERVATION_PHENOMENON_CODE_KEY]),
                indicator_code=int(value[OBSERVATION_INDICATOR_CODE_KEY]),
                sunrise=_parse_time(value.get(SUNRISE_KEY)),
                sunset=_parse_time(value.get(SUNSET_KEY)),
            )
    except (KeyError, TypeError, ValueError) as exc:
        msg = "Invalid current observation data"
        raise UkrHMCDataError(msg) from exc
    return observations


def parse_forecasts(
    payload: Mapping[str, Any],
    lookups: UkrHMCLookups,
) -> dict[int, tuple[UkrHMCForecastDay, ...]]:
    """Parse provider daily records, preserving day and night fields."""
    forecasts: dict[int, tuple[UkrHMCForecastDay, ...]] = {}
    try:
        for station_id, station_values in payload.items():
            if not isinstance(station_values, Mapping):
                continue
            days = []
            for forecast_date, value in station_values.items():
                if not isinstance(value, Mapping):
                    continue
                days.append(
                    UkrHMCForecastDay(
                        date=date.fromisoformat(str(forecast_date)),
                        temperature_night=_optional_float(
                            value, FORECAST_NIGHT_TEMPERATURE_KEY
                        ),
                        temperature_day=_optional_float(
                            value, FORECAST_DAY_TEMPERATURE_KEY
                        ),
                        temperature_night_from=_optional_float(
                            value, FORECAST_NIGHT_TEMPERATURE_FROM_KEY
                        ),
                        temperature_night_to=_optional_float(
                            value, FORECAST_NIGHT_TEMPERATURE_TO_KEY
                        ),
                        temperature_day_from=_optional_float(
                            value, FORECAST_DAY_TEMPERATURE_FROM_KEY
                        ),
                        temperature_day_to=_optional_float(
                            value, FORECAST_DAY_TEMPERATURE_TO_KEY
                        ),
                        icon_code_day=_optional_int(value, FORECAST_DAY_ICON_KEY),
                        icon_code_night=_optional_int(value, FORECAST_NIGHT_ICON_KEY),
                        cloudiness=str(value.get(FORECAST_CLOUDINESS_KEY, "")),
                        cloudiness_en=str(
                            value.get(FORECAST_CLOUDINESS_ENGLISH_KEY, "")
                        ),
                        precipitation_day=str(
                            value.get(FORECAST_DAY_PRECIPITATION_KEY, "")
                        ),
                        precipitation_day_en=str(
                            value.get(FORECAST_DAY_PRECIPITATION_ENGLISH_KEY, "")
                        ),
                        precipitation_night=str(
                            value.get(FORECAST_NIGHT_PRECIPITATION_KEY, "")
                        ),
                        precipitation_night_en=str(
                            value.get(FORECAST_NIGHT_PRECIPITATION_ENGLISH_KEY, "")
                        ),
                        wind_day=_wind(
                            lookups,
                            value.get(
                                FORECAST_DAY_WIND_DIRECTION_KEY,
                                DEFAULT_WIND_DIRECTION_CODE,
                            ),
                        ),
                        wind_speed_day=str(value.get(FORECAST_DAY_WIND_SPEED_KEY, "")),
                        wind_night=_wind(
                            lookups,
                            value.get(
                                FORECAST_NIGHT_WIND_DIRECTION_KEY,
                                DEFAULT_WIND_DIRECTION_CODE,
                            ),
                        ),
                        wind_speed_night=str(
                            value.get(FORECAST_NIGHT_WIND_SPEED_KEY, "")
                        ),
                        sunrise=_parse_time(value.get(SUNRISE_KEY)),
                        sunset=_parse_time(value.get(SUNSET_KEY)),
                        provider_code=_optional_int(value, FORECAST_PROVIDER_CODE_KEY),
                    )
                )
            forecasts[int(station_id)] = tuple(
                sorted(days, key=lambda forecast: forecast.date)
            )
    except (TypeError, ValueError) as exc:
        msg = "Invalid forecast data"
        raise UkrHMCDataError(msg) from exc
    return forecasts


def _parse_hourly_forecast(
    record: Mapping[str, Any],
) -> UkrHMCHourlyForecast | None:
    """Parse one hourly location forecast record."""
    forecast_time = record.get(HOURLY_TIME_KEY)
    temperature = record.get(HOURLY_TEMPERATURE_KEY)
    if forecast_time is None or temperature is None:
        return None
    return UkrHMCHourlyForecast(
        forecast_at=datetime.strptime(
            str(forecast_time),
            "%Y%m%dT%H%M%S",
        ).replace(tzinfo=UKRAINE_TIME_ZONE),
        temperature=float(temperature),
        precipitation=_optional_float(record, HOURLY_PRECIPITATION_KEY),
        condition=str(record.get(HOURLY_CONDITION_KEY) or ""),
        weather=str(record.get(HOURLY_WEATHER_KEY) or ""),
        is_night=bool(int(record.get(HOURLY_IS_NIGHT_KEY, 0))),
        wind_compass=_optional_str(record, HOURLY_WIND_COMPASS_KEY),
        wind_speed=_optional_float(record, HOURLY_WIND_SPEED_KEY),
        wind_gust=_optional_float(record, HOURLY_WIND_GUST_KEY),
        humidity=_optional_float(record, HOURLY_HUMIDITY_KEY),
        pressure=_optional_float(record, HOURLY_PRESSURE_KEY),
        wind_direction=_optional_float(record, HOURLY_WIND_DIRECTION_KEY),
        dew_point=_optional_float(record, HOURLY_DEW_POINT_KEY),
    )


def parse_hourly_forecasts(
    payload: Mapping[str, Any],
) -> tuple[UkrHMCHourlyForecast, ...]:
    """Parse upcoming hourly location forecast records."""
    records = payload.get(HOURLY_FORECASTS_KEY)
    if not isinstance(records, list):
        msg = "Invalid hourly forecast data"
        raise UkrHMCDataError(msg)

    forecasts = []
    try:
        for record in records:
            if not isinstance(record, Mapping):
                continue
            forecast = _parse_hourly_forecast(record)
            if forecast is not None:
                forecasts.append(forecast)
    except (TypeError, ValueError) as exc:
        msg = "Invalid hourly forecast data"
        raise UkrHMCDataError(msg) from exc
    return tuple(sorted(forecasts, key=lambda forecast: forecast.forecast_at))


def parse_current_location_forecast(
    payload: Mapping[str, Any],
    now: datetime,
) -> UkrHMCHourlyForecast | None:
    """Parse the location forecast record for the current provider hour."""
    records = payload.get(LOCATION_FORECAST_RECORDS_KEY)
    if not isinstance(records, list):
        msg = "Invalid current hourly forecast data"
        raise UkrHMCDataError(msg)

    current_hour = now.astimezone(UKRAINE_TIME_ZONE).replace(
        minute=0,
        second=0,
        microsecond=0,
    )
    try:
        for record in records:
            if not isinstance(record, Mapping):
                continue
            forecast = _parse_hourly_forecast(record)
            if forecast is not None and forecast.forecast_at == current_hour:
                return forecast
    except (TypeError, ValueError) as exc:
        msg = "Invalid current hourly forecast data"
        raise UkrHMCDataError(msg) from exc
    return None


def parse_location_daily_forecasts(
    payload: Mapping[str, Any],
) -> tuple[UkrHMCLocationForecastDay, ...]:
    """Parse the exact 03:00 and 15:00 values used by provider daily cards."""
    records = payload.get(LOCATION_FORECAST_RECORDS_KEY)
    if not isinstance(records, list):
        msg = "Invalid daily forecast data for location"
        raise UkrHMCDataError(msg)

    records_by_date: dict[date, dict[int, Mapping[str, Any]]] = {}
    try:
        for record in records:
            if not isinstance(record, Mapping):
                continue
            forecast_time = record.get(HOURLY_TIME_KEY)
            if forecast_time is None:
                continue
            forecast_at = datetime.strptime(
                str(forecast_time),
                "%Y%m%dT%H%M%S",
            ).replace(tzinfo=UKRAINE_TIME_ZONE)
            if forecast_at.minute != 0 or forecast_at.second != 0:
                continue
            if forecast_at.hour not in (
                LOCATION_NIGHT_FORECAST_HOUR,
                LOCATION_DAY_FORECAST_HOUR,
            ):
                continue
            records_by_date.setdefault(forecast_at.date(), {})[forecast_at.hour] = (
                record
            )

        forecasts = []
        for forecast_date, periods in records_by_date.items():
            night = periods.get(LOCATION_NIGHT_FORECAST_HOUR)
            day = periods.get(LOCATION_DAY_FORECAST_HOUR)
            if night is None or day is None:
                continue
            temperature_night = _optional_float(night, HOURLY_MAXIMUM_TEMPERATURE_KEY)
            temperature_day = _optional_float(day, HOURLY_MAXIMUM_TEMPERATURE_KEY)
            if temperature_night is None or temperature_day is None:
                continue
            forecasts.append(
                UkrHMCLocationForecastDay(
                    date=forecast_date,
                    temperature_night=temperature_night,
                    temperature_day=temperature_day,
                    condition_night=str(night.get(HOURLY_CONDITION_KEY) or ""),
                    condition_day=str(day.get(HOURLY_CONDITION_KEY) or ""),
                    weather_night=str(night.get(HOURLY_WEATHER_KEY) or ""),
                    weather_day=str(day.get(HOURLY_WEATHER_KEY) or ""),
                )
            )
    except (TypeError, ValueError) as exc:
        msg = "Invalid daily forecast data for location"
        raise UkrHMCDataError(msg) from exc
    return tuple(sorted(forecasts, key=lambda forecast: forecast.date))


def parse_location_forecast_point(
    payload: Mapping[str, Any],
) -> tuple[float, float]:
    """Parse the location point echoed by the hourly forecast endpoint."""
    metadata = payload.get(HOURLY_METADATA_KEY)
    if not isinstance(metadata, Mapping):
        msg = "Invalid forecast location"
        raise UkrHMCDataError(msg)
    point = metadata.get(LOCATION_POINT_KEY)
    if not isinstance(point, str):
        msg = "Invalid forecast location"
        raise UkrHMCDataError(msg)

    parts = point.split(",")
    if len(parts) != LOCATION_POINT_COMPONENT_COUNT:
        msg = "Invalid forecast location"
        raise UkrHMCDataError(msg)
    try:
        return float(parts[0]), float(parts[1])
    except ValueError as exc:
        msg = "Invalid forecast location"
        raise UkrHMCDataError(msg) from exc


def parse_night_station_ids(payload: Mapping[str, Any]) -> frozenset[int]:
    """Parse station IDs that the provider marks as nighttime."""
    day_night = payload.get(DAY_NIGHT_STATIONS_KEY)
    if not isinstance(day_night, Mapping):
        msg = "Invalid day/night data"
        raise UkrHMCDataError(msg)
    try:
        return frozenset(
            int(station_id)
            for station_id, is_night in day_night.items()
            if int(is_night) == NIGHT_VALUE
        )
    except (TypeError, ValueError) as exc:
        msg = "Invalid day/night data"
        raise UkrHMCDataError(msg) from exc


def parse_alert_flags(payload: Mapping[str, Any]) -> dict[str, bool]:
    """Parse provider-global attention flags."""
    try:
        return {key: bool(int(payload[key])) for key in ALERT_FLAG_KEYS}
    except (KeyError, TypeError, ValueError) as exc:
        msg = "Invalid provider alert data"
        raise UkrHMCDataError(msg) from exc
