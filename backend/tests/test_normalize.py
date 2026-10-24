from app.services.normalize import normalize_actuals, normalize_forecasts, parse_generation
from tests.fixture_data import ACTUALS, FORECASTS


def test_parse_generation_does_not_turn_invalid_values_into_zero() -> None:
    assert parse_generation(None) == (None, None)
    assert parse_generation("n/a")[0] is None
    assert parse_generation(True)[0] is None
    assert parse_generation(-5) == (None, "negative")
    assert parse_generation("120.5") == (120.5, None)


def test_actuals_keep_wind_only_and_the_later_duplicate() -> None:
    records, warnings = normalize_actuals(ACTUALS)
    by_start = {record.start.isoformat(): record for record in records}
    midnight = by_start["2026-01-15T00:00:00+00:00"]
    assert midnight.generation_mw == 100
    assert all(record.generation_mw != 20000 for record in records)
    assert any("Conflicting wind actuals" in warning for warning in warnings)
    four = by_start["2026-01-15T04:00:00+00:00"]
    assert four.generation_mw is None


def test_invalid_forecast_is_dropped_and_identical_duplicates_collapse() -> None:
    rows = FORECASTS + [FORECASTS[2], {"dataset": "WINDFOR", "publishTime": "2026-01-14T07:30:00Z", "startTime": "2026-01-15T05:00:00Z", "generation": -3}]
    records, warnings = normalize_forecasts(rows)
    midnight = [record for record in records if record.start.hour == 0]
    assert {record.generation_mw for record in midnight} == {130, 150}
    assert any("not a valid number" in warning for warning in warnings)
    assert any("negative" in warning for warning in warnings)


def test_conflicting_forecasts_at_one_publication_are_excluded() -> None:
    rows = [
        {"dataset": "WINDFOR", "publishTime": "2026-01-14T07:30:00Z", "startTime": "2026-01-15T06:00:00Z", "generation": 10},
        {"dataset": "WINDFOR", "publishTime": "2026-01-14T07:30:00Z", "startTime": "2026-01-15T06:00:00Z", "generation": 12},
    ]
    records, warnings = normalize_forecasts(rows)
    assert records == []
    assert warnings
