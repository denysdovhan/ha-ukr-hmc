# Provider schema drift diagnostics

Status: done

## Decision

Parsers can report accepted and rejected record counts using sanitized reason
codes (`missing_field`, `invalid_type`, `invalid_value`, `invalid_schema`) and
provider field keys. Values from rejected records are never retained.

The diagnostic representation has `telemetry_schema_version: 1` so tooling can
recognize future format changes. Non-finite numeric values such as NaN and
infinity are rejected instead of entering Home Assistant entity state.

## Initial coverage

Record-level counters cover weather, radiation, and hydrology observations.
Snow observation successes are counted; its existing all-or-nothing parser
continues to surface a product failure when the payload schema is invalid.

## Verification

Fixtures cover extra fields (accepted), a missing field, null, and NaN. Tests
also verify that schema counters and their format version appear in diagnostics.
