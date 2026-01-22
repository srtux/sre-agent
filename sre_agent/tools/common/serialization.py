"""Serialization utilities for SRE Agent tools."""

import json
from typing import Any


def gcp_json_default(obj: Any) -> Any:
    """JSON default handler for GCP types (proto-plus, protobuf, etc.).

    This handles types like RepeatedComposite and MapComposite from proto-plus
    which are not JSON serializable by default but behave like lists and dicts.
    """
    from collections.abc import Mapping, Sequence
    from datetime import timedelta

    # Handle proto-plus RepeatedComposite and MapComposite
    # We use string comparisons for types to avoid hard dependency on proto-plus
    # being present at import time, though it usually is for GCP tools.
    type_name = type(obj).__name__
    if type_name == "RepeatedComposite":
        return list(obj)
    if type_name == "MapComposite":
        return dict(obj)

    # Check for proto-plus or other objects with to_dict
    if hasattr(obj, "to_dict"):
        return obj.to_dict()

    # Handle datetime and other common types
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if isinstance(obj, timedelta):
        return str(obj)

    # Handle generic mappings and sequences that json.dumps might miss
    # (e.g. from specialized libraries)
    if isinstance(obj, Mapping):
        return dict(obj)
    if isinstance(obj, Sequence) and not isinstance(obj, str | bytes):
        return list(obj)

    # Fallback to string representation for unknown types instead of crashing
    try:
        if hasattr(type(obj), "__name__"):
            return f"<{type(obj).__name__}: {obj!s}>"
        return str(obj)
    except Exception:
        return "<Unserializable Object>"


def json_dumps(obj: Any, **kwargs: Any) -> str:
    """Wrapper around json.dumps with GCP types support."""
    if "default" not in kwargs:
        kwargs["default"] = gcp_json_default
    return json.dumps(obj, **kwargs)
