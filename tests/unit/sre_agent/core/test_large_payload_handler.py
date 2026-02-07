"""Tests for sre_agent.core.large_payload_handler.

Covers:
- Payload size estimation and threshold logic
- Template selection for known tool types
- Code-generation prompt builder
- Sandbox processing via templates and generic template
- End-to-end handler integration with various edge cases
- Configuration via environment variables
"""

from __future__ import annotations

import json
import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sre_agent.core.large_payload_handler import (
    DEFAULT_THRESHOLD_CHARS,
    DEFAULT_THRESHOLD_ITEMS,
    GENERIC_SUMMARY_TEMPLATE,
    TOOL_TEMPLATE_MAP,
    build_code_generation_prompt,
    estimate_payload_size,
    get_template_for_tool,
    get_threshold_chars,
    get_threshold_items,
    handle_large_payload,
    is_large_payload_handling_enabled,
    is_payload_large,
)

# Module path for patching lazy imports (they resolve from the source module)
_EXECUTOR_MOD = "sre_agent.tools.sandbox.executor"

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------


class TestIsLargePayloadHandlingEnabled:
    """Tests for is_large_payload_handling_enabled()."""

    def test_enabled_by_default(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SRE_AGENT_LARGE_PAYLOAD_ENABLED", None)
            assert is_large_payload_handling_enabled() is True

    def test_enabled_when_true(self) -> None:
        with patch.dict(os.environ, {"SRE_AGENT_LARGE_PAYLOAD_ENABLED": "true"}):
            assert is_large_payload_handling_enabled() is True

    def test_disabled_when_false(self) -> None:
        with patch.dict(os.environ, {"SRE_AGENT_LARGE_PAYLOAD_ENABLED": "false"}):
            assert is_large_payload_handling_enabled() is False

    def test_disabled_case_insensitive(self) -> None:
        with patch.dict(os.environ, {"SRE_AGENT_LARGE_PAYLOAD_ENABLED": "FALSE"}):
            assert is_large_payload_handling_enabled() is False

    def test_enabled_for_any_non_false_value(self) -> None:
        with patch.dict(os.environ, {"SRE_AGENT_LARGE_PAYLOAD_ENABLED": "yes"}):
            assert is_large_payload_handling_enabled() is True


class TestGetThresholds:
    """Tests for threshold configuration."""

    def test_default_item_threshold(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SRE_AGENT_LARGE_PAYLOAD_THRESHOLD_ITEMS", None)
            assert get_threshold_items() == DEFAULT_THRESHOLD_ITEMS

    def test_custom_item_threshold(self) -> None:
        with patch.dict(os.environ, {"SRE_AGENT_LARGE_PAYLOAD_THRESHOLD_ITEMS": "200"}):
            assert get_threshold_items() == 200

    def test_invalid_item_threshold_returns_default(self) -> None:
        with patch.dict(
            os.environ, {"SRE_AGENT_LARGE_PAYLOAD_THRESHOLD_ITEMS": "not-a-number"}
        ):
            assert get_threshold_items() == DEFAULT_THRESHOLD_ITEMS

    def test_default_char_threshold(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SRE_AGENT_LARGE_PAYLOAD_THRESHOLD_CHARS", None)
            assert get_threshold_chars() == DEFAULT_THRESHOLD_CHARS

    def test_custom_char_threshold(self) -> None:
        with patch.dict(
            os.environ, {"SRE_AGENT_LARGE_PAYLOAD_THRESHOLD_CHARS": "500000"}
        ):
            assert get_threshold_chars() == 500_000


# ---------------------------------------------------------------------------
# Payload analysis
# ---------------------------------------------------------------------------


class TestEstimatePayloadSize:
    """Tests for estimate_payload_size()."""

    def test_none_returns_zeros(self) -> None:
        items, chars = estimate_payload_size(None)
        assert items == 0
        assert chars == 0

    def test_empty_list(self) -> None:
        items, chars = estimate_payload_size([])
        assert items == 0
        assert chars == 2  # "[]"

    def test_list_count_and_chars(self) -> None:
        data = [{"id": i, "name": f"item-{i}"} for i in range(100)]
        items, chars = estimate_payload_size(data)
        assert items == 100
        assert chars > 0

    def test_dict_count_and_chars(self) -> None:
        data = {f"key_{i}": f"value_{i}" for i in range(50)}
        items, chars = estimate_payload_size(data)
        assert items == 50
        assert chars > 0

    def test_string_result(self) -> None:
        data = "a" * 1000
        items, chars = estimate_payload_size(data)
        assert items == 0  # strings don't have item count
        assert chars > 1000  # includes JSON quotes

    def test_nested_dict_chars(self) -> None:
        data = {"nested": {"deep": {"very_deep": "value" * 100}}}
        items, chars = estimate_payload_size(data)
        assert items == 1
        assert chars > 500


class TestIsPayloadLarge:
    """Tests for is_payload_large()."""

    def test_none_is_not_large(self) -> None:
        assert is_payload_large(None) is False

    def test_small_list_is_not_large(self) -> None:
        assert is_payload_large([{"id": i} for i in range(10)]) is False

    def test_large_list_by_item_count(self) -> None:
        data = [{"id": i} for i in range(DEFAULT_THRESHOLD_ITEMS + 10)]
        assert is_payload_large(data) is True

    def test_large_data_by_char_count(self) -> None:
        # Create data that's small in items but large in chars
        # Default char threshold is 100_000, so we need > 100k chars total
        data = [{"payload": "x" * 25_000} for _ in range(5)]
        # 5 items x 25k chars = ~125k > 100k default chars threshold
        assert is_payload_large(data) is True

    def test_respects_custom_thresholds(self) -> None:
        with patch.dict(
            os.environ,
            {
                "SRE_AGENT_LARGE_PAYLOAD_THRESHOLD_ITEMS": "5",
                "SRE_AGENT_LARGE_PAYLOAD_THRESHOLD_CHARS": "1000000",
            },
        ):
            data = [{"id": i} for i in range(10)]
            assert is_payload_large(data) is True

    def test_empty_list_is_not_large(self) -> None:
        assert is_payload_large([]) is False

    def test_empty_dict_is_not_large(self) -> None:
        assert is_payload_large({}) is False


# ---------------------------------------------------------------------------
# Template selection
# ---------------------------------------------------------------------------


class TestGetTemplateForTool:
    """Tests for get_template_for_tool()."""

    def test_known_metric_tool(self) -> None:
        assert get_template_for_tool("list_metric_descriptors") == "summarize_metrics"

    def test_known_log_tool(self) -> None:
        assert get_template_for_tool("list_log_entries") == "summarize_logs"

    def test_known_trace_tool(self) -> None:
        assert get_template_for_tool("list_traces") == "summarize_traces"

    def test_known_timeseries_tool(self) -> None:
        assert get_template_for_tool("list_time_series") == "summarize_timeseries"

    def test_known_promql_tool(self) -> None:
        assert get_template_for_tool("query_promql") == "summarize_timeseries"

    def test_unknown_tool_returns_none(self) -> None:
        assert get_template_for_tool("unknown_tool") is None

    def test_all_mapped_tools_have_valid_templates(self) -> None:
        from sre_agent.tools.sandbox.executor import DATA_PROCESSING_TEMPLATES

        for tool_name, template_name in TOOL_TEMPLATE_MAP.items():
            assert template_name in DATA_PROCESSING_TEMPLATES, (
                f"Tool '{tool_name}' maps to non-existent template '{template_name}'"
            )


# ---------------------------------------------------------------------------
# Code-generation prompt builder
# ---------------------------------------------------------------------------


class TestBuildCodeGenerationPrompt:
    """Tests for build_code_generation_prompt()."""

    def test_list_data_prompt(self) -> None:
        data = [{"id": i, "name": f"item-{i}", "value": i * 10} for i in range(200)]
        prompt = build_code_generation_prompt("my_tool", data)

        assert prompt["large_payload_handled"] is True
        assert prompt["handling_mode"] == "code_generation_prompt"
        assert prompt["tool_name"] == "my_tool"
        assert prompt["total_count"] == 200
        assert isinstance(prompt["data_sample"], list)
        assert len(prompt["data_sample"]) <= 3
        assert "schema_hint" in prompt
        assert "id" in prompt["schema_hint"]
        assert "code_generation_prompt" in prompt
        assert "execute_custom_analysis_in_sandbox" in prompt["code_generation_prompt"]

    def test_dict_data_prompt(self) -> None:
        data = {f"key_{i}": f"value_{i}" for i in range(100)}
        prompt = build_code_generation_prompt("dict_tool", data)

        assert prompt["total_count"] == 100
        assert "schema_hint" in prompt
        assert isinstance(prompt["data_sample"], str)

    def test_schema_hint_from_first_item(self) -> None:
        data = [
            {"name": "test", "count": 42, "active": True},
            {"name": "test2", "count": 10, "active": False},
        ]
        prompt = build_code_generation_prompt("test_tool", data)

        assert prompt["schema_hint"]["name"] == "str"
        assert prompt["schema_hint"]["count"] == "int"
        assert prompt["schema_hint"]["active"] == "bool"

    def test_truncates_large_sample_items(self) -> None:
        data = [{"payload": "x" * 10_000} for _ in range(10)]
        prompt = build_code_generation_prompt("big_tool", data)

        # The sample items should be truncated
        for item in prompt["data_sample"]:
            assert len(str(item)) <= 2_100  # 2000 + some overhead

    def test_non_list_non_dict_data(self) -> None:
        prompt = build_code_generation_prompt("str_tool", "a" * 5000)

        assert prompt["total_count"] == 1
        assert isinstance(prompt["data_sample"], str)
        assert len(prompt["data_sample"]) <= 2_100


# ---------------------------------------------------------------------------
# Generic summary template validation
# ---------------------------------------------------------------------------


class TestGenericSummaryTemplate:
    """Tests for the GENERIC_SUMMARY_TEMPLATE code."""

    @pytest.mark.asyncio
    async def test_template_processes_list_data(self) -> None:
        """Validate template works for list data via LocalCodeExecutor."""
        from sre_agent.tools.sandbox.executor import LocalCodeExecutor

        executor = LocalCodeExecutor()
        data = [{"id": i, "name": f"item-{i}", "category": "test"} for i in range(100)]
        output = await executor.execute_data_processing(
            data=data,
            processing_code=GENERIC_SUMMARY_TEMPLATE,
        )

        assert output.execution_error is None, (
            f"Template error: {output.execution_error}"
        )
        result = json.loads(output.stdout)
        assert result["total_count"] == 100
        assert result["data_type"] == "list"
        assert "id" in result["field_distribution"]
        assert "name" in result["field_distribution"]
        assert len(result["sample_items"]) <= 5

    @pytest.mark.asyncio
    async def test_template_processes_dict_data(self) -> None:
        """Validate template works for dict data via LocalCodeExecutor."""
        from sre_agent.tools.sandbox.executor import LocalCodeExecutor

        executor = LocalCodeExecutor()
        data = {f"key_{i}": f"value_{i}" for i in range(50)}
        output = await executor.execute_data_processing(
            data=data,
            processing_code=GENERIC_SUMMARY_TEMPLATE,
        )

        assert output.execution_error is None, (
            f"Template error: {output.execution_error}"
        )
        result = json.loads(output.stdout)
        assert result["total_count"] == 50
        assert result["data_type"] == "dict"


# ---------------------------------------------------------------------------
# Sandbox processing (_process_with_template)
# ---------------------------------------------------------------------------


class TestProcessWithTemplate:
    """Tests for _process_with_template()."""

    @pytest.mark.asyncio
    async def test_calls_process_data_in_sandbox(self) -> None:
        from sre_agent.core.large_payload_handler import _process_with_template

        with patch(f"{_EXECUTOR_MOD}.process_data_in_sandbox") as mock_process:
            mock_process.return_value = {"total_count": 100, "summary": "test"}

            result = await _process_with_template(
                "list_metric_descriptors",
                [{"id": i} for i in range(100)],
                "summarize_metrics",
            )

            assert result["total_count"] == 100
            mock_process.assert_called_once_with(
                data=[{"id": i} for i in range(100)],
                template_name="summarize_metrics",
            )

    @pytest.mark.asyncio
    async def test_propagates_runtime_error(self) -> None:
        from sre_agent.core.large_payload_handler import _process_with_template

        with patch(f"{_EXECUTOR_MOD}.process_data_in_sandbox") as mock_process:
            mock_process.side_effect = RuntimeError("Sandbox failed")

            with pytest.raises(RuntimeError, match="Sandbox failed"):
                await _process_with_template(
                    "list_log_entries",
                    [{"id": i} for i in range(100)],
                    "summarize_logs",
                )


# ---------------------------------------------------------------------------
# Generic sandbox processing (_process_with_generic_template)
# ---------------------------------------------------------------------------


class TestProcessWithGenericTemplate:
    """Tests for _process_with_generic_template()."""

    @pytest.mark.asyncio
    async def test_returns_code_gen_prompt_when_sandbox_disabled(self) -> None:
        from sre_agent.core.large_payload_handler import (
            _process_with_generic_template,
        )

        with patch(
            f"{_EXECUTOR_MOD}.is_sandbox_enabled",
            return_value=False,
        ):
            result = await _process_with_generic_template(
                "unknown_tool",
                [{"id": i} for i in range(100)],
            )

            assert result["handling_mode"] == "code_generation_prompt"

    @pytest.mark.asyncio
    async def test_processes_via_sandbox_when_enabled(self) -> None:
        from sre_agent.core.large_payload_handler import (
            _process_with_generic_template,
        )
        from sre_agent.tools.sandbox.schemas import CodeExecutionOutput

        mock_executor = MagicMock()
        mock_executor.execute_data_processing = AsyncMock(
            return_value=CodeExecutionOutput(
                stdout=json.dumps(
                    {
                        "total_count": 100,
                        "data_type": "list",
                        "summary": "test summary",
                    }
                ),
                stderr="",
            )
        )
        mock_executor.__aenter__ = AsyncMock(return_value=mock_executor)
        mock_executor.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                f"{_EXECUTOR_MOD}.is_sandbox_enabled",
                return_value=True,
            ),
            patch(
                f"{_EXECUTOR_MOD}.get_code_executor",
                new_callable=AsyncMock,
                return_value=mock_executor,
            ),
        ):
            result = await _process_with_generic_template(
                "unknown_tool",
                [{"id": i} for i in range(100)],
            )

            assert result["handling_mode"] == "generic_sandbox"
            assert result["large_payload_handled"] is True
            assert result["total_count"] == 100

    @pytest.mark.asyncio
    async def test_falls_back_to_code_gen_on_sandbox_error(self) -> None:
        from sre_agent.core.large_payload_handler import (
            _process_with_generic_template,
        )
        from sre_agent.tools.sandbox.schemas import CodeExecutionOutput

        mock_executor = MagicMock()
        mock_executor.execute_data_processing = AsyncMock(
            return_value=CodeExecutionOutput(
                stdout="",
                stderr="",
                execution_error="SyntaxError in template",
            )
        )
        mock_executor.__aenter__ = AsyncMock(return_value=mock_executor)
        mock_executor.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                f"{_EXECUTOR_MOD}.is_sandbox_enabled",
                return_value=True,
            ),
            patch(
                f"{_EXECUTOR_MOD}.get_code_executor",
                new_callable=AsyncMock,
                return_value=mock_executor,
            ),
        ):
            result = await _process_with_generic_template(
                "broken_tool",
                [{"id": i} for i in range(100)],
            )

            assert result["handling_mode"] == "code_generation_prompt"


# ---------------------------------------------------------------------------
# Main handler (handle_large_payload)
# ---------------------------------------------------------------------------


class TestHandleLargePayload:
    """Tests for the main handle_large_payload() entry point."""

    def _make_tool(self, name: str = "test_tool") -> MagicMock:
        tool = MagicMock()
        tool.name = name
        return tool

    @pytest.mark.asyncio
    async def test_returns_none_when_disabled(self) -> None:
        with patch.dict(os.environ, {"SRE_AGENT_LARGE_PAYLOAD_ENABLED": "false"}):
            result = await handle_large_payload(
                self._make_tool(),
                {},
                None,
                {"result": [{"id": i} for i in range(1000)]},
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_non_dict_response(self) -> None:
        result = await handle_large_payload(
            self._make_tool(),
            {},
            None,
            "not a dict",  # type: ignore[arg-type]
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_result_is_none(self) -> None:
        result = await handle_large_payload(
            self._make_tool(),
            {},
            None,
            {"result": None},
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_small_payload(self) -> None:
        result = await handle_large_payload(
            self._make_tool(),
            {},
            None,
            {"result": [{"id": 1}, {"id": 2}]},
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_skips_already_handled_payload(self) -> None:
        result = await handle_large_payload(
            self._make_tool(),
            {},
            None,
            {"result": {"large_payload_handled": True, "data": "x" * 200_000}},
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_processes_large_list_with_known_template(self) -> None:
        """Known tool with template -> template sandbox processing."""
        with (
            patch(
                f"{_EXECUTOR_MOD}.is_sandbox_enabled",
                return_value=True,
            ),
            patch(
                f"{_EXECUTOR_MOD}.process_data_in_sandbox",
                new_callable=AsyncMock,
            ) as mock_process,
        ):
            mock_process.return_value = {
                "total_count": 200,
                "summary": "sandbox result",
            }

            tool_response: dict[str, Any] = {
                "result": [
                    {"type": f"metric-{i}", "display_name": f"Metric {i}"}
                    for i in range(200)
                ],
            }

            result = await handle_large_payload(
                self._make_tool("list_metric_descriptors"),
                {},
                None,
                tool_response,
            )

            assert result is not None
            assert result["result"]["large_payload_handled"] is True
            assert result["result"]["handling_mode"] == "template_sandbox"
            assert result["metadata"]["template_used"] == "summarize_metrics"
            assert result["metadata"]["original_items"] == 200

    @pytest.mark.asyncio
    async def test_processes_large_list_with_generic_template(self) -> None:
        """Unknown tool -> generic sandbox processing."""
        mock_executor = MagicMock()
        mock_executor.execute_data_processing = AsyncMock(
            return_value=MagicMock(
                stdout=json.dumps(
                    {
                        "total_count": 200,
                        "data_type": "list",
                        "summary": "generic result",
                    }
                ),
                stderr="",
                execution_error=None,
                output_files=[],
            )
        )
        mock_executor.__aenter__ = AsyncMock(return_value=mock_executor)
        mock_executor.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                f"{_EXECUTOR_MOD}.is_sandbox_enabled",
                return_value=True,
            ),
            patch(
                f"{_EXECUTOR_MOD}.get_code_executor",
                new_callable=AsyncMock,
                return_value=mock_executor,
            ),
        ):
            tool_response: dict[str, Any] = {
                "result": [{"data": f"item-{i}"} for i in range(200)],
            }

            result = await handle_large_payload(
                self._make_tool("some_unknown_tool"),
                {},
                None,
                tool_response,
            )

            assert result is not None
            assert result["metadata"]["handling_mode"] == "generic_sandbox"

    @pytest.mark.asyncio
    async def test_returns_code_gen_prompt_when_sandbox_unavailable(self) -> None:
        """No sandbox -> code-generation prompt."""
        with patch(
            f"{_EXECUTOR_MOD}.is_sandbox_enabled",
            return_value=False,
        ):
            tool_response: dict[str, Any] = {
                "result": [{"id": i} for i in range(200)],
            }

            result = await handle_large_payload(
                self._make_tool("unknown_tool"),
                {},
                None,
                tool_response,
            )

            assert result is not None
            assert result["result"]["handling_mode"] == "code_generation_prompt"
            assert result["result"]["total_count"] == 200
            assert "code_generation_prompt" in result["result"]
            assert (
                "execute_custom_analysis_in_sandbox"
                in result["result"]["code_generation_prompt"]
            )

    @pytest.mark.asyncio
    async def test_falls_through_on_handler_exception(self) -> None:
        """Handler exception -> returns None (lets truncation guard handle it)."""
        with patch(
            f"{_EXECUTOR_MOD}.is_sandbox_enabled",
            side_effect=RuntimeError("Unexpected crash"),
        ):
            tool_response: dict[str, Any] = {
                "result": [{"id": i} for i in range(200)],
            }

            result = await handle_large_payload(
                self._make_tool("list_metric_descriptors"),
                {},
                None,
                tool_response,
            )

            # Should return None, not crash
            assert result is None

    @pytest.mark.asyncio
    async def test_metadata_includes_processing_info(self) -> None:
        """Verify metadata is populated with processing details."""
        with (
            patch(
                f"{_EXECUTOR_MOD}.is_sandbox_enabled",
                return_value=True,
            ),
            patch(
                f"{_EXECUTOR_MOD}.process_data_in_sandbox",
                new_callable=AsyncMock,
            ) as mock_process,
        ):
            mock_process.return_value = {"total_count": 100, "summary": "ok"}

            tool_response: dict[str, Any] = {
                "result": [{"id": i} for i in range(100)],
                "metadata": {"existing_key": "preserved"},
            }

            result = await handle_large_payload(
                self._make_tool("list_log_entries"),
                {},
                None,
                tool_response,
            )

            assert result is not None
            meta = result["metadata"]
            assert meta["large_payload_handled"] is True
            assert meta["handling_mode"] == "template_sandbox"
            assert meta["template_used"] == "summarize_logs"
            assert meta["original_items"] == 100
            assert meta["original_chars"] > 0
            assert "processing_ms" in meta
            # Existing metadata should be preserved
            assert meta["existing_key"] == "preserved"

    @pytest.mark.asyncio
    async def test_large_dict_triggers_handler(self) -> None:
        """Large dict payloads should also be handled."""
        large_dict = {f"key_{i}": "x" * 1000 for i in range(200)}

        with patch(
            f"{_EXECUTOR_MOD}.is_sandbox_enabled",
            return_value=False,
        ):
            tool_response: dict[str, Any] = {"result": large_dict}

            result = await handle_large_payload(
                self._make_tool("dict_tool"),
                {},
                None,
                tool_response,
            )

            assert result is not None
            assert result["result"]["handling_mode"] == "code_generation_prompt"

    @pytest.mark.asyncio
    async def test_template_failure_falls_through(self) -> None:
        """Template failure -> exception caught -> returns None."""
        with (
            patch(
                f"{_EXECUTOR_MOD}.is_sandbox_enabled",
                return_value=True,
            ),
            patch(
                f"{_EXECUTOR_MOD}.process_data_in_sandbox",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Template failed"),
            ),
        ):
            tool_response: dict[str, Any] = {
                "result": [{"id": i} for i in range(100)],
            }

            # The exception is caught by the outer try/except
            result = await handle_large_payload(
                self._make_tool("list_metric_descriptors"),
                {},
                None,
                tool_response,
            )

            # Returns None so the truncation guard handles it
            assert result is None

    @pytest.mark.asyncio
    async def test_large_string_triggers_by_char_count(self) -> None:
        """Large string results trigger by char threshold."""
        large_string = "x" * (DEFAULT_THRESHOLD_CHARS + 1000)
        tool_response: dict[str, Any] = {"result": large_string}

        with patch(
            f"{_EXECUTOR_MOD}.is_sandbox_enabled",
            return_value=False,
        ):
            result = await handle_large_payload(
                self._make_tool("string_tool"),
                {},
                None,
                tool_response,
            )

            # Large strings exceed char threshold (even though 0 items)
            # Handler should produce a code-gen prompt
            assert result is not None
            assert result["result"]["handling_mode"] == "code_generation_prompt"


# ---------------------------------------------------------------------------
# Integration with composite_after_tool_callback
# ---------------------------------------------------------------------------


class TestCompositeCallbackIntegration:
    """Verify handle_large_payload is called in composite_after_tool_callback."""

    @pytest.mark.asyncio
    async def test_large_payload_handler_in_callback_chain(self) -> None:
        """Verify the handler is invoked before truncation in the chain."""
        with (
            patch(
                "sre_agent.agent.handle_large_payload",
                new_callable=AsyncMock,
            ) as mock_handler,
            patch(
                "sre_agent.agent.truncate_tool_output_callback",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "sre_agent.agent.after_tool_memory_callback",
                new_callable=AsyncMock,
            ),
        ):
            mock_handler.return_value = None  # No modification

            from sre_agent.agent import composite_after_tool_callback

            tool = MagicMock()
            tool.name = "test"
            response: dict[str, Any] = {"result": "small"}

            await composite_after_tool_callback(tool, {}, None, response)

            mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_handler_result_passed_to_truncation(self) -> None:
        """When handler modifies the response, truncation sees the new one."""
        handled_response: dict[str, Any] = {
            "result": {"large_payload_handled": True, "summary": "processed"},
            "metadata": {"handling_mode": "template_sandbox"},
        }

        with (
            patch(
                "sre_agent.agent.handle_large_payload",
                new_callable=AsyncMock,
                return_value=handled_response,
            ),
            patch(
                "sre_agent.agent.truncate_tool_output_callback",
                new_callable=AsyncMock,
                return_value=None,
            ) as mock_truncate,
            patch(
                "sre_agent.agent.after_tool_memory_callback",
                new_callable=AsyncMock,
            ),
        ):
            from sre_agent.agent import composite_after_tool_callback

            tool = MagicMock()
            tool.name = "list_log_entries"
            original: dict[str, Any] = {
                "result": [{"id": i} for i in range(500)],
            }

            await composite_after_tool_callback(tool, {}, None, original)

            # Truncation should receive the handled response, not the original
            mock_truncate.assert_called_once()
            call_args = mock_truncate.call_args
            assert call_args[0][3] == handled_response


# ---------------------------------------------------------------------------
# End-to-end sandbox processing via LocalCodeExecutor
# ---------------------------------------------------------------------------


class TestEndToEndLocalExecution:
    """End-to-end tests using the real LocalCodeExecutor."""

    @pytest.mark.asyncio
    async def test_e2e_metrics_template(self) -> None:
        """Process large metric descriptors end-to-end in local sandbox."""
        with patch.dict(os.environ, {"SRE_AGENT_LOCAL_EXECUTION": "true"}):
            from sre_agent.core.large_payload_handler import _process_with_template

            data = [
                {
                    "type": f"custom.googleapis.com/metric_{i}",
                    "display_name": f"Metric {i}",
                    "description": f"Description for metric {i}",
                    "metric_kind": "GAUGE" if i % 2 == 0 else "DELTA",
                    "value_type": "DOUBLE" if i % 3 == 0 else "INT64",
                }
                for i in range(200)
            ]

            result = await _process_with_template(
                "list_metric_descriptors", data, "summarize_metrics"
            )

            assert result["total_count"] == 200
            assert "by_metric_kind" in result
            assert result["by_metric_kind"]["GAUGE"] == 100
            assert result["by_metric_kind"]["DELTA"] == 100
            assert len(result["top_metrics"]) == 20

    @pytest.mark.asyncio
    async def test_e2e_logs_template(self) -> None:
        """Process large log entries end-to-end in local sandbox."""
        with patch.dict(os.environ, {"SRE_AGENT_LOCAL_EXECUTION": "true"}):
            from sre_agent.core.large_payload_handler import _process_with_template

            data = [
                {
                    "timestamp": f"2025-01-15T{10 + (i % 12):02d}:00:00Z",
                    "severity": ["INFO", "WARNING", "ERROR"][i % 3],
                    "resource": {"type": "gce_instance"},
                    "payload": f"Log message {i}",
                }
                for i in range(150)
            ]

            result = await _process_with_template(
                "list_log_entries", data, "summarize_logs"
            )

            assert result["total_entries"] == 150
            assert "by_severity" in result
            assert result["by_severity"]["INFO"] == 50
            assert result["by_severity"]["WARNING"] == 50
            assert result["by_severity"]["ERROR"] == 50

    @pytest.mark.asyncio
    async def test_e2e_traces_template(self) -> None:
        """Process large traces end-to-end in local sandbox."""
        with patch.dict(os.environ, {"SRE_AGENT_LOCAL_EXECUTION": "true"}):
            from sre_agent.core.large_payload_handler import _process_with_template

            data = [
                {
                    "trace_id": f"trace-{i:04d}",
                    "spans": [
                        {
                            "labels": {"service.name": f"service-{i % 5}"},
                            "status": {"code": 2} if i % 10 == 0 else {"code": 0},
                            "duration_ms": 100 + i * 10,
                        }
                    ],
                }
                for i in range(100)
            ]

            result = await _process_with_template(
                "list_traces", data, "summarize_traces"
            )

            assert result["total_traces"] == 100
            assert "by_service" in result
            assert len(result["by_service"]) == 5
            assert result["by_status"]["error"] == 10
            assert result["by_status"]["ok"] == 90

    @pytest.mark.asyncio
    async def test_e2e_generic_template(self) -> None:
        """Process unknown data end-to-end with the generic template."""
        with patch.dict(os.environ, {"SRE_AGENT_LOCAL_EXECUTION": "true"}):
            from sre_agent.core.large_payload_handler import (
                _process_with_generic_template,
            )

            data = [
                {"resource_id": f"res-{i}", "status": "active", "score": i * 0.1}
                for i in range(100)
            ]

            result = await _process_with_generic_template("custom_tool", data)

            assert result["large_payload_handled"] is True
            assert result["handling_mode"] == "generic_sandbox"
            assert result["total_count"] == 100
            assert result["data_type"] == "list"
            assert "resource_id" in result["field_distribution"]


# ---------------------------------------------------------------------------
# Tool template map completeness
# ---------------------------------------------------------------------------


class TestToolTemplateMapCompleteness:
    """Verify the TOOL_TEMPLATE_MAP is consistent and correct."""

    def test_all_templates_exist(self) -> None:
        """Every template referenced by TOOL_TEMPLATE_MAP must exist."""
        from sre_agent.tools.sandbox.executor import DATA_PROCESSING_TEMPLATES

        for tool, template in TOOL_TEMPLATE_MAP.items():
            assert template in DATA_PROCESSING_TEMPLATES, (
                f"TOOL_TEMPLATE_MAP['{tool}'] = '{template}' "
                f"but '{template}' not in DATA_PROCESSING_TEMPLATES"
            )

    def test_map_contains_key_tools(self) -> None:
        """Core observability tools should be mapped."""
        expected_tools = [
            "list_metric_descriptors",
            "list_time_series",
            "list_log_entries",
            "list_traces",
        ]
        for tool in expected_tools:
            assert tool in TOOL_TEMPLATE_MAP, f"Expected '{tool}' in TOOL_TEMPLATE_MAP"
