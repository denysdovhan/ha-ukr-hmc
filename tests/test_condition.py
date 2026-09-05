"""Tests for provider condition mapping."""

import pytest

from custom_components.ukr_hmc.condition import hmc_condition_to_ha


@pytest.mark.parametrize(
    ("description", "is_night", "expected"),
    [
        ("Ясно", False, "sunny"),
        ("Ясно", True, "clear-night"),
        ("Невелика хмарність", False, "partlycloudy"),
        ("Хмарно", False, "cloudy"),
        ("Туман", False, "fog"),
        ("Сильний дощ", False, "pouring"),
        ("Дощ", False, "rainy"),
        ("Дощ зі снігом", False, "snowy-rainy"),
        ("Сніг", False, "snowy"),
        ("Град", False, "hail"),
        ("Гроза", False, "lightning"),
        ("Гроза, дощ", False, "lightning-rainy"),
        ("Пилова буря", False, "windy"),
        ("clear", True, "clear-night"),
        ("mostly clear", False, "partlycloudy"),
        ("overcast", False, "cloudy"),
        ("periods of moderate rain", False, "rainy"),
        ("Ожеледиця", False, "exceptional"),
        ("Льодяний дощ, ожеледь", False, "rainy"),
        ("Невідомо", False, None),
        ("", False, None),
    ],
)
def test_condition_mapping(description, is_night, expected) -> None:
    assert hmc_condition_to_ha(description, is_night=is_night) == expected
