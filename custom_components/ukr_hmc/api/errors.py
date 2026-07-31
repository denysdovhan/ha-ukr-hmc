"""Exceptions raised by the Ukrhydrometcenter API client."""


class UkrHMCError(Exception):
    """Base Ukrhydrometcenter error."""


class UkrHMCConnectionError(UkrHMCError):
    """Raised when Ukrhydrometcenter cannot be reached."""


class UkrHMCDataError(UkrHMCError):
    """Raised when Ukrhydrometcenter returns invalid data."""
