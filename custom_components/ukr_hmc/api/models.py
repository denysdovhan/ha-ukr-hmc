"""Provider data models for UkrHMC."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

from .const import WIND_BEARINGS

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import date, datetime, time


@dataclass(frozen=True, slots=True)
class UkrHMCWind:
    """Wind direction from the provider lookup table."""

    code: int
    abbreviation: str | None
    name: str | None

    @property
    def bearing(self) -> float | None:
        """Return the provider compass abbreviation as a standard bearing."""
        if self.abbreviation is None:
            return None
        return WIND_BEARINGS.get(self.abbreviation)


@dataclass(frozen=True, slots=True)
class UkrHMCLookups:
    """Provider lookup tables."""

    condition_titles: tuple[str, ...]
    cloud_titles: tuple[str, ...]
    winds: tuple[UkrHMCWind, ...]


@dataclass(frozen=True, slots=True)
class UkrHMCStation:
    """Physical meteorological station."""

    station_id: int
    region_id: int
    region_name: str
    name: str
    latitude: float
    longitude: float
    altitude: int


@dataclass(frozen=True, slots=True)
class UkrHMCRadiationStation:
    """Physical radiation monitoring station."""

    station_id: int
    name: str
    latitude: float
    longitude: float
    altitude: int


@dataclass(frozen=True, slots=True)
class UkrHMCRadiationObservation:
    """Latest radiation observation for one station."""

    observed_at: datetime
    exposure_dose_rate: float
    dose_rate: float


@dataclass(frozen=True, slots=True)
class UkrHMCHydrologyPost:
    """Physical hydrology monitoring post."""

    post_id: int
    river: str
    name: str
    latitude: float
    longitude: float


@dataclass(frozen=True, slots=True)
class UkrHMCHydrologyObservation:
    """Latest daily hydrology observation for one post."""

    observed_at: datetime
    water_level: float
    water_level_altitude: float
    water_level_change: float
    water_temperature: float
    level_class: int


@dataclass(frozen=True, slots=True)
class UkrHMCLocationForecastRequest:
    """Location accepted by the provider's forecast endpoint."""

    name: str
    latitude: float
    longitude: float


@dataclass(frozen=True, slots=True)
class UkrHMCHourlyForecast:
    """Hourly forecast fields published for a location."""

    forecast_at: datetime
    temperature: float
    precipitation: float | None
    condition: str
    weather: str
    is_night: bool
    wind_compass: str | None
    wind_speed: float | None
    wind_gust: float | None
    humidity: float | None
    pressure: float | None
    wind_direction: float | None
    dew_point: float | None

    @property
    def wind_bearing(self) -> float | None:
        """Return the numeric bearing or convert the provider compass value."""
        if self.wind_direction is not None:
            return self.wind_direction
        if self.wind_compass is None:
            return None
        return WIND_BEARINGS.get(self.wind_compass)


@dataclass(frozen=True, slots=True)
class UkrHMCLocationForecastDay:
    """Day and night values used by the provider's location daily cards."""

    date: date
    temperature_night: float
    temperature_day: float
    condition_night: str
    condition_day: str
    weather_night: str
    weather_day: str


@dataclass(frozen=True, slots=True)
class UkrHMCLocationForecast:
    """Current, hourly, and daily forecasts for one location."""

    current: UkrHMCHourlyForecast | None
    hourly_forecasts: tuple[UkrHMCHourlyForecast, ...]
    daily_forecasts: tuple[UkrHMCLocationForecastDay, ...]


@dataclass(frozen=True, slots=True)
class UkrHMCObservation:
    """Latest observation for a station."""

    observed_at: datetime
    temperature: float
    humidity: float
    pressure: float
    wind_speed: float
    wind: UkrHMCWind
    condition: str
    icon_code_day: int
    icon_code_night: int
    phenomenon_code: int
    indicator_code: int
    sunrise: time | None
    sunset: time | None


@dataclass(frozen=True, slots=True)
class UkrHMCForecastDay:
    """Forecast fields published for one station and date."""

    date: date
    temperature_night: float | None
    temperature_day: float | None
    temperature_night_from: float | None
    temperature_night_to: float | None
    temperature_day_from: float | None
    temperature_day_to: float | None
    icon_code_day: int | None
    icon_code_night: int | None
    cloudiness: str
    cloudiness_en: str
    precipitation_day: str
    precipitation_day_en: str
    precipitation_night: str
    precipitation_night_en: str
    wind_day: UkrHMCWind
    wind_speed_day: str
    wind_night: UkrHMCWind
    wind_speed_night: str
    sunrise: time | None
    sunset: time | None
    provider_code: int | None

    @property
    def condition_day(self) -> str:
        """Return the provider's combined daytime description."""
        conditions = []
        if self.cloudiness:
            conditions.append(self.cloudiness)
        if self.precipitation_day:
            conditions.append(self.precipitation_day)
        return ", ".join(conditions)

    @property
    def condition_night(self) -> str:
        """Return the provider's combined nighttime description."""
        conditions = []
        if self.cloudiness:
            conditions.append(self.cloudiness)
        if self.precipitation_night:
            conditions.append(self.precipitation_night)
        return ", ".join(conditions)


@dataclass(frozen=True, slots=True)
class UkrHMCData:
    """Complete provider snapshot."""

    stations: Mapping[int, UkrHMCStation]
    observations: Mapping[int, UkrHMCObservation]
    forecasts: Mapping[int, tuple[UkrHMCForecastDay, ...]]
    location_forecasts: Mapping[str, UkrHMCLocationForecast]
    night_station_ids: frozenset[int]
    radiation_stations: Mapping[int, UkrHMCRadiationStation]
    radiation_observations: Mapping[int, UkrHMCRadiationObservation]
    hydrology_posts: Mapping[int, UkrHMCHydrologyPost]
    hydrology_observations: Mapping[int, UkrHMCHydrologyObservation]
    alert_flags: Mapping[str, bool]

    @classmethod
    def create(  # noqa: PLR0913
        cls,
        *,
        stations: dict[int, UkrHMCStation],
        observations: dict[int, UkrHMCObservation],
        forecasts: dict[int, tuple[UkrHMCForecastDay, ...]],
        location_forecasts: dict[str, UkrHMCLocationForecast],
        night_station_ids: frozenset[int],
        radiation_stations: dict[int, UkrHMCRadiationStation],
        radiation_observations: dict[int, UkrHMCRadiationObservation],
        hydrology_posts: dict[int, UkrHMCHydrologyPost],
        hydrology_observations: dict[int, UkrHMCHydrologyObservation],
        alert_flags: dict[str, bool],
    ) -> UkrHMCData:
        """Create an immutable provider snapshot."""
        return cls(
            stations=MappingProxyType(dict(stations)),
            observations=MappingProxyType(dict(observations)),
            forecasts=MappingProxyType(dict(forecasts)),
            location_forecasts=MappingProxyType(dict(location_forecasts)),
            night_station_ids=night_station_ids,
            radiation_stations=MappingProxyType(dict(radiation_stations)),
            radiation_observations=MappingProxyType(dict(radiation_observations)),
            hydrology_posts=MappingProxyType(dict(hydrology_posts)),
            hydrology_observations=MappingProxyType(dict(hydrology_observations)),
            alert_flags=MappingProxyType(dict(alert_flags)),
        )
