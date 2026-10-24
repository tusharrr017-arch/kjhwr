import math

import pytest
from fastapi.testclient import TestClient

from app.clients.elexon import ElexonError
from app.core.cache import CacheMeta
from app.core.config import Settings
from app.main import create_app
from tests.fixture_data import FakeElexon


def _settings() -> Settings:
    return Settings(
        elexon_base_url="https://data.elexon.co.uk/bmrs/api/v1",
        http_timeout_seconds=5,
        http_max_retries=2,
        cache_ttl_seconds=60,
        cors_origins="*",
        near_zero_mw=1,
        log_level="WARNING",
        forecast_lead_days=4,
        chunk_days=7,
        max_range_days=31,
    )


def _client(source: object) -> TestClient:
    app = create_app(_settings(), client=source)  # type: ignore[arg-type]
    return TestClient(app)


def test_health() -> None:
    with _client(FakeElexon()) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_overview_scores_the_gate_forecast_not_a_later_issue() -> None:
    with _client(FakeElexon()) as client:
        response = client.get(
            "/api/overview",
            params={
                "settlement_from": "2026-01-15",
                "settlement_to": "2026-01-15",
                "cutoff_profile": "epex_60min",
            },
        )
    assert response.status_code == 200
    body = response.json()
    summary = body["summary"]
    assert summary["n_matched"] == 3
    assert summary["n_expected"] == 24
    assert summary["n_with_forecast"] == 5
    assert summary["n_excluded_near_zero"] == 1
    assert summary["mae_mw"] == pytest.approx(50 / 3)
    assert summary["rmse_mw"] == pytest.approx(math.sqrt(300))
    assert summary["bias_mw"] == pytest.approx(10 / 3)
    assert summary["mape_percent"] == pytest.approx((20 / 110 * 100 + 10) / 2)
    assert summary["mean_forecast_mw"] == pytest.approx((130 + 180 + 10) / 3)
    assert summary["mean_actual_mw"] == pytest.approx((110 + 200 + 0) / 3)
    assert summary["forecast_energy_mwh"] == pytest.approx(470)
    assert summary["actual_energy_mwh"] == pytest.approx(355)
    assert body["metadata"]["cache"] == "live"
    assert body["metadata"]["selection_rule"] == "latest_publish_on_or_before_cutoff"
    assert "positive" in body["metadata"]["definitions"]["bias"].lower() or "over" in body["metadata"]["definitions"]["bias"].lower()
    assert any("Conflicting wind actuals" in warning for warning in body["metadata"]["warnings"])


def test_nord_pool_gate_can_see_the_0930_issue() -> None:
    with _client(FakeElexon()) as client:
        response = client.get(
            "/api/overview",
            params={
                "settlement_from": "2026-01-15",
                "settlement_to": "2026-01-15",
                "cutoff_profile": "nordpool_60min",
            },
        )
    assert response.status_code == 200
    summary = response.json()["summary"]
    assert summary["mae_mw"] == pytest.approx(70 / 3)
    assert summary["bias_mw"] == pytest.approx(10)


def test_exact_publication_and_forecast_endpoint_agree() -> None:
    params = {
        "settlement_date": "2026-01-15",
        "cutoff_profile": "epex_60min",
        "publish_time": "2026-01-14T09:30:00Z",
    }
    with _client(FakeElexon()) as client:
        forecasts = client.get("/api/forecasts", params=params)
        overview = client.get(
            "/api/overview",
            params={
                "settlement_from": "2026-01-15",
                "settlement_to": "2026-01-15",
                "cutoff_profile": "epex_60min",
                "publish_time": "2026-01-14T09:30:00Z",
            },
        )
    assert forecasts.status_code == 200
    body = forecasts.json()
    first = body["periods"][0]
    assert first["forecast_mw"] == 150
    assert first["actual_mw"] == 110
    assert first["error_mw"] == 40
    assert first["half_hours"][0]["generation_mw"] == 100
    assert body["summary"]["n_matched"] == 2
    assert body["summary"]["mae_mw"] == pytest.approx(30)
    assert body["evolution"]["start_time"] == "2026-01-15T12:00:00Z"
    assert overview.json()["summary"]["mae_mw"] == pytest.approx(body["summary"]["mae_mw"])
    assert body["metadata"]["selection_rule"] == "exact_publication"


def test_january_window_includes_every_delivery_day() -> None:
    with _client(FakeElexon()) as client:
        response = client.get(
            "/api/accuracy",
            params={"settlement_from": "2026-01-01", "settlement_to": "2026-01-31"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["n_expected"] == 31 * 24
    assert body["summary"]["n_matched"] == 3
    assert [row["settlement_date"] for row in body["daily"]] == [
        f"2026-01-{day:02d}" for day in range(1, 32)
    ]
    january_day = next(row for row in body["daily"] if row["settlement_date"] == "2026-01-15")
    assert january_day["n_matched"] == 3
    assert january_day["mae_mw"] == pytest.approx(body["summary"]["mae_mw"])
    empty = next(row for row in body["daily"] if row["settlement_date"] == "2026-01-01")
    assert empty["n_matched"] == 0
    assert empty["mae_mw"] is None


def test_later_publication_is_listed_but_not_used_at_the_deadline() -> None:
    with _client(FakeElexon()) as client:
        response = client.get(
            "/api/forecasts",
            params={"settlement_date": "2026-01-15", "cutoff_profile": "epex_60min"},
        )
    assert response.status_code == 200
    body = response.json()
    by_time = {item["publish_time"]: item for item in body["publications"]}
    assert by_time["2026-01-14T07:30:00Z"]["eligible"] is True
    assert by_time["2026-01-14T07:30:00Z"]["used_for_delivery_hour"] is True
    assert by_time["2026-01-14T09:30:00Z"]["eligible"] is False
    assert by_time["2026-01-14T09:30:00Z"]["used_for_delivery_hour"] is False
    assert body["summary"]["mae_mw"] == pytest.approx(50 / 3)
    assert "deadline" in body["metadata"]["definitions"]["selection"].lower()


def test_accuracy_uses_the_gate_for_each_day() -> None:
    with _client(FakeElexon()) as client:
        response = client.get(
            "/api/accuracy",
            params={"settlement_from": "2026-01-15", "settlement_to": "2026-01-15"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["mae_mw"] == pytest.approx(50 / 3)
    assert body["daily"][0]["settlement_date"] == "2026-01-15"
    assert body["daily"][0]["n_matched"] == 3
    assert body["daily"][0]["mae_mw"] == pytest.approx(body["summary"]["mae_mw"])


def test_empty_archive_is_an_empty_score_not_an_error() -> None:
    with _client(FakeElexon(actuals=[], forecasts=[])) as client:
        response = client.get(
            "/api/overview",
            params={"settlement_from": "2026-01-15", "settlement_to": "2026-01-15"},
        )
    assert response.status_code == 200
    summary = response.json()["summary"]
    assert summary["n_matched"] == 0
    assert summary["mae_mw"] is None
    assert summary["bias_mw"] is None
    assert summary["actual_energy_mwh"] is None


def test_upstream_failure_is_a_bad_gateway() -> None:
    class Boom:
        async def fetch_fuelhh(self, *args: object, **kwargs: object) -> None:
            raise ElexonError("The Elexon request timed out after 2 attempts.")

        async def fetch_windfor(self, *args: object, **kwargs: object) -> tuple[list[object], CacheMeta]:
            from datetime import datetime, timezone

            return [], CacheMeta(datetime(2026, 1, 16, tzinfo=timezone.utc), "live")

    with _client(Boom()) as client:
        response = client.get(
            "/api/overview",
            params={"settlement_from": "2026-01-15", "settlement_to": "2026-01-15"},
        )
    assert response.status_code == 502
    assert "timed out" in response.json()["detail"]


def test_invalid_ranges_and_profiles_are_rejected() -> None:
    with _client(FakeElexon()) as client:
        reversed_range = client.get(
            "/api/overview",
            params={"settlement_from": "2026-01-18", "settlement_to": "2026-01-12"},
        )
        too_long = client.get(
            "/api/accuracy",
            params={"settlement_from": "2026-01-01", "settlement_to": "2026-02-05"},
        )
        custom = client.get(
            "/api/overview",
            params={
                "settlement_from": "2026-01-15",
                "settlement_to": "2026-01-15",
                "cutoff_profile": "custom",
            },
        )
        unknown_hour = client.get(
            "/api/forecasts",
            params={"settlement_date": "2026-01-15", "start_time": "2026-01-15T00:15:00Z"},
        )
    assert reversed_range.status_code == 422
    assert too_long.status_code == 422
    assert custom.status_code == 422
    assert unknown_hour.status_code == 422
