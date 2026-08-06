"""Constants for the UkrHMC integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "ukr_hmc"
NAME: Final = "UkrHMC"
MANUFACTURER: Final = "Ukrainian Hydrometeorological Center"
ATTRIBUTION: Final = "Data provided by the Ukrainian Hydrometeorological Center"
CONFIGURATION_URL: Final = "https://www.meteo.gov.ua/"

CONF_STATION_ID: Final = "station_id"
SUBENTRY_TYPE_WEATHER_LOCATION: Final = "weather_location"
SUBENTRY_TYPE_WEATHER_STATION: Final = "weather_station"
WEATHER_SUBENTRY_TYPES: Final = (
    SUBENTRY_TYPE_WEATHER_STATION,
    SUBENTRY_TYPE_WEATHER_LOCATION,
)

UPDATE_INTERVAL: Final = timedelta(minutes=15)
