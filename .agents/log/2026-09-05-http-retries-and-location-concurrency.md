# HTTP retries and location concurrency

Status: done

## Decision

- Retry idempotent provider GET requests up to three total attempts for transport
  failures and HTTP 408, 429, 500, 502, 503, and 504 responses.
- Use bounded exponential backoff with jitter and honor numeric or HTTP-date
  `Retry-After` values up to ten seconds.
- Do not retry permanent HTTP 4xx responses or malformed successful payloads.
- Limit simultaneous location forecast requests to four per config entry refresh.

## Reason

Short provider outages and throttling should not immediately make data unavailable,
while permanent client errors should fail quickly. A user with many configured points
must not create an unbounded request burst against the public UkrHMC service.

## Verification

- Tests cover a successful retry after HTTP 503 with `Retry-After`.
- Tests verify HTTP 404 is attempted once.
- A ten-location concurrency test proves that at most four requests run together.
