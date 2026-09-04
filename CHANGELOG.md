# Changelog

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
