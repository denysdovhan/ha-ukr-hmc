"""Shared UkrHMC test data."""

from dataclasses import replace
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME

from custom_components.ukr_hmc.api import (
    UkrHMCData,
    UkrHMCForecastDay,
    UkrHMCHourlyForecast,
    UkrHMCHydrologyObservation,
    UkrHMCHydrologyPost,
    UkrHMCLocationForecast,
    UkrHMCLocationForecastDay,
    UkrHMCLocationForecastRequest,
    UkrHMCObservation,
    UkrHMCRadiationObservation,
    UkrHMCRadiationStation,
    UkrHMCStation,
    UkrHMCWeatherWarning,
    UkrHMCWind,
)
from custom_components.ukr_hmc.const import (
    CONF_STATION_ID,
    SUBENTRY_TYPE_HYDROLOGY_POST,
    SUBENTRY_TYPE_RADIATION_STATION,
    SUBENTRY_TYPE_WEATHER_LOCATION,
    SUBENTRY_TYPE_WEATHER_STATION,
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
RADIATION_STATION = UkrHMCRadiationStation(
    station_id=33345,
    name="Київ",
    latitude=50.391792297363,
    longitude=30.53563117981,
    altitude=167,
)
SECOND_RADIATION_STATION = UkrHMCRadiationStation(
    station_id=33347,
    name="Бориспіль",
    latitude=50.35,
    longitude=30.95,
    altitude=121,
)
RADIATION_OBSERVATION = UkrHMCRadiationObservation(
    observed_at=datetime(
        2026,
        8,
        6,
        12,
        tzinfo=ZoneInfo("Europe/Kyiv"),
    ),
    exposure_dose_rate=11,
    dose_rate=96,
)
HYDROLOGY_POST = UkrHMCHydrologyPost(
    post_id=80986,
    river="Дніпро",
    name="Київ",
    latitude=50.442147,
    longitude=30.569539,
)
SECOND_HYDROLOGY_POST = UkrHMCHydrologyPost(
    post_id=79043,
    river="Дніпро",
    name="Неданчичі",
    latitude=51.50007,
    longitude=30.587199,
)
HYDROLOGY_OBSERVATION = UkrHMCHydrologyObservation(
    observed_at=datetime(
        2026,
        8,
        6,
        8,
        tzinfo=ZoneInfo("Europe/Kyiv"),
    ),
    water_level=444.0,
    water_level_altitude=91.44,
    water_level_change=-0.01,
    water_temperature=25.0,
    level_class=1,
)
LOCATION_FORECAST_REQUEST = UkrHMCLocationForecastRequest(
    name="Home",
    latitude=50.4501,
    longitude=30.5234,
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
HOURLY_FORECAST = UkrHMCHourlyForecast(
    forecast_at=datetime(
        2026,
        7,
        30,
        22,
        tzinfo=ZoneInfo("Europe/Kyiv"),
    ),
    temperature=20,
    precipitation=0,
    condition="clear",
    weather="Ясно",
    is_night=True,
    wind_compass="NW",
    wind_speed=2,
    wind_gust=5,
    humidity=52,
    pressure=1017,
    wind_direction=315,
    dew_point=10,
)
CURRENT_LOCATION_FORECAST = replace(
    HOURLY_FORECAST,
    wind_gust=None,
    pressure=None,
    wind_direction=None,
    dew_point=None,
)
LOCATION_DAILY_FORECAST = UkrHMCLocationForecastDay(
    date=date(2026, 7, 30),
    temperature_night=14,
    temperature_day=26,
    condition_night="clear",
    condition_day="clear",
    weather_night="clear",
    weather_day="clear",
)
WEATHER_WARNING_UPDATED_AT = datetime(
    2026, 9, 4, 13, 13, tzinfo=ZoneInfo("Europe/Kyiv")
)
WEATHER_WARNING = UkrHMCWeatherWarning(
    region_id=1,
    danger_level=1,
    phenomenon_code=8,
    description="пориви 15-20 м/с",
    period="05.09 09:00 — 21:00",
    starts_at=None,
    ends_at=None,
)
DATA = UkrHMCData.create(
    stations={
        STATION.station_id: STATION,
        SECOND_STATION.station_id: SECOND_STATION,
    },
    observations={STATION.station_id: OBSERVATION},
    forecasts={STATION.station_id: (FORECAST,)},
    location_forecasts={
        "location-subentry": UkrHMCLocationForecast(
            current=CURRENT_LOCATION_FORECAST,
            hourly_forecasts=(HOURLY_FORECAST,),
            daily_forecasts=(LOCATION_DAILY_FORECAST,),
        )
    },
    night_station_ids=frozenset(),
    radiation_stations={RADIATION_STATION.station_id: RADIATION_STATION},
    radiation_observations={RADIATION_STATION.station_id: RADIATION_OBSERVATION},
    hydrology_posts={HYDROLOGY_POST.post_id: HYDROLOGY_POST},
    hydrology_observations={HYDROLOGY_POST.post_id: HYDROLOGY_OBSERVATION},
    alert_flags={
        "attns_meteo": True,
        "attns_hydro": False,
        "attns_snigo": False,
        "attns_radio": False,
        "attns_fire": True,
    },
    weather_warnings_updated_at=WEATHER_WARNING_UPDATED_AT,
    regional_weather_warnings={1: (WEATHER_WARNING,)},
)

STATION_SUBENTRY_DATA = {
    "data": {CONF_STATION_ID: STATION.station_id},
    "subentry_id": "station-subentry",
    "subentry_type": SUBENTRY_TYPE_WEATHER_STATION,
    "title": "Kyiv weather",
    "unique_id": f"station:{STATION.station_id}",
}

LOCATION_SUBENTRY_DATA = {
    "data": {
        CONF_NAME: LOCATION_FORECAST_REQUEST.name,
        CONF_LATITUDE: LOCATION_FORECAST_REQUEST.latitude,
        CONF_LONGITUDE: LOCATION_FORECAST_REQUEST.longitude,
    },
    "subentry_id": "location-subentry",
    "subentry_type": SUBENTRY_TYPE_WEATHER_LOCATION,
    "title": LOCATION_FORECAST_REQUEST.name,
    "unique_id": "location:50.450100:30.523400",
}

RADIATION_SUBENTRY_DATA = {
    "data": {CONF_STATION_ID: RADIATION_STATION.station_id},
    "subentry_id": "radiation-subentry",
    "subentry_type": SUBENTRY_TYPE_RADIATION_STATION,
    "title": "Kyiv radiation",
    "unique_id": f"radiation:{RADIATION_STATION.station_id}",
}

HYDROLOGY_SUBENTRY_DATA = {
    "data": {CONF_STATION_ID: HYDROLOGY_POST.post_id},
    "subentry_id": "hydrology-subentry",
    "subentry_type": SUBENTRY_TYPE_HYDROLOGY_POST,
    "title": "Kyiv hydrology",
    "unique_id": f"hydrology:{HYDROLOGY_POST.post_id}",
}
