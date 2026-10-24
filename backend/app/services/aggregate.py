"""Range scores. Daily rows are grouped with pandas; the metrics stay in metrics.py."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from app.services.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_signed_error,
    mean_value,
    root_mean_squared_error,
)
from app.services.models import HourPair


def summarise_pairs(pairs: Sequence[HourPair], near_zero_mw: float) -> dict[str, object]:
    matched = [pair for pair in pairs if pair.error_mw is not None]
    errors = [float(pair.error_mw) for pair in matched if pair.error_mw is not None]
    score_pairs = [
        (float(pair.forecast_mw), float(pair.actual_mw))
        for pair in matched
        if pair.forecast_mw is not None and pair.actual_mw is not None
    ]
    mape, excluded = mean_absolute_percentage_error(score_pairs, near_zero_mw)
    forecast_hours = [pair for pair in pairs if pair.forecast_mw is not None]
    return {
        "mae_mw": mean_absolute_error(errors),
        "rmse_mw": root_mean_squared_error(errors),
        "bias_mw": mean_signed_error(errors),
        "mape_percent": mape,
        "n_matched": len(matched),
        "n_expected": len(pairs),
        "n_complete_actual": sum(1 for pair in pairs if pair.actual_complete),
        "n_with_forecast": len(forecast_hours),
        "n_excluded_near_zero": excluded,
        "mean_forecast_mw": mean_value([float(pair.forecast_mw) for pair in matched if pair.forecast_mw is not None]),
        "mean_actual_mw": mean_value([float(pair.actual_mw) for pair in matched if pair.actual_mw is not None]),
        "forecast_energy_mwh": (
            sum(float(pair.forecast_mw) for pair in forecast_hours if pair.forecast_mw is not None)
            if forecast_hours
            else None
        ),
        "forecast_hours": len(forecast_hours),
    }


def daily_summaries(pairs: Sequence[HourPair], near_zero_mw: float) -> list[dict[str, object]]:
    if not pairs:
        return []
    frame = pd.DataFrame(
        [
            {
                "settlement_date": pair.settlement_date.isoformat(),
                "error": pair.error_mw,
                "forecast": pair.forecast_mw,
                "actual": pair.actual_mw if pair.actual_complete else None,
                "matched": pair.error_mw is not None,
            }
            for pair in pairs
        ]
    )
    rows: list[dict[str, object]] = []
    for settlement_date, group in frame.groupby("settlement_date", sort=True):
        matched = group[group["matched"]]
        errors = [float(value) for value in matched["error"].tolist()]
        score_pairs = [
            (float(forecast), float(actual))
            for forecast, actual in zip(matched["forecast"], matched["actual"], strict=True)
        ]
        mape, excluded = mean_absolute_percentage_error(score_pairs, near_zero_mw)
        rows.append(
            {
                "settlement_date": str(settlement_date),
                "mae_mw": mean_absolute_error(errors),
                "rmse_mw": root_mean_squared_error(errors),
                "bias_mw": mean_signed_error(errors),
                "mape_percent": mape,
                "n_matched": len(errors),
                "n_expected": int(len(group)),
                "n_excluded_near_zero": excluded,
                "mean_forecast_mw": mean_value([float(value) for value in matched["forecast"].tolist()])
                if len(matched)
                else None,
                "mean_actual_mw": mean_value([float(value) for value in matched["actual"].tolist()])
                if len(matched)
                else None,
            }
        )
    return rows
