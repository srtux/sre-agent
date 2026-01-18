import pytest
from datetime import datetime, timedelta, timezone

from sre_agent.tools.common.cache import DataCache, get_data_cache


class FixedTime:
    """Helper to control datetime.now(timezone.utc) via monkeypatch."""

    def __init__(self, start: datetime | None = None) -> None:
        self.now = start or datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    def advance(self, seconds: int) -> None:
        self.now = self.now + timedelta(seconds=seconds)

    def now_utc(self) -> datetime:
        return self.now


@pytest.fixture()
def fixed_time(monkeypatch):
    ft = FixedTime()

    # Patch datetime.now(timezone.utc) used inside the module
    import sre_agent.tools.common.cache as cache_mod

    class _DT:
        @staticmethod
        def now(tz=None):  # type: ignore[override]
            # Only care about timezone-aware calls used by cache
            if tz is timezone.utc:
                return ft.now_utc()
            # Fallback to original for any unexpected usage
            return datetime.now(tz)

    monkeypatch.setattr(cache_mod, "datetime", _DT)
    return ft


def test_returns_cached_value_within_ttl_and_avoids_recompute(fixed_time):
    cache = DataCache(ttl_seconds=10)
    key = "k1"
    cache.put(key, {"v": 1})

    # Within TTL
    fixed_time.advance(5)
    assert cache.get(key) == {"v": 1}

    # Still within TTL
    fixed_time.advance(4)
    assert cache.get(key) == {"v": 1}


def test_recomputes_after_ttl_expiry_and_refreshes_entry(fixed_time):
    cache = DataCache(ttl_seconds=10)
    key = "k2"

    cache.put(key, 10)
    # Expire
    fixed_time.advance(11)
    assert cache.get(key) is None  # expired and evicted on get

    # Refresh with new value
    cache.put(key, 20)
    assert cache.get(key) == 20


def test_manual_clear_forces_miss_then_recache(fixed_time):
    cache = DataCache(ttl_seconds=100)
    key = "k3"

    cache.put(key, "alpha")
    assert cache.get(key) == "alpha"

    cache.clear()
    assert cache.get(key) is None

    cache.put(key, "beta")
    assert cache.get(key) == "beta"


def test_keys_are_isolated_by_string_key_and_args_not_interfering(fixed_time):
    cache = DataCache(ttl_seconds=100)

    cache.put("user:1", {"name": "A"})
    cache.put("user:2", {"name": "B"})

    assert cache.get("user:1") == {"name": "A"}
    assert cache.get("user:2") == {"name": "B"}

    # Ensure no cross-talk
    cache.put("user:1", {"name": "A2"})
    assert cache.get("user:1") == {"name": "A2"}
    assert cache.get("user:2") == {"name": "B"}


def test_stats_reflect_total_active_and_expired_counts(fixed_time):
    cache = DataCache(ttl_seconds=10)

    cache.put("a", 1)  # expires at t+10
    cache.put("b", 2)  # expires at t+10
    s0 = cache.stats()
    assert s0["total_entries"] == 2
    assert s0["expired_entries"] == 0
    assert s0["active_entries"] == 2

    # Advance beyond TTL; entries become expired but remain until get()
    fixed_time.advance(11)
    s1 = cache.stats()
    assert s1["total_entries"] == 2
    assert s1["expired_entries"] == 2
    assert s1["active_entries"] == 0

    # Accessing removes expired entries one-by-one
    assert cache.get("a") is None
    s2 = cache.stats()
    assert s2["total_entries"] == 1
    assert s2["expired_entries"] == 1
    assert s2["active_entries"] == 0

    assert cache.get("b") is None
    s3 = cache.stats()
    assert s3["total_entries"] == 0
    assert s3["expired_entries"] == 0
    assert s3["active_entries"] == 0


def test_global_singleton_cache_is_accessible_and_functional(fixed_time):
    cache = get_data_cache()
    # Use a unique key to avoid coupling with other tests that may use the singleton
    key = f"singleton:{fixed_time.now_utc().timestamp()}"
    cache.put(key, "x")
    assert cache.get(key) == "x"

    # Force expiry by temporarily creating a short-lived cache instance is not possible for singleton;
    # just verify clear works and size updates
    size_before = cache.size()
    assert size_before >= 1
    cache.clear()
    assert cache.size() == 0
