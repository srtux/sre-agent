from unittest.mock import MagicMock

# These functions are not yet exposed/created, so this import will fail initially
# or we can import them from the module once we modify it.
# For TDD, we write the test assuming they will be there.
from sre_agent.tools.clients.trace import _get_ts_str, _get_ts_val


def test_get_ts_val_timestamp_method():
    """Test _get_ts_val with an object having a timestamp() method."""
    mock_proto = MagicMock()
    mock_proto.timestamp.return_value = 1609459200.0  # 2021-01-01 00:00:00 UTC

    val = _get_ts_val(mock_proto)
    assert val == 1609459200.0
    mock_proto.timestamp.assert_called_once()


def test_get_ts_val_seconds_nanos():
    """Test _get_ts_val with an object having seconds and nanos."""
    mock_proto = MagicMock(spec=["seconds", "nanos"])
    mock_proto.seconds = 1609459200
    mock_proto.nanos = 500000000  # 0.5s
    del mock_proto.timestamp  # ensure it doesn't have timestamp method

    val = _get_ts_val(mock_proto)
    assert val == 1609459200.5


def test_get_ts_str_isoformat():
    """Test _get_ts_str with an object having isoformat() method."""
    mock_proto = MagicMock()
    mock_proto.isoformat.return_value = "2021-01-01T00:00:00Z"

    s = _get_ts_str(mock_proto)
    assert s == "2021-01-01T00:00:00Z"
    mock_proto.isoformat.assert_called_once()


def test_get_ts_str_fallback():
    """Test _get_ts_str fallback using _get_ts_val logic."""
    # We use a mock that simulates the seconds/nanos case
    mock_proto = MagicMock(spec=["seconds", "nanos"])
    mock_proto.seconds = 1609459200
    mock_proto.nanos = 0
    # ensure no isoformat/timestamp method
    del mock_proto.isoformat
    del mock_proto.timestamp

    s = _get_ts_str(mock_proto)
    # The current implementation (and future one) uses datetime.fromtimestamp with utc
    expected = "2021-01-01T00:00:00+00:00"
    assert s == expected
