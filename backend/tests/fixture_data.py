"""Deterministic Elexon-shaped rows for January 2026."""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.cache import CacheMeta

UTC = timezone.utc

ACTUALS: list[dict[str, object]] = [
    {
        "dataset": "FUELHH",
        "fuelType": "WIND",
        "startTime": "2026-01-15T00:00:00Z",
        "settlementDate": "2026-01-15",
        "settlementPeriod": 1,
        "generation": 999,
        "publishTime": "2026-01-15T00:30:00Z",
    },
    {
        "dataset": "FUELHH",
        "fuelType": "WIND",
        "startTime": "2026-01-15T00:00:00Z",
        "settlementDate": "2026-01-15",
        "settlementPeriod": 1,
        "generation": 100,
        "publishTime": "2026-01-15T01:00:00Z",
    },
    {
        "dataset": "FUELHH",
        "fuelType": "CCGT",
        "startTime": "2026-01-15T00:00:00Z",
        "settlementDate": "2026-01-15",
        "settlementPeriod": 1,
        "generation": 20000,
        "publishTime": "2026-01-15T01:00:00Z",
    },
    {
        "dataset": "FUELHH",
        "fuelType": "WIND",
        "startTime": "2026-01-15T00:30:00Z",
        "settlementDate": "2026-01-15",
        "settlementPeriod": 2,
        "generation": 120,
        "publishTime": "2026-01-15T01:00:00Z",
    },
    {
        "dataset": "FUELHH",
        "fuelType": "WIND",
        "startTime": "2026-01-15T01:00:00Z",
        "settlementDate": "2026-01-15",
        "settlementPeriod": 3,
        "generation": 200,
        "publishTime": "2026-01-15T01:30:00Z",
    },
    {
        "dataset": "FUELHH",
        "fuelType": "WIND",
        "startTime": "2026-01-15T01:30:00Z",
        "settlementDate": "2026-01-15",
        "settlementPeriod": 4,
        "generation": 200,
        "publishTime": "2026-01-15T02:00:00Z",
    },
    {
        "dataset": "FUELHH",
        "fuelType": "WIND",
        "startTime": "2026-01-15T02:00:00Z",
        "settlementDate": "2026-01-15",
        "settlementPeriod": 5,
        "generation": 50,
        "publishTime": "2026-01-15T02:30:00Z",
    },
    {
        "dataset": "FUELHH",
        "fuelType": "WIND",
        "startTime": "2026-01-15T03:00:00Z",
        "settlementDate": "2026-01-15",
        "settlementPeriod": 7,
        "generation": 0,
        "publishTime": "2026-01-15T03:30:00Z",
    },
    {
        "dataset": "FUELHH",
        "fuelType": "WIND",
        "startTime": "2026-01-15T03:30:00Z",
        "settlementDate": "2026-01-15",
        "settlementPeriod": 8,
        "generation": 0,
        "publishTime": "2026-01-15T04:00:00Z",
    },
    {
        "dataset": "FUELHH",
        "fuelType": "WIND",
        "startTime": "2026-01-15T04:00:00Z",
        "settlementDate": "2026-01-15",
        "settlementPeriod": 9,
        "generation": None,
        "publishTime": "2026-01-15T04:30:00Z",
    },
    {
        "dataset": "FUELHH",
        "fuelType": "WIND",
        "startTime": "2026-01-15T04:30:00Z",
        "settlementDate": "2026-01-15",
        "settlementPeriod": 10,
        "generation": 40,
        "publishTime": "2026-01-15T05:00:00Z",
    },
]

FORECASTS: list[dict[str, object]] = [
    {
        "dataset": "WINDFOR",
        "publishTime": "2026-01-14T04:30:00Z",
        "startTime": "2026-01-15T00:00:00Z",
        "generation": "n/a",
    },
    {
        "dataset": "WINDFOR",
        "publishTime": "2026-01-14T07:30:00Z",
        "startTime": "2026-01-15T00:00:00Z",
        "generation": 130,
    },
    {
        "dataset": "WINDFOR",
        "publishTime": "2026-01-14T09:30:00Z",
        "startTime": "2026-01-15T00:00:00Z",
        "generation": 150,
    },
    {
        "dataset": "WINDFOR",
        "publishTime": "2026-01-14T07:30:00Z",
        "startTime": "2026-01-15T01:00:00Z",
        "generation": 180,
    },
    {
        "dataset": "WINDFOR",
        "publishTime": "2026-01-14T09:30:00Z",
        "startTime": "2026-01-15T01:00:00Z",
        "generation": 180,
    },
    {
        "dataset": "WINDFOR",
        "publishTime": "2026-01-14T07:30:00Z",
        "startTime": "2026-01-15T02:00:00Z",
        "generation": 80,
    },
    {
        "dataset": "WINDFOR",
        "publishTime": "2026-01-14T07:30:00Z",
        "startTime": "2026-01-15T03:00:00Z",
        "generation": 10,
    },
    {
        "dataset": "WINDFOR",
        "publishTime": "2026-01-15T22:30:00Z",
        "startTime": "2026-01-15T03:00:00Z",
        "generation": 0,
    },
    {
        "dataset": "WINDFOR",
        "publishTime": "2026-01-14T07:30:00Z",
        "startTime": "2026-01-15T04:00:00Z",
        "generation": 70,
    },
]


class FakeElexon:
    def __init__(self, actuals: list[dict[str, object]] | None = None, forecasts: list[dict[str, object]] | None = None) -> None:
        self.actuals = list(ACTUALS if actuals is None else actuals)
        self.forecasts = list(FORECASTS if forecasts is None else forecasts)

    async def fetch_fuelhh(self, settlement_from, settlement_to, *, refresh: bool = False):
        del settlement_from, settlement_to, refresh
        return list(reversed(self.actuals)), CacheMeta(datetime(2026, 1, 16, tzinfo=UTC), "live")

    async def fetch_windfor(self, publish_from, publish_to, *, refresh: bool = False):
        del publish_from, publish_to, refresh
        return list(reversed(self.forecasts)), CacheMeta(datetime(2026, 1, 16, tzinfo=UTC), "live")
