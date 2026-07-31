"""Shared UkrHMC test data."""

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from custom_components.ukr_hmc.api import (
    UkrHMCData,
    UkrHMCForecastDay,
    UkrHMCObservation,
    UkrHMCStation,
    UkrHMCWind,
)

STATION = UkrHMCStation(
    station_id=33345,
    region_id=1,
    region_name="Київська",
    name="Київ",
    latitude=50.391792297363,
    longitude=30.53563117981,
    altitude=167,
)
SECOND_STATION = UkrHMCStation(
    station_id=33347,
    region_id=1,
    region_name="Київська",
    name="Бориспіль",
    latitude=50.35,
    longitude=30.95,
    altitude=121,
)
WIND = UkrHMCWind(
    code=31,
    abbreviation="NW",
    name="Північно-Західний",
)
OBSERVATION = UkrHMCObservation(
    observed_at=datetime(
        2026,
        7,
        30,
        15,
        tzinfo=ZoneInfo("Europe/Kyiv"),
    ),
    temperature=25.9,
    humidity=38,
    pressure=750,
    wind_speed=3,
    wind=WIND,
    condition="Хмарно з проясненнями",
    icon_code_day=44,
    icon_code_night=69,
    phenomenon_code=6,
    indicator_code=0,
    sunrise=time(5, 22),
    sunset=time(20, 46),
)
FORECAST = UkrHMCForecastDay(
    date=date(2026, 7, 30),
    temperature_night=14,
    temperature_day=26,
    temperature_night_from=13,
    temperature_night_to=15,
    temperature_day_from=25,
    temperature_day_to=27,
    icon_code_day=42,
    icon_code_night=67,
    cloudiness="невелика хмарність",
    cloudiness_en="little cloudiness",
    precipitation_day="без опадів",
    precipitation_day_en="without precipitation",
    precipitation_night="без опадів",
    precipitation_night_en="without precipitation",
    wind_day=WIND,
    wind_speed_day="5-10",
    wind_night=WIND,
    wind_speed_night="3-8",
    sunrise=time(5, 22),
    sunset=time(20, 46),
    provider_code=16,
)
DATA = UkrHMCData.create(
    stations={
        STATION.station_id: STATION,
        SECOND_STATION.station_id: SECOND_STATION,
    },
    observations={STATION.station_id: OBSERVATION},
    forecasts={STATION.station_id: (FORECAST,)},
    night_station_ids=frozenset(),
)

STATIC_SUBENTRY_DATA = {
    "data": {
        "station_type": "static",
        "station_id": STATION.station_id,
    },
    "subentry_id": "station-subentry",
    "subentry_type": "station",
    "title": "Kyiv weather",
    "unique_id": f"station:{STATION.station_id}",
}
