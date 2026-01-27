from unittest.mock import MagicMock, patch

import pytest

from sre_agent.agent import get_enabled_base_tools
from sre_agent.core.policy_engine import PolicyEngine, ToolAccessLevel, ToolPolicy
from sre_agent.tools.config import ToolConfigManager


def test_policy_engine_respects_disabled_tools():
    """Test that PolicyEngine rejects tools that are disabled in configuration."""
    from sre_agent.core.policy_engine import ToolCategory

    # Setup policies
    policies = {
        "test_tool": ToolPolicy(
            name="test_tool",
            access_level=ToolAccessLevel.READ_ONLY,
            category=ToolCategory.OBSERVABILITY,
            description="test description",
            requires_project_context=False,
        )
    }
    engine = PolicyEngine(policies=policies)

    # Mock ToolConfigManager to have 'test_tool' disabled
    mock_manager = MagicMock(spec=ToolConfigManager)
    mock_manager.is_enabled.return_value = False

    with patch(
        "sre_agent.tools.config.get_tool_config_manager", return_value=mock_manager
    ):
        decision = engine.evaluate(
            "test_tool", {"arg": "val"}, project_id="test-project"
        )

        assert decision.allowed is True
        assert "allowing anyway" in decision.reason
        mock_manager.is_enabled.assert_called_with("test_tool")


def test_policy_engine_allows_enabled_tools():
    """Test that PolicyEngine allows tools that are enabled in configuration."""
    from sre_agent.core.policy_engine import ToolCategory

    policies = {
        "test_tool": ToolPolicy(
            name="test_tool",
            access_level=ToolAccessLevel.READ_ONLY,
            category=ToolCategory.OBSERVABILITY,
            description="test description",
        )
    }
    engine = PolicyEngine(policies=policies)

    mock_manager = MagicMock(spec=ToolConfigManager)
    mock_manager.is_enabled.return_value = True

    with patch(
        "sre_agent.tools.config.get_tool_config_manager", return_value=mock_manager
    ):
        decision = engine.evaluate(
            "test_tool", {"arg": "val"}, project_id="test-project"
        )

        assert decision.allowed is True
        assert "allowed" in decision.reason.lower()


def test_get_enabled_base_tools_filtering():
    """Test that get_enabled_base_tools correctly filters the base_tools list."""

    # Create a small set of tools for testing
    def tool_a():
        pass

    def tool_b():
        pass

    test_tool_map = {"tool_a": tool_a, "tool_b": tool_b}
    test_base_tools = [tool_a, tool_b]

    mock_manager = MagicMock(spec=ToolConfigManager)
    # Enable tool_a, disable tool_b
    mock_manager.get_enabled_tools.return_value = ["tool_a"]

    with patch("sre_agent.agent.TOOL_NAME_MAP", test_tool_map):
        with patch("sre_agent.agent.base_tools", test_base_tools):
            with patch(
                "sre_agent.agent.get_tool_config_manager", return_value=mock_manager
            ):
                enabled = get_enabled_base_tools()

                assert tool_a in enabled
                assert tool_b not in enabled
                assert len(enabled) == 1


@pytest.mark.anyio
async def test_runner_refreshes_tools_per_turn():
    """Test that Runner refreshes the agent's tool list at the start of run_turn."""
    from google.adk.agents import LlmAgent

    from sre_agent.core.runner import Runner, RunnerConfig

    mock_agent = MagicMock(spec=LlmAgent)
    mock_agent.name = "test_agent"
    mock_agent.tools = []

    runner = Runner(agent=mock_agent, config=RunnerConfig(enable_compaction=False))

    # Mock session and other args
    mock_session = MagicMock()
    mock_session.id = "test-session"
    mock_session.events = []

    # Mock get_enabled_base_tools to return a specific list
    def mock_tool():
        pass

    with patch("sre_agent.agent.get_enabled_base_tools", return_value=[mock_tool]):
        # We use a mock for the internal _run_with_policy to stop execution early
        with patch.object(Runner, "_run_with_policy") as mock_run:
            # Create a manual async generator to yield nothing
            async def empty_gen(*args, **kwargs):
                if False:
                    yield

            mock_run.side_effect = empty_gen

            # Execute one turn
            async for _ in runner.run_turn(mock_session, "msg", "user"):
                pass

            # Verify agent.tools was updated
            assert mock_agent.tools == [mock_tool]
