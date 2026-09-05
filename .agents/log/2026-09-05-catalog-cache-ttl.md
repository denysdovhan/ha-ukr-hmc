# Catalog cache TTL

Status: done

## Decision

Station, radiation, hydrology, snow, and lookup catalogs are cached for 24 hours.
After expiry the client refreshes the catalog, but retains and returns the last
valid value when the refresh fails with a connection or data error.

## Why

The catalogs change much less frequently than observations. A bounded cache
avoids repeated downloads without making catalog changes invisible for the
lifetime of the Home Assistant process. Last-good fallback also keeps existing
configuration flows usable during a temporary UkrHMC outage.

## Verification

Tests cover reuse before expiry, refresh after expiry, and fallback to the last
valid station catalog.
