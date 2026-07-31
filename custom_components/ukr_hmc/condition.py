"""Map provider descriptions to Home Assistant weather conditions."""

from homeassistant.components.weather import (
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_CLOUDY,
    ATTR_CONDITION_EXCEPTIONAL,
    ATTR_CONDITION_FOG,
    ATTR_CONDITION_HAIL,
    ATTR_CONDITION_LIGHTNING,
    ATTR_CONDITION_LIGHTNING_RAINY,
    ATTR_CONDITION_PARTLYCLOUDY,
    ATTR_CONDITION_POURING,
    ATTR_CONDITION_RAINY,
    ATTR_CONDITION_SNOWY,
    ATTR_CONDITION_SNOWY_RAINY,
    ATTR_CONDITION_SUNNY,
    ATTR_CONDITION_WINDY,
)

RAIN_KEYWORDS = ("дощ", "злив", "мряк")
SNOW_KEYWORDS = ("сніг", "хуртов", "поземок", "крупа")


def _has_any(description: str, keywords: tuple[str, ...]) -> bool:
    """Return whether a description contains any keyword."""
    return any(keyword in description for keyword in keywords)


def hmc_condition_to_ha(description: str, *, is_night: bool = False) -> str:
    """Map a published HMC description to a canonical HA condition."""
    condition = description.casefold()
    has_rain = _has_any(condition, RAIN_KEYWORDS)
    has_snow = _has_any(condition, SNOW_KEYWORDS)
    clear_condition = ATTR_CONDITION_CLEAR_NIGHT if is_night else ATTR_CONDITION_SUNNY
    condition_rules = (
        ("гроза" in condition and has_rain, ATTR_CONDITION_LIGHTNING_RAINY),
        ("гроза" in condition, ATTR_CONDITION_LIGHTNING),
        ("град" in condition, ATTR_CONDITION_HAIL),
        (has_rain and has_snow, ATTR_CONDITION_SNOWY_RAINY),
        (has_snow, ATTR_CONDITION_SNOWY),
        (
            "злив" in condition or ("сильн" in condition and has_rain),
            ATTR_CONDITION_POURING,
        ),
        (has_rain or "ожелед" in condition, ATTR_CONDITION_RAINY),
        (_has_any(condition, ("туман", "імла", "димка")), ATTR_CONDITION_FOG),
        (_has_any(condition, ("буря", "шквал", "смерч")), ATTR_CONDITION_WINDY),
        (
            _has_any(
                condition,
                (
                    "малохмар",
                    "невелика хмарність",
                    "мінлива хмарність",
                    "з проясненнями",
                ),
            ),
            ATTR_CONDITION_PARTLYCLOUDY,
        ),
        ("хмар" in condition, ATTR_CONDITION_CLOUDY),
        ("ясно" in condition, clear_condition),
    )

    for matches, ha_condition in condition_rules:
        if matches:
            return ha_condition
    return ATTR_CONDITION_EXCEPTIONAL
