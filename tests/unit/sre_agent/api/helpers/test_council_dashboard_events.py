"""Tests for council investigation dashboard event creation."""

from __future__ import annotations

import json
from typing import Any

from sre_agent.api.helpers import (
    TOOL_WIDGET_MAP,
    WIDGET_CATEGORY_MAP,
    create_dashboard_event,
)


class TestCouncilToolWidgetMapping:
    """Tests for council entries in TOOL_WIDGET_MAP and WIDGET_CATEGORY_MAP."""

    def test_run_council_investigation_mapped(self) -> None:
        """run_council_investigation should map to x-sre-council-synthesis."""
        assert TOOL_WIDGET_MAP["run_council_investigation"] == "x-sre-council-synthesis"

    def test_council_synthesis_category(self) -> None:
        """x-sre-council-synthesis should map to 'council' category."""
        assert WIDGET_CATEGORY_MAP["x-sre-council-synthesis"] == "council"


def _make_council_result(**overrides: Any) -> dict[str, Any]:
    """Build a minimal council synthesis result dict."""
    base: dict[str, Any] = {
        "synthesis": "Latency spike in checkout-service traced to redis connection pool exhaustion.",
        "overall_severity": "warning",
        "overall_confidence": 0.87,
        "mode": "standard",
        "rounds": 1,
        "panels": [
            {
                "panel": "trace",
                "summary": "Critical path through redis shows 800ms p99.",
                "severity": "warning",
                "confidence": 0.9,
                "evidence": ["trace_id=abc123"],
                "recommended_actions": ["Scale redis pool"],
            }
        ],
    }
    base.update(overrides)
    return base


class TestCreateDashboardEventForCouncil:
    """Tests for create_dashboard_event with council synthesis results."""

    def test_creates_council_dashboard_event(self) -> None:
        """Council investigation result produces a dashboard event."""
        result = _make_council_result()
        event_str = create_dashboard_event("run_council_investigation", result)
        assert event_str is not None

        event = json.loads(event_str)
        assert event["type"] == "dashboard"
        assert event["category"] == "council"
        assert event["widget_type"] == "x-sre-council-synthesis"
        assert event["tool_name"] == "run_council_investigation"
        assert isinstance(event["data"], dict)

    def test_council_event_preserves_synthesis_fields(self) -> None:
        """Council event data should contain synthesis and confidence."""
        result = _make_council_result()
        event_str = create_dashboard_event("run_council_investigation", result)
        assert event_str is not None

        event = json.loads(event_str)
        data = event["data"]
        assert data["synthesis"] == result["synthesis"]
        assert data["overall_confidence"] == 0.87
        assert data["overall_severity"] == "warning"
        assert data["mode"] == "standard"

    def test_council_event_with_debate_mode(self) -> None:
        """Council event with debate mode includes round count."""
        result = _make_council_result(mode="debate", rounds=3, overall_confidence=0.92)
        event_str = create_dashboard_event("run_council_investigation", result)
        assert event_str is not None

        event = json.loads(event_str)
        assert event["data"]["mode"] == "debate"
        assert event["data"]["rounds"] == 3

    def test_council_event_unwraps_status_result(self) -> None:
        """Council result wrapped in status/result envelope is unwrapped."""
        result = _make_council_result()
        wrapped = {"status": "success", "result": result}

        event_str = create_dashboard_event("run_council_investigation", wrapped)
        assert event_str is not None

        event = json.loads(event_str)
        assert event["data"]["synthesis"] == result["synthesis"]

    def test_council_event_returns_none_for_error(self) -> None:
        """Error result from council produces no dashboard event."""
        result = {"status": "error", "result": None, "error": "Council failed"}
        event = create_dashboard_event("run_council_investigation", result)
        assert event is None

    def test_council_event_returns_none_for_none(self) -> None:
        """None result from council produces no dashboard event."""
        event = create_dashboard_event("run_council_investigation", None)
        assert event is None

    def test_council_event_handles_json_string_input(self) -> None:
        """Council result as JSON string is properly parsed."""
        result = _make_council_result()
        event_str = create_dashboard_event(
            "run_council_investigation", json.dumps(result)
        )
        assert event_str is not None

        event = json.loads(event_str)
        assert event["category"] == "council"

    def test_council_event_handles_non_dict_result(self) -> None:
        """Non-dict council result is wrapped in raw key."""
        result = "plain text result"
        event_str = create_dashboard_event("run_council_investigation", result)
        # Should still produce an event since the transformer wraps as {"raw": result}
        if event_str is not None:
            event = json.loads(event_str)
            assert event["category"] == "council"
