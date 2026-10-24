"""Orchestrates retrieval, forecast selection, and scores."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import date, datetime, time, timedelta

from app.clients.elexon import ElexonClient
from app.core.cache import AsyncTtlCache
from app.core.config import Settings
from app.core.cutoffs import resolve_cutoff
from app.core.time import (
    LONDON,
    decision_cutoff,
    ensure_utc,
    expected_hours,
    hour_label,
    iso_z,
    london_label,
    publish_window,
)
from app.services.aggregate import daily_summaries, summarise_pairs
from app.services.alignment import (
    build_pairs,
    default_hour,
    index_actuals,
    index_forecasts,
    series_points,
)
from app.services.models import ActualRecord, HourPair, LoadedData
from app.services.normalize import normalize_actuals, normalize_forecasts

logger = logging.getLogger("foregate.analytics")

SOURCES = [
    "https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream",
    "https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream",
]

ALIGNMENT = (
    "WINDFOR forecasts in this archive are hourly average MW. FUELHH actuals are "
    "half-hourly average MW. Each score uses the mean of the two half-hours inside "
    "the forecast hour. Hours are matched on the UTC delivery timestamp, not on row order. "
    "A missing half-hour is excluded, not treated as zero."
)


class AnalyticsService:
    def __init__(self, client: ElexonClient, settings: Settings) -> None:
        self.client = client
        self.settings = settings
        self._bundles: AsyncTtlCache[LoadedData] = AsyncTtlCache(settings.cache_ttl_seconds)

    async def overview(
        self,
        settlement_from: date,
        settlement_to: date,
        cutoff_profile: str,
        cutoff_time: str | None,
        publish_time: datetime | None,
        refresh: bool,
    ) -> dict[str, object]:
        loaded = await self.load(settlement_from, settlement_to, refresh)
        profile, label, gate, citation = resolve_cutoff(cutoff_profile, cutoff_time)
        fixed = _optional_utc(publish_time)
        pairs = _pairs(loaded, settlement_from, settlement_to, gate, self.settings.near_zero_mw, fixed)
        summary = _summary(pairs, loaded.actuals, settlement_from, settlement_to, self.settings.near_zero_mw)
        return {
            "metadata": self._meta(
                loaded,
                settlement_from,
                settlement_to,
                profile,
                label,
                gate,
                citation,
                fixed,
            ),
            "summary": summary,
        }

    async def forecasts(
        self,
        settlement_date: date,
        cutoff_profile: str,
        cutoff_time: str | None,
        publish_time: datetime | None,
        start_time: datetime | None,
        refresh: bool,
    ) -> dict[str, object]:
        loaded = await self.load(settlement_date, settlement_date, refresh)
        profile, label, gate, citation = resolve_cutoff(cutoff_profile, cutoff_time)
        fixed = _optional_utc(publish_time)
        pairs = _pairs(loaded, settlement_date, settlement_date, gate, self.settings.near_zero_mw, fixed)
        hours = [pair.start for pair in pairs]
        inspected = ensure_utc(start_time) if start_time else default_hour(settlement_date, hours)
        if inspected not in hours:
            raise ValueError("start_time is not an hour in this settlement day")
        inspected_pair = next(pair for pair in pairs if pair.start == inspected)
        cutoff = decision_cutoff(settlement_date, gate)
        publications = _publications(loaded, settlement_date, cutoff, pairs)
        summary = _summary(pairs, loaded.actuals, settlement_date, settlement_date, self.settings.near_zero_mw)
        chosen_times = {pair.publish_time for pair in pairs if pair.publish_time is not None}
        uniform = next(iter(chosen_times)) if len(chosen_times) == 1 else None
        return {
            "metadata": self._meta(
                loaded, settlement_date, settlement_date, profile, label, gate, citation, fixed
            ),
            "summary": summary,
            "uniform_publish_time": iso_z(uniform) if uniform else None,
            "uniform_publish_label": london_label(uniform) if uniform else None,
            "periods": [_period(pair) for pair in pairs],
            "series": [_series_point(point) for point in series_points(pairs)],
            "publications": publications,
            "evolution": _evolution(loaded, inspected_pair, cutoff, gate),
        }

    async def accuracy(
        self,
        settlement_from: date,
        settlement_to: date,
        cutoff_profile: str,
        cutoff_time: str | None,
        refresh: bool,
    ) -> dict[str, object]:
        loaded = await self.load(settlement_from, settlement_to, refresh)
        profile, label, gate, citation = resolve_cutoff(cutoff_profile, cutoff_time)
        pairs = _pairs(loaded, settlement_from, settlement_to, gate, self.settings.near_zero_mw, None)
        summary = _summary(pairs, loaded.actuals, settlement_from, settlement_to, self.settings.near_zero_mw)
        return {
            "metadata": self._meta(
                loaded,
                settlement_from,
                settlement_to,
                profile,
                label,
                gate,
                citation,
                None,
                selection_rule="latest_publish_on_or_before_cutoff",
            ),
            "summary": summary,
            "daily": daily_summaries(pairs, self.settings.near_zero_mw),
        }

    async def load(self, settlement_from: date, settlement_to: date, refresh: bool) -> LoadedData:
        key = f"{settlement_from.isoformat()}:{settlement_to.isoformat()}"

        async def factory() -> LoadedData:
            return await self._fetch(settlement_from, settlement_to, refresh)

        loaded, meta = await self._bundles.get_or_set(key, factory, refresh=refresh)
        if meta.cache == "cache":
            return replace(loaded, cache="cache")
        return loaded

    async def _fetch(self, settlement_from: date, settlement_to: date, refresh: bool) -> LoadedData:
        actual_rows, actual_meta = await self.client.fetch_fuelhh(
            settlement_from, settlement_to, refresh=refresh
        )
        window_start, window_end = publish_window(
            settlement_from, settlement_to, self.settings.forecast_lead_days
        )
        forecast_rows, forecast_meta = await self.client.fetch_windfor(
            window_start, window_end, refresh=refresh
        )
        actuals, actual_warnings = normalize_actuals(actual_rows)
        forecasts, forecast_warnings = normalize_forecasts(forecast_rows)
        warnings = actual_warnings + forecast_warnings
        status = "cache" if actual_meta.cache == "cache" and forecast_meta.cache == "cache" else "live"
        retrieved = min(actual_meta.retrieved_at, forecast_meta.retrieved_at)
        logger.info(
            "bundle %s to %s actuals=%s forecasts=%s cache=%s warnings=%s",
            settlement_from,
            settlement_to,
            len(actuals),
            len(forecasts),
            status,
            len(warnings),
        )
        if warnings:
            logger.warning("data warnings: %s", " | ".join(warnings[:6]))
        return LoadedData(actuals, forecasts, warnings, retrieved, status)

    def _meta(
        self,
        loaded: LoadedData,
        settlement_from: date,
        settlement_to: date,
        profile: str,
        label: str,
        gate: time,
        citation: str,
        publish_time: datetime | None,
        selection_rule: str | None = None,
    ) -> dict[str, object]:
        if selection_rule is None:
            selection_rule = (
                "exact_publication" if publish_time is not None else "latest_publish_on_or_before_cutoff"
            )
        return {
            "unit": "MW",
            "energy_unit": "MWh",
            "timezone": "Europe/London",
            "settlement_from": settlement_from,
            "settlement_to": settlement_to,
            "cutoff_profile": profile,
            "cutoff_label": label,
            "cutoff_local_time": gate.strftime("%H:%M"),
            "offset_days": 1,
            "cutoff_citation": citation,
            "selection_rule": selection_rule,
            "publish_time": iso_z(publish_time) if publish_time else None,
            "alignment": ALIGNMENT,
            "near_zero_mw": self.settings.near_zero_mw,
            "definitions": _definitions(self.settings.near_zero_mw, gate),
            "retrieved_at": iso_z(loaded.retrieved_at),
            "cache": loaded.cache,
            "warnings": loaded.warnings,
            "sources": SOURCES,
        }


def _optional_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return ensure_utc(value)


def _pairs(
    loaded: LoadedData,
    settlement_from: date,
    settlement_to: date,
    gate: time,
    near_zero_mw: float,
    fixed_publish: datetime | None,
) -> list[HourPair]:
    return build_pairs(
        settlement_from,
        settlement_to,
        index_actuals(loaded.actuals),
        index_forecasts(loaded.forecasts),
        gate=gate,
        near_zero_mw=near_zero_mw,
        fixed_publish=fixed_publish,
    )


def _summary(
    pairs: list[HourPair],
    actuals: list[ActualRecord],
    settlement_from: date,
    settlement_to: date,
    near_zero_mw: float,
) -> dict[str, object]:
    summary = summarise_pairs(pairs, near_zero_mw)
    energy, half_hours, expected = _actual_energy(actuals, settlement_from, settlement_to)
    summary["actual_energy_mwh"] = energy
    summary["actual_half_hours"] = half_hours
    summary["expected_half_hours"] = expected
    return summary


def _actual_energy(
    actuals: list[ActualRecord],
    settlement_from: date,
    settlement_to: date,
) -> tuple[float | None, int, int]:
    relevant = [
        record
        for record in actuals
        if settlement_from <= record.settlement_date <= settlement_to and record.generation_mw is not None
    ]
    expected = 0
    day = settlement_from
    while day <= settlement_to:
        expected += len(expected_hours(day)) * 2
        day += timedelta(days=1)
    if not relevant:
        return None, 0, expected
    energy = sum(float(record.generation_mw) * 0.5 for record in relevant if record.generation_mw is not None)
    return energy, len(relevant), expected


def _period(pair: HourPair) -> dict[str, object]:
    return {
        "start_time": iso_z(pair.start),
        "end_time": iso_z(pair.end),
        "label": hour_label(pair.start),
        "settlement_date": pair.settlement_date,
        "settlement_periods": list(pair.settlement_periods),
        "forecast_mw": pair.forecast_mw,
        "forecast_publish_time": iso_z(pair.publish_time) if pair.publish_time else None,
        "forecast_publish_label": london_label(pair.publish_time) if pair.publish_time else None,
        "actual_mw": pair.actual_mw,
        "error_mw": pair.error_mw,
        "absolute_error_mw": pair.absolute_error_mw,
        "percentage_error": pair.percentage_error,
        "half_hours": [
            {
                "start_time": iso_z(half.start),
                "label": half.start.astimezone(LONDON).strftime("%H:%M"),
                "settlement_period": half.settlement_period,
                "generation_mw": half.generation_mw,
            }
            for half in pair.half_hours
        ],
    }


def _series_point(point: dict[str, object]) -> dict[str, object]:
    start = point["start_time"]
    hour = point["hour_start"]
    assert isinstance(start, datetime)
    assert isinstance(hour, datetime)
    return {
        "start_time": iso_z(start),
        "label": point["label"],
        "hour_start": iso_z(hour),
        "actual_mw": point["actual_mw"],
        "forecast_mw": point["forecast_mw"],
    }


def _publications(
    loaded: LoadedData,
    settlement_date: date,
    cutoff: datetime,
    pairs: list[HourPair],
) -> list[dict[str, object]]:
    hours = {pair.start for pair in pairs}
    selected = {pair.publish_time for pair in pairs if pair.publish_time is not None}
    coverage: dict[datetime, int] = {}
    for record in loaded.forecasts:
        if record.start in hours:
            coverage[record.publish_time] = coverage.get(record.publish_time, 0) + 1
    rows = []
    for published in sorted(coverage):
        rows.append(
            {
                "publish_time": iso_z(published),
                "label": london_label(published),
                "hours_covered": coverage[published],
                "eligible": published <= cutoff,
                "used_for_delivery_hour": published in selected,
            }
        )
    return rows


def _evolution(
    loaded: LoadedData,
    pair: HourPair,
    cutoff: datetime,
    gate: time,
) -> dict[str, object]:
    points = []
    for record in sorted(
        (item for item in loaded.forecasts if item.start == pair.start),
        key=lambda item: item.publish_time,
    ):
        points.append(
            {
                "publish_time": iso_z(record.publish_time),
                "label": london_label(record.publish_time),
                "generation_mw": record.generation_mw,
                "eligible": record.publish_time <= cutoff,
                "selected": pair.publish_time == record.publish_time,
            }
        )
    return {
        "start_time": iso_z(pair.start),
        "label": hour_label(pair.start),
        "actual_mw": pair.actual_mw,
        "cutoff_time": iso_z(cutoff),
        "cutoff_label": london_label(cutoff),
        "gate_local_time": gate.strftime("%H:%M"),
        "points": points,
    }


def _definitions(near_zero_mw: float, gate: time) -> dict[str, str]:
    threshold = f"{near_zero_mw:g}"
    clock = gate.strftime("%H:%M")
    return {
        "error": "Error = forecast MW − actual MW. Positive means the forecast was above measured wind generation.",
        "absolute_error": "Absolute error is the size of that difference, in MW.",
        "mae": "MAE is the average absolute forecast error, in MW, across matched hours. It treats an over-forecast and an under-forecast of the same size as equal.",
        "rmse": "RMSE is an error measure in MW that gives extra weight to large misses. It uses the same matched hours as MAE.",
        "bias": "Bias is the average signed forecast error over the same matched hours. Positive bias means the forecast was too high on average.",
        "matched_hours": (
            "A matched hour has both a selected forecast and measured generation. "
            "Measured generation is the average of the two half-hours inside that hour. "
            "If either half-hour is missing, the hour is not matched and is not treated as zero."
        ),
        "percentage_error": (
            f"Percentage error is the signed error divided by actual MW. "
            f"It is blank when actual generation is under {threshold} MW."
        ),
        "alignment": ALIGNMENT,
        "selection": (
            f"For each delivery hour, the score uses the latest forecast published at or before "
            f"{clock} UK time on the previous calendar day. "
            "A forecast published after that deadline can be inspected, but it is not used in the decision-time score. "
            "The day, week and January scores all use this same rule."
        ),
        "procurement": (
            "These scores describe wind-forecast error only. They do not say how much electricity to buy. "
            "Demand and other market positions are outside this dataset."
        ),
    }
