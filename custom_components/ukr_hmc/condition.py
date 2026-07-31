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


def hmc_condition_to_ha(description: str, *, is_night: bool = False) -> str:
    """Map a published HMC description to a canonical HA condition."""
    condition = description.casefold()

    has_rain = any(word in condition for word in ("дощ", "злив", "мряк"))
    has_snow = any(word in condition for word in ("сніг", "хуртов", "поземок", "крупа"))

    if "гроза" in condition:
        result = (
            ATTR_CONDITION_LIGHTNING_RAINY if has_rain else ATTR_CONDITION_LIGHTNING
        )
    elif "град" in condition:
        result = ATTR_CONDITION_HAIL
    elif has_rain and has_snow:
        result = ATTR_CONDITION_SNOWY_RAINY
    elif has_snow:
        result = ATTR_CONDITION_SNOWY
    elif "злив" in condition or ("сильн" in condition and has_rain):
        result = ATTR_CONDITION_POURING
    elif has_rain or "ожелед" in condition:
        result = ATTR_CONDITION_RAINY
    elif any(word in condition for word in ("туман", "імла", "димка")):
        result = ATTR_CONDITION_FOG
    elif any(word in condition for word in ("буря", "шквал", "смерч")):
        result = ATTR_CONDITION_WINDY
    elif any(
        word in condition
        for word in (
            "малохмар",
            "невелика хмарність",
            "мінлива хмарність",
            "з проясненнями",
        )
    ):
        result = ATTR_CONDITION_PARTLYCLOUDY
    elif "хмар" in condition:
        result = ATTR_CONDITION_CLOUDY
    elif "ясно" in condition:
        result = ATTR_CONDITION_CLEAR_NIGHT if is_night else ATTR_CONDITION_SUNNY
    else:
        result = ATTR_CONDITION_EXCEPTIONAL
    return result
