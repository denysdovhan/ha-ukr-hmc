"""Constants for the UkrHMC API client."""

from typing import Final

# API endpoints.
BASE_URL: Final = "https://www.meteo.gov.ua"
CITY_API_PATH: Final = "/fmi.json"
CURRENT_PATH: Final = "/_/m/current.js"
DAY_NIGHT_PATH: Final = "/_/_e5m.json"
FORECAST_PATH: Final = "/_/m/prognoz.js"
HYDROLOGY_DATA_PATH: Final = "/_/m/hydroday.js"
HYDROLOGY_POST_CATALOG_PATH: Final = "/ua/_hydro-posts.js"
ICON_LOOKUP_PATH: Final = "/ua/_meteo-icons.js"
RADIATION_DATA_PATH: Final = "/_/m/radioday.js"
RADIATION_STATION_CATALOG_PATH: Final = "/ua/_radio-posts.js"
REGIONAL_WEATHER_WARNINGS_PATH: Final = "/ua/_attns-meteo.json"
STATION_CATALOG_PATH: Final = "/ua/_meteo-stations.js"
WIND_LOOKUP_PATH: Final = "/ua/_meteo-winds.js"

# Location forecast request values.
CITY_WEATHER_ACTION: Final = "getCityWeather"
CITY_LANGUAGE: Final = "ua"

# Location forecast query parameter names.
QUERY_ACTION: Final = "action"
QUERY_CITY: Final = "city"
QUERY_LOCATION: Final = "latlon"
QUERY_LANGUAGE: Final = "lang"

# JavaScript variable names.
CONDITION_TITLES_VARIABLE: Final = "METEO_ICONS_TITLES"
CLOUD_TITLES_VARIABLE: Final = "METEO_ICONS_TITLES0"
RADIATION_STATIONS_VARIABLE: Final = "RADIO_POSTS"
HYDROLOGY_POSTS_VARIABLE: Final = "HYDRO_POSTS"
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

# Radiation station record keys.
RADIATION_STATION_NAME_KEY: Final = "P"
RADIATION_STATION_LATITUDE_KEY: Final = "X"
RADIATION_STATION_LONGITUDE_KEY: Final = "Y"
RADIATION_STATION_ALTITUDE_KEY: Final = "H"

# Radiation observation record keys.
RADIATION_DATE_KEY: Final = "CD"
RADIATION_TIME_KEY: Final = "CH"
RADIATION_EXPOSURE_DOSE_RATE_KEY: Final = "VR"
RADIATION_DOSE_RATE_KEY: Final = "VZ"

# Hydrology post record keys.
HYDROLOGY_POST_RIVER_KEY: Final = "R"
HYDROLOGY_POST_NAME_KEY: Final = "P"
HYDROLOGY_POST_LATITUDE_KEY: Final = "X"
HYDROLOGY_POST_LONGITUDE_KEY: Final = "Y"

# Hydrology observation record keys.
HYDROLOGY_DATE_KEY: Final = "PD"
HYDROLOGY_WATER_LEVEL_KEY: Final = "FR"
HYDROLOGY_WATER_LEVEL_ALTITUDE_KEY: Final = "FR_BS"
HYDROLOGY_WATER_LEVEL_CHANGE_KEY: Final = "C_FR"
HYDROLOGY_WATER_TEMPERATURE_KEY: Final = "TW"
HYDROLOGY_LEVEL_CLASS_KEY: Final = "L"
HYDROLOGY_OBSERVATION_HOUR: Final = 8

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

# Location forecast response keys.
HOURLY_METADATA_KEY: Final = "dataTabs"
LOCATION_POINT_KEY: Final = "latlon"
HOURLY_FORECASTS_KEY: Final = "dataDetailed"
LOCATION_FORECAST_RECORDS_KEY: Final = "fulldata"
HOURLY_TIME_KEY: Final = "time"
HOURLY_MAXIMUM_TEMPERATURE_KEY: Final = "maxtemp"
HOURLY_TEMPERATURE_KEY: Final = "meantemp"
HOURLY_PRECIPITATION_KEY: Final = "meanprecip"
HOURLY_CONDITION_KEY: Final = "SmartSymbolText"
HOURLY_WEATHER_KEY: Final = "Weather"
HOURLY_IS_NIGHT_KEY: Final = "dark"
HOURLY_WIND_COMPASS_KEY: Final = "WindCompass8"
HOURLY_WIND_SPEED_KEY: Final = "WindSpeedMS"
HOURLY_WIND_GUST_KEY: Final = "WindGust"
HOURLY_HUMIDITY_KEY: Final = "Humidity"
HOURLY_PRESSURE_KEY: Final = "pressure"
HOURLY_WIND_DIRECTION_KEY: Final = "windDirection"
HOURLY_DEW_POINT_KEY: Final = "dewPoint"

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
ALERT_FLAG_KEYS: Final = (
    "attns_meteo",
    "attns_hydro",
    "attns_snigo",
    "attns_radio",
    "attns_fire",
)

# Regional weather warning keys.
WEATHER_WARNINGS_UPDATED_KEY: Final = "UPD"
WEATHER_WARNINGS_GROUPS_KEY: Final = "OBJ"
WEATHER_WARNING_REGION_KEY: Final = "R"
WEATHER_WARNING_LEVEL_KEY: Final = "L"
WEATHER_WARNING_ALERTS_KEY: Final = "A"
WEATHER_WARNING_CODE_KEY: Final = "T"
WEATHER_WARNING_PERIOD_KEY: Final = "P"
WEATHER_WARNING_DESCRIPTION_KEY: Final = "D"

# Provider enum values.
CLOUD_CONDITION_SELECTOR: Final = 0
LOCATION_POINT_COMPONENT_COUNT: Final = 2
LOCATION_MATCH_TOLERANCE: Final = 1e-6
DEFAULT_WIND_DIRECTION_CODE: Final = 0
MISSING_VALUE_MARKERS: Final = (None, "", "-")
NIGHT_VALUE: Final = 1
LOCATION_NIGHT_FORECAST_HOUR: Final = 3
LOCATION_DAY_FORECAST_HOUR: Final = 15

# HTTP request settings.
REQUEST_TIMEOUT: Final = 20
REQUEST_HEADERS: Final = {
    "Accept": "application/json, text/javascript, */*",
    "Referer": f"{BASE_URL}/",
    "User-Agent": "UkrHMC/0.0.0",
}
