from datetime import datetime, timedelta, timezone

from app.services.models import ForecastRecord
from app.services.selection import select_forecast

UTC = timezone.utc
HOUR = datetime(2026, 1, 15, 0, tzinfo=UTC)
GATE = datetime(2026, 1, 14, 9, 20, tzinfo=UTC)


def _record(published: datetime, generation: float) -> ForecastRecord:
    return ForecastRecord(HOUR, published, generation)


def test_latest_issue_at_or_before_the_gate_is_used() -> None:
    records = [
        _record(datetime(2026, 1, 14, 2, 30, tzinfo=UTC), 1),
        _record(datetime(2026, 1, 14, 7, 30, tzinfo=UTC), 3),
        _record(datetime(2026, 1, 14, 9, 20, tzinfo=UTC), 4),
        _record(datetime(2026, 1, 14, 9, 30, tzinfo=UTC), 5),
    ]
    chosen = select_forecast(records, GATE)
    assert chosen is not None
    assert chosen.generation_mw == 4


def test_forecasts_published_after_the_gate_are_not_used() -> None:
    after_delivery = _record(datetime(2026, 1, 15, 22, 30, tzinfo=UTC), 0)
    before = _record(datetime(2026, 1, 14, 7, 30, tzinfo=UTC), 10)
    chosen = select_forecast([after_delivery, before], GATE)
    assert chosen is not None
    assert chosen.generation_mw == 10
    assert select_forecast([after_delivery], GATE) is None


def test_a_later_deadline_may_use_a_later_issue() -> None:
    early = _record(datetime(2026, 1, 14, 7, 30, tzinfo=UTC), 100)
    afternoon = _record(datetime(2026, 1, 14, 15, 30, tzinfo=UTC), 200)
    evening = _record(datetime(2026, 1, 14, 18, 30, tzinfo=UTC), 300)
    records = [early, afternoon, evening]
    morning_gate = datetime(2026, 1, 14, 9, 20, tzinfo=UTC)
    afternoon_gate = datetime(2026, 1, 14, 15, 30, tzinfo=UTC)
    assert select_forecast(records, morning_gate) == early
    chosen = select_forecast(records, afternoon_gate)
    assert chosen == afternoon
    assert chosen is not None
    assert chosen.generation_mw == 200


def test_one_second_after_the_gate_is_too_late() -> None:
    late = _record(GATE + timedelta(seconds=1), 9)
    assert select_forecast([late], GATE) is None


def test_fixed_publication_does_not_fall_back_to_another_issue() -> None:
    early = _record(datetime(2026, 1, 14, 7, 30, tzinfo=UTC), 3)
    later = _record(datetime(2026, 1, 14, 9, 30, tzinfo=UTC), 8)
    chosen = select_forecast([early, later], GATE, fixed_publish=later.publish_time)
    assert chosen is not None
    assert chosen.generation_mw == 8
    missing = datetime(2026, 1, 14, 11, 30, tzinfo=UTC)
    assert select_forecast([early, later], GATE, fixed_publish=missing) is None
