"""Tests for pre-recorded demo chat responses."""

from __future__ import annotations

import json

import pytest

from sre_agent.tools.synthetic.demo_chat_responses import (
    get_demo_suggestions,
    get_demo_turns,
)


class TestDemoChatResponses:
    """Validate structure and completeness of pre-recorded demo events."""

    def test_get_demo_turns_returns_four_turns(self) -> None:
        assert len(get_demo_turns()) == 4

    def test_each_turn_has_events(self) -> None:
        for turn in get_demo_turns():
            assert len(turn) > 0

    def test_events_are_valid_json_lines(self) -> None:
        for turn in get_demo_turns():
            for line in turn:
                data = json.loads(line)
                assert "type" in data

    def test_all_widget_types_covered(self) -> None:
        widgets: set[str] = set()
        for turn in get_demo_turns():
            for line in turn:
                d = json.loads(line)
                if d.get("type") == "dashboard":
                    widgets.add(d.get("widget_type", ""))
        expected = {
            "x-sre-trace-waterfall",
            "x-sre-metric-chart",
            "x-sre-log-entries-viewer",
            "x-sre-incident-timeline",
            "x-sre-council-synthesis",
            "x-sre-metrics-dashboard",
            "x-sre-remediation-plan",
        }
        assert expected.issubset(widgets)

    def test_council_graph_event_emitted(self) -> None:
        all_events = [json.loads(line) for turn in get_demo_turns() for line in turn]
        assert any(e["type"] == "council_graph" for e in all_events)

    def test_memory_event_emitted(self) -> None:
        all_events = [json.loads(line) for turn in get_demo_turns() for line in turn]
        assert any(e["type"] == "memory" for e in all_events)

    def test_trace_info_event_emitted(self) -> None:
        all_events = [json.loads(line) for turn in get_demo_turns() for line in turn]
        assert any(e["type"] == "trace_info" for e in all_events)

    def test_session_event_in_first_turn(self) -> None:
        first = json.loads(get_demo_turns()[0][0])
        assert first["type"] == "session"

    def test_get_demo_suggestions(self) -> None:
        suggestions = get_demo_suggestions()
        assert len(suggestions) >= 3
        assert all(isinstance(s, str) for s in suggestions)


class TestEventDetails:
    """Deeper validation of individual event payloads."""

    @pytest.fixture()
    def all_events(self) -> list[dict]:
        """Flatten all turns into a single event list."""
        return [json.loads(line) for turn in get_demo_turns() for line in turn]

    def test_session_event_has_session_id(
        self,
        all_events: list[dict],
    ) -> None:
        session_events = [e for e in all_events if e["type"] == "session"]
        assert len(session_events) == 1
        assert "session_id" in session_events[0]

    def test_text_events_have_content(
        self,
        all_events: list[dict],
    ) -> None:
        text_events = [e for e in all_events if e["type"] == "text"]
        assert len(text_events) >= 4  # At least one per turn
        for evt in text_events:
            assert isinstance(evt["content"], str)
            assert len(evt["content"]) > 0

    def test_tool_calls_have_required_fields(
        self,
        all_events: list[dict],
    ) -> None:
        tool_calls = [e for e in all_events if e["type"] == "tool-call"]
        assert len(tool_calls) >= 4
        for tc in tool_calls:
            assert "tool_name" in tc
            assert "args" in tc
            assert "id" in tc

    def test_tool_responses_match_calls(
        self,
        all_events: list[dict],
    ) -> None:
        call_ids = {e["id"] for e in all_events if e["type"] == "tool-call"}
        response_ids = {e["id"] for e in all_events if e["type"] == "tool-response"}
        assert call_ids == response_ids

    def test_agent_activity_event_structure(
        self,
        all_events: list[dict],
    ) -> None:
        activity = [e for e in all_events if e["type"] == "agent_activity"]
        assert len(activity) >= 1
        agent = activity[0]["agent"]
        assert agent["agent_id"] == "root"
        assert agent["status"] == "running"

    def test_council_graph_has_six_agents(
        self,
        all_events: list[dict],
    ) -> None:
        cg = [e for e in all_events if e["type"] == "council_graph"]
        assert len(cg) == 1
        agents = cg[0]["agents"]
        assert len(agents) == 6
        agent_types = {a["agent_type"] for a in agents}
        assert agent_types == {"root", "panel", "synthesizer"}

    def test_memory_event_has_category(
        self,
        all_events: list[dict],
    ) -> None:
        mem = [e for e in all_events if e["type"] == "memory"]
        assert len(mem) == 1
        assert mem[0]["category"] == "pattern"
        assert mem[0]["action"] == "pattern_learned"

    def test_trace_waterfall_has_spans(
        self,
        all_events: list[dict],
    ) -> None:
        waterfalls = [
            e
            for e in all_events
            if e.get("type") == "dashboard"
            and e.get("widget_type") == "x-sre-trace-waterfall"
        ]
        assert len(waterfalls) == 1
        spans = waterfalls[0]["data"]["spans"]
        # Degraded trace should have 18-22 spans
        assert 18 <= len(spans) <= 22

    def test_incident_timeline_has_events(
        self,
        all_events: list[dict],
    ) -> None:
        timelines = [
            e
            for e in all_events
            if e.get("type") == "dashboard"
            and e.get("widget_type") == "x-sre-incident-timeline"
        ]
        assert len(timelines) == 1
        events = timelines[0]["data"]["events"]
        assert len(events) == 5

    def test_remediation_plan_has_actions(
        self,
        all_events: list[dict],
    ) -> None:
        plans = [
            e
            for e in all_events
            if e.get("type") == "dashboard"
            and e.get("widget_type") == "x-sre-remediation-plan"
        ]
        assert len(plans) == 1
        actions = plans[0]["data"]["actions"]
        assert len(actions) == 3
        assert actions[0]["requires_approval"] is True
