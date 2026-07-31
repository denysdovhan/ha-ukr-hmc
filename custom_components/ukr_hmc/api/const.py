"""Constants for the Ukrhydrometcenter API client."""

from typing import Final

BASE_URL: Final = "https://www.meteo.gov.ua"
CURRENT_PATH: Final = "/_/m/current.js"
DAY_NIGHT_PATH: Final = "/_/_e5m.json"
FORECAST_PATH: Final = "/_/m/prognoz.js"
ICON_LOOKUP_PATH: Final = "/ua/_meteo-icons.js"
STATION_CATALOG_PATH: Final = "/ua/_meteo-stations.js"
WIND_LOOKUP_PATH: Final = "/ua/_meteo-winds.js"

REQUEST_TIMEOUT: Final = 20
REQUEST_HEADERS: Final = {
    "Accept": "application/json, text/javascript, */*",
    "Referer": f"{BASE_URL}/",
    "User-Agent": (
        "HomeAssistant-UkrHMC/0.0.0 (+https://github.com/denysdovhan/ha-ukr-hmc)"
    ),
}
