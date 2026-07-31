"""Parsers for UkrHMC JSON and JavaScript data payloads."""

import json
import re
from collections.abc import Mapping
from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from .const import (
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
    UkrHMCLookups,
    UkrHMCObservation,
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
    if value is None:
        return None
    return float(value)


def _optional_int(record: Mapping[str, Any], key: str) -> int | None:
    """Return an optional integer provider field."""
    value = record.get(key)
    if value is None:
        return None
    return int(value)


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
