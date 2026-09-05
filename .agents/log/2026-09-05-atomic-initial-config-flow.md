# Atomic initial config flow

Status: done

## Decision

The top-level config flow now collects and validates the first resource before
creating the UkrHMC service entry. The entry and its initial config subentry are
then created together through Home Assistant's `subentries` API.

## Why

Previously the service entry was created before the resource subflow began. If
the user cancelled that subflow, Home Assistant retained an empty integration
entry. Keeping the resource form in the parent flow makes cancellation atomic:
no confirmed resource means no config entry.

## Compatibility

The existing subentry handlers remain the source of validation and schemas for
both initial and subsequently added resources. The parent flow supplies its own
flow identity and context while invoking them for initial setup.

## Verification

Tests cover all five initial resource types and assert that cancelling the first
resource form leaves no config entry behind.
