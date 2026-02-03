"""Tests for agent trace parsing module (pure functions, no mocks needed)."""

import json

from sre_agent.schema import AgentSpanInfo, AgentSpanKind, GenAIOperationType, Severity
from sre_agent.tools.analysis.agent_trace.parsing import (
    build_interaction_tree,
    classify_span,
    compute_graph_aggregates,
    detect_anti_patterns,
    parse_bq_row_to_agent_span,
    parse_cloud_trace_span_to_agent_span,
)


class TestClassifySpan:
    """Tests for the classify_span function."""

    def test_classify_span_invoke_agent(self) -> None:
        attrs = {"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": "sre_agent"}
        kind, op = classify_span(attrs)
        assert kind == AgentSpanKind.AGENT_INVOCATION
        assert op == GenAIOperationType.INVOKE_AGENT

    def test_classify_span_execute_tool(self) -> None:
        attrs = {"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": "fetch_trace"}
        kind, op = classify_span(attrs)
        assert kind == AgentSpanKind.TOOL_EXECUTION
        assert op == GenAIOperationType.EXECUTE_TOOL

    def test_classify_span_generate_content(self) -> None:
        attrs = {"gen_ai.operation.name": "generate_content"}
        kind, op = classify_span(attrs)
        assert kind == AgentSpanKind.LLM_CALL
        assert op == GenAIOperationType.GENERATE_CONTENT

    def test_classify_span_chat(self) -> None:
        attrs = {"gen_ai.operation.name": "chat"}
        kind, op = classify_span(attrs)
        assert kind == AgentSpanKind.LLM_CALL
        assert op == GenAIOperationType.CHAT

    def test_classify_span_unknown(self) -> None:
        attrs = {"gen_ai.operation.name": "something_new"}
        kind, op = classify_span(attrs)
        assert kind == AgentSpanKind.UNKNOWN
        assert op == GenAIOperationType.UNKNOWN

    def test_classify_span_empty(self) -> None:
        kind, op = classify_span({})
        assert kind == AgentSpanKind.UNKNOWN
        assert op == GenAIOperationType.UNKNOWN


class TestParseBqRow:
    """Tests for BigQuery row parsing."""

    def _make_row(self, **overrides: object) -> dict:
        base = {
            "trace_id": "abc123",
            "span_id": "span1",
            "parent_span_id": None,
            "name": "invoke_agent sre_agent",
            "start_time": "2025-01-15T10:00:00Z",
            "end_time": "2025-01-15T10:00:05Z",
            "duration_nano": 5000000000,
            "status": json.dumps({"code": 0}),
            "attributes": json.dumps({
                "gen_ai.operation.name": "invoke_agent",
                "gen_ai.agent.name": "sre_agent",
                "gen_ai.usage.input_tokens": "1500",
                "gen_ai.usage.output_tokens": "500",
                "gen_ai.request.model": "gemini-2.5-flash",
                "gen_ai.response.model": "gemini-2.5-flash-001",
            }),
            "resource": json.dumps({
                "attributes": {
                    "cloud.resource_id": "projects/my-proj/reasoningEngines/123",
                }
            }),
        }
        base.update(overrides)
        return base

    def test_parse_bq_row_full_attributes(self) -> None:
        row = self._make_row()
        span = parse_bq_row_to_agent_span(row)

        assert span.span_id == "span1"
        assert span.parent_span_id is None
        assert span.name == "invoke_agent sre_agent"
        assert span.kind == AgentSpanKind.AGENT_INVOCATION
        assert span.operation == GenAIOperationType.INVOKE_AGENT
        assert span.agent_name == "sre_agent"
        assert span.input_tokens == 1500
        assert span.output_tokens == 500
        assert span.model_requested == "gemini-2.5-flash"
        assert span.model_used == "gemini-2.5-flash-001"
        assert span.duration_ms == 5000.0
        assert span.status_code == 0

    def test_parse_bq_row_minimal(self) -> None:
        row = {
            "span_id": "s2",
            "name": "unknown",
            "start_time": "2025-01-15T10:00:00Z",
            "end_time": "2025-01-15T10:00:01Z",
            "duration_nano": 1000000000,
        }
        span = parse_bq_row_to_agent_span(row)

        assert span.span_id == "s2"
        assert span.kind == AgentSpanKind.UNKNOWN
        assert span.duration_ms == 1000.0
        assert span.input_tokens is None

    def test_parse_bq_row_error_status(self) -> None:
        row = self._make_row(
            status=json.dumps({"code": 2, "message": "tool failed"}),
        )
        span = parse_bq_row_to_agent_span(row)
        assert span.status_code == 2
        assert span.error_message == "tool failed"

    def test_parse_bq_row_with_parent(self) -> None:
        row = self._make_row(parent_span_id="parent1")
        span = parse_bq_row_to_agent_span(row)
        assert span.parent_span_id == "parent1"


class TestParseCloudTraceSpan:
    """Tests for Cloud Trace API span parsing."""

    def test_parse_cloud_trace_span(self) -> None:
        span_data = {
            "spanId": "ct_span1",
            "parentSpanId": "ct_parent",
            "name": "execute_tool fetch_trace",
            "startTime": "2025-01-15T10:00:00Z",
            "endTime": "2025-01-15T10:00:02Z",
            "labels": {
                "gen_ai.operation.name": "execute_tool",
                "gen_ai.tool.name": "fetch_trace",
                "gen_ai.agent.name": "trace_analyst",
            },
            "status": {"code": 0},
        }
        span = parse_cloud_trace_span_to_agent_span(span_data)

        assert span.span_id == "ct_span1"
        assert span.parent_span_id == "ct_parent"
        assert span.kind == AgentSpanKind.TOOL_EXECUTION
        assert span.tool_name == "fetch_trace"
        assert span.agent_name == "trace_analyst"
        assert span.duration_ms == 2000.0

    def test_parse_cloud_trace_span_no_labels(self) -> None:
        span_data = {
            "spanId": "s1",
            "name": "unknown",
            "startTime": "2025-01-15T10:00:00Z",
            "endTime": "2025-01-15T10:00:01Z",
        }
        span = parse_cloud_trace_span_to_agent_span(span_data)
        assert span.kind == AgentSpanKind.UNKNOWN


class TestBuildInteractionTree:
    """Tests for the tree-building function."""

    def _make_span(
        self,
        span_id: str,
        parent_id: str | None = None,
        kind: AgentSpanKind = AgentSpanKind.UNKNOWN,
        operation: GenAIOperationType = GenAIOperationType.UNKNOWN,
        agent_name: str | None = None,
        tool_name: str | None = None,
    ) -> AgentSpanInfo:
        return AgentSpanInfo(
            span_id=span_id,
            parent_span_id=parent_id,
            name=f"span_{span_id}",
            kind=kind,
            operation=operation,
            start_time_iso="2025-01-15T10:00:00Z",
            end_time_iso="2025-01-15T10:00:01Z",
            duration_ms=1000.0,
            agent_name=agent_name,
            tool_name=tool_name,
        )

    def test_build_interaction_tree_simple(self) -> None:
        spans = [
            self._make_span("root", agent_name="main"),
            self._make_span("child1", parent_id="root"),
            self._make_span("child2", parent_id="root"),
        ]
        roots = build_interaction_tree(spans)

        assert len(roots) == 1
        assert roots[0].span_id == "root"
        assert len(roots[0].children) == 2

    def test_build_interaction_tree_deep_nesting(self) -> None:
        spans = [
            self._make_span("a"),
            self._make_span("b", parent_id="a"),
            self._make_span("c", parent_id="b"),
            self._make_span("d", parent_id="c"),
        ]
        roots = build_interaction_tree(spans)

        assert len(roots) == 1
        assert len(roots[0].children) == 1
        assert len(roots[0].children[0].children) == 1
        assert len(roots[0].children[0].children[0].children) == 1

    def test_build_interaction_tree_multiple_roots(self) -> None:
        spans = [
            self._make_span("root1"),
            self._make_span("root2"),
            self._make_span("child", parent_id="root1"),
        ]
        roots = build_interaction_tree(spans)

        assert len(roots) == 2

    def test_sub_agent_delegation_reclassification(self) -> None:
        """Child invoke_agent with different agent name is reclassified."""
        spans = [
            self._make_span(
                "parent",
                agent_name="sre_agent",
                kind=AgentSpanKind.AGENT_INVOCATION,
                operation=GenAIOperationType.INVOKE_AGENT,
            ),
            self._make_span(
                "child",
                parent_id="parent",
                agent_name="trace_analyst",
                kind=AgentSpanKind.AGENT_INVOCATION,
                operation=GenAIOperationType.INVOKE_AGENT,
            ),
        ]
        roots = build_interaction_tree(spans)

        assert roots[0].children[0].kind == AgentSpanKind.SUB_AGENT_DELEGATION


class TestComputeGraphAggregates:
    """Tests for aggregate computation."""

    def test_compute_graph_aggregates(self) -> None:
        root = AgentSpanInfo(
            span_id="root",
            name="root",
            kind=AgentSpanKind.AGENT_INVOCATION,
            start_time_iso="2025-01-15T10:00:00Z",
            end_time_iso="2025-01-15T10:00:05Z",
            duration_ms=5000.0,
            agent_name="sre_agent",
            input_tokens=100,
            output_tokens=200,
            children=[
                AgentSpanInfo(
                    span_id="llm1",
                    name="llm1",
                    kind=AgentSpanKind.LLM_CALL,
                    start_time_iso="2025-01-15T10:00:01Z",
                    end_time_iso="2025-01-15T10:00:02Z",
                    duration_ms=1000.0,
                    model_used="gemini-flash",
                    input_tokens=50,
                    output_tokens=150,
                ),
                AgentSpanInfo(
                    span_id="tool1",
                    name="tool1",
                    kind=AgentSpanKind.TOOL_EXECUTION,
                    start_time_iso="2025-01-15T10:00:02Z",
                    end_time_iso="2025-01-15T10:00:03Z",
                    duration_ms=1000.0,
                    tool_name="fetch_trace",
                ),
            ],
        )

        agg = compute_graph_aggregates([root])

        assert agg["total_spans"] == 3
        assert agg["total_input_tokens"] == 150
        assert agg["total_output_tokens"] == 350
        assert agg["total_llm_calls"] == 1
        assert agg["total_tool_executions"] == 1
        assert "sre_agent" in agg["unique_agents"]
        assert "fetch_trace" in agg["unique_tools"]
        assert "gemini-flash" in agg["unique_models"]
        assert agg["total_duration_ms"] == 5000.0


class TestDetectAntiPatterns:
    """Tests for anti-pattern detection."""

    def _make_tool_span(self, span_id: str, parent_id: str, tool_name: str) -> AgentSpanInfo:
        return AgentSpanInfo(
            span_id=span_id,
            parent_span_id=parent_id,
            name=f"execute_tool {tool_name}",
            kind=AgentSpanKind.TOOL_EXECUTION,
            operation=GenAIOperationType.EXECUTE_TOOL,
            start_time_iso="2025-01-15T10:00:00Z",
            end_time_iso="2025-01-15T10:00:01Z",
            duration_ms=1000.0,
            tool_name=tool_name,
        )

    def _make_llm_span(
        self, span_id: str, parent_id: str, input_tokens: int = 100, output_tokens: int = 100
    ) -> AgentSpanInfo:
        return AgentSpanInfo(
            span_id=span_id,
            parent_span_id=parent_id,
            name="generate_content",
            kind=AgentSpanKind.LLM_CALL,
            operation=GenAIOperationType.GENERATE_CONTENT,
            start_time_iso="2025-01-15T10:00:00Z",
            end_time_iso="2025-01-15T10:00:01Z",
            duration_ms=1000.0,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def test_detect_excessive_retries(self) -> None:
        root = AgentSpanInfo(
            span_id="root",
            name="root",
            kind=AgentSpanKind.AGENT_INVOCATION,
            start_time_iso="2025-01-15T10:00:00Z",
            end_time_iso="2025-01-15T10:00:10Z",
            duration_ms=10000.0,
            children=[
                self._make_tool_span(f"t{i}", "root", "fetch_trace")
                for i in range(5)
            ],
        )
        patterns = detect_anti_patterns([root])

        retries = [p for p in patterns if p.pattern_type == "excessive_retries"]
        assert len(retries) >= 1
        assert retries[0].severity == Severity.HIGH
        assert retries[0].metric_value == 5.0

    def test_detect_token_waste(self) -> None:
        root = AgentSpanInfo(
            span_id="root",
            name="root",
            kind=AgentSpanKind.AGENT_INVOCATION,
            start_time_iso="2025-01-15T10:00:00Z",
            end_time_iso="2025-01-15T10:00:10Z",
            duration_ms=10000.0,
            children=[
                self._make_llm_span("llm1", "root", input_tokens=100, output_tokens=1000),
                self._make_llm_span("llm2", "root", input_tokens=100, output_tokens=100),
            ],
        )
        patterns = detect_anti_patterns([root])

        waste = [p for p in patterns if p.pattern_type == "token_waste"]
        assert len(waste) >= 1
        assert waste[0].severity == Severity.MEDIUM

    def test_detect_long_chain(self) -> None:
        root = AgentSpanInfo(
            span_id="root",
            name="root",
            kind=AgentSpanKind.AGENT_INVOCATION,
            start_time_iso="2025-01-15T10:00:00Z",
            end_time_iso="2025-01-15T10:00:10Z",
            duration_ms=10000.0,
            children=[
                self._make_llm_span(f"llm{i}", "root")
                for i in range(10)
            ],
        )
        patterns = detect_anti_patterns([root])

        chains = [p for p in patterns if p.pattern_type == "long_chain"]
        assert len(chains) >= 1

    def test_detect_clean_trace(self) -> None:
        """No anti-patterns in a healthy trace."""
        root = AgentSpanInfo(
            span_id="root",
            name="root",
            kind=AgentSpanKind.AGENT_INVOCATION,
            start_time_iso="2025-01-15T10:00:00Z",
            end_time_iso="2025-01-15T10:00:05Z",
            duration_ms=5000.0,
            children=[
                self._make_llm_span("llm1", "root"),
                self._make_tool_span("t1", "root", "fetch_trace"),
                self._make_llm_span("llm2", "root"),
            ],
        )
        patterns = detect_anti_patterns([root])

        # Should have no serious anti-patterns (may have redundant if tool is called once)
        serious = [p for p in patterns if p.severity in (Severity.HIGH, Severity.CRITICAL)]
        assert len(serious) == 0
