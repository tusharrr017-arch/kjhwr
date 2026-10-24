"""Forecast accuracy metrics.

Sign convention, used everywhere:
    error = forecast generation − actual generation

A positive error means the forecast was higher than measured wind generation.
MAE, RMSE, and bias all use the same list of signed errors. Percentage error
is omitted when actual generation is below the near-zero threshold. None of
these functions treat a missing value as zero; callers must pass only valid pairs.
RMSE divides by the number of pairs (not N − 1).
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def forecast_error(forecast_mw: float, actual_mw: float) -> float:
    return forecast_mw - actual_mw


def absolute_error(forecast_mw: float, actual_mw: float) -> float:
    return abs(forecast_error(forecast_mw, actual_mw))


def mean_absolute_error(errors_mw: Sequence[float]) -> float | None:
    if not errors_mw:
        return None
    return sum(abs(error) for error in errors_mw) / len(errors_mw)


def root_mean_squared_error(errors_mw: Sequence[float]) -> float | None:
    if not errors_mw:
        return None
    return math.sqrt(sum(error * error for error in errors_mw) / len(errors_mw))


def mean_signed_error(errors_mw: Sequence[float]) -> float | None:
    """Forecast bias. Positive means the forecast overstated generation."""
    if not errors_mw:
        return None
    return sum(errors_mw) / len(errors_mw)


def percentage_error(forecast_mw: float, actual_mw: float, near_zero_mw: float) -> float | None:
    """Signed percent error. None when actual generation is near zero."""
    if abs(actual_mw) < near_zero_mw:
        return None
    return (forecast_mw - actual_mw) / actual_mw * 100.0


def mean_absolute_percentage_error(
    pairs: Sequence[tuple[float, float]],
    near_zero_mw: float,
) -> tuple[float | None, int]:
    """Return MAPE and the count of pairs excluded for near-zero actuals.

    `pairs` must be the same matched forecast/actual pairs used for MAE.
    """
    values: list[float] = []
    excluded = 0
    for forecast_mw, actual_mw in pairs:
        percent = percentage_error(forecast_mw, actual_mw, near_zero_mw)
        if percent is None:
            excluded += 1
        else:
            values.append(abs(percent))
    if not values:
        return None, excluded
    return sum(values) / len(values), excluded


def mean_value(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)
