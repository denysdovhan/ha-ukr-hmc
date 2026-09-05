# Coordinator equality-based dispatch

Status: done

## Decision

The shared data coordinator uses `always_update=False`, so an unchanged immutable
provider snapshot does not notify every entity on each polling interval.

`UkrHMCData` includes a derived set of currently active warning keys. The set is
recomputed whenever a provider snapshot is created. Crossing a warning start or
end time therefore changes snapshot equality even when the provider payload is
unchanged, preserving warning event transitions.

## Verification

A coordinator test verifies that the second identical snapshot is suppressed and
that a changed active-warning marker dispatches listeners.
