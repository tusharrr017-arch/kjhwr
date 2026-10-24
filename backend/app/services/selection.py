"""Choose the forecast that was knowable at a decision time."""

from __future__ import annotations

from datetime import datetime

from app.services.models import ForecastRecord


def select_forecast(
    records: list[ForecastRecord],
    cutoff: datetime,
    fixed_publish: datetime | None = None,
) -> ForecastRecord | None:
    """Pick one forecast for a single delivery hour.

    With a fixed publication time, only that issue is eligible.
    Otherwise the latest issue at or before `cutoff` is eligible.
    A later issue is never used, including one published after delivery.
    """
    if fixed_publish is not None:
        matches = [record for record in records if record.publish_time == fixed_publish]
        return matches[-1] if matches else None

    eligible = [record for record in records if record.publish_time <= cutoff]
    if not eligible:
        return None
    return max(eligible, key=lambda record: record.publish_time)
