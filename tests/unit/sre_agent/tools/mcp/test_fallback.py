"""Tests for MCP-to-Direct-API fallback chain.

Validates that:
- Primary (MCP) call succeeds → returns primary result
- MCP infrastructure failure → falls back to direct API
- User errors (invalid filter) → returned as-is without fallback
- Connection/timeout errors trigger fallback
- MCP error patterns in response strings trigger fallback
- Fallback metadata is added to response
- Non-MCP exceptions are re-raised
"""

import pytest

from sre_agent.schema import BaseToolResponse, ToolStatus
from sre_agent.tools.mcp.fallback import (
    _is_mcp_failure,
    with_fallback,
)


class TestIsMcpFailure:
    """Tests for the _is_mcp_failure detection function."""

    def test_connection_error_is_mcp(self) -> None:
        """ConnectionError should be detected as MCP failure."""
        assert _is_mcp_failure(error=ConnectionError("refused")) is True

    def test_timeout_error_is_mcp(self) -> None:
        """TimeoutError should be detected as MCP failure."""
        assert _is_mcp_failure(error=TimeoutError("timed out")) is True

    def test_os_error_is_mcp(self) -> None:
        """OSError should be detected as MCP failure."""
        assert _is_mcp_failure(error=OSError("network unreachable")) is True

    def test_value_error_not_mcp(self) -> None:
        """ValueError should NOT be detected as MCP failure."""
        assert _is_mcp_failure(error=ValueError("invalid argument")) is False

    def test_mcp_pattern_in_error_string(self) -> None:
        """Error messages with MCP patterns should be detected."""
        assert _is_mcp_failure(error=Exception("MCP session expired")) is True
        assert _is_mcp_failure(error=Exception("SSE connection reset")) is True
        assert _is_mcp_failure(error=Exception("transport error")) is True

    def test_non_mcp_error_string(self) -> None:
        """Error messages without MCP patterns should not match."""
        assert _is_mcp_failure(error=Exception("invalid filter syntax")) is False
        assert _is_mcp_failure(error=Exception("permission denied")) is False

    def test_base_tool_response_mcp_error(self) -> None:
        """BaseToolResponse with MCP error should be detected."""
        resp = BaseToolResponse(
            status=ToolStatus.ERROR,
            error="MCP session timed out",
        )
        assert _is_mcp_failure(response=resp) is True

    def test_base_tool_response_user_error(self) -> None:
        """BaseToolResponse with user error should NOT trigger fallback."""
        resp = BaseToolResponse(
            status=ToolStatus.ERROR,
            error="Invalid filter: syntax error in expression",
        )
        assert _is_mcp_failure(response=resp) is False

    def test_dict_response_mcp_error(self) -> None:
        """Dict response with MCP error should be detected."""
        resp = {"error": "connection refused to MCP server"}
        assert _is_mcp_failure(response=resp) is True

    def test_dict_response_user_error(self) -> None:
        """Dict response with user error should NOT trigger fallback."""
        resp = {"error": "permission denied for project"}
        assert _is_mcp_failure(response=resp) is False

    def test_none_inputs(self) -> None:
        """No inputs should return False."""
        assert _is_mcp_failure() is False

    def test_success_response(self) -> None:
        """Successful response should not be MCP failure."""
        resp = BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={"data": [1, 2, 3]},
        )
        assert _is_mcp_failure(response=resp) is False


class TestWithFallback:
    """Tests for the with_fallback orchestration function."""

    @pytest.mark.asyncio
    async def test_primary_succeeds(self) -> None:
        """When primary succeeds, should return primary result."""

        async def primary() -> dict[str, str]:
            return {"source": "mcp", "data": "ok"}

        async def fallback() -> dict[str, str]:
            return {"source": "direct_api", "data": "ok"}

        result = await with_fallback(primary, fallback, "test_tool")
        assert result["source"] == "mcp"

    @pytest.mark.asyncio
    async def test_connection_error_triggers_fallback(self) -> None:
        """ConnectionError should trigger fallback."""

        async def primary() -> dict[str, str]:
            raise ConnectionError("refused")

        async def fallback() -> dict[str, str]:
            return {"source": "direct_api", "data": "ok"}

        result = await with_fallback(primary, fallback, "test_tool")
        assert result["source"] == "direct_api"

    @pytest.mark.asyncio
    async def test_timeout_error_triggers_fallback(self) -> None:
        """TimeoutError should trigger fallback."""

        async def primary() -> dict[str, str]:
            raise TimeoutError("timed out")

        async def fallback() -> dict[str, str]:
            return {"source": "direct_api"}

        result = await with_fallback(primary, fallback, "test_tool")
        assert result["source"] == "direct_api"

    @pytest.mark.asyncio
    async def test_mcp_error_in_response_triggers_fallback(self) -> None:
        """MCP error in response (not exception) should trigger fallback."""

        async def primary() -> BaseToolResponse:
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error="MCP session expired",
            )

        async def fallback() -> BaseToolResponse:
            return BaseToolResponse(
                status=ToolStatus.SUCCESS,
                result={"data": "from direct api"},
            )

        result = await with_fallback(primary, fallback, "test_tool")
        assert isinstance(result, BaseToolResponse)
        assert result.status == ToolStatus.SUCCESS
        assert result.metadata.get("fallback_used") is True

    @pytest.mark.asyncio
    async def test_user_error_not_fallback(self) -> None:
        """User errors should be returned as-is, no fallback."""

        async def primary() -> BaseToolResponse:
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error="Invalid filter syntax: missing quote",
            )

        async def fallback() -> BaseToolResponse:
            raise AssertionError("Fallback should not be called")

        result = await with_fallback(primary, fallback, "test_tool")
        assert result.status == ToolStatus.ERROR
        assert "Invalid filter" in result.error

    @pytest.mark.asyncio
    async def test_non_mcp_exception_reraises(self) -> None:
        """Non-MCP exceptions should be re-raised, not caught."""

        async def primary() -> dict[str, str]:
            raise ValueError("bad argument")

        async def fallback() -> dict[str, str]:
            raise AssertionError("Fallback should not be called")

        with pytest.raises(ValueError, match="bad argument"):
            await with_fallback(primary, fallback, "test_tool")

    @pytest.mark.asyncio
    async def test_mcp_pattern_exception_triggers_fallback(self) -> None:
        """Exception with MCP pattern in message should trigger fallback."""

        async def primary() -> dict[str, str]:
            raise RuntimeError("MCP session closed unexpectedly")

        async def fallback() -> dict[str, str]:
            return {"source": "direct_api"}

        result = await with_fallback(primary, fallback, "test_tool")
        assert result["source"] == "direct_api"

    @pytest.mark.asyncio
    async def test_fallback_metadata_added(self) -> None:
        """Fallback result should have metadata indicating fallback was used."""

        async def primary() -> BaseToolResponse:
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error="SSE connection reset",
            )

        async def fallback() -> BaseToolResponse:
            return BaseToolResponse(
                status=ToolStatus.SUCCESS,
                result={"logs": []},
            )

        result = await with_fallback(primary, fallback, "test_tool")
        assert result.metadata["fallback_used"] is True
        assert result.metadata["original_source"] == "mcp"

    @pytest.mark.asyncio
    async def test_primary_success_no_fallback_metadata(self) -> None:
        """Successful primary call should not have fallback metadata."""

        async def primary() -> BaseToolResponse:
            return BaseToolResponse(
                status=ToolStatus.SUCCESS,
                result={"data": "ok"},
            )

        async def fallback() -> BaseToolResponse:
            raise AssertionError("Fallback should not be called")

        result = await with_fallback(primary, fallback, "test_tool")
        assert "fallback_used" not in result.metadata
