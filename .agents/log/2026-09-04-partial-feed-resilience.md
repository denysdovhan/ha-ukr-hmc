# Partial feed resilience

Status: done

## Decision

- Treat regional meteorological, fire, snow/avalanche, and hydrological warning
  feeds as optional enrichments of the core observations.
- Resolve warning geometries independently and skip only an unavailable or malformed
  region geometry.
- Skip isolated malformed weather, radiation, and hydrology observation records.
- Still reject an observation dataset when it contains candidate records but none of
  them can be parsed.

## Reason

An auxiliary warning endpoint, one changed GeoJSON document, or one malformed station
record must not make unrelated entities unavailable. The endpoint health map records
the failed warning source, and sanitized warnings identify skipped record IDs without
logging provider payloads.

## Remaining work

- Isolate failures between the core weather, radiation, hydrology, snow, and individual
  location request families.
- Add product-specific freshness limits and last-success timestamps.
- Extend record-level rejection to forecast, catalog, and snow datasets.

## Verification

- Tests cover independent regional-warning failure and hydrological-warning failure.
- Tests cover mixed valid/invalid radiation and hydrology observation datasets.
