import math
from datetime import date, datetime, time, timedelta, timezone

import pandas as pd

from app.services.aggregate import daily_summaries, summarise_pairs
from app.services.alignment import build_pairs
from app.services.models import HourPair

UTC = timezone.utc


def _pair(day: date, hour: int, forecast: float, actual: float) -> HourPair:
    start = datetime(day.year, day.month, day.day, hour, tzinfo=UTC)
    error = forecast - actual
    return HourPair(
        start=start,
        end=start + timedelta(hours=1),
        settlement_date=day,
        settlement_periods=(1,),
        actual_mw=actual,
        actual_complete=True,
        half_hours=(),
        forecast_mw=forecast,
        publish_time=None,
        error_mw=error,
        absolute_error_mw=abs(error),
        percentage_error=None,
    )


def test_range_mae_is_not_the_average_of_daily_maes() -> None:
    # Guard the import so a missing pandas install fails this test loudly.
    assert pd.__version__
    first = date(2026, 1, 15)
    second = date(2026, 1, 16)
    pairs = [
        _pair(first, 0, 110, 100),
        _pair(first, 1, 110, 100),
        _pair(second, 0, 130, 100),
    ]
    summary = summarise_pairs(pairs, near_zero_mw=1)
    daily = daily_summaries(pairs, near_zero_mw=1)
    assert summary["n_matched"] == 3
    assert summary["mae_mw"] == 16.666666666666668 or summary["mae_mw"] == (10 + 10 + 30) / 3
    assert [row["mae_mw"] for row in daily] == [10, 30]
    assert summary["mae_mw"] != 20


def _gap(day: date, hour: int, forecast: float | None) -> HourPair:
    start = datetime(day.year, day.month, day.day, hour, tzinfo=UTC)
    return HourPair(
        start=start,
        end=start + timedelta(hours=1),
        settlement_date=day,
        settlement_periods=(),
        actual_mw=None,
        actual_complete=False,
        half_hours=(),
        forecast_mw=forecast,
        publish_time=None,
        error_mw=None,
        absolute_error_mw=None,
        percentage_error=None,
    )


def _oracle(errors: list[float]) -> tuple[float, float, float]:
    count = len(errors)
    mae = sum(abs(error) for error in errors) / count
    rmse = math.sqrt(sum(error * error for error in errors) / count)
    bias = sum(errors) / count
    return mae, rmse, bias


def test_daily_scores_use_only_that_days_matched_hours() -> None:
    day = date(2026, 1, 15)
    pairs = [
        _pair(day, 0, 110, 100),
        _gap(day, 1, forecast=999),
        _pair(day, 2, 80, 100),
    ]
    daily = daily_summaries(pairs, near_zero_mw=1)
    mae, rmse, bias = _oracle([10.0, -20.0])
    assert len(daily) == 1
    assert daily[0]["n_expected"] == 3
    assert daily[0]["n_matched"] == 2
    assert daily[0]["mae_mw"] == mae
    assert daily[0]["rmse_mw"] == rmse
    assert daily[0]["bias_mw"] == bias
    zero_filled = _oracle([10.0, 0.0, -20.0])
    assert daily[0]["mae_mw"] != zero_filled[0]
    assert daily[0]["rmse_mw"] != zero_filled[1]
    assert daily[0]["bias_mw"] != zero_filled[2]


def test_weekly_and_monthly_scores_pool_every_matched_hour() -> None:
    def window(days: int) -> list[HourPair]:
        pairs: list[HourPair] = []
        for offset in range(days):
            day = date(2026, 1, 1) + timedelta(days=offset)
            error = float(offset + 1)
            for hour in range(24):
                if hour < offset + 1:
                    pairs.append(_pair(day, hour, 100 + error, 100))
                else:
                    pairs.append(_gap(day, hour, forecast=None))
        return pairs

    for days, expected_hours in ((7, 168), (31, 744)):
        pairs = window(days)
        summary = summarise_pairs(pairs, near_zero_mw=1)
        daily = daily_summaries(pairs, near_zero_mw=1)
        errors = [
            float(offset + 1)
            for offset in range(days)
            for _ in range(min(offset + 1, 24))
        ]
        mae, rmse, bias = _oracle(errors)
        daily_mae = [float(row["mae_mw"]) for row in daily]
        daily_rmse = [float(row["rmse_mw"]) for row in daily]
        daily_bias = [float(row["bias_mw"]) for row in daily]
        assert summary["n_expected"] == expected_hours
        assert summary["n_matched"] == len(errors)
        assert summary["mae_mw"] == mae
        assert summary["rmse_mw"] == rmse
        assert summary["bias_mw"] == bias
        assert summary["mae_mw"] != sum(daily_mae) / len(daily_mae)
        assert summary["rmse_mw"] != sum(daily_rmse) / len(daily_rmse)
        assert summary["bias_mw"] != sum(daily_bias) / len(daily_bias)
        assert [row["n_expected"] for row in daily] == [24] * days
        assert [row["n_matched"] for row in daily] == [min(day, 24) for day in range(1, days + 1)]


def test_a_month_with_no_observations_is_missing_not_zero() -> None:
    pairs = build_pairs(
        date(2026, 1, 1),
        date(2026, 1, 31),
        {},
        {},
        gate=time(9, 20),
        near_zero_mw=1,
    )
    summary = summarise_pairs(pairs, near_zero_mw=1)
    daily = daily_summaries(pairs, near_zero_mw=1)
    assert len(pairs) == 744
    assert summary["n_expected"] == 744
    assert summary["n_matched"] == 0
    assert summary["mae_mw"] is None
    assert summary["rmse_mw"] is None
    assert summary["bias_mw"] is None
    assert len(daily) == 31
    assert all(row["n_expected"] == 24 and row["n_matched"] == 0 for row in daily)
    assert all(row["mae_mw"] is None and row["rmse_mw"] is None and row["bias_mw"] is None for row in daily)
