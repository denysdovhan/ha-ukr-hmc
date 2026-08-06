---
title: Hydrology post monitoring
date: 2026-08-06
status: done
related_paths:
  - AGENTS.md
  - custom_components/ukr_hmc/api/
  - custom_components/ukr_hmc/config_flow.py
  - custom_components/ukr_hmc/const.py
  - custom_components/ukr_hmc/coordinator.py
  - custom_components/ukr_hmc/icons.json
  - custom_components/ukr_hmc/sensor.py
  - custom_components/ukr_hmc/translations/
  - tests/
  - meteo.md
  - readme.md
---

# Hydrology post monitoring

## Background

This implements the `hydrology_post` sibling type reserved by
[Explicit station and location weather modes](2026-07-31-station-and-location-weather-modes.md).
UkrHMC publishes one public post catalog and daily hydrology snapshot for its
daily hydrological situation map.

## Decision

- ✅ Parse `HYDRO_POSTS` and `hydroday.js` in the Home Assistant-independent
  `api/` package.
- ✅ Store only the selected hydrology post ID in the subentry.
- ✅ Fetch the hydrology catalog and daily snapshot only when a hydrology
  subentry exists, using the shared coordinator.
- ✅ Expose direct water level, water-level altitude, daily change, water
  temperature, observation time, and the provider's `L` class.
- ✅ Map `L = 0..4` to stable enum states matching the provider legend without
  deriving new safety judgments.
- ✅ Treat `FR_BS = 0` as unavailable, matching the public map, while preserving
  `TW = 0` as a valid temperature.
- ❌ Do not add automatic-post data, hydrology forecasts, history, or a
  per-post coordinator.

## Verification

- [x] Live catalog, snapshot, frontend map logic, colors, and legend verified.
- [x] Config flow lists only posts with current usable data.
- [x] Each hydrology subentry creates one device and six sensors.
- [x] Missing provider data makes existing hydrology sensors unavailable.
- [x] Ruff and all tests pass.

## Implementation Notes

- 2026-08-06: Live data contained 237 catalog posts and 177 selectable posts.
  The daily snapshot had 279 records, including 101 IDs absent from the public
  catalog. The provider map uses the per-record date at 08:00 Europe/Kyiv.
- 2026-08-06: The map legend defines five hydrological-situation classes:
  calm, floodplain flooding, dangerous high, extreme high, and dangerous low.
- 2026-08-06: Added the `hydrology_post` flow, conditional shared-coordinator
  fetches, one service device, six sensors, bilingual UI copy, and provider
  documentation. Ruff, all 82 tests, and 100% config-flow statement and branch
  coverage pass. The live client parsed 237 posts, 275 usable observations, and
  177 selectable posts.
- 2026-08-06: Removed the generic distance device class from water depth and
  water-level altitude because Home Assistant has no matching depth or altitude
  class. Both retain measurement statistics and their provider units; water
  depth explicitly prefers centimeters. Ruff and all 82 tests pass.
- 2026-08-06: Added frontend icon translations for water depth (`mdi:waves`)
  and water-level altitude (`mdi:altimeter`).
- 2026-08-06: Water depth defaults to zero decimal places. Water-level change
  icons are defined only in `icons.json`: values below zero use the default
  `mdi:wave-arrow-down`, zero uses `mdi:waves`, and positive values use
  `mdi:wave-arrow-up`. The live snapshot ranged from -0.12 m to 0.10 m.
- 2026-08-06: Water-level altitude defaults to one decimal place. Daily water
  level change preserves the provider-native meter value while preferring
  centimeters with zero decimal places in Home Assistant.
