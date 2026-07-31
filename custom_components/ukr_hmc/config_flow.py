"""Config flow for UkrHMC."""

from typing import Any, override

import voluptuous as vol
from homeassistant.config_entries import (
    SOURCE_USER,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    FlowType,
    SubentryFlowContext,
    SubentryFlowResult,
)
from homeassistant.const import CONF_LATITUDE, CONF_LOCATION, CONF_LONGITUDE, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    LocationSelector,
    LocationSelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import UkrHMCClient, UkrHMCError, UkrHMCStation
from .const import (
    CONF_STATION_ID,
    CONF_STATION_TYPE,
    DOMAIN,
    NAME,
    STATION_TYPE_DYNAMIC,
    STATION_TYPE_STATIC,
    SUBENTRY_TYPE_STATION,
)
from .helpers import nearest_station


def _station_options(stations: list[UkrHMCStation]) -> list[SelectOptionDict]:
    """Return stations sorted by region and station name."""
    return [
        SelectOptionDict(
            label=f"{station.name} — {station.region_name}",
            value=str(station.station_id),
        )
        for station in sorted(
            stations,
            key=lambda station: (
                station.region_name.casefold(),
                station.name.casefold(),
            ),
        )
    ]


class UkrHMCConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure the UkrHMC service."""

    VERSION = 1

    @classmethod
    @callback
    @override
    def async_get_supported_subentry_types(
        cls,
        config_entry: ConfigEntry,
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return supported config subentry flows."""
        return {SUBENTRY_TYPE_STATION: StationFlowHandler}

    @override
    async def async_on_create_entry(
        self,
        result: ConfigFlowResult,
    ) -> ConfigFlowResult:
        """Open the station flow after creating the service entry."""
        subentry_result = await self.hass.config_entries.subentries.async_init(
            (result["result"].entry_id, SUBENTRY_TYPE_STATION),
            context=SubentryFlowContext(source=SOURCE_USER),
        )
        result["next_flow"] = (
            FlowType.CONFIG_SUBENTRIES_FLOW,
            subentry_result["flow_id"],
        )
        return result

    @override
    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Set up the provider and test access before configuration."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}
        try:
            stations = await UkrHMCClient(
                async_get_clientsession(self.hass)
            ).async_get_stations()
            if not stations:
                errors["base"] = "no_stations"
        except UkrHMCError:
            errors["base"] = "cannot_connect"

        if not errors:
            return self.async_create_entry(title=NAME, data={})

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            errors=errors,
        )


class StationFlowHandler(ConfigSubentryFlow):
    """Add a physical meteorological station selection."""

    async def _async_get_stations(self) -> list[UkrHMCStation]:
        """Fetch stations for validation and selection."""
        stations = await UkrHMCClient(
            async_get_clientsession(self.hass)
        ).async_get_stations()
        return list(stations.values())

    def _is_duplicate(self, unique_id: str) -> bool:
        """Return whether this station selection already exists."""
        return any(
            subentry.unique_id == unique_id
            for subentry in self._get_entry().subentries.values()
        )

    @override
    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        """Choose how to select a station."""
        return self.async_show_menu(
            step_id="user",
            menu_options=("map", "station"),
        )

    async def async_step_map(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        """Add a dynamic nearest-station selection."""
        errors: dict[str, str] = {}
        if user_input is not None:
            latitude = float(user_input[CONF_LOCATION][CONF_LATITUDE])
            longitude = float(user_input[CONF_LOCATION][CONF_LONGITUDE])
            unique_id = f"location:{latitude:.6f}:{longitude:.6f}"

            if self._is_duplicate(unique_id):
                return self.async_abort(reason="already_configured")

            try:
                station = nearest_station(
                    await self._async_get_stations(),
                    latitude,
                    longitude,
                )
            except UkrHMCError:
                errors["base"] = "cannot_connect"
            except ValueError:
                errors["base"] = "no_stations"
            else:
                title = str(user_input[CONF_NAME]).strip() or station.name
                return self.async_create_entry(
                    title=title,
                    unique_id=unique_id,
                    data={
                        CONF_STATION_TYPE: STATION_TYPE_DYNAMIC,
                        CONF_LATITUDE: latitude,
                        CONF_LONGITUDE: longitude,
                    },
                )

        return self.async_show_form(
            step_id="map",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_NAME): str,
                        vol.Required(CONF_LOCATION): LocationSelector(
                            LocationSelectorConfig(radius=False)
                        ),
                    }
                ),
                {
                    CONF_LOCATION: {
                        CONF_LATITUDE: self.hass.config.latitude,
                        CONF_LONGITUDE: self.hass.config.longitude,
                    }
                },
            ),
            errors=errors,
        )

    async def async_step_station(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        """Add an explicit physical station."""
        errors: dict[str, str] = {}
        try:
            stations = await self._async_get_stations()
        except UkrHMCError:
            stations = []
            errors["base"] = "cannot_connect"

        if user_input is not None and not errors:
            station_id = int(user_input[CONF_STATION_ID])
            unique_id = f"station:{station_id}"
            if self._is_duplicate(unique_id):
                return self.async_abort(reason="already_configured")

            station = next(
                (station for station in stations if station.station_id == station_id),
                None,
            )
            if station is None:
                errors["base"] = "invalid_station"
            else:
                title = str(user_input[CONF_NAME]).strip() or station.name
                return self.async_create_entry(
                    title=title,
                    unique_id=unique_id,
                    data={
                        CONF_STATION_TYPE: STATION_TYPE_STATIC,
                        CONF_STATION_ID: station.station_id,
                    },
                )

        return self.async_show_form(
            step_id="station",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME): str,
                    vol.Required(CONF_STATION_ID): SelectSelector(
                        SelectSelectorConfig(
                            options=_station_options(stations),
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            errors=errors,
        )
