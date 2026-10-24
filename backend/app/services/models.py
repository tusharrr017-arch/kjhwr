"""Domain records. Timestamps are timezone-aware UTC."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class ActualRecord:
    start: datetime
    settlement_date: date
    settlement_period: int | None
    generation_mw: float | None
    publish_time: datetime


@dataclass(frozen=True)
class ForecastRecord:
    start: datetime
    publish_time: datetime
    generation_mw: float


@dataclass(frozen=True)
class HalfHourView:
    start: datetime
    settlement_period: int | None
    generation_mw: float | None


@dataclass(frozen=True)
class HourPair:
    start: datetime
    end: datetime
    settlement_date: date
    settlement_periods: tuple[int, ...]
    actual_mw: float | None
    actual_complete: bool
    half_hours: tuple[HalfHourView, ...]
    forecast_mw: float | None
    publish_time: datetime | None
    error_mw: float | None
    absolute_error_mw: float | None
    percentage_error: float | None


@dataclass
class LoadedData:
    actuals: list[ActualRecord]
    forecasts: list[ForecastRecord]
    warnings: list[str]
    retrieved_at: datetime
    cache: str
