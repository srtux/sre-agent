"""Tests for agent trace analysis tools (async, mock mcp_execute_sql)."""

from unittest.mock import patch

import pytest

from sre_agent.schema import ToolStatus
from sre_agent.tools.analysis.agent_trace.tools import (
    analyze_agent_token_usage,
    detect_agent_anti_patterns,
    list_agent_traces,
    reconstruct_agent_interaction,
)


@pytest.fixture()
def mock_project_id():
    """Patch get_project_id_with_fallback to return a test project."""
    with patch(
        "sre_agent.tools.analysis.agent_trace.tools.get_project_id_with_fallback",
        return_value="test-project",
    ):
        yield


class TestListAgentTraces:
    """Tests for list_agent_traces tool."""

    @pytest.mark.asyncio()
    async def test_generates_sql_query(self, mock_project_id) -> None:
        result = await list_agent_traces(
            project_id="my-project",
            start_time="2025-01-15T00:00:00Z",
            end_time="2025-01-15T23:59:59Z",
        )

        assert result.status == ToolStatus.SUCCESS
        assert "sql_query" in result.result
        assert "my-project" in result.result["sql_query"]
        assert "reasoningEngine" in result.result["sql_query"]
        assert "next_steps" in result.result

    @pytest.mark.asyncio()
    async def test_with_reasoning_engine_filter(self, mock_project_id) -> None:
        result = await list_agent_traces(
            project_id="my-project",
            reasoning_engine_id="12345",
            start_time="2025-01-15T00:00:00Z",
            end_time="2025-01-15T23:59:59Z",
        )

        assert result.status == ToolStatus.SUCCESS
        assert "12345" in result.result["sql_query"]

    @pytest.mark.asyncio()
    async def test_error_only_flag(self, mock_project_id) -> None:
        result = await list_agent_traces(
            project_id="my-project",
            error_only=True,
            start_time="2025-01-15T00:00:00Z",
            end_time="2025-01-15T23:59:59Z",
        )

        assert result.status == ToolStatus.SUCCESS
        assert "HAVING error_count > 0" in result.result["sql_query"]

    @pytest.mark.asyncio()
    async def test_defaults_time_window(self, mock_project_id) -> None:
        """Without explicit time, should default to last 24h."""
        result = await list_agent_traces(project_id="my-project")

        assert result.status == ToolStatus.SUCCESS
        assert "TIMESTAMP(" in result.result["sql_query"]

    @pytest.mark.asyncio()
    async def test_no_project_id_error(self) -> None:
        with patch(
            "sre_agent.tools.analysis.agent_trace.tools.get_project_id_with_fallback",
            return_value=None,
        ):
            result = await list_agent_traces()
            assert result.status == ToolStatus.ERROR
            assert "project_id" in result.error


class TestReconstructAgentInteraction:
    """Tests for reconstruct_agent_interaction tool."""

    @pytest.mark.asyncio()
    async def test_generates_sql_for_trace(self, mock_project_id) -> None:
        result = await reconstruct_agent_interaction(
            trace_id="abc123def456",
            project_id="my-project",
        )

        assert result.status == ToolStatus.SUCCESS
        assert "sql_query" in result.result
        assert "abc123def456" in result.result["sql_query"]
        assert result.result["trace_id"] == "abc123def456"

    @pytest.mark.asyncio()
    async def test_with_custom_dataset(self, mock_project_id) -> None:
        result = await reconstruct_agent_interaction(
            trace_id="t1",
            project_id="my-project",
            dataset_id="my-project.custom_dataset",
        )

        assert result.status == ToolStatus.SUCCESS
        assert "custom_dataset" in result.result["sql_query"]


class TestAnalyzeAgentTokenUsage:
    """Tests for analyze_agent_token_usage tool."""

    @pytest.mark.asyncio()
    async def test_generates_queries_for_traces(self, mock_project_id) -> None:
        result = await analyze_agent_token_usage(
            trace_ids_json='["trace1", "trace2"]',
            project_id="my-project",
        )

        assert result.status == ToolStatus.SUCCESS
        assert len(result.result["queries"]) == 2
        assert result.result["queries"][0]["trace_id"] == "trace1"
        assert "token_usage_sql" in result.result["queries"][0]
        assert "tool_usage_sql" in result.result["queries"][0]

    @pytest.mark.asyncio()
    async def test_invalid_json_error(self, mock_project_id) -> None:
        result = await analyze_agent_token_usage(
            trace_ids_json="not_json",
            project_id="my-project",
        )
        assert result.status == ToolStatus.ERROR
        assert "Invalid JSON" in result.error

    @pytest.mark.asyncio()
    async def test_empty_array_error(self, mock_project_id) -> None:
        result = await analyze_agent_token_usage(
            trace_ids_json="[]",
            project_id="my-project",
        )
        assert result.status == ToolStatus.ERROR

    @pytest.mark.asyncio()
    async def test_single_trace(self, mock_project_id) -> None:
        result = await analyze_agent_token_usage(
            trace_ids_json='["abc"]',
            project_id="my-project",
        )
        assert result.status == ToolStatus.SUCCESS
        assert len(result.result["queries"]) == 1


class TestDetectAgentAntiPatterns:
    """Tests for detect_agent_anti_patterns tool."""

    @pytest.mark.asyncio()
    async def test_generates_sql_and_descriptions(self, mock_project_id) -> None:
        result = await detect_agent_anti_patterns(
            trace_id="trace123",
            project_id="my-project",
        )

        assert result.status == ToolStatus.SUCCESS
        assert "sql_query" in result.result
        assert "trace123" in result.result["sql_query"]
        assert "anti_pattern_definitions" in result.result
        assert "excessive_retries" in result.result["anti_pattern_definitions"]
        assert "token_waste" in result.result["anti_pattern_definitions"]
