"""Provider data models for UkrHMC."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import date, datetime, time


@dataclass(frozen=True, slots=True)
class UkrHMCWind:
    """Wind direction from the provider lookup table."""

    code: int
    abbreviation: str | None
    name: str | None


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
        return ", ".join(
            value for value in (self.cloudiness, self.precipitation_day) if value
        )

    @property
    def condition_night(self) -> str:
        """Return the provider's combined nighttime description."""
        return ", ".join(
            value for value in (self.cloudiness, self.precipitation_night) if value
        )


@dataclass(frozen=True, slots=True)
class UkrHMCData:
    """Complete provider snapshot."""

    stations: Mapping[int, UkrHMCStation]
    observations: Mapping[int, UkrHMCObservation]
    forecasts: Mapping[int, tuple[UkrHMCForecastDay, ...]]
    night_station_ids: frozenset[int]

    @classmethod
    def create(
        cls,
        *,
        stations: dict[int, UkrHMCStation],
        observations: dict[int, UkrHMCObservation],
        forecasts: dict[int, tuple[UkrHMCForecastDay, ...]],
        night_station_ids: frozenset[int],
    ) -> UkrHMCData:
        """Create an immutable provider snapshot."""
        return cls(
            stations=MappingProxyType(dict(stations)),
            observations=MappingProxyType(dict(observations)),
            forecasts=MappingProxyType(dict(forecasts)),
            night_station_ids=night_station_ids,
        )
