"""Config flow for UkrHMC."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

import voluptuous as vol
from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryData,
    ConfigSubentryFlow,
    OptionsFlow,
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
from homeassistant.loader import async_get_loaded_integration

from .api import (
    UkrHMCClient,
    UkrHMCDataError,
    UkrHMCError,
    UkrHMCHydrologyPost,
    UkrHMCLocationForecastRequest,
    UkrHMCRadiationStation,
    UkrHMCSnowStation,
    UkrHMCStation,
)
from .const import (
    CONF_STATION_ID,
    CONF_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    MAX_UPDATE_INTERVAL_MINUTES,
    MIN_UPDATE_INTERVAL_MINUTES,
    NAME,
    SUBENTRY_TYPE_HYDROLOGY_POST,
    SUBENTRY_TYPE_RADIATION_STATION,
    SUBENTRY_TYPE_SNOW_STATION,
    SUBENTRY_TYPE_WEATHER_LOCATION,
    SUBENTRY_TYPE_WEATHER_STATION,
    SUBENTRY_TYPES,
    UPDATE_INTERVAL,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


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


def _radiation_station_options(
    stations: list[UkrHMCRadiationStation],
) -> list[SelectOptionDict]:
    """Return available radiation stations sorted by name."""
    return [
        SelectOptionDict(
            label=station.name,
            value=str(station.station_id),
        )
        for station in sorted(stations, key=lambda station: station.name.casefold())
    ]


def _hydrology_post_options(
    posts: list[UkrHMCHydrologyPost],
) -> list[SelectOptionDict]:
    """Return available hydrology posts sorted by river and name."""
    return [
        SelectOptionDict(
            label=f"{post.name} — {post.river}",
            value=str(post.post_id),
        )
        for post in sorted(
            posts,
            key=lambda post: (post.river.casefold(), post.name.casefold()),
        )
    ]


def _snow_station_options(
    stations: list[UkrHMCSnowStation],
) -> list[SelectOptionDict]:
    """Return available snow stations sorted by name."""
    return [
        SelectOptionDict(label=station.name, value=str(station.station_id))
        for station in sorted(stations, key=lambda station: station.name.casefold())
    ]


def _is_duplicate(config_entry: ConfigEntry, unique_id: str) -> bool:
    """Return whether this configured resource already exists."""
    return any(
        subentry.unique_id == unique_id for subentry in config_entry.subentries.values()
    )


def _api_client(hass: HomeAssistant) -> UkrHMCClient:
    """Return a provider client carrying the installed integration version."""
    return UkrHMCClient(
        async_get_clientsession(hass),
        version=async_get_loaded_integration(hass, DOMAIN).version,
    )


class UkrHMCConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure the UkrHMC service."""

    VERSION = 1

    @staticmethod
    @callback
    @override
    def async_get_options_flow(config_entry: ConfigEntry) -> UkrHMCOptionsFlow:
        """Return service-level polling options."""
        return UkrHMCOptionsFlow()

    @classmethod
    @callback
    @override
    def async_get_supported_subentry_types(
        cls,
        config_entry: ConfigEntry,
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return supported config subentry flows."""
        return {
            SUBENTRY_TYPE_WEATHER_STATION: WeatherStationFlowHandler,
            SUBENTRY_TYPE_WEATHER_LOCATION: WeatherLocationFlowHandler,
            SUBENTRY_TYPE_RADIATION_STATION: RadiationStationFlowHandler,
            SUBENTRY_TYPE_HYDROLOGY_POST: HydrologyPostFlowHandler,
            SUBENTRY_TYPE_SNOW_STATION: SnowStationFlowHandler,
        }

    @override
    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Choose the first weather resource."""
        return self.async_show_menu(
            step_id="user",
            menu_options=SUBENTRY_TYPES,
        )

    async def async_step_weather_station(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Configure the first weather station atomically."""
        return await self._async_step_initial_subentry(
            SUBENTRY_TYPE_WEATHER_STATION, WeatherStationFlowHandler, user_input
        )

    async def async_step_weather_location(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Configure the first weather location atomically."""
        return await self._async_step_initial_subentry(
            SUBENTRY_TYPE_WEATHER_LOCATION, WeatherLocationFlowHandler, user_input
        )

    async def async_step_radiation_station(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Configure the first radiation station atomically."""
        return await self._async_step_initial_subentry(
            SUBENTRY_TYPE_RADIATION_STATION, RadiationStationFlowHandler, user_input
        )

    async def async_step_hydrology_post(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Configure the first hydrology post atomically."""
        return await self._async_step_initial_subentry(
            SUBENTRY_TYPE_HYDROLOGY_POST, HydrologyPostFlowHandler, user_input
        )

    async def async_step_snow_station(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Configure the first snow station atomically."""
        return await self._async_step_initial_subentry(
            SUBENTRY_TYPE_SNOW_STATION, SnowStationFlowHandler, user_input
        )

    async def _async_step_initial_subentry(
        self,
        subentry_type: str,
        handler_type: type[UkrHMCSubentryFlow],
        user_input: dict[str, Any] | None,
    ) -> ConfigFlowResult:
        """Run a subentry form before atomically creating the service entry."""
        handler = handler_type()
        handler.hass = self.hass
        handler.flow_id = self.flow_id
        handler.handler = self.handler
        handler.context = self.context
        handler.creating_initial_subentry = True
        result = await handler.async_step_user(user_input)
        if result["type"].value == "create_entry":
            return self.async_create_entry(
                title=NAME,
                data={},
                subentries=(
                    ConfigSubentryData(
                        data=result["data"],
                        subentry_type=subentry_type,
                        title=result["title"],
                        unique_id=result.get("unique_id"),
                    ),
                ),
            )
        result["step_id"] = subentry_type
        return result


class UkrHMCOptionsFlow(OptionsFlow):
    """Configure bounded service-level polling options."""

    @override
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure the provider polling interval."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current_interval = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL_MINUTES,
            int(UPDATE_INTERVAL.total_seconds() // 60),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_UPDATE_INTERVAL_MINUTES,
                        default=current_interval,
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(
                            min=MIN_UPDATE_INTERVAL_MINUTES,
                            max=MAX_UPDATE_INTERVAL_MINUTES,
                        ),
                    )
                }
            ),
        )


class UkrHMCSubentryFlow(ConfigSubentryFlow):
    """Base flow shared by initial and additional resources."""

    creating_initial_subentry = False

    def _is_duplicate(self, unique_id: str) -> bool:
        """Return whether a resource exists outside the initial atomic flow."""
        if self.creating_initial_subentry:
            return False
        excluded_id = (
            self._get_reconfigure_subentry().subentry_id
            if self.source == SOURCE_RECONFIGURE
            else None
        )
        return any(
            subentry.unique_id == unique_id and subentry.subentry_id != excluded_id
            for subentry in self._get_entry().subentries.values()
        )

    def _finish_resource(
        self,
        *,
        title: str,
        unique_id: str,
        data: dict[str, Any],
    ) -> SubentryFlowResult:
        """Create a resource or update and reload its existing subentry."""
        if self.source == SOURCE_RECONFIGURE:
            return self.async_update_and_abort(
                self._get_entry(),
                self._get_reconfigure_subentry(),
                title=title,
                unique_id=unique_id,
                data=data,
            )
        return self.async_create_entry(
            title=title,
            unique_id=unique_id,
            data=data,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Edit an existing resource with the same validated form."""
        return await self.async_step_user(user_input)


class WeatherLocationFlowHandler(UkrHMCSubentryFlow):
    """Add weather for a map location."""

    @override
    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        """Configure a forecast for a map location."""
        errors: dict[str, str] = {}
        if user_input is not None:
            latitude = float(user_input[CONF_LOCATION][CONF_LATITUDE])
            longitude = float(user_input[CONF_LOCATION][CONF_LONGITUDE])
            unique_id = f"location:{latitude:.6f}:{longitude:.6f}"

            if self._is_duplicate(unique_id):
                return self.async_abort(reason="already_configured")

            title = str(user_input[CONF_NAME]).strip()
            if not title:
                title = f"{latitude:.4f}, {longitude:.4f}"

            try:
                await _api_client(self.hass).async_validate_location_forecast(
                    UkrHMCLocationForecastRequest(
                        name=title,
                        latitude=latitude,
                        longitude=longitude,
                    )
                )
            except UkrHMCDataError:
                errors["base"] = "no_forecast"
            except UkrHMCError:
                errors["base"] = "cannot_connect"
            else:
                return self._finish_resource(
                    title=title,
                    unique_id=unique_id,
                    data={
                        CONF_NAME: title,
                        CONF_LATITUDE: latitude,
                        CONF_LONGITUDE: longitude,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_NAME): str,
                        vol.Required(CONF_LOCATION): LocationSelector(
                            LocationSelectorConfig(radius=False)
                        ),
                    }
                ),
                user_input or self._suggested_values(),
            ),
            errors=errors,
        )

    def _suggested_values(self) -> dict[str, Any]:
        """Return current values for reconfigure or Home defaults for add."""
        if self.source == SOURCE_RECONFIGURE:
            subentry = self._get_reconfigure_subentry()
            return {
                CONF_NAME: subentry.title,
                CONF_LOCATION: {
                    CONF_LATITUDE: subentry.data[CONF_LATITUDE],
                    CONF_LONGITUDE: subentry.data[CONF_LONGITUDE],
                },
            }
        return {
            CONF_NAME: self.hass.config.location_name,
            CONF_LOCATION: {
                CONF_LATITUDE: self.hass.config.latitude,
                CONF_LONGITUDE: self.hass.config.longitude,
            },
        }


class WeatherStationFlowHandler(UkrHMCSubentryFlow):
    """Add weather from a physical station."""

    async def _async_get_stations(self) -> list[UkrHMCStation]:
        """Fetch stations for validation and selection."""
        stations = await _api_client(self.hass).async_get_stations()
        return list(stations.values())

    @override
    async def async_step_user(
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
                return self._finish_resource(
                    title=title,
                    unique_id=unique_id,
                    data={CONF_STATION_ID: station.station_id},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
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
                user_input or self._station_suggested_values(),
            ),
            errors=errors,
        )

    def _station_suggested_values(self) -> dict[str, Any]:
        """Return current station values or defaults for a new resource."""
        if self.source == SOURCE_RECONFIGURE:
            subentry = self._get_reconfigure_subentry()
            return {
                CONF_NAME: subentry.title,
                CONF_STATION_ID: str(subentry.data[CONF_STATION_ID]),
            }
        return {CONF_NAME: self.hass.config.location_name}


class RadiationStationFlowHandler(UkrHMCSubentryFlow):
    """Add a physical radiation monitoring station."""

    async def _async_get_stations(
        self,
    ) -> list[UkrHMCRadiationStation]:
        """Fetch radiation stations with current observations."""
        stations, observations = await _api_client(self.hass).async_get_radiation_data()
        return [
            station
            for station_id, station in stations.items()
            if station_id in observations
        ]

    @override
    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        """Add an explicit radiation station."""
        errors: dict[str, str] = {}
        try:
            stations = await self._async_get_stations()
        except UkrHMCError:
            stations = []
            errors["base"] = "cannot_connect"

        if user_input is not None and not errors:
            station_id = int(user_input[CONF_STATION_ID])
            unique_id = f"radiation:{station_id}"
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
                return self._finish_resource(
                    title=title,
                    unique_id=unique_id,
                    data={CONF_STATION_ID: station.station_id},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_NAME): str,
                        vol.Required(CONF_STATION_ID): SelectSelector(
                            SelectSelectorConfig(
                                options=_radiation_station_options(stations),
                                mode=SelectSelectorMode.DROPDOWN,
                            )
                        ),
                    }
                ),
                user_input or self._station_suggested_values(),
            ),
            errors=errors,
        )

    def _station_suggested_values(self) -> dict[str, Any]:
        """Return current station values or defaults for a new resource."""
        if self.source == SOURCE_RECONFIGURE:
            subentry = self._get_reconfigure_subentry()
            return {
                CONF_NAME: subentry.title,
                CONF_STATION_ID: str(subentry.data[CONF_STATION_ID]),
            }
        return {CONF_NAME: self.hass.config.location_name}


class HydrologyPostFlowHandler(UkrHMCSubentryFlow):
    """Add a physical hydrology monitoring post."""

    async def _async_get_posts(self) -> list[UkrHMCHydrologyPost]:
        """Fetch hydrology posts with current observations."""
        posts, observations = await _api_client(self.hass).async_get_hydrology_data()
        return [post for post_id, post in posts.items() if post_id in observations]

    @override
    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        """Add an explicit hydrology post."""
        errors: dict[str, str] = {}
        try:
            posts = await self._async_get_posts()
        except UkrHMCError:
            posts = []
            errors["base"] = "cannot_connect"

        if user_input is not None and not errors:
            post_id = int(user_input[CONF_STATION_ID])
            unique_id = f"hydrology:{post_id}"
            if self._is_duplicate(unique_id):
                return self.async_abort(reason="already_configured")

            post = next((post for post in posts if post.post_id == post_id), None)
            if post is None:
                errors["base"] = "invalid_station"
            else:
                title = str(user_input[CONF_NAME]).strip() or post.name
                return self._finish_resource(
                    title=title,
                    unique_id=unique_id,
                    data={CONF_STATION_ID: post.post_id},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_NAME): str,
                        vol.Required(CONF_STATION_ID): SelectSelector(
                            SelectSelectorConfig(
                                options=_hydrology_post_options(posts),
                                mode=SelectSelectorMode.DROPDOWN,
                            )
                        ),
                    }
                ),
                user_input or self._station_suggested_values(),
            ),
            errors=errors,
        )

    def _station_suggested_values(self) -> dict[str, Any]:
        """Return current post values or defaults for a new resource."""
        if self.source == SOURCE_RECONFIGURE:
            subentry = self._get_reconfigure_subentry()
            return {
                CONF_NAME: subentry.title,
                CONF_STATION_ID: str(subentry.data[CONF_STATION_ID]),
            }
        return {CONF_NAME: self.hass.config.location_name}


class SnowStationFlowHandler(UkrHMCSubentryFlow):
    """Add a physical snow and avalanche station."""

    async def _async_get_stations(self) -> list[UkrHMCSnowStation]:
        """Fetch snow stations with a current provider record."""
        stations, observations = await _api_client(self.hass).async_get_snow_data()
        return [
            station
            for station_id, station in stations.items()
            if station_id in observations
        ]

    @override
    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        """Add an explicit snow and avalanche station."""
        errors: dict[str, str] = {}
        try:
            stations = await self._async_get_stations()
        except UkrHMCError:
            stations = []
            errors["base"] = "cannot_connect"

        if user_input is not None and not errors:
            station_id = int(user_input[CONF_STATION_ID])
            unique_id = f"snow:{station_id}"
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
                return self._finish_resource(
                    title=title,
                    unique_id=unique_id,
                    data={CONF_STATION_ID: station.station_id},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_NAME): str,
                        vol.Required(CONF_STATION_ID): SelectSelector(
                            SelectSelectorConfig(
                                options=_snow_station_options(stations),
                                mode=SelectSelectorMode.DROPDOWN,
                            )
                        ),
                    }
                ),
                user_input or self._station_suggested_values(),
            ),
            errors=errors,
        )

    def _station_suggested_values(self) -> dict[str, Any]:
        """Return current station values or defaults for a new resource."""
        if self.source == SOURCE_RECONFIGURE:
            subentry = self._get_reconfigure_subentry()
            return {
                CONF_NAME: subentry.title,
                CONF_STATION_ID: str(subentry.data[CONF_STATION_ID]),
            }
        return {CONF_NAME: self.hass.config.location_name}
