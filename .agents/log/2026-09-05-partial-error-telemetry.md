# Partial-error telemetry

Status: done

## Decision

Every provider HTTP request records privacy-safe operational telemetry keyed by
endpoint path: availability, total duration, attempt count, HTTP status and
status category, and a sanitized error category.

Endpoint state transitions are logged once. The first failure and a transition
from available to unavailable produce a warning; recovery produces an info log.
Repeated failures do not flood the log.

## Privacy

Telemetry never stores response payloads, request parameters, configured labels,
or coordinates. Location requests are aggregated under the common city endpoint.

## Verification

Tests cover retry attempt counts, HTTP status categorization, and permanent
request failures. The data is exposed through Home Assistant diagnostics.
