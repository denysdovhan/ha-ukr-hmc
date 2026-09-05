# Changelog

## v0.5.0

### Added

- Reconfiguration for weather locations, physical stations, radiation stations,
  hydrology posts, and snow/avalanche stations.
- A bounded 5–30 minute polling interval option.
- Endpoint timing/retry telemetry and sanitized provider schema diagnostics.
- Compact station, region, altitude, and river metadata on diagnostic observation
  time/date sensors.

### Changed

- Expose all five provider-wide UkrHMC attention indicators with explicit global
  scope, separately from detailed regional warnings.
- Suppress redundant coordinator entity updates while preserving timed warning
  transitions.
- Treat unknown weather descriptions as unknown instead of exceptional.
- Publish water-level change as a signed measurement suitable for statistics.
- Add product freshness checks, partial-source isolation, bounded request
  concurrency, retry/backoff, and expiring catalog caches.
- Mark provider observation time/date entities as diagnostic and send the actual
  installed integration version plus the upstream project URL in HTTP requests.
- Require Home Assistant 2026.9.0.

## v0.4.0

### Added

- Exact-location hourly forecasts and current precipitation.
- Forecast summaries for precipitation, temperature, and wind gusts.
- Station forecast details, sunrise/sunset, and provider diagnostic codes.
- Derived Steadman apparent-temperature sensors.
- Regional meteorological, fire-danger, avalanche, and hydrological warnings.
- Read-only Home Assistant warning calendars.
- Warning transition event entities for automation triggers.
- Radiation monitoring stations and daily hydrology posts.
- Snow and avalanche station observations from `snigost.js`.
- Privacy-safe Home Assistant diagnostics download with endpoint health and
  aggregate record counts.

### Changed

- Replaced global fire, snow, and hydrology flags with detailed regional levels.
- Kept the global radiological flag because the available regional map feed is
  stale and does not provide current text or validity periods.
