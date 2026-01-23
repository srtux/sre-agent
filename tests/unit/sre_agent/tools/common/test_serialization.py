import json

from sre_agent.tools.common.serialization import json_dumps, normalize_obj


class MockRepeatedComposite:
    def __init__(self, items):
        self.items = items

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        return self.items[i]


class MockMapComposite:
    def __init__(self, data):
        self.data = data

    def __iter__(self):
        return iter(self.data.items())

    def items(self):
        return self.data.items()


def test_json_dumps_repeated_composite():
    inner = MockRepeatedComposite(["a", "b"])
    # Set name to match our heuristic in serialization.py
    type(inner).__name__ = "RepeatedComposite"

    data = {"key": inner}
    result = json_dumps(data)
    assert json.loads(result) == {"key": ["a", "b"]}


def test_json_dumps_map_composite():
    inner = MockMapComposite({"a": 1})
    type(inner).__name__ = "MapComposite"

    data = {"key": inner}
    result = json_dumps(data)
    assert json.loads(result) == {"key": {"a": 1}}


def test_json_dumps_nested():
    inner = MockRepeatedComposite(["val"])
    type(inner).__name__ = "RepeatedComposite"
    outer = MockMapComposite({"inner": inner})
    type(outer).__name__ = "MapComposite"

    data = {"outer": outer}
    result = json_dumps(data)
    assert json.loads(result) == {"outer": {"inner": ["val"]}}


def test_json_dumps_to_dict():
    class ObjWithToDict:
        def to_dict(self):
            return {"foo": "bar"}

    data = {"obj": ObjWithToDict()}
    result = json_dumps(data)
    assert json.loads(result) == {"obj": {"foo": "bar"}}


def test_json_dumps_isoformat():
    from datetime import datetime

    dt = datetime(2024, 1, 1, 12, 0, 0)
    data = {"time": dt}
    result = json_dumps(data)
    assert json.loads(result) == {"time": "2024-01-01T12:00:00"}


def test_json_dumps_timedelta():
    from datetime import timedelta

    td = timedelta(hours=5)
    data = {"duration": td}
    result = json_dumps(data)
    assert json.loads(result) == {"duration": "5:00:00"}


def test_json_dumps_mapping_and_sequence():
    from collections.abc import Mapping, Sequence

    class MyMap(Mapping):
        def __init__(self, d):
            self._d = d

        def __getitem__(self, k):
            return self._d[k]

        def __iter__(self):
            return iter(self._d)

        def __len__(self):
            return len(self._d)

    class MySeq(Sequence):
        def __init__(self, items):
            self._items = items

        def __getitem__(self, i):
            return self._items[i]

        def __len__(self):
            return len(self._items)

    data = {"m": MyMap({"a": 1}), "s": MySeq([1, 2, 3])}
    result = json_dumps(data)
    assert json.loads(result) == {"m": {"a": 1}, "s": [1, 2, 3]}


def test_json_dumps_extreme_nested():
    inner = MockRepeatedComposite([{"a": 1}, MockMapComposite({"b": 2})])
    type(inner).__name__ = "RepeatedComposite"
    type(inner[1]).__name__ = "MapComposite"

    data = {"root": [inner]}
    result = json_dumps(data)
    assert json.loads(result) == {"root": [[{"a": 1}, {"b": 2}]]}


def test_json_dumps_fallback():
    class UnknownType:
        def __str__(self):
            return "strange"

    data = {"val": UnknownType()}
    result = json_dumps(data)
    assert json.loads(result) == {"val": "<UnknownType: strange>"}


def test_normalize_obj_map_composite():
    inner = MockMapComposite({"a": 1})
    type(inner).__name__ = "MapComposite"

    normalized = normalize_obj(inner)
    assert isinstance(normalized, dict)
    assert normalized == {"a": 1}


def test_normalize_obj_nested():
    inner = MockRepeatedComposite([MockMapComposite({"a": 1})])
    type(inner).__name__ = "RepeatedComposite"
    type(inner[0]).__name__ = "MapComposite"

    normalized = normalize_obj({"root": inner})
    assert isinstance(normalized, dict)
    assert isinstance(normalized["root"], list)
    assert isinstance(normalized["root"][0], dict)
    assert normalized == {"root": [{"a": 1}]}


def test_normalize_obj_to_dict():
    class ObjWithToDict:
        def to_dict(self):
            return {"foo": "bar"}

    normalized = normalize_obj(ObjWithToDict())
    assert normalized == {"foo": "bar"}
    assert isinstance(normalized, dict)
