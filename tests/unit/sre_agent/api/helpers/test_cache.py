import asyncio

import pytest

from sre_agent.api.helpers import cache
from sre_agent.api.helpers.cache import async_ttl_cache

# Explicitly tell the module to allow caching during these tests
cache.ENABLE_CACHE_DURING_TESTS = True


@pytest.mark.asyncio
async def test_async_ttl_cache_caches_result():
    call_count = 0

    @async_ttl_cache(ttl_seconds=1.0)
    async def get_data(x: int):
        nonlocal call_count
        call_count += 1
        return x * 2

    # First call - cache miss
    res1 = await get_data(5)
    assert res1 == 10
    assert call_count == 1

    # Second call, same args - cache hit
    res2 = await get_data(5)
    assert res2 == 10
    assert call_count == 1  # Still 1, didn't re-execute

    # Third call, different args - cache miss
    res3 = await get_data(10)
    assert res3 == 20
    assert call_count == 2


@pytest.mark.asyncio
async def test_async_ttl_cache_expires():
    call_count = 0

    @async_ttl_cache(ttl_seconds=0.1)
    async def get_data(x: int):
        nonlocal call_count
        call_count += 1
        return x * 2

    # First call
    res1 = await get_data(5)
    assert res1 == 10
    assert call_count == 1

    # Cache hit
    res2 = await get_data(5)
    assert res2 == 10
    assert call_count == 1

    # Wait for TTL to expire
    await asyncio.sleep(0.2)

    # Cache miss
    res3 = await get_data(5)
    assert res3 == 10
    assert call_count == 2


@pytest.mark.asyncio
async def test_async_ttl_cache_clears_on_exception():
    call_count = 0

    @async_ttl_cache(ttl_seconds=1.0)
    async def fail_data(x: int):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("First call fails")
        return x * 2

    # First call fails
    with pytest.raises(ValueError, match="First call fails"):
        await fail_data(5)

    # It shouldn't have cached the exception, so second call evaluates
    res2 = await fail_data(5)
    assert res2 == 10
    assert call_count == 2
