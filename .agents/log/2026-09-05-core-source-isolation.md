# Core source isolation and parallel loading

Status: done

## Decision

- Start radiation, hydrology, snow, and bounded location forecast loads concurrently
  while station weather and attention metadata are processed.
- Isolate expected connection and provider-data errors by configured product family.
- Return a partial snapshot when at least one configured core source succeeds; missing
  records make only the affected entities unavailable.
- Keep successfully returned location forecasts when another configured point fails.
- Fail the whole coordinator refresh when every configured core source fails, preserving
  Home Assistant's normal setup and update retry behavior.
- Publish sanitized product-level availability in diagnostics and on the API availability
  binary sensor attributes.

## Reason

Independent public endpoints have independent failure modes. Serial, atomic loading made
unrelated entities unavailable and accumulated timeout latency across product families.

## Verification

- Tests cover radiation failure with successful hydrology in the same snapshot.
- Tests cover one failed location alongside one successful location.
- A scheduling test confirms core product requests are in flight concurrently.
- Existing coordinator error tests continue to cover total failure behavior.
