# Radiological warning feed research

Status: done

## Decision

Do not integrate `/ua/_attns-radio.json` as current regional warnings and do not
replace the global `attns_radio` flag with it.

Live verification on 2026-09-04 found an update timestamp of 30.06.2023 14:30.
The feed describes fixed 10/30/100 km NPP zones, while alert records have empty
begin, end, and description fields. It cannot provide the requested current
territory, text, or validity period. The Ukrainian and English feeds are
identical apart from lookup labels.

Continue exposing direct `radioday.js` measurements per station and the global
radiological-attention flag. Revisit only if UkrHMC publishes a maintained feed
with explicit current alert data and validity.
