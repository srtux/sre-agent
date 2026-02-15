"""Tests for tool_callbacks — truncation safety guard for tool outputs."""

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from sre_agent.core.tool_callbacks import MAX_RESULT_CHARS, truncate_tool_output_callback


class TestMaxResultCharsConstant:
    """Validate the MAX_RESULT_CHARS constant."""

    def test_is_positive_integer(self) -> None:
        """MAX_RESULT_CHARS must be a positive integer."""
        assert isinstance(MAX_RESULT_CHARS, int)
        assert MAX_RESULT_CHARS > 0

    def test_value_is_200k(self) -> None:
        """Current value should be 200_000."""
        assert MAX_RESULT_CHARS == 200_000


class TestTruncateStringResult:
    """Tests for string-type tool results."""

    @pytest.mark.asyncio
    async def test_short_string_passes_through(self) -> None:
        """Output shorter than MAX_RESULT_CHARS should be returned unchanged."""
        tool = SimpleNamespace(name="fetch_trace")
        response: dict[str, Any] = {"result": "short output"}
        result = await truncate_tool_output_callback(tool, {}, MagicMock(), response)
        assert result is not None
        assert result["result"] == "short output"

    @pytest.mark.asyncio
    async def test_exact_limit_passes_through(self) -> None:
        """Output exactly at MAX_RESULT_CHARS should not be truncated."""
        tool = SimpleNamespace(name="list_log_entries")
        exact_string = "x" * MAX_RESULT_CHARS
        response: dict[str, Any] = {"result": exact_string}
        result = await truncate_tool_output_callback(tool, {}, MagicMock(), response)
        assert result is not None
        assert result["result"] == exact_string

    @pytest.mark.asyncio
    async def test_oversized_string_is_truncated(self) -> None:
        """Output exceeding MAX_RESULT_CHARS should be truncated with a safety message."""
        tool = SimpleNamespace(name="list_log_entries")
        big_string = "A" * (MAX_RESULT_CHARS + 1000)
        response: dict[str, Any] = {"result": big_string}
        result = await truncate_tool_output_callback(tool, {}, MagicMock(), response)
        assert result is not None
        assert "TRUNCATED BY SRE AGENT SAFETY GUARD" in result["result"]
        assert len(result["result"]) < len(big_string)

    @pytest.mark.asyncio
    async def test_truncated_string_starts_with_original_prefix(self) -> None:
        """Truncated result should preserve the first MAX_RESULT_CHARS characters."""
        tool = SimpleNamespace(name="fetch_trace")
        prefix = "PREFIX_DATA_"
        big_string = prefix + "B" * (MAX_RESULT_CHARS + 500)
        response: dict[str, Any] = {"result": big_string}
        result = await truncate_tool_output_callback(tool, {}, MagicMock(), response)
        assert result is not None
        assert result["result"].startswith(prefix)


class TestTruncateListResult:
    """Tests for list-type tool results."""

    @pytest.mark.asyncio
    async def test_small_list_passes_through(self) -> None:
        """List with <=500 items should not be truncated."""
        tool = SimpleNamespace(name="list_log_entries")
        items = list(range(100))
        response: dict[str, Any] = {"result": items}
        result = await truncate_tool_output_callback(tool, {}, MagicMock(), response)
        assert result is not None
        assert result["result"] == items

    @pytest.mark.asyncio
    async def test_large_list_is_truncated(self) -> None:
        """List with >500 items should be truncated to 500."""
        tool = SimpleNamespace(name="list_log_entries")
        items = list(range(1000))
        response: dict[str, Any] = {"result": items}
        result = await truncate_tool_output_callback(tool, {}, MagicMock(), response)
        assert result is not None
        assert len(result["result"]) == 500
        assert result["metadata"]["truncated_count"] == 500

    @pytest.mark.asyncio
    async def test_exactly_500_items_passes_through(self) -> None:
        """List with exactly 500 items should not be truncated."""
        tool = SimpleNamespace(name="fetch_trace")
        items = list(range(500))
        response: dict[str, Any] = {"result": items}
        result = await truncate_tool_output_callback(tool, {}, MagicMock(), response)
        assert result is not None
        assert len(result["result"]) == 500
        assert "metadata" not in result or "truncated_count" not in result.get(
            "metadata", {}
        )

    @pytest.mark.asyncio
    async def test_501_items_triggers_truncation(self) -> None:
        """List with 501 items should be truncated."""
        tool = SimpleNamespace(name="fetch_trace")
        items = list(range(501))
        response: dict[str, Any] = {"result": items}
        result = await truncate_tool_output_callback(tool, {}, MagicMock(), response)
        assert result is not None
        assert len(result["result"]) == 500
        assert result["metadata"]["truncated_count"] == 1


class TestTruncateDictResult:
    """Tests for dict-type tool results."""

    @pytest.mark.asyncio
    async def test_small_dict_passes_through(self) -> None:
        """Dict that serialises under MAX_RESULT_CHARS should be returned unchanged."""
        tool = SimpleNamespace(name="fetch_trace")
        data = {"key": "value", "count": 42}
        response: dict[str, Any] = {"result": data}
        result = await truncate_tool_output_callback(tool, {}, MagicMock(), response)
        assert result is not None
        assert result["result"] == data

    @pytest.mark.asyncio
    async def test_oversized_dict_is_replaced(self) -> None:
        """Dict exceeding MAX_RESULT_CHARS should be replaced with an error summary."""
        tool = SimpleNamespace(name="list_log_entries")
        data = {"payload": "X" * (MAX_RESULT_CHARS + 1000)}
        response: dict[str, Any] = {"result": data}
        result = await truncate_tool_output_callback(tool, {}, MagicMock(), response)
        assert result is not None
        assert result["result"]["error"] == "Result too large"
        assert "truncated_preview" in result["result"]
        assert "more specific filter" in result["result"]["message"]


class TestEdgeCases:
    """Edge-case and guard-clause tests."""

    @pytest.mark.asyncio
    async def test_none_result_returns_none(self) -> None:
        """When result key is None, callback should return None (no-op)."""
        tool = SimpleNamespace(name="fetch_trace")
        response: dict[str, Any] = {"result": None}
        result = await truncate_tool_output_callback(tool, {}, MagicMock(), response)
        assert result is None

    @pytest.mark.asyncio
    async def test_missing_result_key_returns_none(self) -> None:
        """When response dict has no 'result' key, callback returns None."""
        tool = SimpleNamespace(name="fetch_trace")
        response: dict[str, Any] = {"status": "ok"}
        result = await truncate_tool_output_callback(tool, {}, MagicMock(), response)
        assert result is None

    @pytest.mark.asyncio
    async def test_non_dict_response_returns_none(self) -> None:
        """When tool_response is not a dict, callback should return None."""
        tool = SimpleNamespace(name="fetch_trace")
        result = await truncate_tool_output_callback(
            tool, {}, MagicMock(), "not a dict"  # type: ignore[arg-type]
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_string_result_passes_through(self) -> None:
        """Empty string result should pass through (not truncated, not None)."""
        tool = SimpleNamespace(name="fetch_trace")
        response: dict[str, Any] = {"result": ""}
        result = await truncate_tool_output_callback(tool, {}, MagicMock(), response)
        assert result is not None
        assert result["result"] == ""

    @pytest.mark.asyncio
    async def test_tool_without_name_attribute(self) -> None:
        """Callback should handle tools without a .name attribute via str()."""
        tool = object()  # No .name attribute
        big_string = "Z" * (MAX_RESULT_CHARS + 100)
        response: dict[str, Any] = {"result": big_string}
        result = await truncate_tool_output_callback(tool, {}, MagicMock(), response)
        assert result is not None
        assert "TRUNCATED" in result["result"]

    @pytest.mark.asyncio
    async def test_preserves_other_response_keys(self) -> None:
        """Truncation should preserve other keys in the response dict."""
        tool = SimpleNamespace(name="fetch_trace")
        big_string = "Q" * (MAX_RESULT_CHARS + 100)
        response: dict[str, Any] = {
            "result": big_string,
            "status": "success",
            "extra": 42,
        }
        result = await truncate_tool_output_callback(tool, {}, MagicMock(), response)
        assert result is not None
        assert result["status"] == "success"
        assert result["extra"] == 42

    @pytest.mark.asyncio
    async def test_list_truncation_preserves_existing_metadata(self) -> None:
        """Truncation of list result should merge with existing metadata."""
        tool = SimpleNamespace(name="fetch_trace")
        items = list(range(600))
        response: dict[str, Any] = {
            "result": items,
            "metadata": {"source": "test"},
        }
        result = await truncate_tool_output_callback(tool, {}, MagicMock(), response)
        assert result is not None
        assert result["metadata"]["source"] == "test"
        assert result["metadata"]["truncated_count"] == 100

    @pytest.mark.asyncio
    async def test_dict_truncated_preview_length(self) -> None:
        """Truncated dict preview should be at most MAX_RESULT_CHARS // 2 + '...'."""
        tool = SimpleNamespace(name="fetch_trace")
        data = {"payload": "Y" * (MAX_RESULT_CHARS * 2)}
        response: dict[str, Any] = {"result": data}
        result = await truncate_tool_output_callback(tool, {}, MagicMock(), response)
        assert result is not None
        preview = result["result"]["truncated_preview"]
        assert preview.endswith("...")
        # preview = first half chars + "..."
        assert len(preview) <= MAX_RESULT_CHARS // 2 + 3
