"""Tests for emergency context compaction and token management.

Validates that:
- _compact_llm_contents correctly condenses LLM history.
- before_model_callback triggers compaction when token limits are approached.
- Tool output truncation prevents massive responses from blowing up context.
"""

from unittest.mock import MagicMock, patch

import pytest
from google.genai import types as genai_types

from sre_agent.core.model_callbacks import (
    _compact_llm_contents,
    before_model_callback,
)
from sre_agent.core.tool_callbacks import truncate_tool_output_callback


class TestContextCompaction:
    """Tests for heuristic history compaction."""

    def test_compact_llm_contents_basic(self) -> None:
        """Should condense tool calls and results into a summary."""
        contents = [
            genai_types.Content(
                role="model",
                parts=[
                    genai_types.Part(
                        function_call=genai_types.FunctionCall(
                            name="list_log_entries",
                            args={"filter": "severity>=ERROR"},
                        )
                    )
                ],
            ),
            genai_types.Content(
                role="user",
                parts=[
                    genai_types.Part(
                        function_response=genai_types.FunctionResponse(
                            name="list_log_entries",
                            response={
                                "status": "success",
                                "result": [{"message": "err1"}, {"message": "err2"}],
                            },
                        )
                    )
                ],
            ),
            genai_types.Content(
                role="model",
                parts=[genai_types.Part(text="Thinking about logs...")],
            ),
        ]

        summary = _compact_llm_contents(contents)

        assert "Called tool: list_log_entries" in summary
        assert "Retrieved 2 log entries" in summary
        assert "Thought: Thinking about logs..." in summary

    def test_before_model_callback_triggers_compaction(self) -> None:
        """Should compact history when estimated tokens exceed limit."""
        # Create a large request (> 700k tokens estimated via chars/3.2)
        # 1M tokens * 3.2 chars/token = 3.2M characters
        large_text = "x" * 3_200_000

        # Create lots of turns to ensure we trigger the length check (> 14 turns)
        contents = [
            genai_types.Content(role="user", parts=[genai_types.Part(text="Init")])
        ]
        for i in range(20):
            contents.append(
                genai_types.Content(
                    role="model",
                    parts=[genai_types.Part(text=f"Turn {i} " + large_text[:100])],
                )
            )
            contents.append(
                genai_types.Content(
                    role="user", parts=[genai_types.Part(text=f"Res {i}")]
                )
            )

        # Add the one massive message at the end of the middle turns
        contents[5].parts[0].text = large_text

        llm_request = MagicMock()
        llm_request.contents = contents

        ctx = MagicMock()
        ctx.state = {}
        ctx.agent_name = "test_agent"

        with patch("sre_agent.core.model_callbacks.logger") as mock_logger:
            before_model_callback(ctx, llm_request)

            # Should have reduced length
            # Original: 1 (init) + 40 (turns) = 41
            # New: 1 (first) + 1 (indicator) + 6 (recent, since 1M tokens > 900k) = 8
            assert len(llm_request.contents) == 8
            assert "Middle 34 turns compacted" in llm_request.contents[1].parts[0].text
            mock_logger.warning.assert_called()

    def test_before_model_callback_no_compaction_needed(self) -> None:
        """Should not modify request if under token limit."""
        contents = [
            genai_types.Content(
                role="user", parts=[genai_types.Part(text="Short message")]
            )
        ]
        llm_request = MagicMock()
        llm_request.contents = contents

        ctx = MagicMock()
        before_model_callback(ctx, llm_request)

        assert len(llm_request.contents) == 1
        assert llm_request.contents[0].parts[0].text == "Short message"


class TestToolOutputTruncation:
    """Tests for safety guards on massive tool results."""

    @pytest.mark.asyncio
    async def test_truncate_string_output(self) -> None:
        """Should truncate massive strings in tool results."""
        large_result = "A" * 300_000  # > 200k limit
        response = {"status": "success", "result": large_result}

        tool = MagicMock()
        tool.name = "test_tool"

        truncated = await truncate_tool_output_callback(tool, {}, MagicMock(), response)

        assert len(truncated["result"]) < 300_000
        assert "TRUNCATED BY SRE AGENT SAFETY GUARD" in truncated["result"]

    @pytest.mark.asyncio
    async def test_truncate_list_output(self) -> None:
        """Should truncate massive lists in tool results."""
        large_list = [{"id": i} for i in range(1000)]  # > 500 limit
        response = {"status": "success", "result": large_list}

        truncated = await truncate_tool_output_callback(
            MagicMock(), {}, MagicMock(), response
        )

        assert len(truncated["result"]) == 500
        assert truncated["metadata"]["truncated_count"] == 500

    @pytest.mark.asyncio
    async def test_truncate_dict_output(self) -> None:
        """Should handle massive dicts by returning an error/preview."""
        # Create a dict that's very large when serialized
        large_dict = {"data": "B" * 300_000}
        response = {"status": "success", "result": large_dict}

        truncated = await truncate_tool_output_callback(
            MagicMock(), {}, MagicMock(), response
        )

        assert truncated["result"]["error"] == "Result too large"
        assert "exceeded safety limit" in truncated["result"]["message"]
