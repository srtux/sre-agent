import asyncio
import os
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


def async_ttl_cache(
    ttl_seconds: float = 300.0,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """A simple TTL memory cache for async functions.

    Caches the results of the wrapped function based on its arguments.
    Entries expire after `ttl_seconds`.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        cache: dict[str, tuple[float, Any]] = {}
        lock = asyncio.Lock()

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Bypass cache entirely during tests to prevent inter-test state pollution
            # Allow tests to explicitly declare they want the cache enabled via a global flag on the module
            from sre_agent.api.helpers import cache as cache_mod

            if os.environ.get("PYTEST_CURRENT_TEST") and not getattr(
                cache_mod, "ENABLE_CACHE_DURING_TESTS", False
            ):
                return await func(*args, **kwargs)  # type: ignore

            # Create a simple string key from arguments
            # Note: This requires arguments to be cleanly convertible to strings
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = "|".join(key_parts)

            async with lock:
                now = time.time()
                # Clean up expired entries
                expired_keys = [
                    k
                    for k, (timestamp, _) in cache.items()
                    if now - timestamp > ttl_seconds
                ]
                for k in expired_keys:
                    del cache[k]

                # Check for active cache entry
                if cache_key in cache:
                    timestamp, result = cache[cache_key]
                    if now - timestamp <= ttl_seconds:
                        return result  # type: ignore

            # Not cached or expired, call the function
            result = await func(*args, **kwargs)  # type: ignore

            async with lock:
                cache[cache_key] = (time.time(), result)

            return result  # type: ignore

        return wrapper  # type: ignore

    return decorator
