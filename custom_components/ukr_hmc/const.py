"""Constants for the UkrHMC integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "ukr_hmc"
NAME: Final = "UkrHMC"
MANUFACTURER: Final = "Ukrainian Hydrometeorological Center"
ATTRIBUTION: Final = "Data provided by the Ukrainian Hydrometeorological Center"
CONFIGURATION_URL: Final = "https://www.meteo.gov.ua/"

CONF_STATION_ID: Final = "station_id"
CONF_STATION_TYPE: Final = "station_type"
STATION_TYPE_DYNAMIC: Final = "dynamic"
STATION_TYPE_STATIC: Final = "static"
SUBENTRY_TYPE_STATION: Final = "station"

UPDATE_INTERVAL: Final = timedelta(minutes=30)
