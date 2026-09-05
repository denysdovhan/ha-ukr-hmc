# Provider-global attention indicators

Status: done

## Decision

All five flags published in the shared UkrHMC payload are exposed on the service
device: `attns_meteo`, `attns_hydro`, `attns_snigo`, `attns_radio`, and
`attns_fire`.

Their entity names deliberately use “provider-wide attention indicator” rather
than “regional warning”. Each entity publishes `scope=provider_global`, its
provider key, and `has_regional_details=false`. It does not invent a territory,
severity, description, or validity period.

Detailed meteorological, fire, avalanche, and hydrological products remain
separate resource-level entities. A global flag therefore cannot be confused
with or override a validated regional level.

## Availability

The indicators become unavailable when the attention feed fails or their key is
absent, rather than silently presenting an off state as current data.

## Verification

Tests cover all five provider keys, values, global-scope attributes, and service
device placement. README documentation explicitly describes the distinction.
