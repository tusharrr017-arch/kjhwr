import asyncio

import httpx

from app.clients.elexon import ElexonClient, ElexonError
from app.core.config import Settings


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "elexon_base_url": "https://data.elexon.co.uk/bmrs/api/v1",
        "http_timeout_seconds": 5,
        "http_max_retries": 3,
        "cache_ttl_seconds": 60,
        "cors_origins": "*",
        "near_zero_mw": 1,
        "log_level": "WARNING",
        "forecast_lead_days": 4,
        "chunk_days": 7,
        "max_range_days": 31,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


async def _noop(_: float) -> None:
    return None


def test_fuelhh_requests_wind_and_caches() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(
            200,
            json=[
                {
                    "dataset": "FUELHH",
                    "fuelType": "WIND",
                    "startTime": "2026-01-15T00:00:00Z",
                    "settlementDate": "2026-01-15",
                    "settlementPeriod": 1,
                    "generation": 10,
                    "publishTime": "2026-01-15T01:00:00Z",
                }
            ],
        )

    async def scenario() -> None:
        client = ElexonClient(_settings(), transport=httpx.MockTransport(handler), sleep=_noop)
        from datetime import date

        first_rows, first_meta = await client.fetch_fuelhh(date(2026, 1, 15), date(2026, 1, 15))
        second_rows, second_meta = await client.fetch_fuelhh(date(2026, 1, 15), date(2026, 1, 15))
        await client.aclose()
        assert first_rows[0]["generation"] == 10
        assert second_rows == first_rows
        assert first_meta.cache == "live"
        assert second_meta.cache == "cache"
        assert len(calls) == 1
        assert "fuelType=WIND" in calls[0]
        assert "settlementDateFrom=" in calls[0]
        assert "publishDateTimeFrom" not in calls[0]

    asyncio.run(scenario())


def test_windfor_uses_a_publication_window() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json={"data": []})

    async def scenario() -> None:
        from datetime import datetime, timezone

        client = ElexonClient(_settings(), transport=httpx.MockTransport(handler), sleep=_noop)
        start = datetime(2026, 1, 14, tzinfo=timezone.utc)
        end = datetime(2026, 1, 15, tzinfo=timezone.utc)
        rows, _ = await client.fetch_windfor(start, end)
        await client.aclose()
        assert rows == []
        assert "publishDateTimeFrom=" in seen[0]
        assert "publishDateTimeTo=" in seen[0]
        assert "fuelType" not in seen[0]

    asyncio.run(scenario())


def test_retries_a_transient_failure_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503, json={"error": "busy"})
        return httpx.Response(200, json=[])

    async def scenario() -> None:
        from datetime import date

        client = ElexonClient(_settings(), transport=httpx.MockTransport(handler), sleep=_noop)
        rows, meta = await client.fetch_fuelhh(date(2026, 1, 15), date(2026, 1, 15))
        await client.aclose()
        assert rows == []
        assert meta.cache == "live"
        assert calls["n"] == 2

    asyncio.run(scenario())


def test_bad_request_is_not_retried() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        calls["n"] += 1
        return httpx.Response(400, json={"detail": "bad"})

    async def scenario() -> None:
        from datetime import date

        client = ElexonClient(_settings(http_max_retries=3), transport=httpx.MockTransport(handler), sleep=_noop)
        try:
            await client.fetch_fuelhh(date(2026, 1, 15), date(2026, 1, 15))
        except ElexonError as exc:
            assert "400" in str(exc)
        else:
            raise AssertionError("expected ElexonError")
        await client.aclose()
        assert calls["n"] == 1

    asyncio.run(scenario())


def test_timeout_is_retried_and_reported() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        calls["n"] += 1
        raise httpx.TimeoutException("timed out")

    async def scenario() -> None:
        from datetime import date

        client = ElexonClient(_settings(http_max_retries=2), transport=httpx.MockTransport(handler), sleep=_noop)
        try:
            await client.fetch_fuelhh(date(2026, 1, 15), date(2026, 1, 15))
        except ElexonError as exc:
            assert "timed out" in str(exc)
        else:
            raise AssertionError("expected ElexonError")
        await client.aclose()
        assert calls["n"] == 2

    asyncio.run(scenario())
