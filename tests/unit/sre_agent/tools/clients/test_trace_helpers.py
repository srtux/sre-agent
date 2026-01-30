from sre_agent.tools.clients.trace import _get_ts_str, _get_ts_val


class MockProtoTimestamp:
    def __init__(self, seconds=0, nanos=0):
        self.seconds = seconds
        self.nanos = nanos

    def timestamp(self):
        return self.seconds + self.nanos / 1e9


class MockStructTimestamp:
    def __init__(self, seconds=0, nanos=0):
        self.seconds = seconds
        self.nanos = nanos


class MockIsoTimestamp:
    def __init__(self, iso_str):
        self._iso_str = iso_str

    def isoformat(self):
        return self._iso_str


def test_get_ts_val():
    # Test with timestamp() method
    ts1 = MockProtoTimestamp(1600000000, 500000000)
    assert _get_ts_val(ts1) == 1600000000.5

    # Test with seconds/nanos attributes
    ts2 = MockStructTimestamp(1600000000, 500000000)
    assert _get_ts_val(ts2) == 1600000000.5


def test_get_ts_str():
    # Test with isoformat() method
    iso_obj = MockIsoTimestamp("2020-09-13T12:26:40.500000+00:00")
    assert _get_ts_str(iso_obj) == "2020-09-13T12:26:40.500000+00:00"

    # Test fallback to _get_ts_val -> datetime.isoformat
    # Case 1: Object with timestamp() method
    ts1 = MockProtoTimestamp(1600000000, 0)
    # 1600000000 is 2020-09-13 12:26:40 UTC
    expected = "2020-09-13T12:26:40+00:00"
    assert _get_ts_str(ts1) == expected

    # Case 2: Object with seconds/nanos
    ts2 = MockStructTimestamp(1600000000, 500000000)
    # 2020-09-13 12:26:40.500000 UTC
    expected_ms = "2020-09-13T12:26:40.500000+00:00"
    assert _get_ts_str(ts2) == expected_ms
