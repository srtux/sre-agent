"""Tests for sandbox processors."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sre_agent.schema import ToolStatus
from sre_agent.tools.sandbox.processors import (
    SANDBOX_THRESHOLD_BYTES,
    SANDBOX_THRESHOLD_ITEMS,
    _fallback_summarize,
    _should_use_sandbox,
    execute_custom_analysis_in_sandbox,
    get_sandbox_status,
    summarize_log_entries_in_sandbox,
    summarize_metric_descriptors_in_sandbox,
    summarize_time_series_in_sandbox,
    summarize_traces_in_sandbox,
)
from sre_agent.tools.sandbox.schemas import CodeExecutionOutput


class TestShouldUseSandbox:
    def test_returns_false_when_disabled(self) -> None:
        with patch.dict(os.environ, {"SRE_AGENT_SANDBOX_ENABLED": "false"}):
            assert _should_use_sandbox([{"id": i} for i in range(100)]) is False

    def test_returns_true_for_large_list_when_enabled(self) -> None:
        with patch.dict(os.environ, {"SRE_AGENT_SANDBOX_ENABLED": "true"}):
            # Create list larger than threshold
            large_data = [{"id": i} for i in range(SANDBOX_THRESHOLD_ITEMS + 10)]
            assert _should_use_sandbox(large_data) is True

    def test_returns_false_for_small_list_when_enabled(self) -> None:
        with patch.dict(os.environ, {"SRE_AGENT_SANDBOX_ENABLED": "true"}):
            small_data = [{"id": i} for i in range(10)]
            assert _should_use_sandbox(small_data) is False

    def test_checks_serialized_size(self) -> None:
        with patch.dict(os.environ, {"SRE_AGENT_SANDBOX_ENABLED": "true"}):
            # Create data with small count but large size
            large_content = {"data": "x" * (SANDBOX_THRESHOLD_BYTES + 1000)}
            assert _should_use_sandbox(large_content) is True

    def test_returns_false_for_empty_list(self) -> None:
        with patch.dict(os.environ, {"SRE_AGENT_SANDBOX_ENABLED": "true"}):
            assert _should_use_sandbox([]) is False


class TestFallbackSummarize:
    def test_small_data_not_truncated(self) -> None:
        data = [{"id": i, "name": f"item-{i}"} for i in range(10)]
        result = _fallback_summarize(data, "items")

        assert result.total_count == 10
        assert result.truncated is False
        assert len(result.top_items) == 10

    def test_large_data_truncated(self) -> None:
        data = [{"id": i, "name": f"item-{i}"} for i in range(100)]
        result = _fallback_summarize(data, "items")

        assert result.total_count == 100
        assert result.truncated is True
        assert len(result.top_items) == 20  # Truncated to 20

    def test_summary_contains_count(self) -> None:
        data = [{"id": i} for i in range(50)]
        result = _fallback_summarize(data, "metric descriptors")

        assert "50" in result.summary
        assert "metric descriptors" in result.summary


class TestSummarizeMetricDescriptorsInSandbox:
    @pytest.mark.asyncio
    async def test_empty_descriptors(self) -> None:
        result = await summarize_metric_descriptors_in_sandbox([])

        assert result.status == ToolStatus.SUCCESS
        assert result.result["total_count"] == 0
        assert result.result["summary"] == "No metric descriptors to analyze."

    @pytest.mark.asyncio
    async def test_filter_by_pattern(self) -> None:
        descriptors = [
            {"type": "compute.googleapis.com/cpu", "display_name": "CPU"},
            {"type": "storage.googleapis.com/disk", "display_name": "Disk"},
            {"type": "compute.googleapis.com/memory", "display_name": "Memory"},
        ]

        result = await summarize_metric_descriptors_in_sandbox(
            descriptors, filter_pattern="compute"
        )

        assert result.status == ToolStatus.SUCCESS
        # Only compute metrics should be included
        assert result.metadata["input_count"] == 2

    @pytest.mark.asyncio
    async def test_fallback_when_sandbox_disabled(self) -> None:
        with patch.dict(os.environ, {"SRE_AGENT_SANDBOX_ENABLED": "false"}):
            descriptors = [
                {"type": f"metric-{i}", "display_name": f"Metric {i}"}
                for i in range(100)
            ]

            result = await summarize_metric_descriptors_in_sandbox(descriptors)

            assert result.status == ToolStatus.SUCCESS
            assert result.metadata["processed_in_sandbox"] is False

    @pytest.mark.asyncio
    async def test_uses_sandbox_for_large_data(self) -> None:
        with patch.dict(os.environ, {"SRE_AGENT_SANDBOX_ENABLED": "true"}):
            with patch(
                "sre_agent.tools.sandbox.processors.process_data_in_sandbox"
            ) as mock_process:
                mock_process.return_value = {
                    "total_count": 100,
                    "summary": "sandbox processed",
                }

                descriptors = [
                    {"type": f"metric-{i}", "display_name": f"Metric {i}"}
                    for i in range(100)
                ]

                result = await summarize_metric_descriptors_in_sandbox(descriptors)

                assert result.status == ToolStatus.SUCCESS
                assert result.metadata["processed_in_sandbox"] is True
                mock_process.assert_called_once()


class TestSummarizeTimeSeriesInSandbox:
    @pytest.mark.asyncio
    async def test_empty_time_series(self) -> None:
        result = await summarize_time_series_in_sandbox([])

        assert result.status == ToolStatus.SUCCESS
        assert result.result["total_count"] == 0

    @pytest.mark.asyncio
    async def test_fallback_for_small_data(self) -> None:
        with patch.dict(os.environ, {"SRE_AGENT_SANDBOX_ENABLED": "false"}):
            time_series = [
                {
                    "metric": {"type": "cpu"},
                    "resource": {"type": "gce_instance"},
                    "points": [{"value": 0.5}],
                }
                for _ in range(10)
            ]

            result = await summarize_time_series_in_sandbox(time_series)

            assert result.status == ToolStatus.SUCCESS
            assert result.metadata["processed_in_sandbox"] is False


class TestSummarizeLogEntriesInSandbox:
    @pytest.mark.asyncio
    async def test_empty_log_entries(self) -> None:
        result = await summarize_log_entries_in_sandbox([])

        assert result.status == ToolStatus.SUCCESS
        assert result.result["total_count"] == 0

    @pytest.mark.asyncio
    async def test_fallback_for_small_data(self) -> None:
        with patch.dict(os.environ, {"SRE_AGENT_SANDBOX_ENABLED": "false"}):
            log_entries = [
                {
                    "timestamp": "2024-01-15T10:00:00Z",
                    "severity": "ERROR",
                    "payload": f"Error message {i}",
                }
                for i in range(10)
            ]

            result = await summarize_log_entries_in_sandbox(log_entries)

            assert result.status == ToolStatus.SUCCESS
            assert result.metadata["processed_in_sandbox"] is False


class TestSummarizeTracesInSandbox:
    @pytest.mark.asyncio
    async def test_empty_traces(self) -> None:
        result = await summarize_traces_in_sandbox([])

        assert result.status == ToolStatus.SUCCESS
        assert result.result["total_count"] == 0

    @pytest.mark.asyncio
    async def test_with_slow_threshold(self) -> None:
        with patch.dict(os.environ, {"SRE_AGENT_SANDBOX_ENABLED": "false"}):
            traces = [
                {
                    "trace_id": f"trace-{i}",
                    "spans": [{"duration_ms": 500}],
                }
                for i in range(10)
            ]

            result = await summarize_traces_in_sandbox(traces, slow_threshold_ms=2000)

            assert result.status == ToolStatus.SUCCESS
            assert result.metadata["input_count"] == 10


class TestExecuteCustomAnalysisInSandbox:
    @pytest.mark.asyncio
    async def test_empty_code_returns_error(self) -> None:
        result = await execute_custom_analysis_in_sandbox(
            data=[{"id": 1}],
            analysis_code="",
        )

        assert result.status == ToolStatus.ERROR
        assert "required" in result.error.lower()

    @pytest.mark.asyncio
    async def test_dangerous_pattern_rejected(self) -> None:
        result = await execute_custom_analysis_in_sandbox(
            data=[{"id": 1}],
            analysis_code="import os; os.system('rm -rf /')",
        )

        assert result.status == ToolStatus.ERROR
        assert "unsafe pattern" in result.error.lower()

    @pytest.mark.asyncio
    async def test_subprocess_pattern_rejected(self) -> None:
        result = await execute_custom_analysis_in_sandbox(
            data=[{"id": 1}],
            analysis_code="import subprocess; subprocess.run(['ls'])",
        )

        assert result.status == ToolStatus.ERROR
        assert "unsafe" in result.error.lower()

    @pytest.mark.asyncio
    async def test_sandbox_disabled_returns_error(self) -> None:
        with patch.dict(os.environ, {"SRE_AGENT_SANDBOX_ENABLED": "false"}):
            result = await execute_custom_analysis_in_sandbox(
                data=[{"id": 1}],
                analysis_code="print(len(data))",
            )

            assert result.status == ToolStatus.ERROR
            assert "not enabled" in result.error.lower()

    @pytest.mark.asyncio
    async def test_successful_execution(self) -> None:
        with patch.dict(os.environ, {"SRE_AGENT_SANDBOX_ENABLED": "true"}):
            with patch(
                "sre_agent.tools.sandbox.processors.SandboxExecutor"
            ) as MockExecutor:
                mock_instance = MagicMock()
                mock_instance.execute_data_processing = AsyncMock(
                    return_value=CodeExecutionOutput(
                        stdout='{"result": "success"}',
                        stderr="",
                    )
                )
                mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
                mock_instance.__aexit__ = AsyncMock(return_value=None)

                MockExecutor.create = AsyncMock(return_value=mock_instance)

                result = await execute_custom_analysis_in_sandbox(
                    data=[{"id": 1}],
                    analysis_code='import json; print(json.dumps({"result": "success"}))',
                )

                assert result.status == ToolStatus.SUCCESS
                assert result.result["result"] == "success"
                assert result.metadata["processed_in_sandbox"] is True


class TestGetSandboxStatus:
    @pytest.mark.asyncio
    async def test_status_when_disabled(self) -> None:
        with patch.dict(os.environ, {"SRE_AGENT_SANDBOX_ENABLED": "false"}, clear=True):
            result = await get_sandbox_status()

            assert result.status == ToolStatus.SUCCESS
            assert result.result["enabled"] is False
            assert "disabled" in result.result["message"].lower()

    @pytest.mark.asyncio
    async def test_status_when_enabled(self) -> None:
        with patch.dict(os.environ, {"SRE_AGENT_SANDBOX_ENABLED": "true"}):
            result = await get_sandbox_status()

            assert result.status == ToolStatus.SUCCESS
            assert result.result["enabled"] is True

    @pytest.mark.asyncio
    async def test_status_includes_templates(self) -> None:
        result = await get_sandbox_status()

        assert "available_templates" in result.result
        assert "summarize_metrics" in result.result["available_templates"]
        assert "summarize_logs" in result.result["available_templates"]

    @pytest.mark.asyncio
    async def test_status_includes_thresholds(self) -> None:
        result = await get_sandbox_status()

        assert "thresholds" in result.result
        assert result.result["thresholds"]["items"] == SANDBOX_THRESHOLD_ITEMS
        assert result.result["thresholds"]["bytes"] == SANDBOX_THRESHOLD_BYTES
