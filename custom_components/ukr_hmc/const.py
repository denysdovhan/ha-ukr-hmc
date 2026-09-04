"""Constants for the UkrHMC integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "ukr_hmc"
NAME: Final = "Ukrainian Hydrometeorological Center"
MANUFACTURER: Final = "Ukrainian Hydrometeorological Center"
ATTRIBUTION: Final = "Data provided by the Ukrainian Hydrometeorological Center"
CONFIGURATION_URL: Final = "https://www.meteo.gov.ua/"
HYDROLOGY_CONFIGURATION_URL: Final = (
    f"{CONFIGURATION_URL}ua/Shchodenna-hidrolohichna-situaciya"
)
RADIATION_CONFIGURATION_URL: Final = f"{CONFIGURATION_URL}#RADIO"
SNOW_CONFIGURATION_URL: Final = f"{CONFIGURATION_URL}ua/Sniholavinna-situaciya"

CONF_STATION_ID: Final = "station_id"
SUBENTRY_TYPE_HYDROLOGY_POST: Final = "hydrology_post"
SUBENTRY_TYPE_RADIATION_STATION: Final = "radiation_station"
SUBENTRY_TYPE_SNOW_STATION: Final = "snow_station"
SUBENTRY_TYPE_WEATHER_LOCATION: Final = "weather_location"
SUBENTRY_TYPE_WEATHER_STATION: Final = "weather_station"
WEATHER_SUBENTRY_TYPES: Final = (
    SUBENTRY_TYPE_WEATHER_STATION,
    SUBENTRY_TYPE_WEATHER_LOCATION,
)
SUBENTRY_TYPES: Final = (
    SUBENTRY_TYPE_WEATHER_STATION,
    SUBENTRY_TYPE_WEATHER_LOCATION,
    SUBENTRY_TYPE_RADIATION_STATION,
    SUBENTRY_TYPE_HYDROLOGY_POST,
    SUBENTRY_TYPE_SNOW_STATION,
)

UPDATE_INTERVAL: Final = timedelta(minutes=15)
STALE_DATA_AFTER: Final = timedelta(minutes=45)
