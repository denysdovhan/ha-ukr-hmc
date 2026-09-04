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
    DOMAIN,
    NAME,
    SUBENTRY_TYPE_HYDROLOGY_POST,
    SUBENTRY_TYPE_RADIATION_STATION,
    SUBENTRY_TYPE_SNOW_STATION,
    SUBENTRY_TYPE_WEATHER_LOCATION,
    SUBENTRY_TYPE_WEATHER_STATION,
    SUBENTRY_TYPES,
)


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


class UkrHMCConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure the UkrHMC service."""

    VERSION = 1
    _initial_subentry_type: str

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
    async def async_on_create_entry(
        self,
        result: ConfigFlowResult,
    ) -> ConfigFlowResult:
        """Open the selected weather flow after creating the service entry."""
        subentry_result = await self.hass.config_entries.subentries.async_init(
            (result["result"].entry_id, self._initial_subentry_type),
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
        """Choose the first weather resource."""
        return self.async_show_menu(
            step_id="user",
            menu_options=SUBENTRY_TYPES,
        )

    async def async_step_weather_station(
        self,
        _user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Create the provider entry before adding a weather station."""
        self._initial_subentry_type = SUBENTRY_TYPE_WEATHER_STATION
        return self.async_create_entry(title=NAME, data={})

    async def async_step_weather_location(
        self,
        _user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Create the provider entry before adding a weather location."""
        self._initial_subentry_type = SUBENTRY_TYPE_WEATHER_LOCATION
        return self.async_create_entry(title=NAME, data={})

    async def async_step_radiation_station(
        self,
        _user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Create the provider entry before adding a radiation station."""
        self._initial_subentry_type = SUBENTRY_TYPE_RADIATION_STATION
        return self.async_create_entry(title=NAME, data={})

    async def async_step_hydrology_post(
        self,
        _user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Create the provider entry before adding a hydrology post."""
        self._initial_subentry_type = SUBENTRY_TYPE_HYDROLOGY_POST
        return self.async_create_entry(title=NAME, data={})

    async def async_step_snow_station(
        self,
        _user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Create the provider entry before adding a snow station."""
        self._initial_subentry_type = SUBENTRY_TYPE_SNOW_STATION
        return self.async_create_entry(title=NAME, data={})


class WeatherLocationFlowHandler(ConfigSubentryFlow):
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

            if _is_duplicate(self._get_entry(), unique_id):
                return self.async_abort(reason="already_configured")

            title = str(user_input[CONF_NAME]).strip()
            if not title:
                title = f"{latitude:.4f}, {longitude:.4f}"

            try:
                await UkrHMCClient(
                    async_get_clientsession(self.hass)
                ).async_validate_location_forecast(
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
                return self.async_create_entry(
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
                user_input
                or {
                    CONF_NAME: self.hass.config.location_name,
                    CONF_LOCATION: {
                        CONF_LATITUDE: self.hass.config.latitude,
                        CONF_LONGITUDE: self.hass.config.longitude,
                    },
                },
            ),
            errors=errors,
        )


class WeatherStationFlowHandler(ConfigSubentryFlow):
    """Add weather from a physical station."""

    async def _async_get_stations(self) -> list[UkrHMCStation]:
        """Fetch stations for validation and selection."""
        stations = await UkrHMCClient(
            async_get_clientsession(self.hass)
        ).async_get_stations()
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
            if _is_duplicate(self._get_entry(), unique_id):
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
                user_input or {CONF_NAME: self.hass.config.location_name},
            ),
            errors=errors,
        )


class RadiationStationFlowHandler(ConfigSubentryFlow):
    """Add a physical radiation monitoring station."""

    async def _async_get_stations(
        self,
    ) -> list[UkrHMCRadiationStation]:
        """Fetch radiation stations with current observations."""
        stations, observations = await UkrHMCClient(
            async_get_clientsession(self.hass)
        ).async_get_radiation_data()
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
            if _is_duplicate(self._get_entry(), unique_id):
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
                user_input or {CONF_NAME: self.hass.config.location_name},
            ),
            errors=errors,
        )


class HydrologyPostFlowHandler(ConfigSubentryFlow):
    """Add a physical hydrology monitoring post."""

    async def _async_get_posts(self) -> list[UkrHMCHydrologyPost]:
        """Fetch hydrology posts with current observations."""
        posts, observations = await UkrHMCClient(
            async_get_clientsession(self.hass)
        ).async_get_hydrology_data()
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
            if _is_duplicate(self._get_entry(), unique_id):
                return self.async_abort(reason="already_configured")

            post = next((post for post in posts if post.post_id == post_id), None)
            if post is None:
                errors["base"] = "invalid_station"
            else:
                title = str(user_input[CONF_NAME]).strip() or post.name
                return self.async_create_entry(
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
                user_input or {CONF_NAME: self.hass.config.location_name},
            ),
            errors=errors,
        )


class SnowStationFlowHandler(ConfigSubentryFlow):
    """Add a physical snow and avalanche station."""

    async def _async_get_stations(self) -> list[UkrHMCSnowStation]:
        """Fetch snow stations with a current provider record."""
        stations, observations = await UkrHMCClient(
            async_get_clientsession(self.hass)
        ).async_get_snow_data()
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
            if _is_duplicate(self._get_entry(), unique_id):
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
                user_input or {CONF_NAME: self.hass.config.location_name},
            ),
            errors=errors,
        )
