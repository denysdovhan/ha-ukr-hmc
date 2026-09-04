---
title: Extended weather data and global attention flags
date: 2026-09-04
status: wip
related_paths:
  - custom_components/ukr_hmc/api/
  - custom_components/ukr_hmc/binary_sensor.py
  - custom_components/ukr_hmc/sensor.py
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

## Verification

- [x] Ruff formatting and lint checks pass for `custom_components` and `tests`.
- [ ] Full tests pass. They cannot start in this Windows workspace because the
      Home Assistant pytest plugin imports the POSIX-only `fcntl` module.
- [ ] Live provider payload verified.
- [x] The Home Assistant-independent API smoke test parses all five attention
      flags successfully.
