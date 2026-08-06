# AI Coding Agents Guide

## Purpose

Act as a concise, senior Python and Home Assistant collaborator. Confirm
uncertainties before changing behavior, prefer the smallest correct diff, and
ground decisions in current repository code, provider data, and Home Assistant
documentation.

## Important directives

- Keep replies and commit messages concise and concrete.
- Ask before making a significant product or architecture decision when the
  requirement is ambiguous.
- Add narrow debug logging and request the resulting output when runtime behavior
  cannot be established from code and tests. Do not guess.
- Commit only when directly asked. Use conventional commit messages.
- When updating `AGENTS.md`, preserve its structure and style. Add or correct
  relevant facts without rewriting unrelated sections.

<instruction>Keep this guide synchronized with implemented architecture and tooling.</instruction>

## Design Log

- Before repository work, read `.agents/log/index.md`.
- Search `.agents/log/` by touched paths and 2-3 task keywords, then read matching
  entries in full.
- Treat `done` entries as binding decisions and `wip` entries as current direction.
  Newer decisions win; surface conflicts before proceeding.
- Never edit a `done` entry. Keep a matching `wip` entry and the index current for
  significant feature work; skip routine chores.
- Do not mark the initial integration entry `done` until the user explicitly
  confirms the feature is complete.

## Project Overview

This repository implements the Home Assistant custom integration **Ukrainian
Hydrometeorological Center** (`ukr_hmc`). It exposes weather observations,
forecasts, and radiation measurements from
[meteo.gov.ua](https://www.meteo.gov.ua/). Integration code lives in
`custom_components/ukr_hmc`.

One integration config entry owns multiple typed subentries. Weather stations,
exact forecast locations, and radiation monitoring stations use separate
subentry and device types. Keep future provider products, such as hydrology
posts, in sibling types.

### Code structure

- `__init__.py` - creates the shared API client and coordinator, stores typed
  `entry.runtime_data`, and forwards sensor and weather platforms.
- `api/` - Home Assistant-independent async client, constants, errors, immutable
  data models, and parsers. Keep it ready for extraction to a standalone package.
- `condition.py` - maps Ukrainian provider descriptions to canonical Home
  Assistant weather conditions.
- `config_flow.py` - creates the single service entry and typed weather and
  radiation subentries.
- `const.py` - integration constants, subentry types, and the 15-minute update
  interval.
- `coordinator.py` - fetches shared weather and radiation snapshots plus direct
  forecasts for configured map locations.
- `data.py` - `UkrHMCRuntimeData` and the typed `UkrHMCConfigEntry` alias.
- `entity.py` - shared weather data access, availability, and device metadata.
- `icons.json` - frontend icons for generic sensor types and canonical weather
  condition states.
- `sensor.py` - current-condition and radiation sensor descriptions and
  entities.
- `weather.py` - current weather plus forecast modes supported by each location
  type.
- `translations/` - English and Ukrainian UI strings.
- `tests/` - focused API, condition, config-flow, coordinator, entity, and setup
  coverage.
- `meteo.md` - reverse-engineering notes for provider schemas and additional
  researched endpoints. The JSON lookup files preserve researched icon and wind
  data.

## Architecture contracts

### Provider API isolation

- Keep `custom_components/ukr_hmc/api/` free of Home Assistant imports.
- Inject an `aiohttp.ClientSession`; keep all HTTP and provider parsing inside the
  API package.
- Convert provider payloads to typed Python models before returning them to the
  coordinator. The coordinator and entities must not depend on raw field names.
- Keep provider snapshots immutable. Preserve provider fields in API models even
  when Home Assistant cannot expose them natively.
- Parse JSON-compatible JavaScript assignments as data. Never evaluate or execute
  provider JavaScript.

### Runtime data and polling

- Use one shared `UkrHMCClient` and one `UkrHMCCoordinator` per config entry.
- Store both in `entry.runtime_data`; do not introduce globals or singleton state.
- The coordinator downloads the global station, observation, forecast, lookup,
  and day/night data once every 15 minutes when weather-station subentries need
  it, the radiation catalog and snapshot when radiation-station subentries need
  them, plus one direct forecast for each weather-location subentry. Do not add
  per-location coordinators or duplicate global requests.
- Entities read cached coordinator data only. Never perform I/O in entity
  properties or forecast callbacks.
- Convert provider failures to the appropriate Home Assistant coordinator or
  config-flow errors while preserving useful exception context.

### Typed subentries

- Catalog records are physical meteorological stations, not cities.
- Use `weather_station` for physical stations and `weather_location` for exact
  point forecasts. Do not store a second weather-source discriminator.
- Use `radiation_station` for radiation monitoring stations. Future provider
  products should use explicit sibling types such as `hydrology_post`. Weather
  platforms must ignore non-weather subentry types.
- Weather-station subentries store a selected provider station ID.
- Weather-location subentries store only their label, latitude, and longitude.
  Do not resolve or store a physical station for map locations.
- Radiation-station subentries store a selected provider station ID. Keep the
  station number in device metadata, not in selector labels.
- Add entities with `config_subentry_id=subentry.subentry_id`.
- Weather unique IDs use the subentry ID. Sensor unique IDs use
  `{subentry_id}-{sensor_key}`.
- Reject duplicate weather resources using stable subentry unique IDs.
- The explicit station picker is intentionally a strict single-selection
  dropdown. Do not enable multiple or custom values merely to make it searchable.

### Weather and sensor behavior

- Weather-station sources expose current-condition sensors for canonical
  condition, provider weather text, temperature, humidity, pressure, wind speed,
  numeric wind direction, and data time.
- Weather-location sources expose canonical condition, provider weather text,
  temperature, humidity, wind speed, raw compass direction, mapped numeric wind
  direction, and data time. Do not create a current pressure sensor because the
  exact current-hour location record does not publish pressure.
- Station current values come from physical observations. Location current
  values come from the exact current-hour `fulldata` record for the point.
- Keep `condition` sensor states canonical for Home Assistant. Keep direct
  provider text in the separate `weather` sensor; do not invent a localized
  location description when UkrHMC returns English text.
- Expose only forecast values directly supplied by UkrHMC. Do not calculate
  averages, infer missing values, or publish raw unsupported fields as custom
  entity attributes.
- Station sources expose the provider's direct daily and twice-daily station
  forecasts. A single wind speed may be exposed; a textual speed range must
  remain unset rather than being averaged.
- Location sources expose direct hourly values plus daily forecasts matching
  meteo.gov.ua: 03:00 supplies the low/night value and 15:00 supplies the
  high/day value and condition. Omit a day unless both records are published.
- Do not use physical-station observations as location current values or infer
  a station from latitude and longitude.
- Keep temperature ranges, textual cloudiness and precipitation, wind ranges,
  sunrise, sunset, and other unsupported fields in API models for future use.
- The wind-direction sensor exposes degrees with the native wind-direction device
  class. For location current values, map the direct `WindCompass8` value through
  the provider bearing mapping and also expose the raw compass value separately.
  The weather entity may use the provider's compass abbreviation directly.
- Radiation stations expose the provider's direct `VR` value in µR/h and `VZ`
  value in nSv/h, plus their observation time. Do not convert one measurement
  into the other.
- Do not expose a derived dose-level entity until Home Assistant has a suitable
  way to present the provider map colors without misleading history colors.
- Point radiation devices to the provider's `#RADIO` page; keep weather devices
  linked to the main provider page.
- Show only radiation stations with a current measurement in the selector.
  Missing observations and negative provider sentinel values make existing
  entities unavailable.
- Use `Радіологічна станція` consistently in Ukrainian UI text.

## Provider data

Current supported endpoints are:

- `/_/m/current.js` - latest observations for all stations.
- `/_/m/prognoz.js` - forecasts for all stations.
- `/_/m/radioday.js` - latest radiation measurements for available stations.
- `/fmi.json?action=getCityWeather` - direct location forecast values using a
  non-empty label and `latlon`; `dataDetailed` supplies upcoming hourly values,
  while `fulldata` supplies the current-hour record and daily-card records.
- `/_/_e5m.json` - provider day/night flags.
- `/ua/_meteo-stations.js` - region and physical-station catalog.
- `/ua/_radio-posts.js` - radiation monitoring station catalog.
- `/ua/_meteo-icons.js` and `/ua/_meteo-winds.js` - condition and wind lookups.

The `.js` endpoints contain JSON or JSON-compatible assignments despite their
extension and content type. Bare requests have returned HTTP 403 during live
validation; preserve the honest browser-like user agent and meteo.gov.ua referer
in `api/const.py`, and re-verify live behavior before changing request logic.

Treat the hydrology, snow, avalanche, and alert endpoints documented in
`meteo.md` as research only. They are outside the implemented scope unless the
user explicitly expands it. Use `Europe/Kyiv` for provider-local dates and times.

## Configuration and translations

- Keep config-entry setup in the UI; do not add YAML configuration.
- Preserve all three subentry types: physical weather station, map location, and
  radiation monitoring station.
- Edit `translations/en.json` and `translations/uk.json` together when UI keys
  change. Translate values only and keep JSON keys aligned.
- Use the full official organization name in integration titles, manifest
  metadata, and top-level connection or duplicate messages.
- Preserve Ukrainian provider labels. English integration UI and Ukrainian UI
  translations do not authorize translating provider observations.

## Workflow

- Dependencies live in `pyproject.toml` and `uv.lock`; use `uv` and the repository
  scripts rather than ad hoc environments.
- Keep the public repository lockfile on public PyPI sources. Check for private or
  local registry references after dependency changes.
- Add focused tests for behavior changes. Prefer the closest test module while
  iterating, then run the full suite.
- Inspect the dirty and staged diff before and after formatters or hooks. Preserve
  unrelated user changes.
- Use current Home Assistant developer documentation and installed APIs/types
  before changing integration contracts; do not rely on memory alone.

### Development scripts

- `scripts/bootstrap` - recreate the uv environment, sync development
  dependencies, and install pre-commit hooks.
- `scripts/setup` - run the complete initial project setup.
- `scripts/develop` - start development Home Assistant at
  `http://localhost:8123`. It must place the repository root, not
  `custom_components`, on `PYTHONPATH`.
- `scripts/lint` - run Ruff formatting and autofix checks. Review its resulting
  diff because it can modify files.
- `scripts/test [path-or-node]` - run all tests or a focused pytest target.
- `scripts/bump_version` - update the integration manifest version for release
  work only.

### Validation

- After Python changes: run `scripts/lint`, then `scripts/test`.
- After config-flow, entity, or provider changes: add focused regression tests and
  verify the relevant setup path.
- For provider schema changes: update parsers and fixtures together, then verify
  live endpoint behavior when network access is available.
- Before committing: run the full relevant validation and check `git diff` plus
  `git status` for unrelated changes.

## Code style

- Follow `pyproject.toml` and Ruff. Match surrounding code instead of introducing
  a new local style.
- Keep imports at module scope. Use `TYPE_CHECKING` for imports needed only by
  annotations.
- Prefer typed dataclasses, explicit constants for provider schema keys, and
  standard Home Assistant helpers already used in the repository.
- Keep changes surgical. Do not refactor adjacent code or add speculative
  abstractions.

## Home Assistant references

Consult current Home Assistant developer documentation before modifying related
APIs:

- File structure: https://developers.home-assistant.io/docs/creating_integration_file_structure
- Config entries and flows: https://developers.home-assistant.io/docs/config_entries_index
- Data entry flows: https://developers.home-assistant.io/docs/data_entry_flow_index
- Fetching data: https://developers.home-assistant.io/docs/integration_fetching_data
- Weather entities: https://developers.home-assistant.io/docs/core/entity/weather
- Sensor entities: https://developers.home-assistant.io/docs/core/entity/sensor
- Manifest: https://developers.home-assistant.io/docs/creating_integration_manifest
- Quality scale: https://developers.home-assistant.io/docs/core/integration-quality-scale

Also inspect current Home Assistant core implementations and developer guidance
when local APIs or documentation disagree. Do not claim a quality tier without
checking its current rules against the repository.

## Commit messages

Use conventional commits:

```text
<type>(<scope>): concise summary

Optional explanation only when the change needs context.
```

Avoid vague summaries such as `improve`, `enhance`, or `update`. State the
observable change.
