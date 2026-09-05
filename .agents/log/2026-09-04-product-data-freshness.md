# Product data freshness

Status: done

## Decision

- Validate provider timestamps independently for station weather, location forecasts,
  radiation, hydrology, and snow observations.
- Use conservative product-specific maximum ages: 12 hours, 3 hours, 36 hours,
  48 hours, and 48 hours respectively.
- Permit at most two hours of future clock skew; larger future timestamps are invalid
  for availability purposes.
- Keep warning entities independent from observation freshness because warnings have
  their own publication and validity periods.
- Expose aggregate timestamp, age, threshold, record count, and stale state in
  privacy-safe diagnostics without station IDs or location coordinates.

## Reason

An HTTP 200 response can contain old cached provider data. Successful transport is not
enough to declare a measurement current, and one stale product must not hide fresh data
from another product.

## Verification

- Boundary tests cover recent, stale, and implausibly future timestamps.
- Entity tests cover stale radiation and hydrology observations.
- Diagnostics tests cover aggregate freshness metadata and privacy constraints.
