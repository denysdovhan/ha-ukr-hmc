# Condition mapping hardening

Status: done

## Decision

Unknown and empty provider descriptions now map to `None`, allowing Home
Assistant to expose an unknown condition instead of incorrectly reporting an
exceptional weather event.

Pure ice phenomena such as glaze ice remain a recognized exceptional condition;
freezing-rain descriptions that explicitly contain rain use Home Assistant's
closest supported `rainy` condition. Precipitation, thunderstorm, hail, fog,
wind, cloud, and clear-condition precedence is covered by a provider-language
corpus in tests.

## Limitation

Home Assistant has no dedicated canonical condition for glaze ice. The original
provider description and service codes remain available through separate
sensors, so automations can distinguish it without relying on the lossy weather
condition.
