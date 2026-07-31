"""Station selection helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.util import location

from .const import (
    CONF_STATION_ID,
    CONF_STATION_TYPE,
    STATION_TYPE_DYNAMIC,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigSubentry

    from .api import UkrHMCData, UkrHMCStation


def distance_to_station(
    latitude: float,
    longitude: float,
    station: UkrHMCStation,
) -> float:
    """Return distance to a station or infinity."""
    distance = location.distance(
        latitude,
        longitude,
        station.latitude,
        station.longitude,
    )
    return distance if distance is not None else float("inf")


def nearest_station(
    stations: list[UkrHMCStation],
    latitude: float,
    longitude: float,
) -> UkrHMCStation:
    """Return the nearest physical station."""
    if not stations:
        msg = "No stations available"
        raise ValueError(msg)
    return min(
        stations,
        key=lambda station: distance_to_station(latitude, longitude, station),
    )


def resolve_station_id(
    data: UkrHMCData,
    subentry: ConfigSubentry,
) -> int | None:
    """Resolve an explicit or nearest station subentry."""
    if subentry.data.get(CONF_STATION_TYPE) != STATION_TYPE_DYNAMIC:
        station_id = subentry.data.get(CONF_STATION_ID)
        return int(station_id) if station_id is not None else None

    if not data.stations:
        return None
    return nearest_station(
        list(data.stations.values()),
        float(subentry.data[CONF_LATITUDE]),
        float(subentry.data[CONF_LONGITUDE]),
    ).station_id
