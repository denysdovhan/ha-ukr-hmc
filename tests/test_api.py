"""Tests for the isolated UkrHMC API package."""

from types import MappingProxyType

import pytest

from custom_components.ukr_hmc.api import UkrHMCDataError
from custom_components.ukr_hmc.api.parsers import (
    parse_forecasts,
    parse_lookups,
    parse_night_station_ids,
    parse_observations,
    parse_station_catalog,
)

from .fixtures import DATA, STATION

ICON_SCRIPT = (
    'const METEO_ICONS_TITLES = ["", "Дощ"]; '
    'const METEO_ICONS_TITLES0 = ["Ясно", "Малохмарно"];'
)
WIND_SCRIPT = 'const METEO_WINDS = [[], {"r": "NNE", "t": "Північно-Східний"}];'


def test_parse_station_catalog() -> None:
    script = (
        'const METEO_OBLASTI = {"1": "Київська"}; '
        'const METEO_STATIONS = {"0": '
        '{"i": 33345, "o": 1, "h": 167, "t": "Київ", '
        '"x": "50.391792297363", "y": "30.53563117981"}};'
    )

    stations = parse_station_catalog(script)

    assert stations[33345] == STATION


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


def test_parse_night_station_ids() -> None:
    assert parse_night_station_ids({"dn": {"33345": 1, "33347": 0}}) == {33345}


@pytest.mark.parametrize(
    ("function", "args"),
    [
        (parse_station_catalog, ("invalid",)),
        (parse_lookups, ("const X = [];", WIND_SCRIPT)),
        (parse_lookups, ("const METEO_ICONS_TITLES = {};", WIND_SCRIPT)),
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
        night_station_ids=DATA.night_station_ids,
    )

    stations.clear()

    assert isinstance(snapshot.stations, MappingProxyType)
    assert snapshot.stations


def test_api_user_agent_is_integration_agnostic() -> None:
    assert REQUEST_HEADERS["User-Agent"] == "UkrHMC/0.0.0"
