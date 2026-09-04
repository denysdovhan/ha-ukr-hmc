---
title: Warning calendar and regional hazard levels
date: 2026-09-04
status: wip
related_paths:
  - custom_components/ukr_hmc/calendar.py
  - custom_components/ukr_hmc/api/
  - custom_components/ukr_hmc/sensor.py
  - tests/
  - readme.md
  - meteo.md
---

# Warning calendar and regional hazard levels

## Decision

- Create one read-only Home Assistant calendar per configured weather station or
  exact location. It combines timed meteorological, fire-danger, and avalanche
  warnings matched to that source and performs no entity-time I/O.
- Use the verified `/ua/_attns-fire.json` and `/ua/_attns-snigolav.json` feeds.
  Both use the same `UPD`/`OBJ`/`R`/`L`/`A` validity structure as the existing
  meteorological warning feed.
- Replace the provider-global fire and snow attention binary sensors with
  regional enum sensors. Preserve the other three global flags because no
  detailed replacement has been implemented for those products.
- Fire levels map provider categories 3 and 4 to `extreme` and
  `prolonged_extreme`. Avalanche levels map the official European 1–5 scale.
- Resolve exact locations against feed-referenced official polygons. Resolve
  physical stations against avalanche polygons using station coordinates;
  fire danger uses the station's direct oblast id.
- Omit warnings without parseable start and end timestamps from the calendar,
  while preserving them in sensor attributes.
- Use `/ua/_attns-hydro.json` for hydrological warnings. Match each configured
  hydrology post by coordinates against the official basin-area polygons, expose
  the map's distinct I, II, III, and brown low-water III levels, and preserve the
  official basin name, phenomenon, full text, and validity period. Replace the
  global hydrology attention entity and add a post-specific warning calendar.

## Verification

- [x] Live fire, avalanche, and hydrology schemas verified on 2026-09-04.
- [x] Ruff and full Home Assistant tests pass (`100 passed`).
