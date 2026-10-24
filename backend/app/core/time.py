"""Timezone helpers. Settlement days and auction gates use Europe/London."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

UTC = timezone.utc
LONDON = ZoneInfo("Europe/London")


def parse_utc(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError(f"Timestamp {value} is missing a timezone")
    return parsed.astimezone(UTC).replace(microsecond=0)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Timestamps must include a timezone")
    return value.astimezone(UTC).replace(microsecond=0)


def iso_z(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def london_label(value: datetime, *, with_date: bool = True) -> str:
    local = value.astimezone(LONDON)
    stamp = local.strftime("%d %b %Y %H:%M") if with_date else local.strftime("%H:%M")
    zone = local.tzname() or "UK"
    return f"{stamp} {zone}"


def hour_label(start: datetime) -> str:
    local = start.astimezone(LONDON)
    end = (start + timedelta(hours=1)).astimezone(LONDON)
    return f"{local.strftime('%H:%M')}–{end.strftime('%H:%M')}"


def clock_label(moment: datetime) -> str:
    local = moment.astimezone(LONDON)
    return local.strftime("%H:%M")


def expected_hours(settlement_date: date) -> list[datetime]:
    """UTC starts of each clock hour in the UK settlement day.

    A normal day has 24 hours. The last Sunday in March has 23 and the last
    Sunday in October has 25. January 2026 has 24.
    """
    start = datetime.combine(settlement_date, time.min, tzinfo=LONDON).astimezone(UTC)
    end = datetime.combine(settlement_date + timedelta(days=1), time.min, tzinfo=LONDON).astimezone(UTC)
    cursor = start.replace(microsecond=0)
    stop = end.replace(microsecond=0)
    hours: list[datetime] = []
    while cursor < stop:
        hours.append(cursor)
        cursor += timedelta(hours=1)
    return hours


def decision_cutoff(settlement_date: date, local_time: time) -> datetime:
    """Auction gate on the calendar day before the settlement date, as UTC."""
    decision_day = settlement_date - timedelta(days=1)
    local = datetime.combine(decision_day, local_time, tzinfo=LONDON)
    return local.astimezone(UTC).replace(microsecond=0)


def publish_window(
    settlement_from: date,
    settlement_to: date,
    lead_days: int,
) -> tuple[datetime, datetime]:
    """Publication window that can cover the settlement range.

    WINDFOR issues observed for January 2026 cover roughly three days, so the
    lead needs to start before the first delivery day. The end includes the
    delivery day itself so later issues can be inspected. The end is exclusive.
    """
    start = datetime.combine(settlement_from - timedelta(days=lead_days), time.min, tzinfo=UTC)
    end = datetime.combine(settlement_to + timedelta(days=1), time.min, tzinfo=UTC)
    return start, end


def date_chunks(start: date, end: date, days: int) -> list[tuple[date, date]]:
    """Inclusive date chunks on a fixed grid so overlapping requests share a cache key."""
    if end < start:
        return []
    if days < 1:
        raise ValueError("Chunk length must be at least one day")
    origin = date(2025, 1, 1)
    offset = (start - origin).days // days
    cursor = origin + timedelta(days=offset * days)
    chunks: list[tuple[date, date]] = []
    while cursor <= end:
        chunk_end = cursor + timedelta(days=days - 1)
        chunks.append((cursor, chunk_end))
        cursor = chunk_end + timedelta(days=1)
    return chunks


def datetime_chunks(start: datetime, end: datetime, days: int) -> list[tuple[datetime, datetime]]:
    """Half-open UTC chunks on a fixed grid. `end` is exclusive."""
    if end <= start:
        return []
    if days < 1:
        raise ValueError("Chunk length must be at least one day")
    origin = datetime(2025, 1, 1, tzinfo=UTC)
    step = timedelta(days=days)
    offset = int((start - origin).total_seconds() // step.total_seconds())
    cursor = origin + (offset * step)
    chunks: list[tuple[datetime, datetime]] = []
    while cursor < end:
        chunks.append((cursor, cursor + step))
        cursor += step
    return chunks
