"""Tests for agent trace SQL query generators."""

from sre_agent.tools.analysis.agent_trace.queries import (
    get_agent_token_usage_query,
    get_agent_tool_usage_query,
    get_agent_trace_spans_query,
    get_agent_traces_query,
)


class TestGetAgentTracesQuery:
    """Tests for the list agent traces query."""

    def test_basic_query(self) -> None:
        sql = get_agent_traces_query("project.dataset._AllSpans")

        assert "project.dataset._AllSpans" in sql
        assert "trace_id" in sql
        assert "start_time BETWEEN @start AND @end" in sql
        assert "reasoningEngine" in sql
        assert "ORDER BY start_time DESC" in sql
        assert "LIMIT 20" in sql

    def test_with_agent_name_filter(self) -> None:
        sql = get_agent_traces_query(
            "p.d.t",
            agent_name="sre_agent",
        )
        assert "gen_ai.agent.name" in sql
        assert "sre_agent" in sql

    def test_with_reasoning_engine_filter(self) -> None:
        sql = get_agent_traces_query(
            "p.d.t",
            reasoning_engine_id="12345",
        )
        assert "12345" in sql
        assert "cloud.resource_id" in sql

    def test_error_only_filter(self) -> None:
        sql = get_agent_traces_query("p.d.t", error_only=True)
        assert "HAVING error_count > 0" in sql

    def test_custom_limit(self) -> None:
        sql = get_agent_traces_query("p.d.t", limit=50)
        assert "LIMIT 50" in sql

    def test_token_aggregation(self) -> None:
        sql = get_agent_traces_query("p.d.t")
        assert "gen_ai.usage.input_tokens" in sql
        assert "gen_ai.usage.output_tokens" in sql

    def test_json_extract_paths(self) -> None:
        sql = get_agent_traces_query("p.d.t")
        assert "JSON_EXTRACT_SCALAR" in sql
        assert "$.gen_ai.usage.input_tokens" in sql
        assert "$.gen_ai.agent.name" in sql


class TestGetAgentTraceSpansQuery:
    """Tests for the single trace spans query."""

    def test_basic_query(self) -> None:
        sql = get_agent_trace_spans_query("project.dataset._AllSpans")

        assert "project.dataset._AllSpans" in sql
        assert "@trace_id" in sql
        assert "span_id" in sql
        assert "parent_span_id" in sql
        assert "attributes" in sql
        assert "ORDER BY start_time ASC" in sql

    def test_includes_all_fields(self) -> None:
        sql = get_agent_trace_spans_query("t")
        for field in ["trace_id", "span_id", "parent_span_id", "name",
                       "start_time", "end_time", "duration_nano",
                       "status", "kind", "attributes", "resource", "events"]:
            assert field in sql


class TestGetAgentTokenUsageQuery:
    """Tests for the token usage breakdown query."""

    def test_basic_query(self) -> None:
        sql = get_agent_token_usage_query("p.d.t")

        assert "@trace_id" in sql
        assert "gen_ai.agent.name" in sql
        assert "gen_ai.request.model" in sql
        assert "gen_ai.usage.input_tokens" in sql
        assert "gen_ai.usage.output_tokens" in sql
        assert "GROUP BY agent_name, model" in sql

    def test_filters_llm_operations(self) -> None:
        sql = get_agent_token_usage_query("p.d.t")
        assert "generate_content" in sql
        assert "chat" in sql


class TestGetAgentToolUsageQuery:
    """Tests for the tool usage statistics query."""

    def test_basic_query(self) -> None:
        sql = get_agent_tool_usage_query("p.d.t")

        assert "@trace_id" in sql
        assert "gen_ai.tool.name" in sql
        assert "gen_ai.agent.name" in sql
        assert "call_count" in sql
        assert "avg_duration_ms" in sql
        assert "error_count" in sql
        assert "GROUP BY tool_name, invoked_by" in sql

    def test_filters_tool_operations(self) -> None:
        sql = get_agent_tool_usage_query("p.d.t")
        assert "execute_tool" in sql
