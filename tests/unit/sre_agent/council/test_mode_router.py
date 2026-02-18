"""Tests for the investigation mode router tool.

Validates that the classify_investigation_mode @adk_tool correctly
wraps the intent classifier and returns BaseToolResponse.
"""

from unittest.mock import patch

import pytest

from sre_agent.council.mode_router import classify_investigation_mode


class TestClassifyInvestigationMode:
    """Tests for the mode router tool."""

    @pytest.mark.asyncio
    async def test_returns_success_for_standard(self) -> None:
        """Should return success with STANDARD mode for generic query."""
        result = await classify_investigation_mode(
            query="analyze the latency for checkout-service"
        )
        assert result.status.value == "success"
        assert result.result["mode"] == "standard"

    @pytest.mark.asyncio
    async def test_returns_success_for_fast(self) -> None:
        """Should return success with FAST mode for status query."""
        result = await classify_investigation_mode(query="quick status check on API")
        assert result.status.value == "success"
        assert result.result["mode"] == "fast"

    @pytest.mark.asyncio
    async def test_returns_success_for_debate(self) -> None:
        """Should return success with DEBATE mode for incident query."""
        result = await classify_investigation_mode(
            query="root cause of the production outage"
        )
        assert result.status.value == "success"
        assert result.result["mode"] == "debate"

    @pytest.mark.asyncio
    async def test_includes_mode_description(self) -> None:
        """Result should include a description of the selected mode."""
        result = await classify_investigation_mode(query="quick status check")
        assert "description" in result.result
        assert isinstance(result.result["description"], str)
        assert len(result.result["description"]) > 0

    @pytest.mark.asyncio
    async def test_includes_original_query(self) -> None:
        """Result should include the original query."""
        query = "analyze service metrics"
        result = await classify_investigation_mode(query=query)
        assert result.result["query"] == query

    @pytest.mark.asyncio
    async def test_metadata_contains_classifier_type(self) -> None:
        """Metadata should indicate the classifier type (rule_based when adaptive disabled)."""
        with patch.dict("os.environ", {"SRE_AGENT_ADAPTIVE_CLASSIFIER": "false"}):
            result = await classify_investigation_mode(query="test query")
            assert result.metadata["classifier"] == "rule_based"
