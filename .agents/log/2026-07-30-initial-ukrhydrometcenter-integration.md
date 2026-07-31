---
title: Initial Ukrhydrometcenter integration
date: 2026-07-30
status: wip
related_paths:
  - custom_components/ukr_hmc/
  - tests/
  - .github/workflows/
  - readme.md
---

# Initial Ukrhydrometcenter integration

## Background

The initial integration is based on reverse-engineered meteo.gov.ua station,
observation, forecast, icon, and wind data documented in `meteo.md`.

## Problem

Expose Ukrhydrometcenter observations and forecasts through native Home
Assistant weather and sensor entities while keeping the provider API code ready
for extraction into a standalone package.

## Questions & Answers

- Are catalog entries cities or physical stations? They are physical
  meteorological stations with IDs, coordinates, altitude, and observations.
  Support both nearest-station and explicit-list selection like LUN Misto Air.
- Which forecasts should be exposed? Use the forecast periods and values
  provided by Ukrhydrometcenter. Do not calculate or infer weather values.
- Which current-condition sensors should be created? Follow the OpenWeatherMap
  pattern and expose the researched current values.
- Which language behavior should be used? Use Ukrainian provider labels,
  English integration strings, and Ukrainian translations.
- Home Assistant's forecast schema cannot represent provider temperature
  ranges, textual precipitation/cloudiness, wind-speed ranges, or sunrise and
  sunset. Keep those values in the API model without adding raw entity
  attributes.

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
- Map provider condition codes to Home Assistant's canonical weather conditions;
  this is representation mapping, not weather inference.

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
