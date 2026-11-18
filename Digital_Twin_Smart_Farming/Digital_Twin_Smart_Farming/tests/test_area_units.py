import pytest

from app.services.virtual_farm import (
    SQFT_PER_HECTARE,
    hectares_to_square_feet,
    square_feet_to_hectares,
)


def test_one_acre_converts_to_square_feet_and_hectares():
    # International definition: one acre is 43,560 square feet.
    hectares = square_feet_to_hectares(43560)
    assert hectares == pytest.approx(0.40468564224, rel=1e-8)
    assert hectares_to_square_feet(hectares) == pytest.approx(43560, abs=0.01)


def test_square_feet_conversion_uses_internal_hectare_factor():
    assert SQFT_PER_HECTARE == pytest.approx(107639.104167)
    assert square_feet_to_hectares(107639.104167) == pytest.approx(1.0)


@pytest.mark.parametrize("value", [None, "", 0, 9, -1, "not a number"])
def test_invalid_small_or_non_numeric_farm_area_is_rejected(value):
    with pytest.raises(ValueError):
        square_feet_to_hectares(value)


def test_area_conversion_rejects_non_finite_values():
    for value in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError):
            square_feet_to_hectares(value)
