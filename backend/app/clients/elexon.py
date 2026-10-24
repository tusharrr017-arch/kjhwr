"""Elexon Insights client for FUELHH and WINDFOR streams.

The stream endpoints have no documented page token. FUELHH accepts a settlement
date range. WINDFOR returns only the latest issue unless a publication window
is supplied, so every forecast request sets publishDateTimeFrom and
publishDateTimeTo. Requests are chunked onto a fixed grid and cached.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import date, datetime, timedelta
from typing import Any

import httpx

from app.core.cache import AsyncTtlCache, CacheMeta
from app.core.config import Settings
from app.core.time import date_chunks, datetime_chunks, iso_z, parse_utc

logger = logging.getLogger("foregate.elexon")


class ElexonError(Exception):
    """The upstream dataset could not be retrieved."""


class ElexonClient:
    def __init__(
        self,
        settings: Settings,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        self.settings = settings
        self._sleep = sleep or _asleep
        self._cache: AsyncTtlCache[list[dict[str, Any]]] = AsyncTtlCache(settings.cache_ttl_seconds)
        self.http = httpx.AsyncClient(
            transport=transport,
            timeout=httpx.Timeout(settings.http_timeout_seconds),
            headers={"Accept": "application/json", "User-Agent": "foregate/1.0"},
            follow_redirects=True,
        )

    async def aclose(self) -> None:
        await self.http.aclose()

    async def fetch_fuelhh(
        self,
        settlement_from: date,
        settlement_to: date,
        *,
        refresh: bool = False,
    ) -> tuple[list[dict[str, Any]], CacheMeta]:
        rows: list[dict[str, Any]] = []
        metas: list[CacheMeta] = []
        for chunk_start, chunk_end in date_chunks(settlement_from, settlement_to, self.settings.chunk_days):
            params = {
                "settlementDateFrom": chunk_start.isoformat(),
                "settlementDateTo": chunk_end.isoformat(),
                "fuelType": "WIND",
            }
            key = f"fuelhh:{chunk_start.isoformat()}:{chunk_end.isoformat()}"
            chunk_rows, meta = await self._cached_get("/datasets/FUELHH/stream", params, key, refresh)
            rows.extend(chunk_rows)
            metas.append(meta)
        filtered = [row for row in rows if _in_settlement_range(row, settlement_from, settlement_to)]
        return filtered, _combine(metas)

    async def fetch_windfor(
        self,
        publish_from: datetime,
        publish_to: datetime,
        *,
        refresh: bool = False,
    ) -> tuple[list[dict[str, Any]], CacheMeta]:
        """Return WINDFOR rows published in [publish_from, publish_to)."""
        rows: list[dict[str, Any]] = []
        metas: list[CacheMeta] = []
        for chunk_start, chunk_end in datetime_chunks(publish_from, publish_to, self.settings.chunk_days):
            inclusive_to = chunk_end - timedelta(seconds=1)
            params = {
                "publishDateTimeFrom": iso_z(chunk_start),
                "publishDateTimeTo": iso_z(inclusive_to),
            }
            key = f"windfor:{iso_z(chunk_start)}:{iso_z(chunk_end)}"
            chunk_rows, meta = await self._cached_get("/datasets/WINDFOR/stream", params, key, refresh)
            rows.extend(chunk_rows)
            metas.append(meta)
        filtered = [row for row in rows if _in_publish_window(row, publish_from, publish_to)]
        return filtered, _combine(metas)

    async def _cached_get(
        self,
        path: str,
        params: dict[str, str],
        key: str,
        refresh: bool,
    ) -> tuple[list[dict[str, Any]], CacheMeta]:
        async def factory() -> list[dict[str, Any]]:
            payload = await self._request(path, params)
            return _extract_rows(payload)

        return await self._cache.get_or_set(key, factory, refresh=refresh)

    async def _request(self, path: str, params: dict[str, str]) -> Any:
        url = self.settings.elexon_base_url.rstrip("/") + path
        attempts = max(1, self.settings.http_max_retries)
        last_error = "Elexon request failed"
        for attempt in range(1, attempts + 1):
            try:
                response = await self.http.get(url, params=params)
            except httpx.TimeoutException:
                last_error = "The Elexon request timed out"
                logger.warning("timeout path=%s attempt=%s", path, attempt)
                await self._pause(attempt, attempts)
                continue
            except httpx.TransportError:
                last_error = "The connection to Elexon failed"
                logger.warning("transport path=%s attempt=%s", path, attempt)
                await self._pause(attempt, attempts)
                continue

            if response.status_code in {429, 500, 502, 503, 504}:
                last_error = f"Elexon returned HTTP {response.status_code}"
                logger.warning("retryable path=%s status=%s attempt=%s", path, response.status_code, attempt)
                await self._pause(attempt, attempts)
                continue
            if response.status_code >= 400:
                logger.error("rejected path=%s status=%s", path, response.status_code)
                raise ElexonError(f"Elexon rejected the request (HTTP {response.status_code}).")
            logger.info("fetched path=%s status=%s", path, response.status_code)
            try:
                return response.json()
            except ValueError as exc:
                raise ElexonError("Elexon returned a response that was not JSON.") from exc
        raise ElexonError(f"{last_error} after {attempts} attempts.")

    async def _pause(self, attempt: int, attempts: int) -> None:
        if attempt >= attempts:
            return
        await self._sleep(0.4 * (2 ** (attempt - 1)))


async def _asleep(seconds: float) -> None:
    import asyncio

    await asyncio.sleep(seconds)


def _extract_rows(payload: Any) -> list[dict[str, Any]]:
    rows: object
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("data"), list):
        rows = payload["data"]
    else:
        raise ElexonError("Elexon returned an unexpected payload.")
    return [row for row in rows if isinstance(row, dict)]


def _combine(metas: list[CacheMeta]) -> CacheMeta:
    from datetime import timezone

    if not metas:
        return CacheMeta(datetime.now(timezone.utc), "live")
    status = "cache" if all(item.cache == "cache" for item in metas) else "live"
    return CacheMeta(min(item.retrieved_at for item in metas), status)


def _in_settlement_range(row: dict[str, Any], start: date, end: date) -> bool:
    raw = row.get("settlementDate")
    if not isinstance(raw, str):
        return True
    try:
        day = date.fromisoformat(raw)
    except ValueError:
        return True
    return start <= day <= end


def _in_publish_window(row: dict[str, Any], start: datetime, end: datetime) -> bool:
    raw = row.get("publishTime")
    if not isinstance(raw, str):
        return True
    try:
        published = parse_utc(raw)
    except ValueError:
        return True
    return start <= published < end
