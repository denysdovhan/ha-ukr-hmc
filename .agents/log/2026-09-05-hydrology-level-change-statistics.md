# Hydrology level-change statistics

Status: done

## Decision

The hydrology `water_level_change` sensor is a signed distance measurement. It
retains the Home Assistant distance device class, native metres, suggested
centimetres, and now declares `SensorStateClass.MEASUREMENT`.

This permits consistent recorder statistics while preserving negative values for
falling water and positive values for rising water. A total or total-increasing
state class would be semantically incorrect for a signed change.

## Verification

Entity tests assert the distance units, display precision, and measurement state
class.
