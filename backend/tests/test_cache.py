import asyncio

from app.core.cache import AsyncTtlCache


def test_cache_single_flight_and_hit() -> None:
    async def scenario() -> None:
        cache: AsyncTtlCache[str] = AsyncTtlCache(60)
        calls = 0

        async def factory() -> str:
            nonlocal calls
            calls += 1
            await asyncio.sleep(0.05)
            return "value"

        first, second = await asyncio.gather(
            cache.get_or_set("key", factory),
            cache.get_or_set("key", factory),
        )
        assert calls == 1
        assert first[0] == "value"
        assert second[0] == "value"
        assert "live" in {first[1].cache, second[1].cache}
        cached = await cache.get_or_set("key", factory)
        assert cached[1].cache == "cache"
        assert calls == 1

    asyncio.run(scenario())
