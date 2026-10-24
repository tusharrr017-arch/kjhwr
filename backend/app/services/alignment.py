"""Align half-hourly actuals with hourly forecasts by delivery timestamp."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta

from app.core.time import LONDON, UTC, expected_hours, hour_label
from app.services.metrics import absolute_error, forecast_error, percentage_error
from app.services.models import ActualRecord, ForecastRecord, HalfHourView, HourPair
from app.services.selection import select_forecast


def index_actuals(records: list[ActualRecord]) -> dict[datetime, ActualRecord]:
    return {record.start: record for record in records}


def index_forecasts(records: list[ForecastRecord]) -> dict[datetime, list[ForecastRecord]]:
    indexed: dict[datetime, list[ForecastRecord]] = defaultdict(list)
    for record in records:
        indexed[record.start].append(record)
    for group in indexed.values():
        group.sort(key=lambda record: record.publish_time)
    return indexed


def build_pairs(
    settlement_from: date,
    settlement_to: date,
    actuals: dict[datetime, ActualRecord],
    forecasts: dict[datetime, list[ForecastRecord]],
    *,
    gate: time,
    near_zero_mw: float,
    fixed_publish: datetime | None = None,
) -> list[HourPair]:
    pairs: list[HourPair] = []
    day = settlement_from
    while day <= settlement_to:
        pairs.extend(
            build_day_pairs(
                day,
                actuals,
                forecasts,
                gate=gate,
                near_zero_mw=near_zero_mw,
                fixed_publish=fixed_publish,
            )
        )
        day += timedelta(days=1)
    return pairs


def build_day_pairs(
    settlement_date: date,
    actuals: dict[datetime, ActualRecord],
    forecasts: dict[datetime, list[ForecastRecord]],
    *,
    gate: time,
    near_zero_mw: float,
    fixed_publish: datetime | None = None,
) -> list[HourPair]:
    from app.core.time import decision_cutoff

    cutoff = decision_cutoff(settlement_date, gate)
    pairs: list[HourPair] = []
    for start in expected_hours(settlement_date):
        pairs.append(
            _pair_for_hour(
                start,
                settlement_date,
                actuals,
                forecasts.get(start, []),
                cutoff=cutoff,
                near_zero_mw=near_zero_mw,
                fixed_publish=fixed_publish,
            )
        )
    return pairs


def _pair_for_hour(
    start: datetime,
    settlement_date: date,
    actuals: dict[datetime, ActualRecord],
    forecasts: list[ForecastRecord],
    *,
    cutoff: datetime,
    near_zero_mw: float,
    fixed_publish: datetime | None,
) -> HourPair:
    second = start + timedelta(minutes=30)
    views = tuple(_owned_view(actuals, moment, settlement_date) for moment in (start, second))
    complete = (
        views[0].generation_mw is not None
        and views[1].generation_mw is not None
    )
    actual_mw = None
    if complete:
        assert views[0].generation_mw is not None and views[1].generation_mw is not None
        actual_mw = (views[0].generation_mw + views[1].generation_mw) / 2.0

    chosen = select_forecast(forecasts, cutoff, fixed_publish)
    forecast_mw = chosen.generation_mw if chosen else None
    publish_time = chosen.publish_time if chosen else None

    error = None
    magnitude = None
    percent = None
    if complete and actual_mw is not None and forecast_mw is not None:
        error = forecast_error(forecast_mw, actual_mw)
        magnitude = absolute_error(forecast_mw, actual_mw)
        percent = percentage_error(forecast_mw, actual_mw, near_zero_mw)

    periods = tuple(
        half.settlement_period for half in views if half.settlement_period is not None
    )
    return HourPair(
        start=start,
        end=start + timedelta(hours=1),
        settlement_date=settlement_date,
        settlement_periods=periods,
        actual_mw=actual_mw,
        actual_complete=complete,
        half_hours=views,
        forecast_mw=forecast_mw,
        publish_time=publish_time,
        error_mw=error,
        absolute_error_mw=magnitude,
        percentage_error=percent,
    )


def _owned_view(
    actuals: dict[datetime, ActualRecord],
    moment: datetime,
    settlement_date: date,
) -> HalfHourView:
    record = actuals.get(moment)
    if record is None or record.settlement_date != settlement_date:
        return HalfHourView(moment, None, None)
    return HalfHourView(moment, record.settlement_period, record.generation_mw)


def default_hour(settlement_date: date, hours: list[datetime]) -> datetime:
    noon_local = datetime.combine(settlement_date, time(12, 0), tzinfo=LONDON)
    noon = noon_local.astimezone(UTC).replace(microsecond=0)
    if noon in hours:
        return noon
    if not hours:
        raise ValueError("This settlement day has no hours")
    return hours[0]


def series_points(pairs: list[HourPair]) -> list[dict[str, object]]:
    """Half-hourly chart rows.

    The hourly forecast is repeated on both half-hours so a step line can hold
    across the hour. A missing hour stays null on both points and must not be
    bridged. The repeated value is a display hold, not a second forecast.
    """
    points: list[dict[str, object]] = []
    for pair in pairs:
        for half in pair.half_hours:
            local = half.start.astimezone(LONDON)
            points.append(
                {
                    "start_time": half.start,
                    "label": local.strftime("%H:%M"),
                    "hour_start": pair.start,
                    "actual_mw": half.generation_mw,
                    "forecast_mw": pair.forecast_mw,
                }
            )
    return points


def period_label(pair: HourPair) -> str:
    return hour_label(pair.start)
