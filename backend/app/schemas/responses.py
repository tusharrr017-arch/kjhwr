"""API response models."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str
    time: str


class Summary(BaseModel):
    mae_mw: float | None
    rmse_mw: float | None
    bias_mw: float | None
    mape_percent: float | None
    n_matched: int
    n_expected: int
    n_complete_actual: int
    n_with_forecast: int
    n_excluded_near_zero: int
    mean_forecast_mw: float | None
    mean_actual_mw: float | None
    forecast_energy_mwh: float | None
    forecast_hours: int
    actual_energy_mwh: float | None
    actual_half_hours: int
    expected_half_hours: int


class Metadata(BaseModel):
    unit: str
    energy_unit: str
    timezone: str
    settlement_from: date
    settlement_to: date
    cutoff_profile: str
    cutoff_label: str
    cutoff_local_time: str
    offset_days: int
    cutoff_citation: str
    selection_rule: str
    publish_time: str | None
    alignment: str
    near_zero_mw: float
    definitions: dict[str, str]
    retrieved_at: str
    cache: str
    warnings: list[str]
    sources: list[str]


class OverviewResponse(BaseModel):
    metadata: Metadata
    summary: Summary


class HalfHour(BaseModel):
    start_time: str
    label: str
    settlement_period: int | None
    generation_mw: float | None


class Period(BaseModel):
    start_time: str
    end_time: str
    label: str
    settlement_date: date
    settlement_periods: list[int]
    forecast_mw: float | None
    forecast_publish_time: str | None
    forecast_publish_label: str | None
    actual_mw: float | None
    error_mw: float | None
    absolute_error_mw: float | None
    percentage_error: float | None
    half_hours: list[HalfHour]


class SeriesPoint(BaseModel):
    start_time: str
    label: str
    hour_start: str
    actual_mw: float | None
    forecast_mw: float | None


class Publication(BaseModel):
    publish_time: str
    label: str
    hours_covered: int
    eligible: bool
    used_for_delivery_hour: bool


class EvolutionPoint(BaseModel):
    publish_time: str
    label: str
    generation_mw: float
    eligible: bool
    selected: bool


class Evolution(BaseModel):
    start_time: str
    label: str
    actual_mw: float | None
    cutoff_time: str
    cutoff_label: str
    gate_local_time: str
    points: list[EvolutionPoint]


class ForecastResponse(BaseModel):
    metadata: Metadata
    summary: Summary
    uniform_publish_time: str | None
    uniform_publish_label: str | None
    periods: list[Period]
    series: list[SeriesPoint]
    publications: list[Publication]
    evolution: Evolution


class DailyScore(BaseModel):
    settlement_date: date
    mae_mw: float | None
    rmse_mw: float | None
    bias_mw: float | None
    mape_percent: float | None
    n_matched: int
    n_expected: int
    n_excluded_near_zero: int
    mean_forecast_mw: float | None
    mean_actual_mw: float | None


class AccuracyResponse(BaseModel):
    metadata: Metadata
    summary: Summary
    daily: list[DailyScore] = Field(default_factory=list)
