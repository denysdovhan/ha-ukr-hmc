"""Tests for the isolated UkrHMC API package."""

from dataclasses import replace
from datetime import datetime
from types import MappingProxyType
from unittest.mock import AsyncMock, Mock
from zoneinfo import ZoneInfo

import pytest

from custom_components.ukr_hmc.api import UkrHMCClient, UkrHMCDataError
from custom_components.ukr_hmc.api.const import (
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
    SNOW_DATA_PATH,
    SNOW_STATION_CATALOG_PATH,
)
from custom_components.ukr_hmc.api.parsers import (
    parse_alert_flags,
    parse_current_location_forecast,
    parse_forecasts,
    parse_hourly_forecasts,
    parse_hydrology_observations,
    parse_hydrology_post_catalog,
    parse_location_daily_forecasts,
    parse_lookups,
    parse_night_station_ids,
    parse_observations,
    parse_radiation_observations,
    parse_radiation_station_catalog,
    parse_region_geometry,
    parse_regional_hydrology_warnings,
    parse_regional_weather_warnings,
    parse_snow_observations,
    parse_snow_station_catalog,
    parse_station_catalog,
    point_in_region,
)

from .fixtures import (
    DATA,
    HYDROLOGY_OBSERVATION,
    HYDROLOGY_POST,
    LOCATION_FORECAST_REQUEST,
    RADIATION_OBSERVATION,
    RADIATION_STATION,
    SNOW_OBSERVATION,
    SNOW_STATION,
    STATION,
)

ICON_SCRIPT = (
    'const METEO_ICONS_TITLES = ["", "Дощ"]; '
    'const METEO_ICONS_TITLES0 = ["Ясно", "Малохмарно"];'
)
WIND_SCRIPT = 'const METEO_WINDS = [[], {"r": "NNE", "t": "Північно-Східний"}];'
RADIATION_STATION_SCRIPT = (
    'const RADIO_POSTS = {"33345": {"P": "Київ", '
    '"X": 50.391792297363, "Y": 30.53563117981, "H": 167}};'
)
RADIATION_PAYLOAD = {
    "0": "06.08.2026",
    "33345": {
        "CD": "06.08.2026",
        "CH": "12:00:00",
        "VR": 11,
        "VZ": 96,
    },
}
HYDROLOGY_POST_SCRIPT = (
    'const HYDRO_POSTS = {"80986": {"R": "Дніпро", "P": "Київ", '
    '"X": 50.442147, "Y": 30.569539}};'
)
SNOW_STATION_SCRIPT = 'const ATTNS_STANTIONS = {"9":{"G":[48.6674,23.198],"T":"Плай"}};'
SNOW_PAYLOAD = {
    "0": "20.04.2026",
    "9": {
        "ST": 9,
        "TT": 4,
        "SN": 11,
        "SD": -3,
        "WD": 1,
        "WS": 4,
        "VL": 97,
        "HT": "Хмарно",
        "OT": "Туман",
    },
}
HYDROLOGY_PAYLOAD = {
    "0": "06.08.2026",
    "80986": {
        "PD": "06.08.2026",
        "FR": 444,
        "FR_BS": 91.44,
        "C_FR": -0.01,
        "TW": 25,
        "L": 1,
    },
}
ALERT_PAYLOAD = {
    "dn": {},
    "attns_meteo": 1,
    "attns_hydro": 0,
    "attns_snigo": 0,
    "attns_radio": 0,
    "attns_fire": 1,
}
WEATHER_WARNING_PAYLOAD = {
    "UPD": "04.09.2026, 13:13",
    "OBJ": [
        [],
        [
            {
                "R": 1,
                "L": 1,
                "U": "/_/geo/ua/1.json",
                "A": [
                    {
                        "T": 8,
                        "P": "05.09 09:00 &mdash; 21:00",
                        "D": "пориви 15-20 м/с",
                    }
                ],
            }
        ],
        [],
    ],
}
REGION_GEOMETRY_PAYLOAD = {
    "type": "GeometryCollection",
    "geometries": [
        {
            "type": "Polygon",
            "coordinates": [
                [
                    [30.0, 50.0],
                    [31.0, 50.0],
                    [31.0, 51.0],
                    [30.0, 51.0],
                    [30.0, 50.0],
                ]
            ],
        }
    ],
}
REGION_FEATURE_COLLECTION_PAYLOAD = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {},
            "geometry": REGION_GEOMETRY_PAYLOAD["geometries"][0],
        }
    ],
}


def test_parse_station_catalog() -> None:
    script = (
        'const METEO_OBLASTI = {"1": "Київська"}; '
        'const METEO_STATIONS = {"0": '
        '{"i": 33345, "o": 1, "h": 167, "t": "Київ", '
        '"x": "50.391792297363", "y": "30.53563117981"}};'
    )

    stations = parse_station_catalog(script)

    assert stations[33345] == STATION


def test_parse_radiation_catalog_and_observations() -> None:
    stations = parse_radiation_station_catalog(RADIATION_STATION_SCRIPT)
    observations = parse_radiation_observations(
        {
            **RADIATION_PAYLOAD,
            "33347": {
                "CD": "06.08.2026",
                "CH": "12:00:00",
                "VR": -1,
                "VZ": -1,
            },
        }
    )

    assert stations == {RADIATION_STATION.station_id: RADIATION_STATION}
    assert observations == {RADIATION_STATION.station_id: RADIATION_OBSERVATION}


async def test_client_gets_radiation_catalog_and_observations() -> None:
    client = UkrHMCClient(Mock())
    client._get_text = AsyncMock(return_value=RADIATION_STATION_SCRIPT)
    client._get_json = AsyncMock(return_value=RADIATION_PAYLOAD)

    stations, observations = await client.async_get_radiation_data()

    assert stations[RADIATION_STATION.station_id] == RADIATION_STATION
    assert observations[RADIATION_STATION.station_id] == RADIATION_OBSERVATION
    client._get_text.assert_awaited_once_with(RADIATION_STATION_CATALOG_PATH)
    client._get_json.assert_awaited_once_with(RADIATION_DATA_PATH)


def test_parse_hydrology_catalog_and_observations() -> None:
    posts = parse_hydrology_post_catalog(HYDROLOGY_POST_SCRIPT)
    observations = parse_hydrology_observations(
        {
            **HYDROLOGY_PAYLOAD,
            "79043": {
                "PD": "06.08.2026",
                "FR": 0,
                "FR_BS": 0,
                "C_FR": 0,
                "TW": 0,
                "L": 0,
            },
        }
    )

    assert posts == {HYDROLOGY_POST.post_id: HYDROLOGY_POST}
    assert observations == {HYDROLOGY_POST.post_id: HYDROLOGY_OBSERVATION}

    zero_temperature = parse_hydrology_observations(
        {
            "79043": {
                "PD": "06.08.2026",
                "FR": -5,
                "FR_BS": 1,
                "C_FR": 0,
                "TW": 0,
                "L": 0,
            }
        }
    )
    assert zero_temperature[79043].water_temperature == 0


async def test_client_gets_hydrology_catalog_and_observations() -> None:
    client = UkrHMCClient(Mock())
    client._get_text = AsyncMock(return_value=HYDROLOGY_POST_SCRIPT)
    client._get_json = AsyncMock(return_value=HYDROLOGY_PAYLOAD)

    posts, observations = await client.async_get_hydrology_data()

    assert posts[HYDROLOGY_POST.post_id] == HYDROLOGY_POST
    assert observations[HYDROLOGY_POST.post_id] == HYDROLOGY_OBSERVATION
    client._get_text.assert_awaited_once_with(HYDROLOGY_POST_CATALOG_PATH)
    client._get_json.assert_awaited_once_with(HYDROLOGY_DATA_PATH)


def test_parse_snow_catalog_and_observations() -> None:
    stations = parse_snow_station_catalog(SNOW_STATION_SCRIPT)
    lookups = parse_lookups(ICON_SCRIPT, WIND_SCRIPT)
    observations = parse_snow_observations(SNOW_PAYLOAD, lookups)

    assert stations[SNOW_STATION.station_id] == SNOW_STATION
    assert observations[SNOW_STATION.station_id] == SNOW_OBSERVATION


async def test_client_gets_snow_catalog_and_observations() -> None:
    client = UkrHMCClient(Mock())
    client._get_text = AsyncMock(
        side_effect=[SNOW_STATION_SCRIPT, ICON_SCRIPT, WIND_SCRIPT]
    )
    client._get_json = AsyncMock(return_value=SNOW_PAYLOAD)

    stations, observations = await client.async_get_snow_data()

    assert stations[SNOW_STATION.station_id] == SNOW_STATION
    assert observations[SNOW_STATION.station_id] == SNOW_OBSERVATION
    client._get_text.assert_any_await(SNOW_STATION_CATALOG_PATH)
    client._get_json.assert_awaited_once_with(SNOW_DATA_PATH)


def test_parse_observations_and_lookups() -> None:
    lookups = parse_lookups(ICON_SCRIPT, WIND_SCRIPT)
    observations = parse_observations(
        {
            "33345": {
                "CD": "2026-07-30",
                "CT": 15,
                "C_A": 750,
                "C_V": 38,
                "C_T": 25.9,
                "C_W": 3,
                "C_D": 1,
                "C_I": 0,
                "C_O": 6,
                "IM": 44,
                "IT": 0,
                "TX": 1,
                "IM_N": 69,
                "SR": "522",
                "SS": "2046",
            }
        },
        lookups,
    )

    observation = observations[33345]
    assert observation.condition == "Малохмарно"
    assert observation.wind.abbreviation == "NNE"
    assert observation.wind.bearing == 22.5
    assert observation.observed_at.isoformat() == "2026-07-30T15:00:00+03:00"
    assert observation.sunrise.isoformat() == "05:22:00"


def test_parse_forecasts_preserves_ranges_and_text() -> None:
    lookups = parse_lookups(ICON_SCRIPT, WIND_SCRIPT)
    forecasts = parse_forecasts(
        {
            "33345": {
                "2026-07-30": {
                    "T_N": 14,
                    "T_D": 26,
                    "T_IN_F": 13,
                    "T_IN_T": 15,
                    "T_ID_F": 25,
                    "T_ID_T": 27,
                    "I_D": 42,
                    "I_N": 67,
                    "HM": "невелика хмарність",
                    "O_D": "без опадів",
                    "O_N": "дощ",
                    "HM_EN": "little cloudiness",
                    "O_D_EN": "without precipitation",
                    "O_N_EN": "rain",
                    "WD_N": 1,
                    "WD_S": "5-10",
                    "WN_N": 1,
                    "WN_S": "3-8",
                    "SR": "5:22",
                    "SS": "20:46",
                    "MP": 16,
                }
            }
        },
        lookups,
    )

    forecast = forecasts[33345][0]
    assert forecast.temperature_day_from == 25
    assert forecast.temperature_day_to == 27
    assert forecast.wind_speed_day == "5-10"
    assert forecast.condition_night == "невелика хмарність, дощ"


def test_parse_alert_flags() -> None:
    assert parse_alert_flags(ALERT_PAYLOAD) == {
        "attns_meteo": True,
        "attns_hydro": False,
        "attns_snigo": False,
        "attns_radio": False,
        "attns_fire": True,
    }


def test_parse_regional_weather_warnings() -> None:
    updated_at, warnings = parse_regional_weather_warnings(WEATHER_WARNING_PAYLOAD)

    warning = warnings[1][0]
    assert updated_at.isoformat() == "2026-09-04T13:13:00+03:00"
    assert warning.description == "пориви 15-20 м/с"
    assert warning.phenomenon_code == 8
    assert warning.danger_level == 1
    assert warning.period == "05.09 09:00 — 21:00"
    assert warning.starts_at.isoformat() == "2026-09-05T09:00:00+03:00"
    assert warning.ends_at.isoformat() == "2026-09-05T21:00:00+03:00"
    assert warning.geometry_path == "/_/geo/ua/1.json"


def test_parse_regional_warning_multiday_period() -> None:
    payload = {
        "UPD": "04.09.2026, 11:24",
        "OBJ": [
            [
                {
                    "R": 1,
                    "L": 3,
                    "U": "/_/geo/ua/1.json",
                    "A": [
                        {
                            "T": "",
                            "D": "",
                            "P": "06.09, 00:01 &mdash; 07.09, 23:58",
                        }
                    ],
                }
            ]
        ],
    }

    _, warnings = parse_regional_weather_warnings(payload)

    assert warnings[1][0].starts_at.isoformat() == "2026-09-06T00:01:00+03:00"
    assert warnings[1][0].ends_at.isoformat() == "2026-09-07T23:58:00+03:00"


def test_parse_regional_hydrology_warning_skips_basin_outlines() -> None:
    payload = {
        "UPD": "31.08.2026, 14:11",
        "OBJ": [
            [
                {"R": "sb1", "L": "sb", "U": "/_/geo/ha/1.json", "A": ""},
                {
                    "R": 61,
                    "L": "4_hb",
                    "U": "/_/geo/hb/61.json",
                    "A": [
                        {
                            "C": 4,
                            "T": 6,
                            "P": "04.09, 00:00 &mdash; 15.10, 00:00",
                            "D": "Зниження рівнів води",
                        }
                    ],
                },
            ]
        ],
    }
    lookup = 'const ATTNS_REGIONS = {"61": "Середній Дніпро"};'

    updated_at, warnings = parse_regional_hydrology_warnings(payload, lookup)

    assert updated_at.isoformat() == "2026-08-31T14:11:00+03:00"
    warning = warnings[61][0]
    assert warning.basin_name == "Середній Дніпро"
    assert warning.danger_level == 4
    assert warning.phenomenon == "Зниження рівнів води"
    assert warning.ends_at.isoformat() == "2026-10-15T00:00:00+03:00"


def test_parse_region_geometry_and_point_in_polygon() -> None:
    geometry = parse_region_geometry(REGION_GEOMETRY_PAYLOAD)

    assert point_in_region(30.5234, 50.4501, geometry)
    assert not point_in_region(32.0, 50.4501, geometry)


def test_parse_region_feature_collection_and_point_in_polygon() -> None:
    geometry = parse_region_geometry(REGION_FEATURE_COLLECTION_PAYLOAD)

    assert point_in_region(30.5234, 50.4501, geometry)
    assert not point_in_region(32.0, 50.4501, geometry)


def _hourly_payload(
    *,
    point: str = "50.4501,30.5234",
    forecasts: list[dict] | None = None,
    daily_forecasts: list[dict] | None = None,
) -> dict:
    """Return one location forecast response."""
    if forecasts is None:
        forecasts = [{"time": "20260730T220000", "meantemp": 20}]
    if daily_forecasts is None:
        daily_forecasts = [
            {
                "time": "20260730T030000",
                "maxtemp": 16,
                "SmartSymbolText": "clear",
                "dark": 1,
            },
            {
                "time": "20260730T150000",
                "maxtemp": 30,
                "SmartSymbolText": "clear",
                "dark": 0,
            },
        ]
    return {
        "dataTabs": {"latlon": point},
        "dataDetailed": forecasts,
        "fulldata": daily_forecasts,
    }


async def test_location_forecast_uses_city_label_and_point() -> None:
    client = UkrHMCClient(Mock())
    client._get_json = AsyncMock(return_value=_hourly_payload())

    forecast = await client.async_validate_location_forecast(LOCATION_FORECAST_REQUEST)

    assert forecast.hourly_forecasts[0].temperature == 20
    assert forecast.daily_forecasts[0].temperature_night == 16
    assert forecast.daily_forecasts[0].temperature_day == 30
    client._get_json.assert_awaited_once_with(
        CITY_API_PATH,
        params={
            QUERY_ACTION: CITY_WEATHER_ACTION,
            QUERY_CITY: LOCATION_FORECAST_REQUEST.name,
            QUERY_LOCATION: "50.4501,30.5234",
            QUERY_LANGUAGE: CITY_LANGUAGE,
        },
    )


async def test_location_forecast_requires_non_empty_city_label() -> None:
    client = UkrHMCClient(Mock())

    with pytest.raises(UkrHMCDataError, match="city label is required"):
        await client.async_validate_location_forecast(
            replace(LOCATION_FORECAST_REQUEST, name=" ")
        )


async def test_location_forecast_rejects_echoed_location_mismatch() -> None:
    client = UkrHMCClient(Mock())
    client._get_json = AsyncMock(return_value=_hourly_payload(point="50.4501,30.6"))

    with pytest.raises(UkrHMCDataError, match="does not match"):
        await client.async_validate_location_forecast(LOCATION_FORECAST_REQUEST)


async def test_location_validation_rejects_empty_forecast() -> None:
    client = UkrHMCClient(Mock())
    client._get_json = AsyncMock(return_value=_hourly_payload(forecasts=[]))

    with pytest.raises(UkrHMCDataError, match="No hourly forecast data"):
        await client.async_validate_location_forecast(LOCATION_FORECAST_REQUEST)


async def test_data_snapshot_keys_empty_forecast_by_caller_id() -> None:
    client = UkrHMCClient(Mock())
    client.async_get_stations = AsyncMock(return_value={})
    client._async_get_lookups = AsyncMock(
        return_value=parse_lookups(ICON_SCRIPT, WIND_SCRIPT)
    )

    async def get_json(path, params=None):
        if path in (CURRENT_PATH, FORECAST_PATH):
            return {}
        if path == DAY_NIGHT_PATH:
            return ALERT_PAYLOAD
        if path in (
            REGIONAL_WEATHER_WARNINGS_PATH,
            REGIONAL_FIRE_WARNINGS_PATH,
            REGIONAL_SNOW_WARNINGS_PATH,
        ):
            return WEATHER_WARNING_PAYLOAD
        if path == "/_/geo/ua/1.json":
            return REGION_GEOMETRY_PAYLOAD
        assert path == CITY_API_PATH
        assert params is not None
        return _hourly_payload(forecasts=[])

    client._get_json = AsyncMock(side_effect=get_json)

    snapshot = await client.async_get_data(
        {"location-subentry": LOCATION_FORECAST_REQUEST}
    )

    assert snapshot.location_forecasts["location-subentry"].hourly_forecasts == ()
    assert (
        snapshot.location_forecasts["location-subentry"]
        .daily_forecasts[0]
        .temperature_day
        == 30
    )
    assert snapshot.alert_flags["attns_meteo"]


async def test_data_snapshot_can_skip_all_station_endpoints() -> None:
    client = UkrHMCClient(Mock())
    client.async_get_stations = AsyncMock(return_value={STATION.station_id: STATION})
    client._async_get_lookups = AsyncMock(
        side_effect=AssertionError("station lookups must not be fetched")
    )
    client.async_get_radiation_data = AsyncMock(
        side_effect=AssertionError("radiation data must not be fetched")
    )
    client.async_get_hydrology_data = AsyncMock(
        side_effect=AssertionError("hydrology data must not be fetched")
    )

    async def get_json(path, params=None):
        if path == DAY_NIGHT_PATH:
            return ALERT_PAYLOAD
        if path in (
            REGIONAL_WEATHER_WARNINGS_PATH,
            REGIONAL_FIRE_WARNINGS_PATH,
            REGIONAL_SNOW_WARNINGS_PATH,
        ):
            return WEATHER_WARNING_PAYLOAD
        if path == "/_/geo/ua/1.json":
            return REGION_GEOMETRY_PAYLOAD
        assert path == CITY_API_PATH
        assert params is not None
        return _hourly_payload()

    client._get_json = AsyncMock(side_effect=get_json)

    snapshot = await client.async_get_data(
        {"location-subentry": LOCATION_FORECAST_REQUEST},
        include_station_data=False,
    )

    assert snapshot.stations == {STATION.station_id: STATION}
    assert snapshot.observations == {}
    assert snapshot.forecasts == {}
    assert snapshot.night_station_ids == set()
    assert snapshot.radiation_stations == {}
    assert snapshot.radiation_observations == {}
    assert snapshot.hydrology_posts == {}
    assert snapshot.hydrology_observations == {}
    assert (
        snapshot.location_forecasts["location-subentry"].hourly_forecasts[0].temperature
        == 20
    )
    assert (
        snapshot.location_forecasts["location-subentry"]
        .daily_forecasts[0]
        .temperature_day
        == 30
    )
    client.async_get_stations.assert_awaited_once()
    client._async_get_lookups.assert_not_awaited()
    client.async_get_radiation_data.assert_not_awaited()
    client.async_get_hydrology_data.assert_not_awaited()


async def test_data_snapshot_can_include_only_radiation_data() -> None:
    client = UkrHMCClient(Mock())
    client._get_json = AsyncMock(return_value=ALERT_PAYLOAD)
    client.async_get_radiation_data = AsyncMock(
        return_value=(
            {RADIATION_STATION.station_id: RADIATION_STATION},
            {RADIATION_STATION.station_id: RADIATION_OBSERVATION},
        )
    )

    snapshot = await client.async_get_data(
        include_station_data=False,
        include_radiation_data=True,
    )

    assert snapshot.radiation_stations[RADIATION_STATION.station_id] == (
        RADIATION_STATION
    )
    assert snapshot.radiation_observations[RADIATION_STATION.station_id] == (
        RADIATION_OBSERVATION
    )


async def test_data_snapshot_can_include_only_hydrology_data() -> None:
    client = UkrHMCClient(Mock())
    client._get_json = AsyncMock(
        side_effect=lambda path, _params=None: (
            ALERT_PAYLOAD
            if path == DAY_NIGHT_PATH
            else {"UPD": "04.09.2026, 12:00", "OBJ": []}
        )
    )
    client._get_text = AsyncMock(
        return_value='const ATTNS_REGIONS = {"61": "Середній Дніпро"};'
    )
    client.async_get_hydrology_data = AsyncMock(
        return_value=(
            {HYDROLOGY_POST.post_id: HYDROLOGY_POST},
            {HYDROLOGY_POST.post_id: HYDROLOGY_OBSERVATION},
        )
    )

    snapshot = await client.async_get_data(
        include_station_data=False,
        include_hydrology_data=True,
    )

    assert snapshot.hydrology_posts[HYDROLOGY_POST.post_id] == HYDROLOGY_POST
    assert snapshot.hydrology_observations[HYDROLOGY_POST.post_id] == (
        HYDROLOGY_OBSERVATION
    )
    client._get_json.assert_any_await(HYDROLOGY_WARNINGS_PATH)
    client._get_text.assert_awaited_once_with(HYDROLOGY_WARNING_LOOKUP_PATH)


def test_parse_hourly_forecasts_preserves_provider_values() -> None:
    forecasts = parse_hourly_forecasts(
        {
            "dataDetailed": [
                {
                    "time": "20260730T220000",
                    "mintemp": 20,
                    "maxtemp": 20,
                    "meantemp": 20,
                    "meanprecip": 0,
                    "SmartSymbol": 101,
                    "SmartSymbolText": "clear",
                    "Weather": "clear",
                    "dark": 1,
                    "WindCompass8": "NW",
                    "WindSpeedMS": 2,
                    "WindGust": "-",
                    "Humidity": 52,
                    "pressure": 1017,
                    "windDirection": 315,
                    "dewPoint": 10,
                },
                {"time": "20260731T000000", "meantemp": None},
            ]
        }
    )

    assert len(forecasts) == 1
    forecast = forecasts[0]
    assert forecast.forecast_at.isoformat() == "2026-07-30T22:00:00+03:00"
    assert forecast.temperature == 20
    assert forecast.pressure == 1017
    assert forecast.wind_gust is None


def test_parse_current_location_forecast_requires_present_hour() -> None:
    payload = {
        "fulldata": [
            {
                "time": "20260804T150000",
                "meantemp": 32,
                "WindCompass8": "NW",
                "WindSpeedMS": 2,
                "Humidity": 52,
            },
            {"time": "20260804T160000", "meantemp": 33},
        ]
    }
    current = parse_current_location_forecast(
        payload,
        datetime(2026, 8, 4, 15, 48, tzinfo=ZoneInfo("Europe/Kyiv")),
    )

    assert current is not None
    assert current.forecast_at.isoformat() == "2026-08-04T15:00:00+03:00"
    assert current.temperature == 32
    assert current.pressure is None
    assert current.wind_compass == "NW"
    assert current.wind_direction is None
    assert current.wind_bearing == 315
    assert (
        parse_current_location_forecast(
            payload,
            datetime(2026, 8, 4, 14, 48, tzinfo=ZoneInfo("Europe/Kyiv")),
        )
        is None
    )


def test_parse_location_daily_forecasts_uses_exact_provider_hours() -> None:
    forecasts = parse_location_daily_forecasts(
        {
            "fulldata": [
                {
                    "time": "20260801T030000",
                    "maxtemp": 19,
                    "SmartSymbol": 101,
                    "SmartSymbolText": "clear",
                    "Weather": "clear",
                },
                {"time": "20260801T060000", "maxtemp": 17},
                {
                    "time": "20260801T150000",
                    "maxtemp": 32,
                    "SmartSymbol": 2,
                    "SmartSymbolText": "mostly clear",
                    "Weather": "mostly clear",
                },
                {"time": "20260802T030000", "maxtemp": 20},
                {"time": "20260803T030000", "maxtemp": "-"},
                {"time": "20260803T150000", "maxtemp": 29},
            ]
        }
    )

    assert len(forecasts) == 1
    forecast = forecasts[0]
    assert forecast.date.isoformat() == "2026-08-01"
    assert forecast.temperature_night == 19
    assert forecast.temperature_day == 32
    assert forecast.condition_night == "clear"
    assert forecast.condition_day == "mostly clear"


def test_parse_night_station_ids() -> None:
    assert parse_night_station_ids({"dn": {"33345": 1, "33347": 0}}) == {33345}


@pytest.mark.parametrize(
    ("function", "args"),
    [
        (parse_station_catalog, ("invalid",)),
        (parse_radiation_station_catalog, ("invalid",)),
        (parse_radiation_observations, ({"33345": {}},)),
        (parse_hydrology_post_catalog, ("invalid",)),
        (parse_hydrology_observations, ({"80986": {}},)),
        (parse_lookups, ("const X = [];", WIND_SCRIPT)),
        (parse_lookups, ("const METEO_ICONS_TITLES = {};", WIND_SCRIPT)),
        (parse_location_daily_forecasts, ({},)),
        (parse_alert_flags, ({},)),
        (parse_regional_weather_warnings, ({},)),
        (parse_region_geometry, ({},)),
        (parse_night_station_ids, ({"dn": {"invalid": 1}},)),
    ],
)
def test_invalid_data_raises_api_error(function, args) -> None:
    with pytest.raises(UkrHMCDataError):
        function(*args)


def test_data_snapshot_copies_input_mappings() -> None:
    stations = dict(DATA.stations)
    snapshot = DATA.create(
        stations=stations,
        observations=dict(DATA.observations),
        forecasts=dict(DATA.forecasts),
        location_forecasts=dict(DATA.location_forecasts),
        night_station_ids=DATA.night_station_ids,
        radiation_stations=dict(DATA.radiation_stations),
        radiation_observations=dict(DATA.radiation_observations),
        hydrology_posts=dict(DATA.hydrology_posts),
        hydrology_observations=dict(DATA.hydrology_observations),
        snow_stations=dict(DATA.snow_stations),
        snow_observations=dict(DATA.snow_observations),
        alert_flags=dict(DATA.alert_flags),
        weather_warnings_updated_at=DATA.weather_warnings_updated_at,
        regional_weather_warnings=dict(DATA.regional_weather_warnings),
        location_region_ids=dict(DATA.location_region_ids),
    )

    stations.clear()

    assert isinstance(snapshot.stations, MappingProxyType)
    assert snapshot.stations


def test_api_user_agent_is_integration_agnostic() -> None:
    assert REQUEST_HEADERS["User-Agent"] == "UkrHMC/0.0.0"
