
import pytest
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any, cast
from sre_agent.tools.clients.trace import _get_ts_val, _get_ts_str

@dataclass
class MockTimestamp:
    seconds: int
    nanos: int

    def timestamp(self) -> float:
        return self.seconds + self.nanos / 1e9

    def isoformat(self) -> str:
        return datetime.fromtimestamp(self.timestamp(), tz=timezone.utc).isoformat()

@dataclass
class MockProtoTimestamp:
    """Simulates a protobuf timestamp that doesn't have .timestamp() method but has seconds/nanos."""
    seconds: int
    nanos: int

def test_get_ts_val_with_timestamp_method():
    ts = MockTimestamp(1678886400, 500000000)
    # 1678886400.5
    val = _get_ts_val(ts)
    assert val == 1678886400.5

def test_get_ts_val_with_seconds_nanos():
    ts = MockProtoTimestamp(1678886400, 500000000)
    val = _get_ts_val(ts)
    assert val == 1678886400.5

def test_get_ts_str_with_isoformat():
    ts = MockTimestamp(1678886400, 500000000)
    # Should use the object's isoformat method
    s = _get_ts_str(ts)
    assert s == "2023-03-15T13:20:00.500000+00:00"

def test_get_ts_str_without_isoformat():
    ts = MockProtoTimestamp(1678886400, 500000000)
    # Should use datetime.fromtimestamp
    s = _get_ts_str(ts)
    # Depending on system tz, fromtimestamp might return local time if tz not specified,
    # but the implementation uses timezone.utc
    assert s == "2023-03-15T13:20:00.500000+00:00"
