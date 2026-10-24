from datetime import date, datetime, time, timedelta, timezone

from app.core.time import date_chunks, datetime_chunks, decision_cutoff, expected_hours, publish_window
from app.services.alignment import build_day_pairs, index_actuals, index_forecasts, series_points
from app.services.normalize import normalize_actuals, normalize_forecasts
from tests.fixture_data import ACTUALS, FORECASTS

UTC = timezone.utc


def test_january_gate_is_previous_day_at_the_same_clock_time() -> None:
    cutoff = decision_cutoff(date(2026, 1, 15), time(9, 20))
    assert cutoff == datetime(2026, 1, 14, 9, 20, tzinfo=UTC)


def test_january_delivery_boundaries_use_december_and_the_previous_day() -> None:
    first = decision_cutoff(date(2026, 1, 1), time(9, 20))
    last = decision_cutoff(date(2026, 1, 31), time(9, 20))
    assert first == datetime(2025, 12, 31, 9, 20, tzinfo=UTC)
    assert last == datetime(2026, 1, 30, 9, 20, tzinfo=UTC)
    start, end = publish_window(date(2026, 1, 1), date(2026, 1, 31), 4)
    assert start == datetime(2025, 12, 28, tzinfo=UTC)
    assert end == datetime(2026, 2, 1, tzinfo=UTC)


def test_summer_gate_converts_british_summer_time_to_utc() -> None:
    cutoff = decision_cutoff(date(2026, 7, 15), time(9, 20))
    assert cutoff == datetime(2026, 7, 14, 8, 20, tzinfo=UTC)


def test_clock_change_days_do_not_assume_twenty_four_hours() -> None:
    assert len(expected_hours(date(2026, 1, 15))) == 24
    assert len(expected_hours(date(2026, 3, 29))) == 23
    assert len(expected_hours(date(2026, 10, 25))) == 25


def test_january_2026_contains_744_expected_hours() -> None:
    total = 0
    for day_number in range(1, 32):
        hours = expected_hours(date(2026, 1, day_number))
        assert len(hours) == 24
        assert hours[0] == datetime(2026, 1, day_number, tzinfo=UTC)
        assert hours[-1] == datetime(2026, 1, day_number, 23, tzinfo=UTC)
        total += len(hours)
    assert total == 31 * 24 == 744


def test_chunks_cover_the_requested_range_without_overlap() -> None:
    chunks = date_chunks(date(2026, 1, 1), date(2026, 1, 31), 7)
    covered: set[date] = set()
    for start, end in chunks:
        assert end >= start
        day = start
        while day <= end:
            covered.add(day)
            day += timedelta(days=1)
    january = {date(2026, 1, day) for day in range(1, 32)}
    assert january <= covered
    windows = datetime_chunks(
        datetime(2026, 1, 11, tzinfo=UTC),
        datetime(2026, 1, 16, tzinfo=UTC),
        7,
    )
    assert windows
    assert windows[0][0] <= datetime(2026, 1, 11, tzinfo=UTC)
    assert windows[-1][1] >= datetime(2026, 1, 16, tzinfo=UTC)


def test_pairs_match_on_timestamp_and_hold_the_forecast_across_the_hour() -> None:
    actuals, _ = normalize_actuals(list(reversed(ACTUALS)))
    forecasts, _ = normalize_forecasts(list(reversed(FORECASTS)))
    pairs = build_day_pairs(
        date(2026, 1, 15),
        index_actuals(actuals),
        index_forecasts(forecasts),
        gate=time(9, 20),
        near_zero_mw=1,
    )
    by_hour = {pair.start.hour: pair for pair in pairs}
    assert by_hour[0].actual_mw == 110
    assert by_hour[0].forecast_mw == 130
    assert by_hour[0].error_mw == 20
    assert by_hour[2].actual_complete is False
    assert by_hour[2].error_mw is None
    assert by_hour[2].actual_mw is None
    assert by_hour[3].actual_mw == 0
    assert by_hour[3].error_mw == 10
    assert by_hour[3].percentage_error is None
    assert by_hour[3].forecast_mw == 10

    series = series_points(pairs)
    two_am = [point for point in series if point["label"] in {"02:00", "02:30"}]
    assert [point["forecast_mw"] for point in two_am] == [80, 80]
    assert [point["actual_mw"] for point in two_am] == [50, None]
    five_am = next(point for point in series if point["label"] == "05:00")
    assert five_am["forecast_mw"] is None
    assert five_am["actual_mw"] is None
