# Diagnostics download

Status: wip

## Decision

Provide Home Assistant config-entry diagnostics without subentry data, titles,
unique IDs, station IDs, labels, or coordinates. Include only config schema
versions, counts by subentry type, coordinator health, per-path endpoint
availability, and aggregate record counts.

The API client records success/failure for each endpoint path during normal
polling. Diagnostics must not perform extra network requests.
