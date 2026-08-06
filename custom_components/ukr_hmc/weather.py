"""Weather entity for UkrHMC."""

from __future__ import annotations

from datetime import UTC, datetime, time
from typing import TYPE_CHECKING, override
from zoneinfo import ZoneInfo

from homeassistant.components.weather import (
    Forecast,
    SingleCoordinatorWeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.const import (
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import callback

from .condition import hmc_condition_to_ha
from .const import ATTRIBUTION, WEATHER_SUBENTRY_TYPES
from .coordinator import UkrHMCCoordinator
from .entity import UkrHMCWeatherEntityMixin

if TYPE_CHECKING:
    from datetime import date

    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .data import UkrHMCConfigEntry

UKRAINE_TIME_ZONE = ZoneInfo("Europe/Kyiv")
LOCATION_SUPPORTED_FEATURES = (
    WeatherEntityFeature.FORECAST_HOURLY | WeatherEntityFeature.FORECAST_DAILY
)
STATION_SUPPORTED_FEATURES = (
    WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_TWICE_DAILY
)


def _as_utc(forecast_date: date, forecast_time: time) -> str:
    """Return a provider-local date and time as an RFC 3339 UTC string."""
    return (
        datetime.combine(
            forecast_date,
            forecast_time,
            tzinfo=UKRAINE_TIME_ZONE,
        )
        .astimezone(UTC)
        .isoformat()
    )


def _single_wind_speed(value: str) -> float | None:
    """Return a direct single wind value, never an inferred range value."""
    if not value or "-" in value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: UkrHMCConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up weather entities for configured locations."""
    coordinator = config_entry.runtime_data.coordinator
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type not in WEATHER_SUBENTRY_TYPES:
            continue
        async_add_entities(
            [UkrHMCWeather(coordinator, subentry)],
            config_subentry_id=subentry.subentry_id,
        )


class UkrHMCWeather(
    UkrHMCWeatherEntityMixin,
    SingleCoordinatorWeatherEntity[UkrHMCCoordinator],
):
    """Represent current and forecast weather for one configured location."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_name = None
    _attr_native_precipitation_unit = UnitOfPrecipitationDepth.MILLIMETERS
    _attr_native_pressure_unit = UnitOfPressure.MMHG
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_wind_speed_unit = UnitOfSpeed.METERS_PER_SECOND

    def __init__(
        self,
        coordinator: UkrHMCCoordinator,
        subentry: ConfigSubentry,
    ) -> None:
        """Initialize a weather entity."""
        super().__init__(coordinator, context=subentry.subentry_id)
        self._initialize_weather_source(subentry)
        self._attr_supported_features = (
            LOCATION_SUPPORTED_FEATURES
            if self._station_id is None
            else STATION_SUPPORTED_FEATURES
        )
        if self._station_id is None:
            self._attr_native_pressure_unit = UnitOfPressure.HPA
        self._attr_unique_id = subentry.subentry_id

    @property
    @override
    def condition(self) -> str | None:
        """Return the canonical current weather condition."""
        if self.current_forecast is not None:
            return hmc_condition_to_ha(
                self.current_forecast.condition,
                is_night=self.current_forecast.is_night,
            )
        if self.observation is None:
            return None
        return hmc_condition_to_ha(
            self.observation.condition,
            is_night=self._station_id in self.coordinator.data.night_station_ids,
        )

    @property
    @override
    def native_temperature(self) -> float | None:
        """Return current temperature."""
        if self.current_forecast is not None:
            return self.current_forecast.temperature
        return self.observation.temperature if self.observation else None

    @property
    @override
    def humidity(self) -> float | None:
        """Return current humidity."""
        if self.current_forecast is not None:
            return self.current_forecast.humidity
        return self.observation.humidity if self.observation else None

    @property
    @override
    def native_pressure(self) -> float | None:
        """Return current pressure."""
        if self.current_forecast is not None:
            return self.current_forecast.pressure
        return self.observation.pressure if self.observation else None

    @property
    @override
    def native_wind_speed(self) -> float | None:
        """Return current wind speed."""
        if self.current_forecast is not None:
            return self.current_forecast.wind_speed
        return self.observation.wind_speed if self.observation else None

    @property
    @override
    def wind_bearing(self) -> float | str | None:
        """Return current wind direction."""
        if self.current_forecast is not None:
            return (
                self.current_forecast.wind_direction
                if self.current_forecast.wind_direction is not None
                else self.current_forecast.wind_compass
            )
        return self.observation.wind.abbreviation if self.observation else None

    @property
    @override
    def native_wind_gust_speed(self) -> float | None:
        """Return current wind gust speed."""
        return self.current_forecast.wind_gust if self.current_forecast else None

    @property
    @override
    def native_dew_point(self) -> float | None:
        """Return current dew point."""
        return self.current_forecast.dew_point if self.current_forecast else None

    @callback
    @override
    def _async_forecast_daily(self) -> list[Forecast] | None:
        """Return direct provider daily values in native units."""
        if self._station_id is None:
            return [
                Forecast(
                    datetime=_as_utc(day.date, time.min),
                    condition=hmc_condition_to_ha(day.condition_day),
                    native_temperature=day.temperature_day,
                    native_templow=day.temperature_night,
                )
                for day in self.coordinator.data.location_forecasts[
                    self._subentry.subentry_id
                ].daily_forecasts
            ]

        return [
            Forecast(
                datetime=_as_utc(day.date, time.min),
                condition=hmc_condition_to_ha(day.condition_day),
                native_temperature=day.temperature_day,
                native_templow=day.temperature_night,
                native_wind_speed=_single_wind_speed(day.wind_speed_day),
                wind_bearing=day.wind_day.abbreviation,
            )
            for day in self.coordinator.data.forecasts.get(self._station_id, ())
        ]

    @callback
    @override
    def _async_forecast_hourly(self) -> list[Forecast] | None:
        """Return direct provider hourly location values in native units."""
        if self._station_id is not None:
            return None

        return [
            Forecast(
                datetime=hour.forecast_at.astimezone(UTC).isoformat(),
                condition=hmc_condition_to_ha(
                    hour.condition,
                    is_night=hour.is_night,
                ),
                native_temperature=hour.temperature,
                native_precipitation=hour.precipitation,
                native_pressure=hour.pressure,
                humidity=hour.humidity,
                native_dew_point=hour.dew_point,
                native_wind_speed=hour.wind_speed,
                native_wind_gust_speed=hour.wind_gust,
                wind_bearing=(
                    hour.wind_direction
                    if hour.wind_direction is not None
                    else hour.wind_compass
                ),
            )
            for hour in self.coordinator.data.location_forecasts[
                self._subentry.subentry_id
            ].hourly_forecasts
        ]

    @callback
    @override
    def _async_forecast_twice_daily(self) -> list[Forecast] | None:
        """Return direct provider day and night forecast periods."""
        if self._station_id is None:
            return None

        forecast: list[Forecast] = []
        for day in self.coordinator.data.forecasts.get(self._station_id, ()):
            if day.sunrise is not None:
                forecast.append(
                    Forecast(
                        datetime=_as_utc(day.date, day.sunrise),
                        condition=hmc_condition_to_ha(day.condition_day),
                        is_daytime=True,
                        native_temperature=day.temperature_day,
                        native_wind_speed=_single_wind_speed(day.wind_speed_day),
                        wind_bearing=day.wind_day.abbreviation,
                    )
                )
            if day.sunset is not None:
                forecast.append(
                    Forecast(
                        datetime=_as_utc(day.date, day.sunset),
                        condition=hmc_condition_to_ha(
                            day.condition_night,
                            is_night=True,
                        ),
                        is_daytime=False,
                        native_temperature=day.temperature_night,
                        native_wind_speed=_single_wind_speed(day.wind_speed_night),
                        wind_bearing=day.wind_night.abbreviation,
                    )
                )
        return forecast
