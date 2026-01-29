
import pytest
from datetime import datetime, timezone
from dataclasses import dataclass
from sre_agent.tools.clients.trace import _get_ts_val, _get_ts_str

@dataclass
class MockTimestamp:
    seconds: int
    nanos: int

class MockProtoTimestamp:
    def __init__(self, seconds, nanos):
        self._seconds = seconds
        self._nanos = nanos

    @property
    def seconds(self):
        return self._seconds

    @property
    def nanos(self):
        return self._nanos

    def timestamp(self):
        return self.seconds + self.nanos / 1e9

    def isoformat(self):
        return datetime.fromtimestamp(self.timestamp(), tz=timezone.utc).isoformat()

class MockProtoWithSecondsNanos:
    def __init__(self, seconds, nanos):
        self.seconds = seconds
        self.nanos = nanos

def test_get_ts_val_with_timestamp_method():
    ts = MockProtoTimestamp(1620000000, 500000000)
    assert _get_ts_val(ts) == 1620000000.5

def test_get_ts_val_with_seconds_nanos():
    ts = MockProtoWithSecondsNanos(1620000000, 500000000)
    assert _get_ts_val(ts) == 1620000000.5

def test_get_ts_str_with_isoformat():
    ts = MockProtoTimestamp(1620000000, 500000000)
    # The MockProtoTimestamp.isoformat returns what we expect
    expected = datetime.fromtimestamp(1620000000.5, tz=timezone.utc).isoformat()
    assert _get_ts_str(ts) == expected

def test_get_ts_str_without_isoformat():
    ts = MockProtoWithSecondsNanos(1620000000, 500000000)
    expected = datetime.fromtimestamp(1620000000.5, tz=timezone.utc).isoformat()
    assert _get_ts_str(ts) == expected
