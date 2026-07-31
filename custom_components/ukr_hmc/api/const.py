"""Constants for the UkrHMC API client."""

from typing import Final

# API endpoints.
BASE_URL: Final = "https://www.meteo.gov.ua"
CURRENT_PATH: Final = "/_/m/current.js"
DAY_NIGHT_PATH: Final = "/_/_e5m.json"
FORECAST_PATH: Final = "/_/m/prognoz.js"
ICON_LOOKUP_PATH: Final = "/ua/_meteo-icons.js"
STATION_CATALOG_PATH: Final = "/ua/_meteo-stations.js"
WIND_LOOKUP_PATH: Final = "/ua/_meteo-winds.js"

# JavaScript variable names.
CONDITION_TITLES_VARIABLE: Final = "METEO_ICONS_TITLES"
CLOUD_TITLES_VARIABLE: Final = "METEO_ICONS_TITLES0"
REGIONS_VARIABLE: Final = "METEO_OBLASTI"
STATIONS_VARIABLE: Final = "METEO_STATIONS"
WINDS_VARIABLE: Final = "METEO_WINDS"

# Station record keys.
STATION_ID_KEY: Final = "i"
STATION_REGION_ID_KEY: Final = "o"
STATION_ALTITUDE_KEY: Final = "h"
STATION_NAME_KEY: Final = "t"
STATION_LATITUDE_KEY: Final = "x"
STATION_LONGITUDE_KEY: Final = "y"

# Wind record keys and bearings.
WIND_ABBREVIATION_KEY: Final = "r"
WIND_NAME_KEY: Final = "t"
WIND_BEARINGS: Final = {
    "N": 0.0,
    "NNE": 22.5,
    "NE": 45.0,
    "ENE": 67.5,
    "E": 90.0,
    "ESE": 112.5,
    "SE": 135.0,
    "SSE": 157.5,
    "S": 180.0,
    "SSW": 202.5,
    "SW": 225.0,
    "WSW": 247.5,
    "W": 270.0,
    "WNW": 292.5,
    "NW": 315.0,
    "NNW": 337.5,
}

# Current observation record keys.
OBSERVATION_DATE_KEY: Final = "CD"
OBSERVATION_HOUR_KEY: Final = "CT"
OBSERVATION_TEMPERATURE_KEY: Final = "C_T"
OBSERVATION_HUMIDITY_KEY: Final = "C_V"
OBSERVATION_PRESSURE_KEY: Final = "C_A"
OBSERVATION_WIND_SPEED_KEY: Final = "C_W"
OBSERVATION_WIND_DIRECTION_KEY: Final = "C_D"
OBSERVATION_CONDITION_SELECTOR_KEY: Final = "IT"
OBSERVATION_CONDITION_CODE_KEY: Final = "TX"
OBSERVATION_DAY_ICON_KEY: Final = "IM"
OBSERVATION_NIGHT_ICON_KEY: Final = "IM_N"
OBSERVATION_PHENOMENON_CODE_KEY: Final = "C_O"
OBSERVATION_INDICATOR_CODE_KEY: Final = "C_I"

# Forecast record keys.
FORECAST_NIGHT_TEMPERATURE_KEY: Final = "T_N"
FORECAST_DAY_TEMPERATURE_KEY: Final = "T_D"
FORECAST_NIGHT_TEMPERATURE_FROM_KEY: Final = "T_IN_F"
FORECAST_NIGHT_TEMPERATURE_TO_KEY: Final = "T_IN_T"
FORECAST_DAY_TEMPERATURE_FROM_KEY: Final = "T_ID_F"
FORECAST_DAY_TEMPERATURE_TO_KEY: Final = "T_ID_T"
FORECAST_DAY_ICON_KEY: Final = "I_D"
FORECAST_NIGHT_ICON_KEY: Final = "I_N"
FORECAST_CLOUDINESS_KEY: Final = "HM"
FORECAST_CLOUDINESS_ENGLISH_KEY: Final = "HM_EN"
FORECAST_DAY_PRECIPITATION_KEY: Final = "O_D"
FORECAST_DAY_PRECIPITATION_ENGLISH_KEY: Final = "O_D_EN"
FORECAST_NIGHT_PRECIPITATION_KEY: Final = "O_N"
FORECAST_NIGHT_PRECIPITATION_ENGLISH_KEY: Final = "O_N_EN"
FORECAST_DAY_WIND_DIRECTION_KEY: Final = "WD_N"
FORECAST_DAY_WIND_SPEED_KEY: Final = "WD_S"
FORECAST_NIGHT_WIND_DIRECTION_KEY: Final = "WN_N"
FORECAST_NIGHT_WIND_SPEED_KEY: Final = "WN_S"
FORECAST_PROVIDER_CODE_KEY: Final = "MP"

# Shared astronomy and day/night keys.
SUNRISE_KEY: Final = "SR"
SUNSET_KEY: Final = "SS"
DAY_NIGHT_STATIONS_KEY: Final = "dn"

# Provider enum values.
CLOUD_CONDITION_SELECTOR: Final = 0
DEFAULT_WIND_DIRECTION_CODE: Final = 0
NIGHT_VALUE: Final = 1

# HTTP request settings.
REQUEST_TIMEOUT: Final = 20
REQUEST_HEADERS: Final = {
    "Accept": "application/json, text/javascript, */*",
    "Referer": f"{BASE_URL}/",
    "User-Agent": "UkrHMC/0.0.0",
}
