"""Parse Elexon rows into domain records.

Missing generation stays missing. It is never replaced with zero.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timezone

from app.core.time import parse_utc
from app.services.models import ActualRecord, ForecastRecord

UTC = timezone.utc


def parse_generation(value: object) -> tuple[float | None, str | None]:
    """Return (megawatts, problem). A null is a missing value, not an error."""
    if value is None:
        return None, None
    if isinstance(value, bool):
        return None, "invalid"
    number: float
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None, None
        try:
            number = float(text)
        except ValueError:
            return None, "invalid"
    else:
        return None, "invalid"
    if math.isnan(number) or math.isinf(number):
        return None, "invalid"
    if number < 0:
        return None, "negative"
    return number, None


def _cap(messages: list[str], limit: int = 8) -> list[str]:
    if len(messages) <= limit:
        return messages
    hidden = len(messages) - limit
    return messages[:limit] + [f"{hidden} further data warnings were omitted."]


def normalize_actuals(rows: list[object]) -> tuple[list[ActualRecord], list[str]]:
    warnings: list[str] = []
    invalid = 0
    negative = 0
    malformed = 0
    parsed: list[ActualRecord] = []

    for row in rows:
        if not isinstance(row, dict):
            malformed += 1
            continue
        dataset = row.get("dataset")
        if dataset not in (None, "FUELHH"):
            continue
        fuel = row.get("fuelType")
        if not isinstance(fuel, str) or fuel.strip().upper() != "WIND":
            continue
        try:
            start = parse_utc(str(row["startTime"]))
            settlement = date.fromisoformat(str(row["settlementDate"]))
        except (KeyError, TypeError, ValueError):
            malformed += 1
            continue
        raw_publish = row.get("publishTime")
        try:
            published = parse_utc(str(raw_publish)) if raw_publish else datetime.min.replace(tzinfo=UTC)
        except (TypeError, ValueError):
            malformed += 1
            continue
        period_raw = row.get("settlementPeriod")
        period = (
            period_raw
            if isinstance(period_raw, int) and not isinstance(period_raw, bool) and 1 <= period_raw <= 50
            else None
        )
        generation, problem = parse_generation(row.get("generation"))
        if problem == "negative":
            negative += 1
            generation = None
        elif problem == "invalid":
            invalid += 1
            generation = None
        parsed.append(
            ActualRecord(
                start=start,
                settlement_date=settlement,
                settlement_period=period,
                generation_mw=generation,
                publish_time=published,
            )
        )

    deduped, conflicts = _dedupe_actuals(parsed)
    warnings.extend(conflicts)
    if malformed:
        warnings.append(f"Skipped {malformed} wind actual rows with unusable timestamps.")
    if invalid:
        warnings.append(f"Left {invalid} actual generation values blank because they were not valid numbers.")
    if negative:
        warnings.append(f"Left {negative} negative actual generation values blank.")
    return deduped, _cap(warnings)


def _dedupe_actuals(records: list[ActualRecord]) -> tuple[list[ActualRecord], list[str]]:
    chosen: dict[datetime, ActualRecord] = {}
    warnings: list[str] = []
    for record in records:
        current = chosen.get(record.start)
        if current is None:
            chosen[record.start] = record
            continue
        same_value = current.generation_mw == record.generation_mw
        if same_value:
            if record.publish_time >= current.publish_time:
                chosen[record.start] = record
            continue
        winner = record if record.publish_time >= current.publish_time else current
        warnings.append(
            f"Conflicting wind actuals at {record.start.strftime('%Y-%m-%d %H:%M')} UTC; kept the later publication."
        )
        chosen[record.start] = winner
    return list(chosen.values()), warnings


def normalize_forecasts(rows: list[object]) -> tuple[list[ForecastRecord], list[str]]:
    warnings: list[str] = []
    invalid = 0
    negative = 0
    malformed = 0
    parsed: list[ForecastRecord] = []

    for row in rows:
        if not isinstance(row, dict):
            malformed += 1
            continue
        dataset = row.get("dataset")
        if dataset not in (None, "WINDFOR"):
            continue
        try:
            start = parse_utc(str(row["startTime"]))
            published = parse_utc(str(row["publishTime"]))
        except (KeyError, TypeError, ValueError):
            malformed += 1
            continue
        generation, problem = parse_generation(row.get("generation"))
        if problem == "negative":
            negative += 1
            continue
        if problem == "invalid" or generation is None:
            if problem == "invalid":
                invalid += 1
            continue
        parsed.append(ForecastRecord(start=start, publish_time=published, generation_mw=generation))

    deduped, conflicts = _dedupe_forecasts(parsed)
    warnings.extend(conflicts)
    if malformed:
        warnings.append(f"Skipped {malformed} forecast rows with unusable timestamps.")
    if invalid:
        warnings.append(f"Excluded {invalid} forecast rows whose generation was not a valid number.")
    if negative:
        warnings.append(f"Excluded {negative} forecast rows with negative generation.")
    return deduped, _cap(warnings)


def _dedupe_forecasts(records: list[ForecastRecord]) -> tuple[list[ForecastRecord], list[str]]:
    grouped: dict[tuple[datetime, datetime], list[ForecastRecord]] = {}
    for record in records:
        grouped.setdefault((record.start, record.publish_time), []).append(record)
    kept: list[ForecastRecord] = []
    warnings: list[str] = []
    for (start, published), group in grouped.items():
        values = {item.generation_mw for item in group}
        if len(values) > 1:
            warnings.append(
                "Conflicting forecasts for "
                f"{start.strftime('%Y-%m-%d %H:%M')} UTC published "
                f"{published.strftime('%Y-%m-%d %H:%M')} UTC were excluded."
            )
            continue
        kept.append(group[0])
    return kept, warnings
