# Warning event entities

Status: done

## Decision

Create one event entity per warning kind and configured source. Weather stations
and exact locations receive meteorological, fire, and avalanche event entities;
hydrology posts receive one hydrological event entity.

Supported event types are `started`, `level_increased`, and `ended`. Establish
the initial active level as a baseline when the entity is created so Home
Assistant restarts do not emit false starts. Compare only coordinator snapshots,
and include type, previous/current level, territory, provider region, text, raw
period, and parsed validity in event attributes. End events preserve the warning
that just ended.
