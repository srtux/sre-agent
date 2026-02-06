"""Tests for the CA Data Agent tool (query_data_agent)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from sre_agent.schema import ToolStatus
from sre_agent.tools.bigquery.ca_data_agent import (
    CA_AGENT_ENV,
    DEFAULT_CA_AGENT_ID,
    _build_agent_resource_name,
    _extract_text,
    _extract_vega_config,
    query_data_agent,
)

# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------


class TestBuildAgentResourceName:
    def test_default_location(self) -> None:
        with patch.dict("os.environ", {"GOOGLE_CLOUD_LOCATION": "global"}):
            result = _build_agent_resource_name("my-project", "my-agent")
            assert result == "projects/my-project/locations/global/dataAgents/my-agent"

    def test_custom_location(self) -> None:
        with patch.dict("os.environ", {"GOOGLE_CLOUD_LOCATION": "us-central1"}):
            result = _build_agent_resource_name("proj", "agent-1")
            assert result == "projects/proj/locations/us-central1/dataAgents/agent-1"


class TestExtractText:
    def test_extracts_text(self) -> None:
        msg = MagicMock()
        msg.system_message.text.text = "Hello world"
        assert _extract_text(msg) == "Hello world"

    def test_no_system_message(self) -> None:
        msg = MagicMock(spec=[])  # no system_message attribute
        assert _extract_text(msg) == ""

    def test_no_text_attribute(self) -> None:
        msg = MagicMock()
        msg.system_message = MagicMock(spec=[])  # no text attribute
        assert _extract_text(msg) == ""

    def test_none_text_value(self) -> None:
        msg = MagicMock()
        msg.system_message.text.text = None
        assert _extract_text(msg) == ""


class TestExtractVegaConfig:
    def test_no_system_message(self) -> None:
        msg = MagicMock(spec=[])
        assert _extract_vega_config(msg) is None

    def test_no_chart(self) -> None:
        msg = MagicMock()
        msg.system_message.chart = None
        assert _extract_vega_config(msg) is None

    def test_no_result(self) -> None:
        msg = MagicMock()
        msg.system_message.chart.result = None
        assert _extract_vega_config(msg) is None

    def test_no_vega_config(self) -> None:
        msg = MagicMock()
        msg.system_message.chart.result.vega_config = None
        assert _extract_vega_config(msg) is None

    def test_simple_primitive_vega_config(self) -> None:
        """When vega_config is a plain primitive it should be returned."""
        msg = MagicMock()
        msg.system_message.chart.result.vega_config = "simple"
        result = _extract_vega_config(msg)
        assert result == "simple"


# ---------------------------------------------------------------------------
# Integration-style tests for the main tool function
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_query_data_agent_no_project_id() -> None:
    """Should error when no project ID is available."""
    with patch(
        "sre_agent.tools.bigquery.ca_data_agent.get_project_id_with_fallback",
        return_value=None,
    ):
        result = await query_data_agent(question="test query")
        # @adk_tool returns BaseToolResponse directly when called outside ADK
        assert hasattr(result, "status")
        assert result.status == ToolStatus.ERROR
        assert "project" in result.error.lower()


@pytest.mark.asyncio
async def test_query_data_agent_sdk_not_installed() -> None:
    """Should error gracefully when SDK is not installed."""
    with (
        patch(
            "sre_agent.tools.bigquery.ca_data_agent.get_project_id_with_fallback",
            return_value="test-project",
        ),
        patch(
            "sre_agent.tools.bigquery.ca_data_agent._get_ca_clients",
            side_effect=ImportError("no module"),
        ),
    ):
        result = await query_data_agent(question="test query")
        assert result.status == ToolStatus.ERROR
        assert "sdk" in result.error.lower() or "SDK" in result.error


@pytest.mark.asyncio
async def test_query_data_agent_not_found_error() -> None:
    """Should give actionable guidance when agent is not found."""
    mock_chat = MagicMock()
    mock_chat.chat.side_effect = Exception("NOT_FOUND: agent not found")

    mock_gda = MagicMock()

    with (
        patch(
            "sre_agent.tools.bigquery.ca_data_agent.get_project_id_with_fallback",
            return_value="test-project",
        ),
        patch(
            "sre_agent.tools.bigquery.ca_data_agent._get_ca_clients",
            return_value=(MagicMock(), mock_chat),
        ),
        patch.dict("os.environ", {"GOOGLE_CLOUD_LOCATION": "global"}),
        patch(
            "google.cloud.geminidataanalytics",
            mock_gda,
            create=True,
        ),
    ):
        result = await query_data_agent(question="test query")
        assert result.status == ToolStatus.ERROR
        assert "not found" in result.error.lower()
        assert "setup_ca_agent" in result.error


@pytest.mark.asyncio
async def test_query_data_agent_success() -> None:
    """Should return structured result on success."""
    # Build mock streaming response
    mock_reply = MagicMock()
    mock_reply.system_message.text.text = "The top service is frontend"
    mock_reply.system_message.chart = None

    mock_chat = MagicMock()
    mock_chat.chat.return_value = [mock_reply]

    mock_gda = MagicMock()

    with (
        patch(
            "sre_agent.tools.bigquery.ca_data_agent.get_project_id_with_fallback",
            return_value="test-project",
        ),
        patch(
            "sre_agent.tools.bigquery.ca_data_agent._get_ca_clients",
            return_value=(MagicMock(), mock_chat),
        ),
        patch.dict("os.environ", {"GOOGLE_CLOUD_LOCATION": "global"}),
        patch(
            "google.cloud.geminidataanalytics",
            mock_gda,
            create=True,
        ),
    ):
        result = await query_data_agent(
            question="top 5 slowest spans",
            project_id="test-project",
        )
        assert result.status == ToolStatus.SUCCESS
        res: dict[str, Any] = result.result
        assert res["question"] == "top 5 slowest spans"
        assert "frontend" in res["answer"]
        assert res["project_id"] == "test-project"


@pytest.mark.asyncio
async def test_query_data_agent_with_charts() -> None:
    """Should include vega_lite_charts when CA returns chart data."""
    vega_spec = {"mark": "bar", "encoding": {"x": {"field": "service"}}}

    # Reply with text
    mock_text_reply = MagicMock()
    mock_text_reply.system_message.text.text = "Chart generated"
    mock_text_reply.system_message.chart = None

    # Reply with chart - mock _extract_vega_config to return our spec
    mock_chart_reply = MagicMock()
    mock_chart_reply.system_message.text.text = ""
    # For _extract_vega_config: the vega_config is a primitive (int/float/str/bool)
    # at the top level, _convert returns it. For dicts, we mock it via
    # patching _extract_vega_config directly.

    mock_chat = MagicMock()
    mock_chat.chat.return_value = [mock_text_reply, mock_chart_reply]

    mock_gda = MagicMock()

    def _mock_extract(message: Any) -> dict[str, Any] | None:
        if message is mock_chart_reply:
            return vega_spec
        return None

    with (
        patch(
            "sre_agent.tools.bigquery.ca_data_agent.get_project_id_with_fallback",
            return_value="test-project",
        ),
        patch(
            "sre_agent.tools.bigquery.ca_data_agent._get_ca_clients",
            return_value=(MagicMock(), mock_chat),
        ),
        patch.dict("os.environ", {"GOOGLE_CLOUD_LOCATION": "global"}),
        patch(
            "google.cloud.geminidataanalytics",
            mock_gda,
            create=True,
        ),
        patch(
            "sre_agent.tools.bigquery.ca_data_agent._extract_vega_config",
            side_effect=_mock_extract,
        ),
    ):
        result = await query_data_agent(
            question="error rate by service as bar chart",
            project_id="test-project",
        )
        assert result.status == ToolStatus.SUCCESS
        res: dict[str, Any] = result.result
        assert len(res["vega_lite_charts"]) == 1
        assert res["vega_lite_charts"][0]["mark"] == "bar"


class TestDefaultAgentId:
    def test_default_value(self) -> None:
        assert DEFAULT_CA_AGENT_ID == "ca-autosre"

    def test_env_key(self) -> None:
        assert CA_AGENT_ENV == "SRE_AGENT_CA_DATA_AGENT"
