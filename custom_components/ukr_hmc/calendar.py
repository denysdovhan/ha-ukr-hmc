"""Read-only UkrHMC warning calendars."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    ATTRIBUTION,
    CONF_STATION_ID,
    DOMAIN,
    HYDROLOGY_CONFIGURATION_URL,
    MANUFACTURER,
    SUBENTRY_TYPE_HYDROLOGY_POST,
    SUBENTRY_TYPE_WEATHER_LOCATION,
    SUBENTRY_TYPE_WEATHER_STATION,
)
from .coordinator import UkrHMCCoordinator
from .entity import UkrHMCEntity

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import datetime

    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .api import UkrHMCWeatherWarning
    from .data import UkrHMCConfigEntry


class UkrHMCWarningCalendar(UkrHMCEntity, CalendarEntity):
    """Expose provider warning validity periods as calendar events."""

    _attr_translation_key = "warning_calendar"
    _attr_icon = "mdi:calendar-alert"

    def __init__(
        self,
        coordinator: UkrHMCCoordinator,
        subentry: ConfigSubentry,
    ) -> None:
        """Initialize the warning calendar."""
        super().__init__(coordinator, subentry)
        self._attr_unique_id = f"{subentry.subentry_id}-warning_calendar"

    @property
    @override
    def available(self) -> bool:
        """Keep warnings independent from current observation freshness."""
        return self.coordinator.last_update_success

    def _region_ids(self) -> tuple[int | None, int | None, int | None]:
        """Return meteorological, fire, and avalanche regions for this source."""
        station = self.coordinator.data.stations.get(self._station_id)
        if station is not None:
            return (
                station.region_id,
                station.region_id,
                self.coordinator.data.station_snow_region_ids.get(self._station_id),
            )
        subentry_id = self._subentry.subentry_id
        return (
            self.coordinator.data.location_region_ids.get(subentry_id),
            self.coordinator.data.location_fire_region_ids.get(subentry_id),
            self.coordinator.data.location_snow_region_ids.get(subentry_id),
        )

    def _warning_groups(
        self,
    ) -> Iterable[tuple[str, tuple[UkrHMCWeatherWarning, ...]]]:
        """Return warnings matched to the configured source."""
        weather_region, fire_region, snow_region = self._region_ids()
        yield (
            "Метеорологічне попередження",
            self.coordinator.data.regional_weather_warnings.get(weather_region, ()),
        )
        yield (
            "Пожежна небезпека",
            self.coordinator.data.regional_fire_warnings.get(fire_region, ()),
        )
        yield (
            "Сніголавинна небезпека",
            self.coordinator.data.regional_snow_warnings.get(snow_region, ()),
        )

    def _events(self) -> list[CalendarEvent]:
        """Convert cached provider warnings to ordered calendar events."""
        events = []
        for warning_type, warnings in self._warning_groups():
            for warning in warnings:
                if warning.starts_at is None or warning.ends_at is None:
                    continue
                detail = warning.description or f"Рівень {warning.danger_level}"
                events.append(
                    CalendarEvent(
                        start=warning.starts_at,
                        end=warning.ends_at,
                        summary=f"{warning_type}: {detail}",
                        description=(
                            f"Період УкрГМЦ: {warning.period}\n"
                            f"Рівень: {warning.danger_level}"
                        ),
                        location=self._subentry.title,
                        uid=(
                            f"ukr-hmc-{warning_type}-{warning.region_id}-"
                            f"{warning.danger_level}-{warning.starts_at.isoformat()}"
                        ),
                    )
                )
        return sorted(events, key=lambda item: item.start)

    @property
    @override
    def event(self) -> CalendarEvent | None:
        """Return the active or next provider warning."""
        now = dt_util.now()
        return next((event for event in self._events() if event.end > now), None)

    async def async_get_events(
        self,
        hass: HomeAssistant,  # noqa: ARG002
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return cached warning events overlapping a requested interval."""
        return [
            event
            for event in self._events()
            if event.end > start_date and event.start < end_date
        ]


class UkrHMCHydrologyWarningCalendar(
    CoordinatorEntity[UkrHMCCoordinator], CalendarEntity
):
    """Expose hydrological warning periods for one configured post."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_translation_key = "hydrology_warning_calendar"
    _attr_icon = "mdi:calendar-alert"

    def __init__(
        self, coordinator: UkrHMCCoordinator, subentry: ConfigSubentry
    ) -> None:
        """Initialize the hydrological warning calendar."""
        super().__init__(coordinator, context=subentry.subentry_id)
        self._subentry = subentry
        self._post_id = int(subentry.data[CONF_STATION_ID])
        self._attr_unique_id = f"{subentry.subentry_id}-hydrology_warning_calendar"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the hydrology post device metadata."""
        return DeviceInfo(
            configuration_url=HYDROLOGY_CONFIGURATION_URL,
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._subentry.subentry_id)},
            manufacturer=MANUFACTURER,
            model=f"UkrHMC Hydrology Post {self._post_id}",
            name=self._subentry.title,
        )

    def _events(self) -> list[CalendarEvent]:
        """Convert cached hydrological warnings to ordered events."""
        region_id = self.coordinator.data.hydrology_post_warning_region_ids.get(
            self._post_id
        )
        warnings = self.coordinator.data.regional_hydrology_warnings.get(region_id, ())
        events = []
        for warning in warnings:
            if warning.starts_at is None or warning.ends_at is None:
                continue
            events.append(
                CalendarEvent(
                    start=warning.starts_at,
                    end=warning.ends_at,
                    summary=warning.phenomenon or "Гідрологічне попередження",
                    description=(
                        f"{warning.description}\n\n"
                        f"Басейн: {warning.basin_name}\n"
                        f"Річка поста: "
                        f"{self.coordinator.data.hydrology_posts[self._post_id].river}\n"
                        f"Рівень: {warning.danger_level}\n"
                        f"Період УкрГМЦ: {warning.period}"
                    ),
                    location=warning.basin_name,
                    uid=(
                        f"ukr-hmc-hydrology-{warning.region_id}-"
                        f"{warning.danger_level}-{warning.starts_at.isoformat()}"
                    ),
                )
            )
        return sorted(events, key=lambda item: item.start)

    @property
    @override
    def event(self) -> CalendarEvent | None:
        """Return the active or next hydrological warning."""
        now = dt_util.now()
        return next((event for event in self._events() if event.end > now), None)

    async def async_get_events(
        self,
        hass: HomeAssistant,  # noqa: ARG002
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return cached events overlapping a requested interval."""
        return [
            event
            for event in self._events()
            if event.end > start_date and event.start < end_date
        ]


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: UkrHMCConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one warning calendar per configured weather source."""
    coordinator = config_entry.runtime_data.coordinator
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type == SUBENTRY_TYPE_HYDROLOGY_POST:
            async_add_entities(
                [UkrHMCHydrologyWarningCalendar(coordinator, subentry)],
                config_subentry_id=subentry.subentry_id,
            )
            continue
        if subentry.subentry_type not in (
            SUBENTRY_TYPE_WEATHER_STATION,
            SUBENTRY_TYPE_WEATHER_LOCATION,
        ):
            continue
        async_add_entities(
            [UkrHMCWarningCalendar(coordinator, subentry)],
            config_subentry_id=subentry.subentry_id,
        )
