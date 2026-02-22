"""Tests for circuit breaker integration in the @adk_tool decorator.

Validates that:
- External API tools are protected by circuit breaker
- Analysis tools bypass circuit breaker
- Open circuits return structured BaseToolResponse errors
- Failures are recorded and trigger circuit opening
- Successes are recorded and trigger circuit recovery
- Circuit breaker can be disabled via env var
"""

import logging
import os
from unittest.mock import patch

import pytest

from sre_agent.core.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
)
from sre_agent.schema import BaseToolResponse, ToolStatus
from sre_agent.tools.common.decorators import (
    _CIRCUIT_BREAKER_TOOL_PREFIXES,
    _is_tool_failure,
    _should_use_circuit_breaker,
    adk_tool,
)


@pytest.fixture(autouse=True)
def reset_circuit_breaker() -> None:
    """Reset the circuit breaker registry between tests."""
    CircuitBreakerRegistry.reset()


@pytest.fixture()
def disable_logging_skip() -> dict[str, str]:
    """Environment dict that disables OTel logging skip."""
    return {"OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "false"}


class TestCircuitBreakerToolSelection:
    """Tests for which tools get circuit breaker protection."""

    def test_external_api_tools_are_protected(self) -> None:
        """Tools in the protection set should use circuit breaker."""
        assert _should_use_circuit_breaker("fetch_trace")
        assert _should_use_circuit_breaker("list_log_entries")
        assert _should_use_circuit_breaker("query_promql")
        assert _should_use_circuit_breaker("list_alerts")
        assert _should_use_circuit_breaker("gcp_execute_sql")

    def test_analysis_tools_are_not_protected(self) -> None:
        """Pure analysis tools should not use circuit breaker."""
        assert not _should_use_circuit_breaker("analyze_critical_path")
        assert not _should_use_circuit_breaker("build_call_graph")
        assert not _should_use_circuit_breaker("extract_log_patterns")
        assert not _should_use_circuit_breaker("detect_metric_anomalies")

    def test_circuit_breaker_disabled_via_env(self) -> None:
        """Circuit breaker should be disabled when env var is false."""
        with patch.dict(os.environ, {"SRE_AGENT_CIRCUIT_BREAKER": "false"}):
            assert not _should_use_circuit_breaker("fetch_trace")
            assert not _should_use_circuit_breaker("list_log_entries")

    def test_circuit_breaker_enabled_by_default(self) -> None:
        """Circuit breaker should be enabled by default."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SRE_AGENT_CIRCUIT_BREAKER", None)
            assert _should_use_circuit_breaker("fetch_trace")

    def test_protection_set_has_expected_tools(self) -> None:
        """The protection set should include all external API tools."""
        expected = {
            "fetch_trace",
            "list_traces",
            "list_log_entries",
            "query_promql",
            "list_alerts",
            "list_metric_descriptors",
            "gcp_execute_sql",
        }
        assert expected.issubset(_CIRCUIT_BREAKER_TOOL_PREFIXES)


class TestCircuitBreakerDecoratorIntegration:
    """Tests for circuit breaker behavior inside @adk_tool."""

    @pytest.mark.asyncio
    async def test_open_circuit_returns_error_response(
        self, disable_logging_skip: dict[str, str]
    ) -> None:
        """When circuit is open, tool should return BaseToolResponse error."""
        # Configure circuit with low threshold
        registry = CircuitBreakerRegistry()
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout_seconds=60)
        registry.configure("fetch_trace", config)

        @adk_tool
        async def fetch_trace(trace_id: str = "test") -> BaseToolResponse:
            return BaseToolResponse(status=ToolStatus.SUCCESS, result={"data": "ok"})

        with patch.dict(os.environ, disable_logging_skip):
            # Trip the circuit by recording a failure
            registry.pre_call("fetch_trace")
            registry.record_failure("fetch_trace")

            # Next call should be blocked
            result = await fetch_trace(trace_id="test-123")

        assert isinstance(result, BaseToolResponse)
        assert result.status == ToolStatus.ERROR
        assert "Circuit breaker OPEN" in result.error
        assert result.metadata["circuit_breaker"] is True
        assert result.metadata["non_retryable"] is True

    @pytest.mark.asyncio
    async def test_success_records_in_circuit_breaker(
        self, disable_logging_skip: dict[str, str]
    ) -> None:
        """Successful tool calls should record success in circuit breaker."""
        registry = CircuitBreakerRegistry()
        # Pre-record a failure to verify success decrements it
        registry.record_failure("list_alerts")

        @adk_tool
        async def list_alerts() -> BaseToolResponse:
            return BaseToolResponse(status=ToolStatus.SUCCESS, result=[])

        with patch.dict(os.environ, disable_logging_skip):
            await list_alerts()

        status = registry.get_status("list_alerts")
        assert status["failure_count"] == 0  # Decremented from 1

    @pytest.mark.asyncio
    async def test_failure_records_in_circuit_breaker(
        self, disable_logging_skip: dict[str, str]
    ) -> None:
        """Failed tool calls should record failure in circuit breaker."""
        registry = CircuitBreakerRegistry()

        @adk_tool
        async def list_log_entries() -> BaseToolResponse:
            return BaseToolResponse(status=ToolStatus.ERROR, error="Permission denied")

        with patch.dict(os.environ, disable_logging_skip):
            await list_log_entries()

        status = registry.get_status("list_log_entries")
        assert status["total_failures"] == 1

    @pytest.mark.asyncio
    async def test_exception_records_failure(
        self, disable_logging_skip: dict[str, str]
    ) -> None:
        """Tool exceptions should record failure in circuit breaker."""
        registry = CircuitBreakerRegistry()

        @adk_tool
        async def query_promql() -> BaseToolResponse:
            raise ConnectionError("Network unreachable")

        with patch.dict(os.environ, disable_logging_skip):
            with pytest.raises(ConnectionError):
                await query_promql()

        status = registry.get_status("query_promql")
        assert status["total_failures"] == 1

    @pytest.mark.asyncio
    async def test_non_protected_tool_ignores_circuit_breaker(
        self, disable_logging_skip: dict[str, str]
    ) -> None:
        """Non-protected tools should work normally even with tripped circuits."""

        @adk_tool
        async def analyze_critical_path() -> dict[str, str]:
            return {"result": "analysis done"}

        with patch.dict(os.environ, disable_logging_skip):
            result = await analyze_critical_path()

        assert result == {"result": "analysis done"}

    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_does_not_block_tool(
        self, disable_logging_skip: dict[str, str], caplog: pytest.LogCaptureFixture
    ) -> None:
        """If circuit breaker itself fails, tool should still execute."""
        caplog.set_level(logging.DEBUG)

        @adk_tool
        async def fetch_trace(trace_id: str = "test") -> BaseToolResponse:
            return BaseToolResponse(status=ToolStatus.SUCCESS, result={"ok": True})

        # Patch the registry to raise an unexpected error
        with (
            patch.dict(os.environ, disable_logging_skip),
            patch(
                "sre_agent.tools.common.decorators._should_use_circuit_breaker",
                return_value=True,
            ),
            patch(
                "sre_agent.core.circuit_breaker.CircuitBreakerRegistry.pre_call",
                side_effect=RuntimeError("unexpected CB error"),
            ),
        ):
            result = await fetch_trace(trace_id="abc")

        # Tool should have executed despite CB failure
        assert isinstance(result, BaseToolResponse)
        assert result.status == ToolStatus.SUCCESS


class TestIsToolFailure:
    """Tests for the _is_tool_failure helper function."""

    def test_json_string_with_error(self) -> None:
        assert _is_tool_failure('{"error": "something failed"}') is True

    def test_json_string_without_error(self) -> None:
        assert _is_tool_failure('{"status": "ok"}') is False

    def test_dict_with_error(self) -> None:
        assert _is_tool_failure({"error": "permission denied"}) is True

    def test_dict_without_error(self) -> None:
        assert _is_tool_failure({"result": "ok"}) is False

    def test_base_tool_response_error(self) -> None:
        resp = BaseToolResponse(status=ToolStatus.ERROR, error="failed")
        assert _is_tool_failure(resp) is True

    def test_base_tool_response_success(self) -> None:
        resp = BaseToolResponse(status=ToolStatus.SUCCESS, result="ok")
        assert _is_tool_failure(resp) is False

    def test_string_without_json(self) -> None:
        assert _is_tool_failure("just a plain string") is False

    def test_none(self) -> None:
        assert _is_tool_failure(None) is False

    def test_invalid_json_string(self) -> None:
        assert _is_tool_failure('{"error": broken}') is False
