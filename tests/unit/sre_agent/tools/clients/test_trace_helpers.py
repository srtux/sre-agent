"""Unit tests for the Cloud Trace client helper functions."""

from unittest.mock import MagicMock

from sre_agent.tools.clients.trace import _get_ts_str, _get_ts_val


class MockTimestamp:
    def __init__(self, seconds=0, nanos=0):
        self.seconds = seconds
        self.nanos = nanos

    def timestamp(self):
        return self.seconds + self.nanos / 1e9


class MockTimestampNoMethod:
    def __init__(self, seconds=0, nanos=0):
        self.seconds = seconds
        self.nanos = nanos


def test_get_ts_val_with_timestamp_method():
    """Test _get_ts_val with an object having a timestamp() method."""
    ts = MockTimestamp(seconds=1609459200, nanos=500000000)  # 2021-01-01 00:00:00.5 UTC
    assert _get_ts_val(ts) == 1609459200.5


def test_get_ts_val_without_timestamp_method():
    """Test _get_ts_val with an object having seconds and nanos attributes."""
    ts = MockTimestampNoMethod(seconds=1609459200, nanos=500000000)
    assert _get_ts_val(ts) == 1609459200.5


def test_get_ts_str_with_isoformat():
    """Test _get_ts_str with an object having an isoformat() method."""
    ts = MagicMock()
    ts.isoformat.return_value = "2021-01-01T00:00:00Z"
    assert _get_ts_str(ts) == "2021-01-01T00:00:00Z"


def test_get_ts_str_conversion():
    """Test _get_ts_str calculating ISO string from timestamp."""
    # 2021-01-01 00:00:00 UTC
    ts = MockTimestamp(seconds=1609459200, nanos=0)
    # The output might have +00:00 or Z depending on environment/python version,
    # but isoformat() usually returns +00:00 for timezone-aware datetimes.
    result = _get_ts_str(ts)
    assert result.startswith("2021-01-01T00:00:00")
    assert "+00:00" in result or "Z" in result
