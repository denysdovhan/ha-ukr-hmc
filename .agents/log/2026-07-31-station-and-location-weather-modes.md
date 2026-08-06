---
title: Explicit station and location weather modes
date: 2026-07-31
status: wip
related_paths:
  - custom_components/ukr_hmc/api/
  - custom_components/ukr_hmc/config_flow.py
  - custom_components/ukr_hmc/coordinator.py
  - custom_components/ukr_hmc/entity.py
  - custom_components/ukr_hmc/helpers.py
  - custom_components/ukr_hmc/sensor.py
  - custom_components/ukr_hmc/weather.py
  - custom_components/ukr_hmc/translations/
  - tests/
  - meteo.md
  - readme.md
---

# Explicit station and location weather modes

## Background

This refines the location model from the
[initial UkrHMC integration](2026-07-30-initial-ukrhydrometcenter-integration.md).
Live investigation confirmed that meteo.gov.ua publishes point forecast values
for exact latitude and longitude, including the hourly records used to present
current and daily location weather.

## Problem

The initial hourly implementation turns a selected location into a nearest
station, searches for a similarly named locality, and attaches that locality's
forecast to the station. The hidden identity changes can select a different
forecast point and make station entities claim hourly data that is not keyed by
station ID.

## Questions & Answers

- May this break existing subentries? Yes. The integration is still in
  development, so migration and compatibility code are explicitly out of
  scope.
- How should a physical station behave? Use only observations and forecasts
  published directly for its station ID.
- How should a location behave? Use forecast values for the exact point. The
  exact current-hour `fulldata` record supplies current values and sensors; no
  physical station is resolved.
- Which forecasts should be exposed? Station sources expose direct station
  daily/twice-daily products. Location sources expose hourly values and the
  deterministic daily view used by meteo.gov.ua.
- How does meteo.gov.ua form location daily cards? It selects `fulldata`
  records at 03:00 for the low/night value and 15:00 for the high/day value and
  condition. It does not calculate a daily average.

## Decision

- ✅ Use `weather_station` for physical meteorological stations and
  `weather_location` for exact point forecasts. The subentry type is the
  discriminator; do not store a separate weather-source field.
- ✅ Add future provider products as explicit sibling types when implemented:
  `radiation_station` for radiation monitoring and `hydrology_post` for water
  levels and other hydrology values.
- ✅ Store a station ID only for physical-station mode. Location mode stores a
  label, latitude, and longitude without resolving a station or showing a
  confirmation step.
- ✅ Query location forecasts with the provider's required non-empty `city`
  label and explicit `latlon=latitude,longitude` parameter.
- ✅ Give station weather entities daily and twice-daily features; give
  location weather entities hourly and daily features.
- ✅ Use the exact current-hour location record for current weather and sensor
  values; never expose a future record as current.
- ✅ Follow OpenWeather's sensor split: canonical Home Assistant keys in
  `condition`, and direct provider text in `weather`.
- ✅ Match the website's location daily view: 03:00 supplies the low, while
  15:00 supplies the high and condition. Omit incomplete dates.
- ✅ Keep all HTTP, parsing, and provider models in the Home Assistant-agnostic
  `api/` package.
- ❌ Do not search for a locality matching a station name.
- ❌ Do not register placeholder radiation or hydrology handlers before those
  products are implemented.
- ❌ Do not calculate daily averages or infer missing location forecast values.
- ❌ Do not add migration code for development-only subentries.

## Tradeoffs & Alternatives

- Location current conditions and forecasts consistently describe the same
  point, but they are model forecast values rather than physical observations.
- Home Assistant daily forecasts support one condition, while the website shows
  night and day icons. Use the 15:00 daytime condition in Home Assistant.
- `latlon` is an undocumented provider parameter and still requires a `city`
  value. Setup validation must reject empty forecast responses.
- `smartmet.js` overlaps with `prognoz.js`; mixing conflicting station daily
  products is rejected. Keep the richer direct `prognoz.js` product.
- A single `weather` type with a stored `station` or `location` source was
  rejected because it duplicates Home Assistant's native subentry type
  discriminator and adds an unnecessary menu level.

## Implementation Plan

1. Replace dynamic/static station semantics with explicit weather-station and
   weather-location subentry types.
2. Replace station-to-locality lookup with direct location forecast requests.
3. Split weather current values and forecast features by mode.
4. Update translations, documentation, and focused tests.
5. Validate live station observations and location current/hourly/daily values
   in Home Assistant.

## Verification

- [x] Station entries expose current observations plus daily/twice-daily only.
- [x] Location entries expose point-forecast current values plus hourly and
      daily forecasts.
- [x] Location setup creates the entry without resolving or confirming a
      station and rejects empty point forecasts.
- [x] No station-name locality lookup remains.
- [x] Ruff, tests, and pre-commit pass after the revised location behavior.
- [x] Live Home Assistant validation passes.

## Implementation Notes

- 2026-07-31: Initial live Зарічанка validation compared the website header with
  station `33548`. Further provider investigation replaced that interim design
  with location-only model values.
- 2026-07-31: The integration starts successfully on Home Assistant 2026.7.4.
  The in-app Browser reaches the integration page, but its automation layer
  focuses and hovers Home Assistant buttons without dispatching their click
  handlers. Live entry creation is the remaining validation step.
- 2026-08-01: The location design was revised to remove the nearest-station
  confirmation and expose the website's deterministic 03:00/15:00 daily view.
- 2026-08-01: Home Assistant matched live UkrHMC values for location
  Зарічанка (01:00 forecast hour: 21 °C, 65%, 1018 hPa, 2 m/s) and physical
  station 33658 Чернівці (21:00 observation: 26.1 °C, 48%, 742 mmHg, 0 m/s).
  The complete suite passed with 57 tests, along with Ruff and pre-commit.
- 2026-08-04: Live payloads showed that `dataDetailed` begins at the next future
  hour, while `fulldata` includes the exact current hour. Current location
  values now use only that present-hour record. Condition sensors expose
  canonical Home Assistant keys, and separate `weather` sensors retain direct
  provider descriptions.
- 2026-08-04: The final Ponytail review replaced parallel location maps and
  entity-side clock scans with one explicit `current`/`hourly`/`daily` provider
  object, and removed parsed fields that Home Assistant never consumes. Ruff
  and all 58 tests pass. At 18:36 Kyiv time, Home Assistant matched Зарічанка's
  exact 18:00 provider record and did not use the 19:00 forecast as current.
- 2026-08-05: Renamed the point-forecast source to `location` throughout the
  development schema and API. The final Ponytail pass shortened the location
  request/result mapping; Ruff and all 58 tests pass.
- 2026-08-05: Replaced the interim combined `weather` subentry with native
  `weather_station` and `weather_location` types. Future radiation and hydrology
  products are reserved as `radiation_station` and `hydrology_post` without
  speculative handlers. Ruff and all 59 tests pass; `config_flow.py` retains
  100% statement and branch coverage.
- 2026-08-06: Weather devices identify their models as `UkrHMC Station {number}`
  or `UkrHMC Location Forecast`. The sensor initializer overrides the pressure
  unit with hPa for location forecasts; setup creates all sensors uniformly.
  Both weather subentry forms suggest Home Assistant's configured home name.
  Ruff and all 59 tests pass.
