"""Small in-process TTL cache with single-flight requests."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Generic, TypeVar

T = TypeVar("T")
UTC = timezone.utc


@dataclass(frozen=True)
class CacheMeta:
    retrieved_at: datetime
    cache: str


class AsyncTtlCache(Generic[T]):
    def __init__(self, ttl_seconds: int) -> None:
        self.ttl = ttl_seconds
        self._items: dict[str, tuple[float, datetime, T]] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._guard = asyncio.Lock()

    def _read(self, key: str) -> tuple[T, CacheMeta] | None:
        item = self._items.get(key)
        if item is None:
            return None
        expiry, retrieved_at, value = item
        if expiry < time.monotonic():
            return None
        return value, CacheMeta(retrieved_at, "cache")

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[T]],
        *,
        refresh: bool = False,
    ) -> tuple[T, CacheMeta]:
        if not refresh:
            cached = self._read(key)
            if cached is not None:
                return cached

        async with self._guard:
            lock = self._locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._locks[key] = lock

        async with lock:
            if not refresh:
                cached = self._read(key)
                if cached is not None:
                    return cached
            value = await factory()
            retrieved_at = datetime.now(UTC)
            self._items[key] = (time.monotonic() + self.ttl, retrieved_at, value)
            return value, CacheMeta(retrieved_at, "live")
