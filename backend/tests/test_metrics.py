import math

import pytest

from app.services.metrics import (
    absolute_error,
    forecast_error,
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_signed_error,
    percentage_error,
    root_mean_squared_error,
)


def test_error_sign_and_absolute_value() -> None:
    assert forecast_error(110, 100) == 10
    assert forecast_error(90, 100) == -10
    assert absolute_error(90, 100) == 10


def test_mae_rmse_and_bias_use_the_same_errors() -> None:
    errors = [10.0, -20.0, 30.0]
    assert mean_absolute_error(errors) == pytest.approx(20)
    assert mean_signed_error(errors) == pytest.approx(20 / 3)
    assert root_mean_squared_error(errors) == pytest.approx(math.sqrt((100 + 400 + 900) / 3))


def test_empty_inputs_are_missing_not_zero() -> None:
    assert mean_absolute_error([]) is None
    assert root_mean_squared_error([]) is None
    assert mean_signed_error([]) is None


def test_percentage_error_skips_near_zero_actuals() -> None:
    assert percentage_error(10, 0, 1) is None
    assert percentage_error(10, 0.5, 1) is None
    assert percentage_error(15, 10, 1) == pytest.approx(50)
    assert percentage_error(8, 10, 1) == pytest.approx(-20)

    mape, excluded = mean_absolute_percentage_error([(15, 10), (10, 0), (8, 10)], 1)
    assert excluded == 1
    assert mape == pytest.approx(35)
