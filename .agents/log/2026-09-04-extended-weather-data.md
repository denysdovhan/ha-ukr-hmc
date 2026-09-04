---
title: Extended weather data and global attention flags
date: 2026-09-04
status: wip
related_paths:
  - custom_components/ukr_hmc/api/
  - custom_components/ukr_hmc/binary_sensor.py
  - custom_components/ukr_hmc/sensor.py
  - custom_components/ukr_hmc/coordinator.py
  - custom_components/ukr_hmc/translations/
  - tests/
  - readme.md
  - readme.uk.md
---

# Extended weather data and global attention flags

## Decision

- Expose direct current precipitation for weather-location subentries.
- Expose station sunrise and sunset as timestamp sensors.
- Keep provider phenomenon and indicator codes as disabled-by-default diagnostic sensors.
- Preserve unsupported station forecast fields in one diagnostic detailed-forecast sensor instead of creating per-day entities. Its state is the first forecast date and its `forecasts` attribute contains direct day/night temperature ranges, precipitation text, cloudiness, wind-speed ranges, sunrise, sunset, and provider code.
- Parse all five `attns_*` values from `/_/_e5m.json` and expose them once per config entry as problem-class binary sensors on a shared service device.
- Name the flags as global attention indicators. Do not claim they are regional warnings: the payload has no region, severity, description, or validity period.
- Fetch `/_/_e5m.json` for every active config entry so global flags work without a weather-station subentry.
- Expose one always-readable connectivity binary sensor for the latest API update
  result and one diagnostic timestamp for the latest successful complete snapshot.
  Preserve the timestamp across temporary update failures.
- Keep hourly forecasts attached to exact map locations. The provider's
  `dataDetailed` response is the verified direct source; do not manufacture
  station-hourly forecasts or create one entity per forecast hour.
- Document every added sensor and distinguish the coordinator refresh time from
  provider observation timestamps.
- For exact weather locations, expose direct forecast summaries without new
  network calls: complete-horizon precipitation totals for 1/3/6/12/24 hours,
  the next wet hour, today's and tomorrow's provider daily low/high values, and
  the maximum published gust in the next 24 hours with its timestamp. Missing
  precipitation in any hour makes that horizon unknown rather than assuming 0.
- Mark shared data stale after 45 minutes (three polling intervals) and retain a
  consecutive update-failure counter that resets after a successful snapshot.

## Verification

- [x] Ruff formatting and lint checks pass for `custom_components` and `tests`.
- [ ] Full tests pass. They cannot start in this Windows workspace because the
      Home Assistant pytest plugin imports the POSIX-only `fcntl` module.
- [ ] Live provider payload verified.
- [x] The Home Assistant-independent API smoke test parses all five attention
      flags successfully.
