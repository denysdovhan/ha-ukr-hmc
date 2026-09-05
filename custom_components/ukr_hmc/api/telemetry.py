"""Privacy-safe provider schema diagnostics."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


class SchemaTelemetry:
    """Collect parser outcomes without retaining provider values."""

    def __init__(self) -> None:
        """Initialize empty counters."""
        self._accepted: Counter[str] = Counter()
        self._rejected: Counter[str] = Counter()
        self._reasons: dict[str, Counter[str]] = defaultdict(Counter)
        self._keys: dict[str, Counter[str]] = defaultdict(Counter)

    def accepted(self, product: str, count: int = 1) -> None:
        """Record accepted provider records."""
        self._accepted[product] += count

    def rejected(self, product: str, exc: BaseException, count: int = 1) -> None:
        """Record a rejected record using sanitized reason and key codes."""
        reason = {
            KeyError: "missing_field",
            TypeError: "invalid_type",
            ValueError: "invalid_value",
        }.get(type(exc), "invalid_schema")
        self._rejected[product] += count
        self._reasons[product][reason] += count
        if isinstance(exc, KeyError) and exc.args:
            self._keys[product][str(exc.args[0])] += count

    def snapshot(self) -> dict[str, dict[str, Any]]:
        """Return deterministic, serialization-safe diagnostics."""
        products = self._accepted.keys() | self._rejected.keys()
        snapshot = {
            product: {
                "accepted": self._accepted[product],
                "rejected": self._rejected[product],
                "reason_counts": dict(sorted(self._reasons[product].items())),
                "affected_keys": dict(sorted(self._keys[product].items())),
            }
            for product in sorted(products)
        }
        return {"_meta": {"telemetry_schema_version": 1}, **snapshot}
