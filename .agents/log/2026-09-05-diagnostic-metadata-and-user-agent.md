# Diagnostic metadata and versioned provider identity

Status: done

## Decision

Provider observation time/date sensors are categorized as diagnostic. Those
entities carry compact public source metadata: weather station name, region and
altitude; radiation station name and altitude; hydrology post and river; or snow
station name. Exact-location coordinates and large payloads are not duplicated.

The API client accepts the installed integration version from Home Assistant and
uses it in the User-Agent together with the upstream project URL. The standalone
API fallback omits a fake release number while retaining the contact URL.

The project and HACS minimum are updated to Home Assistant 2026.9.0.

## Verification

Entity tests cover diagnostic categories and metadata. API tests cover both the
standalone fallback and the runtime-versioned User-Agent.
