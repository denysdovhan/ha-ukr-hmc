---
title: Initial UkrHMC integration
date: 2026-07-30
status: wip
related_paths:
  - custom_components/ukr_hmc/
  - tests/
  - .github/workflows/
  - readme.md
---

# Initial UkrHMC integration

## Background

The initial UkrHMC integration is based on reverse-engineered meteo.gov.ua
station, observation, forecast, icon, and wind data documented in `meteo.md`.

## Problem

Expose Ukrainian Hydrometeorological Center observations and forecasts through
native Home Assistant weather and sensor entities while keeping the provider
API code ready for extraction into a standalone package.

## Questions & Answers

- Are catalog entries cities or physical stations? They are physical
  meteorological stations with IDs, latitude, longitude, altitude, and
  observations. Support both nearest-station and explicit-list selection like
  LUN Misto Air.
- Which forecasts should be exposed? Use the forecast periods and values
  provided by UkrHMC. Do not calculate or infer weather values.
- Which current-condition sensors should be created? Follow the OpenWeatherMap
  pattern and expose the researched current values.
- Which language behavior should be used? Use Ukrainian provider labels,
  English integration strings, and Ukrainian translations.
- Home Assistant's forecast schema cannot represent provider temperature
  ranges, textual precipitation/cloudiness, wind-speed ranges, or sunrise and
  sunset. Keep those values in the API model without adding raw entity
  attributes.
- Which temperature represents current weather? Keep using the latest physical
  station observation from `/_/m/current.js`. City-model temperatures are
  forecasts and must not replace the current observation.
- How should physical stations use the city-based hourly endpoint? Resolve an
  exact-name Ukrainian locality from the provider search results and choose the
  closest match by distance. If no match is available, omit hourly forecasts
  for that station without affecting observations or daily forecasts.

## Decision

- Keep provider-only code in `custom_components/ukr_hmc/api/` with no Home
  Assistant imports.
- Create one integration config entry with station subentries. Each subentry is
  either an explicit station ID or a location whose nearest station is selected
  on refresh.
- Use one shared API client and one polling coordinator for the provider's
  global current, forecast, day/night, and catalog endpoints. Station
  subentries select from the shared snapshot.
- Expose one weather entity plus current-condition sensors for each station.
- Expose daily and twice-daily native forecasts using only directly compatible
  provider values. Keep unsupported source fields in the API model.
- Expose the provider's city-model hourly records as native hourly forecasts.
  Keep the station-to-locality resolution and payload parsing inside the
  extractable API package.
- Map provider condition codes to Home Assistant's canonical weather conditions;
  this is representation mapping, not weather inference.
- Poll every 15 minutes. Station observations are published in three-hour
  periods, while a shorter bounded interval limits the delay after a new period
  appears and refreshes subscribed hourly forecasts without aggressive polling.

## Tradeoffs & Alternatives

- Multiple config entries per station are simpler, but subentries match the
  requested LUN Misto Air station-management experience.
- Per-station coordinators match LUN Misto Air but would download the same
  global HMC forecast repeatedly. One shared coordinator avoids duplicate
  network traffic.
- Bundling a static station catalog would avoid parsing JavaScript, but would
  become stale. Parse the provider catalog safely as data without evaluating
  JavaScript.

## Implementation Plan

1. Scaffold the repository and isolated API package.
2. Add config-entry lifecycle, station subentry flows, and coordinators.
3. Add weather and sensor entities, translations, docs, CI, and tests.
4. Validate formatting, tests, HACS metadata, and the Home Assistant Bronze
   quality baseline.

## Verification

- [x] API parsers cover stations, observations, forecasts, icons, and wind data.
- [x] Both station-selection paths are covered by config-flow tests.
- [x] Weather and sensor entities expose cached coordinator data only.
- [x] Daily and provider day/night forecasts use only direct HMC values.
- [x] Lint, tests, lockfile checks, and live Home Assistant validation pass.
- [x] Local light/dark brand icons and logos use official UkrHMC artwork.
- [x] Review feedback uses descriptive provider-field constants, native wind
      direction metadata, official naming, and custom-integration translations.
- [x] Current weather continues to use `current.js` observations.
- [x] Hourly forecasts expose direct provider city-model values when available.
- [x] Coordinator polling uses the documented 15-minute interval.

## Implementation Notes

- 2026-07-30: Live endpoint checks confirmed the researched station, current
  observation, and six-day Kyiv forecast schemas still match the notes.
- 2026-07-30: Implemented the isolated API package, shared coordinator,
  integration and station subentry flows, native weather and sensor entities,
  translations, project scaffolding, and focused tests.
- 2026-07-30: Browser validation found and fixed the development launcher's
  `PYTHONPATH`, then confirmed eight live Kyiv entities against meteo.gov.ua.
  Native forecast actions returned six daily and twelve day/night periods.
- 2026-07-30: Final validation passed Ruff, 40 tests, 100% branch coverage for
  the config flow, JSON/pre-commit/shell/compile checks, and a public-PyPI-only
  lockfile.
- 2026-07-31: Added local Home Assistant brand assets derived from the official
  meteo.gov.ua symbol and vector wordmark, with transparent light/dark and
  normal/hDPI variants.
- 2026-07-31: Applied initial review feedback. Removed Home Assistant coupling
  from the extractable API user agent, replaced provider schema literals with
  documented constants, simplified condition and parser expressions, and
  removed the duplicate `strings.json` because custom integrations load
  `translations/*.json` directly.
- 2026-07-31: Matched OpenWeatherMap's native wind-direction sensor contract by
  exposing provider compass directions as degrees with the wind-direction
  device class. Confirmed the existing service `DeviceInfo.configuration_url`
  already supplies the same Visit action as Met.no.
- 2026-07-31: Kept the station picker as a strict dropdown. Home Assistant
  2026.7 only uses its searchable generic picker for multiple selections or
  custom values; Aerial Danger is searchable because its preset selectors are
  multi-select, while UkrHMC must accept exactly one provider station.
- 2026-07-31: Review validation passed Ruff, the full pre-commit suite, and all
  41 tests.
- 2026-07-31: Follow-up review uses the full official organization name for
  the localized integration title in both English and Ukrainian.
- 2026-07-31: Extended the full English organization name to the top-level
  connection errors and duplicate-configuration message.
- 2026-07-31: Kept the original direct UkrHMC text for the `condition` sensor;
  canonical Home Assistant conditions remain on the weather entity. Grouped
  API constants with descriptive headers and used the full official name in
  the manifest.
- 2026-07-31: Replaced the assembled brand logos with the official
  `ugmc-map-wm-ua.svg` composition, cropped above its `meteo.gov.ua` line.
  Preserved transparent light/dark and normal/hDPI variants; icons are
  unchanged.
- 2026-07-31: Live investigation confirmed Chernivtsi station `33658` reported
  31.4 C at 18:00 through `current.js`, while the city endpoint separately
  forecast 25 C at 22:00. Began adding optional native hourly forecasts without
  relabeling model data as a current observation.
- 2026-07-31: Added exact-name, nearest-location locality resolution and
  native hourly forecasts from `fmi.json`. Live validation returned 221 hourly
  records for Chernivtsi while the weather entity retained the 31.4 C station
  observation from `current.js`; Ruff and all 47 tests passed. The restarted
  Home Assistant instance loaded UkrHMC successfully with a 15-minute polling
  interval; browser UI inspection stopped at the existing login screen.
