"""Parsers for UkrHMC JSON and JavaScript data payloads."""

import json
import re
from collections.abc import Mapping
from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

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
    r"const METEO_OBLASTI\s*=\s*(\{.*?\});\s*"
    r"const METEO_STATIONS\s*=\s*(\{.*\});?\s*$",
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
    return None if value is None else float(value)


def _optional_int(record: Mapping[str, Any], key: str) -> int | None:
    """Return an optional integer provider field."""
    value = record.get(key)
    return None if value is None else int(value)


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
    titles = lookups.cloud_titles if int(selector) == 0 else lookups.condition_titles
    index = int(code)
    return titles[index] if 0 <= index < len(titles) else ""


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
            int(record["i"]): UkrHMCStation(
                station_id=int(record["i"]),
                region_id=int(record["o"]),
                region_name=str(regions[str(record["o"])]),
                name=str(record["t"]),
                latitude=float(record["x"]),
                longitude=float(record["y"]),
                altitude=int(record["h"]),
            )
            for record in station_records.values()
        }
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        msg = "Invalid station catalog data"
        raise UkrHMCDataError(msg) from exc


def parse_lookups(icon_script: str, wind_script: str) -> UkrHMCLookups:
    """Parse provider condition and wind lookup tables."""
    condition_titles = _parse_js_assignment(icon_script, "METEO_ICONS_TITLES")
    cloud_titles = _parse_js_assignment(icon_script, "METEO_ICONS_TITLES0")
    wind_records = _parse_js_assignment(wind_script, "METEO_WINDS")

    if not all(
        isinstance(value, list)
        for value in (condition_titles, cloud_titles, wind_records)
    ):
        msg = "Invalid provider lookup data"
        raise UkrHMCDataError(msg)

    try:
        winds = tuple(
            UkrHMCWind(
                code=index,
                abbreviation=record.get("r") if isinstance(record, dict) else None,
                name=record.get("t") if isinstance(record, dict) else None,
            )
            for index, record in enumerate(wind_records)
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
                f"{value['CD']} {int(value['CT']):02d}",
                "%Y-%m-%d %H",
            ).replace(tzinfo=UKRAINE_TIME_ZONE)
            observations[int(station_id)] = UkrHMCObservation(
                observed_at=observed_at,
                temperature=float(value["C_T"]),
                humidity=float(value["C_V"]),
                pressure=float(value["C_A"]),
                wind_speed=float(value["C_W"]),
                wind=_wind(lookups, value["C_D"]),
                condition=_condition_title(lookups, value["IT"], value["TX"]),
                icon_code_day=int(value["IM"]),
                icon_code_night=int(value["IM_N"]),
                phenomenon_code=int(value["C_O"]),
                indicator_code=int(value["C_I"]),
                sunrise=_parse_time(value.get("SR")),
                sunset=_parse_time(value.get("SS")),
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
                        temperature_night=_optional_float(value, "T_N"),
                        temperature_day=_optional_float(value, "T_D"),
                        temperature_night_from=_optional_float(value, "T_IN_F"),
                        temperature_night_to=_optional_float(value, "T_IN_T"),
                        temperature_day_from=_optional_float(value, "T_ID_F"),
                        temperature_day_to=_optional_float(value, "T_ID_T"),
                        icon_code_day=_optional_int(value, "I_D"),
                        icon_code_night=_optional_int(value, "I_N"),
                        cloudiness=str(value.get("HM", "")),
                        cloudiness_en=str(value.get("HM_EN", "")),
                        precipitation_day=str(value.get("O_D", "")),
                        precipitation_day_en=str(value.get("O_D_EN", "")),
                        precipitation_night=str(value.get("O_N", "")),
                        precipitation_night_en=str(value.get("O_N_EN", "")),
                        wind_day=_wind(lookups, value.get("WD_N", 0)),
                        wind_speed_day=str(value.get("WD_S", "")),
                        wind_night=_wind(lookups, value.get("WN_N", 0)),
                        wind_speed_night=str(value.get("WN_S", "")),
                        sunrise=_parse_time(value.get("SR")),
                        sunset=_parse_time(value.get("SS")),
                        provider_code=_optional_int(value, "MP"),
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
    day_night = payload.get("dn")
    if not isinstance(day_night, Mapping):
        msg = "Invalid day/night data"
        raise UkrHMCDataError(msg)
    try:
        return frozenset(
            int(station_id)
            for station_id, is_night in day_night.items()
            if int(is_night) == 1
        )
    except (TypeError, ValueError) as exc:
        msg = "Invalid day/night data"
        raise UkrHMCDataError(msg) from exc
