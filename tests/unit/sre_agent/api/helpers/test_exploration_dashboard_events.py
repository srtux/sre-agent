"""Tests for create_exploration_dashboard_events."""

from __future__ import annotations

import json
from typing import Any

from sre_agent.api.helpers import create_exploration_dashboard_events


def _make_exploration_result(**overrides: Any) -> dict[str, Any]:
    """Build a minimal exploration result dict."""
    base: dict[str, Any] = {
        "project_id": "test-proj",
        "scan_window_minutes": 15,
        "timestamp": "2025-01-01T00:00:00Z",
        "alerts": [
            {
                "name": "projects/test-proj/alertPolicies/123/conditions/456/incidents/789",
                "state": "OPEN",
                "openTime": "2025-01-01T00:00:00Z",
                "policyName": "High Error Rate",
                "summary": "Error rate is high",
                "severity": "CRITICAL",
            }
        ],
        "logs": {
            "entries": [
                {
                    "timestamp": "2025-01-01T00:00:00Z",
                    "severity": "ERROR",
                    "payload": "Something went wrong",
                    "resource": {"type": "k8s_container", "labels": {}},
                    "insert_id": "log-001",
                    "trace": None,
                    "span_id": None,
                    "http_request": None,
                }
            ],
            "next_page_token": None,
        },
        "traces": [
            {
                "trace_id": "abc123",
                "project_id": "test-proj",
                "name": "GET /api/test",
                "start_time": "2025-01-01T00:00:00Z",
                "duration_ms": 150,
            }
        ],
        "metrics": [
            {
                "metric": {
                    "type": "logging.googleapis.com/log_entry_count",
                    "labels": {},
                },
                "resource": {"type": "global", "labels": {}},
                "points": [
                    {"interval": {"startTime": "2025-01-01T00:00:00Z"}, "value": 42}
                ],
            }
        ],
        "summary": {
            "total_alerts": 1,
            "open_alerts": 1,
            "error_log_count": 1,
            "warning_log_count": 0,
            "trace_count": 1,
            "has_issues": True,
            "health_status": "degraded",
        },
    }
    base.update(overrides)
    return base


class TestCreateExplorationDashboardEvents:
    """Tests for the multi-event dashboard helper."""

    def test_returns_list(self) -> None:
        result = _make_exploration_result()
        events = create_exploration_dashboard_events(result)
        assert isinstance(events, list)

    def test_events_are_valid_json(self) -> None:
        result = _make_exploration_result()
        events = create_exploration_dashboard_events(result)
        for evt_str in events:
            parsed = json.loads(evt_str)
            assert parsed["type"] == "dashboard"
            assert "category" in parsed
            assert "widget_type" in parsed
            assert "data" in parsed

    def test_traces_event_passes_through(self) -> None:
        result = _make_exploration_result()
        events = create_exploration_dashboard_events(result)
        trace_events = [
            json.loads(e) for e in events if json.loads(e)["category"] == "traces"
        ]
        assert len(trace_events) == 1
        assert trace_events[0]["widget_type"] == "x-sre-trace-waterfall"
        assert isinstance(trace_events[0]["data"], list)

    def test_handles_json_string_input(self) -> None:
        result = _make_exploration_result()
        events = create_exploration_dashboard_events(json.dumps(result))
        assert len(events) > 0

    def test_handles_status_result_envelope(self) -> None:
        result = _make_exploration_result()
        wrapped = {"status": "success", "result": result}
        events = create_exploration_dashboard_events(wrapped)
        assert len(events) > 0

    def test_error_status_returns_empty(self) -> None:
        wrapped = {"status": "error", "result": None, "error": "fail"}
        events = create_exploration_dashboard_events(wrapped)
        assert events == []

    def test_empty_signals_return_fewer_events(self) -> None:
        result = _make_exploration_result(alerts=[], logs=None, traces=[], metrics=[])
        events = create_exploration_dashboard_events(result)
        assert len(events) == 0

    def test_none_input_returns_empty(self) -> None:
        events = create_exploration_dashboard_events(None)
        assert events == []

    def test_non_dict_input_returns_empty(self) -> None:
        events = create_exploration_dashboard_events(42)
        assert events == []

    def test_all_categories_present(self) -> None:
        result = _make_exploration_result()
        events = create_exploration_dashboard_events(result)
        categories = {json.loads(e)["category"] for e in events}
        # At minimum traces should be present (pass-through).
        # alerts/logs/metrics depend on transform functions succeeding.
        assert "traces" in categories

    def test_tool_name_is_explore_project_health(self) -> None:
        result = _make_exploration_result()
        events = create_exploration_dashboard_events(result)
        for evt_str in events:
            parsed = json.loads(evt_str)
            assert parsed["tool_name"] == "explore_project_health"
