---
title: Regional meteorological warnings
date: 2026-09-04
status: wip
related_paths:
  - custom_components/ukr_hmc/api/
  - custom_components/ukr_hmc/binary_sensor.py
  - custom_components/ukr_hmc/translations/
  - tests/
  - README.md
  - meteo.md
---

# Regional meteorological warnings

## Decision

- Use the verified `/ua/_attns-meteo.json` feed for regional meteorological
  warnings; keep it distinct from the five global attention flags.
- Join provider region id `R` to the oblast id already stored on physical
  meteorological stations.
- Expose one problem-class binary sensor per station. Preserve all warnings in
  attributes with the maximum danger level, text, phenomenon code, provider
  update time, raw period, and parsed start/end timestamps.
- Keep the problem sensor on only while at least one warning is active. Expose
  active/future counts, the next start and end, and a per-warning status for
  automation use.
- Expose a companion enum sensor with stable `none`, `yellow`, `orange`, and
  `red` states representing the highest active warning level.
- Do not create unstable per-warning entities.
- Do not infer an oblast for exact map locations because their forecast response
  does not publish a reliable region id.

## Verification

- [x] Live provider schema verified on 2026-09-04.
- [x] Ruff formatting and lint checks pass for `custom_components` and `tests`.
- [x] Home Assistant-independent parser smoke test passes with the verified live
      payload shape.
- [x] Full Home Assistant test suite passes under WSL with Python 3.14.2:
      `91 passed`.
