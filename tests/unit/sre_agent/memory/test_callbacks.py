"""Tests for memory callbacks that auto-record tool failures."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sre_agent.memory.callbacks import (
    _extract_error_lesson,
    _extract_failure_lesson,
    _is_learnable_failure,
    after_tool_memory_callback,
    on_tool_error_memory_callback,
)


class TestIsLearnableFailure:
    """Tests for _is_learnable_failure detection."""

    def test_learnable_invalid_filter(self) -> None:
        response = {"status": "error", "error": "Invalid filter expression: bad syntax"}
        assert _is_learnable_failure(response) is True

    def test_learnable_invalid_argument(self) -> None:
        response = {"status": "error", "error": "INVALID_ARGUMENT: unknown metric type"}
        assert _is_learnable_failure(response) is True

    def test_learnable_resource_type(self) -> None:
        response = {
            "status": "error",
            "error": "resource.type 'gke_container' is not valid",
        }
        assert _is_learnable_failure(response) is True

    def test_learnable_parse_error(self) -> None:
        response = {"status": "error", "error": "Could not parse filter expression"}
        assert _is_learnable_failure(response) is True

    def test_learnable_400_error(self) -> None:
        response = {"status": "error", "error": "400 Bad Request: malformed query"}
        assert _is_learnable_failure(response) is True

    def test_not_learnable_transient_error(self) -> None:
        response = {"status": "error", "error": "Connection timeout after 30s"}
        assert _is_learnable_failure(response) is False

    def test_not_learnable_success(self) -> None:
        response = {"status": "success", "result": {"data": []}}
        assert _is_learnable_failure(response) is False

    def test_not_learnable_missing_status(self) -> None:
        response = {"result": "some data"}
        assert _is_learnable_failure(response) is False

    def test_not_learnable_permission_denied(self) -> None:
        response = {"status": "error", "error": "Permission denied for this resource"}
        assert _is_learnable_failure(response) is False


class TestExtractFailureLesson:
    """Tests for lesson extraction from tool failures."""

    def test_basic_extraction(self) -> None:
        lesson = _extract_failure_lesson(
            tool_name="list_log_entries",
            tool_args={"filter": 'container_name="app"', "project_id": "my-proj"},
            tool_response={
                "status": "error",
                "error": "Invalid filter: use resource.labels.container_name",
            },
        )
        assert "[TOOL FAILURE LESSON]" in lesson
        assert "list_log_entries" in lesson
        assert "Invalid filter" in lesson

    def test_sensitive_args_filtered(self) -> None:
        lesson = _extract_failure_lesson(
            tool_name="some_tool",
            tool_args={"access_token": "secret123", "query": "test"},
            tool_response={"status": "error", "error": "syntax error"},
        )
        assert "secret123" not in lesson
        assert "test" in lesson

    def test_long_args_truncated(self) -> None:
        lesson = _extract_failure_lesson(
            tool_name="some_tool",
            tool_args={"query": "x" * 500},
            tool_response={"status": "error", "error": "syntax error"},
        )
        assert "..." in lesson


class TestExtractErrorLesson:
    """Tests for lesson extraction from tool exceptions."""

    def test_basic_extraction(self) -> None:
        lesson = _extract_error_lesson(
            tool_name="query_promql",
            tool_args={"query": "rate(bad_metric[5m])"},
            error=ValueError("unknown metric: bad_metric"),
        )
        assert "[TOOL ERROR LESSON]" in lesson
        assert "query_promql" in lesson
        assert "ValueError" in lesson

    def test_sensitive_args_filtered(self) -> None:
        lesson = _extract_error_lesson(
            tool_name="some_tool",
            tool_args={"credentials": "secret", "filter": "test"},
            error=RuntimeError("parse error"),
        )
        assert "secret" not in lesson


class TestAfterToolMemoryCallback:
    """Tests for the after_tool_callback integration."""

    @pytest.mark.asyncio
    async def test_records_learnable_failure(self) -> None:
        tool = MagicMock()
        tool.name = "list_log_entries"

        tool_context = MagicMock()
        inv_ctx = MagicMock()
        inv_ctx.session.id = "sess-123"
        inv_ctx.user_id = "user@test.com"
        tool_context.invocation_context = inv_ctx

        tool_response = {
            "status": "error",
            "error": "Invalid filter: resource.labels prefix required",
        }

        with patch("sre_agent.memory.factory.get_memory_manager") as mock_mgr:
            mock_manager = MagicMock()
            mock_manager.add_finding = AsyncMock()
            mock_mgr.return_value = mock_manager

            result = await after_tool_memory_callback(
                tool, {"filter": "bad"}, tool_context, tool_response
            )

            assert result is None
            mock_manager.add_finding.assert_called_once()
            call_args = mock_manager.add_finding.call_args
            assert "TOOL FAILURE LESSON" in call_args.kwargs["description"]
            assert call_args.kwargs["source_tool"] == "list_log_entries"

    @pytest.mark.asyncio
    async def test_ignores_success_response(self) -> None:
        tool = MagicMock()
        tool.name = "fetch_trace"
        tool_context = MagicMock()
        tool_response = {"status": "success", "result": {"trace_id": "abc"}}

        with patch("sre_agent.memory.factory.get_memory_manager") as mock_mgr:
            result = await after_tool_memory_callback(
                tool, {}, tool_context, tool_response
            )
            assert result is None
            mock_mgr.return_value.add_finding.assert_not_called()

    @pytest.mark.asyncio
    async def test_ignores_non_dict_response(self) -> None:
        tool = MagicMock()
        tool.name = "some_tool"
        tool_context = MagicMock()

        result = await after_tool_memory_callback(
            tool,
            {},
            tool_context,
            "string response",  # type: ignore[arg-type]
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_never_breaks_on_error(self) -> None:
        """Callback must never raise, even if memory manager fails."""
        tool = MagicMock()
        tool.name = "list_log_entries"
        tool_context = MagicMock()
        tool_context.invocation_context = None

        tool_response = {"status": "error", "error": "invalid filter syntax"}

        with patch(
            "sre_agent.memory.factory.get_memory_manager",
            side_effect=RuntimeError("boom"),
        ):
            result = await after_tool_memory_callback(
                tool, {}, tool_context, tool_response
            )
            assert result is None


class TestOnToolErrorMemoryCallback:
    """Tests for the on_tool_error_callback integration."""

    @pytest.mark.asyncio
    async def test_records_learnable_exception(self) -> None:
        tool = MagicMock()
        tool.name = "query_promql"

        tool_context = MagicMock()
        inv_ctx = MagicMock()
        inv_ctx.session.id = "sess-456"
        inv_ctx.user_id = "user@test.com"
        tool_context.invocation_context = inv_ctx

        error = ValueError("invalid_argument: unknown metric type foo_bar")

        with patch("sre_agent.memory.factory.get_memory_manager") as mock_mgr:
            mock_manager = MagicMock()
            mock_manager.add_finding = AsyncMock()
            mock_mgr.return_value = mock_manager

            result = await on_tool_error_memory_callback(
                tool, {"query": "rate(foo_bar[5m])"}, tool_context, error
            )

            assert result is None
            mock_manager.add_finding.assert_called_once()

    @pytest.mark.asyncio
    async def test_ignores_transient_exception(self) -> None:
        tool = MagicMock()
        tool.name = "some_tool"
        tool_context = MagicMock()
        error = ConnectionError("Connection refused")

        with patch("sre_agent.memory.factory.get_memory_manager") as mock_mgr:
            result = await on_tool_error_memory_callback(tool, {}, tool_context, error)
            assert result is None
            mock_mgr.return_value.add_finding.assert_not_called()

    @pytest.mark.asyncio
    async def test_never_breaks_on_error(self) -> None:
        """Callback must never raise, even if memory recording fails."""
        tool = MagicMock()
        tool.name = "query_promql"
        tool_context = MagicMock()
        tool_context.invocation_context = None
        error = ValueError("invalid_argument: bad query")

        with patch(
            "sre_agent.memory.factory.get_memory_manager",
            side_effect=RuntimeError("boom"),
        ):
            result = await on_tool_error_memory_callback(tool, {}, tool_context, error)
            assert result is None
