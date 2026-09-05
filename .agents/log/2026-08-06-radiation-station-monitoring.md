---
title: Radiation station monitoring
date: 2026-08-06
status: done
related_paths:
  - custom_components/ukr_hmc/api/
  - custom_components/ukr_hmc/config_flow.py
  - custom_components/ukr_hmc/coordinator.py
  - custom_components/ukr_hmc/entity.py
  - custom_components/ukr_hmc/sensor.py
  - custom_components/ukr_hmc/translations/
  - custom_components/ukr_hmc/icons.json
  - tests/
  - meteo.md
  - readme.md
---

# Radiation station monitoring

## Background

This implements the `radiation_station` sibling type reserved by
[Explicit station and location weather modes](2026-07-31-station-and-location-weather-modes.md).
UkrHMC publishes a radiation-station catalog and one global current snapshot.

## Problem

Expose radiation observations as native Home Assistant sensors without mixing
them into weather stations or inferring safety states from provider values.

## Questions & Answers

- How should a radiation source be configured? As a `radiation_station`
  subentry with one Home Assistant device.
- Which measurements should be exposed? Both provider values: exposure dose
  rate in `µR/h` and dose rate in `nSv/h`, plus the observation time.
- How should the map colors be exposed? Defer the derived dose-level entity until
  Home Assistant can present the colors without assigning contradictory History
  colors.
- How should stations without current measurements appear? Omit them from the
  station selector. Existing configured entities remain unavailable until data
  arrives again.
- Should station codes appear in selector labels? No. Keep the number in the
  provider model and use station names in the UI, matching weather stations.
- How should the main config entry be named? Use the full official organization
  name, not the `UkrHMC` abbreviation.
- Which Ukrainian UI term should identify this source? Use "Радіологічна
  станція" consistently instead of "пункт радіологічного спостереження".

## Decision

- ✅ Parse `RADIO_POSTS` and `radioday.js` inside the Home Assistant-independent
  `api/` package.
- ✅ Store only the selected radiation station ID in the subentry.
- ✅ Fetch the global radiation catalog and snapshot once per coordinator refresh
  only when radiation subentries exist.
- ✅ Expose the provider's `VR` and `VZ` values directly with their supplied
  units; do not convert between them.
- ✅ Create one service device per radiation subentry and attach its sensors with
  `config_subentry_id`.
- ✅ Link radiation devices directly to the provider's `#RADIO` page.
- ✅ Name the main config entry `Ukrainian Hydrometeorological Center`.
- ❌ Do not expose or infer a dose-level classification yet.
- ❌ Do not add per-station coordinators, history, or other provider products.

## Tradeoffs & Alternatives

- Stations without observations are hidden to keep the selector unambiguous.
  Existing subentries remain configured when their observations disappear.
- Two measurements preserve the provider response even though the website often
  emphasizes `VZ` in its table.
- The provider's color thresholds remain documented as research, but are not
  exposed until Home Assistant can present them without contradictory colors.

## Implementation Plan

1. Add radiation catalog and observation models, parsers, and client methods.
2. Extend the shared snapshot and coordinator request gating.
3. Add the radiation subentry flow, device, sensors, and translations.
4. Add focused API, flow, coordinator, setup, and entity tests.
5. Validate formatting, tests, and live provider values.

## Verification

- [x] Radiation catalog and observations parse without Home Assistant imports.
- [x] Config flow lists only stations with current data.
- [x] Each radiation subentry creates one device and three sensors.
- [x] Weather entities continue to ignore radiation subentries.
- [x] Missing or checked provider data makes radiation sensors unavailable.
- [x] Ruff, tests, and live endpoint verification pass.

## Implementation Notes

- 2026-08-06: Live investigation found 189 catalog stations and 136 current
  observations. Query suffixes did not change either response body.
- 2026-08-06: Added the `radiation_station` subentry, one service device, direct
  µR/h and nSv/h sensors, observation time, catalog filtering, and request
  gating in the shared coordinator.
- 2026-08-06: Ruff passed, all 72 tests passed, and the implemented live client
  parsed Kyiv as 11 µR/h and 96 nSv/h at 12:00 Europe/Kyiv.
- 2026-08-06: The radiation device configuration URL now opens the provider's
  radiation page instead of its general landing page, and newly created main
  entries use the full official organization name. No migration is needed while
  the integration remains development-only.
- 2026-08-06: Removed the derived dose-level sensor until its provider colors can
  be represented without contradictory Home Assistant History colors. Ruff and
  all 71 tests passed.
- 2026-08-06: Standardized Ukrainian UI terminology on "Радіологічна станція".
  Ruff and all 71 tests passed.
