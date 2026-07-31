"""Runtime data types for UkrHMC."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from .api import UkrHMCClient
    from .coordinator import UkrHMCCoordinator


@dataclass(slots=True)
class UkrHMCRuntimeData:
    """Objects shared for the lifetime of a config entry."""

    api: UkrHMCClient
    coordinator: UkrHMCCoordinator


type UkrHMCConfigEntry = ConfigEntry[UkrHMCRuntimeData]
