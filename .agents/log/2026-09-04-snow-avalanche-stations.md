# Snow and avalanche stations

Status: wip

## Decision

Add `snow_station` as a sibling config subentry backed by the official
`/_/m/snigost.js` observation feed and `ATTNS_STANTIONS` catalog in
`/ua/_attns-snigo.js`.

Expose snow depth, snow-depth change, air temperature, humidity, wind speed and
direction, cloudiness, weather phenomena, and the feed's observation date on a
separate device. Station 11 (Драгобрат) must not expose wind values because the
official renderer explicitly suppresses wind for that station.

Do not label `SD` as density: the official renderer describes its sign as an
increase/decrease in snow height in centimetres. `snigost.js` has no density,
snow-surface, or observation-time field, so those values must remain absent
unless a separate reliable official source is found.
