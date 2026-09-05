# Hydrology warning geometry compatibility

Status: done

## Decision

- Accept both GeoJSON `GeometryCollection` and `FeatureCollection` payloads when resolving warning regions.
- Keep rejecting unsupported or malformed geometry payloads with `UkrHMCDataError`.

## Reason

The live hydrological warning geometry endpoints use `FeatureCollection`, while the
original parser only accepted `GeometryCollection`. Adding a hydrology post therefore
failed during the first coordinator refresh with `Invalid regional geometry data`.

## Verification

- Added a regression test matching the live hydrological GeoJSON envelope.
- Existing `GeometryCollection` behavior remains covered.
