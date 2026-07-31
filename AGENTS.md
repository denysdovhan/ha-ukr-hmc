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
Hydrometeorological Center** (`ukr_hmc`). It exposes observations and forecasts
from [meteo.gov.ua](https://www.meteo.gov.ua/) for physical meteorological
stations. Integration code lives in `custom_components/ukr_hmc`.

One integration config entry owns multiple station subentries. Each station can
be selected explicitly from the provider catalog or resolved dynamically as the
nearest station to a configured location.

### Code structure

- `__init__.py` - creates the shared API client and coordinator, stores typed
  `entry.runtime_data`, and forwards sensor and weather platforms.
- `api/` - Home Assistant-independent async client, constants, errors, immutable
  data models, and parsers. Keep it ready for extraction to a standalone package.
- `condition.py` - maps Ukrainian provider descriptions to canonical Home
  Assistant weather conditions.
- `config_flow.py` - creates the single service entry and physical-station
  subentries using nearest-location or explicit-list selection.
- `const.py` - integration constants, station types, and the 30-minute update
  interval.
- `coordinator.py` - fetches one complete provider snapshot shared by every
  station subentry.
- `data.py` - `UkrHMCRuntimeData` and the typed `UkrHMCConfigEntry` alias.
- `entity.py` - shared station resolution, availability, and device metadata.
- `helpers.py` - nearest-station and station-ID resolution helpers.
- `sensor.py` - current-condition sensor descriptions and entities.
- `weather.py` - current weather plus native daily and twice-daily forecasts.
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
  and day/night data once every 30 minutes. Do not add per-station coordinators or
  duplicate global requests.
- Entities read cached coordinator data only. Never perform I/O in entity
  properties or forecast callbacks.
- Convert provider failures to the appropriate Home Assistant coordinator or
  config-flow errors while preserving useful exception context.

### Station subentries

- Catalog records are physical meteorological stations, not cities.
- Static subentries store a provider station ID. Dynamic subentries store a
  location and resolve the nearest current catalog station after each refresh.
- Add entities with `config_subentry_id=subentry.subentry_id`.
- Weather unique IDs use the subentry ID. Sensor unique IDs use
  `{subentry_id}-{sensor_key}`.
- Reject duplicate station selections using stable subentry unique IDs.
- The explicit station picker is intentionally a strict single-selection
  dropdown. Do not enable multiple or custom values merely to make it searchable.

### Weather and sensor behavior

- Expose one weather entity and current-condition sensors for condition,
  temperature, humidity, pressure, wind speed, wind direction, and observation
  time per station.
- Keep the condition sensor's original Ukrainian provider text. Map conditions to
  Home Assistant canonical values only for the weather entity and forecasts.
- Expose only forecast values directly supplied by UkrHMC. Do not calculate
  averages, infer missing values, or publish raw unsupported fields as custom
  entity attributes.
- Daily forecasts use direct day/night temperatures. Twice-daily forecasts use
  provider sunrise/sunset periods. A single wind speed may be exposed; a textual
  speed range must remain unset rather than being averaged.
- Keep temperature ranges, textual cloudiness and precipitation, wind ranges,
  sunrise, sunset, and other unsupported fields in API models for future use.
- The wind-direction sensor exposes degrees with the native wind-direction device
  class. The weather entity uses the provider's compass abbreviation.

## Provider data

Current supported endpoints are:

- `/_/m/current.js` - latest observations for all stations.
- `/_/m/prognoz.js` - forecasts for all stations.
- `/_/_e5m.json` - provider day/night flags.
- `/ua/_meteo-stations.js` - region and physical-station catalog.
- `/ua/_meteo-icons.js` and `/ua/_meteo-winds.js` - condition and wind lookups.

The `.js` endpoints contain JSON or JSON-compatible assignments despite their
extension and content type. Bare requests have returned HTTP 403 during live
validation; preserve the honest browser-like user agent and meteo.gov.ua referer
in `api/const.py`, and re-verify live behavior before changing request logic.

Treat the hydrology, radiation, snow, avalanche, and alert endpoints documented
in `meteo.md` as research only. They are outside the implemented weather scope
unless the user explicitly expands it. Use `Europe/Kyiv` for provider-local dates
and times.

## Configuration and translations

- Keep config-entry setup in the UI; do not add YAML configuration.
- Preserve both station-selection paths: nearest map location and explicit
  station list.
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
