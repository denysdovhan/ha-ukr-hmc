# Resource reconfigure and polling options

Status: done

## Decision

All supported config subentry handlers accept Home Assistant's reconfigure
source. They reuse the same provider validation as resource creation, exclude
the edited subentry from duplicate detection, and atomically update its title,
unique ID, and data. The integration's existing update listener performs the
reload.

The service entry also exposes an options flow for a polling interval from 5 to
30 minutes, with 15 minutes as the default. The upper bound stays below the
integration's 45-minute general stale-data threshold.

## Verification

Tests cover editing a location label and coordinates, provider validation,
unique-ID replacement, options persistence, range validation, and coordinator
use of the selected interval.
