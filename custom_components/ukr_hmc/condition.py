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

THUNDER_KEYWORDS = ("гроза", "thunder")
HAIL_KEYWORDS = ("град", "hail")
RAIN_KEYWORDS = ("дощ", "злив", "мряк", "rain", "drizzle")
SNOW_KEYWORDS = ("сніг", "хуртов", "поземок", "крупа", "snow")
HEAVY_KEYWORDS = ("сильн", "heavy")
FOG_KEYWORDS = ("туман", "імла", "димка", "fog", "mist", "haze")
WIND_KEYWORDS = (
    "буря",
    "шквал",
    "смерч",
    "storm",
    "gale",
    "squall",
    "tornado",
)
PARTLY_CLOUDY_KEYWORDS = (
    "малохмар",
    "невелика хмарність",
    "мінлива хмарність",
    "з проясненнями",
    "mostly clear",
    "partly cloudy",
    "few clouds",
)
CLOUDY_KEYWORDS = ("хмар", "cloud", "overcast")
CLEAR_KEYWORDS = ("ясно", "clear")
ICE_KEYWORDS = ("ожелед", "памороз", "glaze", "freezing")


def _has_any(description: str, keywords: tuple[str, ...]) -> bool:
    """Return whether a description contains any keyword."""
    return any(keyword in description for keyword in keywords)


def hmc_condition_to_ha(description: str, *, is_night: bool = False) -> str | None:
    """Map a published HMC description to a canonical HA condition."""
    condition = description.casefold()
    has_rain = _has_any(condition, RAIN_KEYWORDS)
    has_snow = _has_any(condition, SNOW_KEYWORDS)
    has_ice = _has_any(condition, ICE_KEYWORDS)
    clear_condition = ATTR_CONDITION_CLEAR_NIGHT if is_night else ATTR_CONDITION_SUNNY
    condition_rules = (
        (
            _has_any(condition, THUNDER_KEYWORDS) and has_rain,
            ATTR_CONDITION_LIGHTNING_RAINY,
        ),
        (_has_any(condition, THUNDER_KEYWORDS), ATTR_CONDITION_LIGHTNING),
        (_has_any(condition, HAIL_KEYWORDS), ATTR_CONDITION_HAIL),
        ((has_rain and has_snow) or "sleet" in condition, ATTR_CONDITION_SNOWY_RAINY),
        (has_snow, ATTR_CONDITION_SNOWY),
        (
            "злив" in condition or (_has_any(condition, HEAVY_KEYWORDS) and has_rain),
            ATTR_CONDITION_POURING,
        ),
        (has_rain, ATTR_CONDITION_RAINY),
        (has_ice, ATTR_CONDITION_EXCEPTIONAL),
        (
            _has_any(condition, FOG_KEYWORDS),
            ATTR_CONDITION_FOG,
        ),
        (_has_any(condition, WIND_KEYWORDS), ATTR_CONDITION_WINDY),
        (_has_any(condition, PARTLY_CLOUDY_KEYWORDS), ATTR_CONDITION_PARTLYCLOUDY),
        (_has_any(condition, CLOUDY_KEYWORDS), ATTR_CONDITION_CLOUDY),
        (_has_any(condition, CLEAR_KEYWORDS), clear_condition),
    )

    for matches, ha_condition in condition_rules:
        if matches:
            return ha_condition
    return None
