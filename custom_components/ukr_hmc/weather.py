"""Weather entity for Ukrhydrometcenter."""

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
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import callback

from .condition import hmc_condition_to_ha
from .const import ATTRIBUTION
from .coordinator import UkrHMCCoordinator
from .entity import UkrHMCStationEntityMixin

if TYPE_CHECKING:
    from datetime import date

    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .data import UkrHMCConfigEntry

UKRAINE_TIME_ZONE = ZoneInfo("Europe/Kyiv")


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
    """Set up weather entities for station subentries."""
    coordinator = config_entry.runtime_data.coordinator
    for subentry in config_entry.subentries.values():
        async_add_entities(
            [UkrHMCWeather(coordinator, subentry)],
            config_subentry_id=subentry.subentry_id,
        )


class UkrHMCWeather(
    UkrHMCStationEntityMixin,
    SingleCoordinatorWeatherEntity[UkrHMCCoordinator],
):
    """Represent current and forecast weather for one station selection."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_name = None
    _attr_native_pressure_unit = UnitOfPressure.MMHG
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_wind_speed_unit = UnitOfSpeed.METERS_PER_SECOND
    _attr_supported_features = (
        WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_TWICE_DAILY
    )

    def __init__(
        self,
        coordinator: UkrHMCCoordinator,
        subentry: ConfigSubentry,
    ) -> None:
        """Initialize a station weather entity."""
        super().__init__(coordinator, context=subentry.subentry_id)
        self._initialize_station(subentry)
        self._attr_unique_id = subentry.subentry_id

    @property
    @override
    def condition(self) -> str | None:
        """Return the canonical current weather condition."""
        if self.observation is None or self._station_id is None:
            return None
        return hmc_condition_to_ha(
            self.observation.condition,
            is_night=self._station_id in self.coordinator.data.night_station_ids,
        )

    @property
    @override
    def native_temperature(self) -> float | None:
        """Return current temperature."""
        return self.observation.temperature if self.observation else None

    @property
    @override
    def humidity(self) -> float | None:
        """Return current humidity."""
        return self.observation.humidity if self.observation else None

    @property
    @override
    def native_pressure(self) -> float | None:
        """Return current pressure."""
        return self.observation.pressure if self.observation else None

    @property
    @override
    def native_wind_speed(self) -> float | None:
        """Return current wind speed."""
        return self.observation.wind_speed if self.observation else None

    @property
    @override
    def wind_bearing(self) -> str | None:
        """Return current cardinal wind direction."""
        return self.observation.wind.abbreviation if self.observation else None

    @callback
    @override
    def _async_forecast_daily(self) -> list[Forecast] | None:
        """Return direct provider daily values in native units."""
        if self._station_id is None:
            return None

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
