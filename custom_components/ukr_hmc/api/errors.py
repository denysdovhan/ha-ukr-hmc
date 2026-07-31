"""Exceptions raised by the UkrHMC API client."""


class UkrHMCError(Exception):
    """Base UkrHMC error."""


class UkrHMCConnectionError(UkrHMCError):
    """Raised when UkrHMC cannot be reached."""


class UkrHMCDataError(UkrHMCError):
    """Raised when UkrHMC returns invalid data."""
