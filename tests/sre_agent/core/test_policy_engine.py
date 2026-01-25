"""Tests for the Policy Engine."""

import pytest
from pydantic import ValidationError

from sre_agent.core.policy_engine import (
    PolicyDecision,
    PolicyEngine,
    ToolAccessLevel,
    ToolCategory,
    ToolPolicy,
    get_policy_engine,
)


class TestToolPolicy:
    """Tests for ToolPolicy dataclass."""

    def test_tool_policy_creation(self) -> None:
        """Test creating a tool policy."""
        policy = ToolPolicy(
            name="test_tool",
            access_level=ToolAccessLevel.READ_ONLY,
            category=ToolCategory.OBSERVABILITY,
            description="A test tool",
        )

        assert policy.name == "test_tool"
        assert policy.access_level == ToolAccessLevel.READ_ONLY
        assert policy.category == ToolCategory.OBSERVABILITY
        assert policy.description == "A test tool"
        assert policy.requires_project_context is True
        assert policy.risk_level == "low"

    def test_tool_policy_with_high_risk(self) -> None:
        """Test creating a high-risk tool policy."""
        policy = ToolPolicy(
            name="dangerous_tool",
            access_level=ToolAccessLevel.WRITE,
            category=ToolCategory.MUTATION,
            description="A dangerous tool",
            risk_level="critical",
        )

        assert policy.risk_level == "critical"
        assert policy.access_level == ToolAccessLevel.WRITE


class TestPolicyEngine:
    """Tests for PolicyEngine."""

    @pytest.fixture
    def engine(self) -> PolicyEngine:
        """Create a policy engine for testing."""
        return PolicyEngine()

    def test_get_policy_existing(self, engine: PolicyEngine) -> None:
        """Test getting an existing policy."""
        policy = engine.get_policy("fetch_trace")
        assert policy is not None
        assert policy.name == "fetch_trace"
        assert policy.access_level == ToolAccessLevel.READ_ONLY

    def test_get_policy_nonexistent(self, engine: PolicyEngine) -> None:
        """Test getting a non-existent policy."""
        policy = engine.get_policy("nonexistent_tool")
        assert policy is None

    def test_evaluate_read_only_tool(self, engine: PolicyEngine) -> None:
        """Test evaluating a read-only tool."""
        decision = engine.evaluate(
            tool_name="fetch_trace",
            tool_args={"trace_id": "abc123"},
            project_id="test-project",
        )

        assert decision.allowed is True
        assert decision.requires_approval is False
        assert decision.access_level == ToolAccessLevel.READ_ONLY

    def test_evaluate_write_tool(self, engine: PolicyEngine) -> None:
        """Test evaluating a write tool."""
        decision = engine.evaluate(
            tool_name="restart_pod",
            tool_args={"pod_name": "test-pod"},
            project_id="test-project",
        )

        assert decision.allowed is True
        assert decision.requires_approval is True
        assert decision.access_level == ToolAccessLevel.WRITE
        assert decision.risk_assessment is not None

    def test_evaluate_admin_tool(self, engine: PolicyEngine) -> None:
        """Test evaluating an admin tool."""
        decision = engine.evaluate(
            tool_name="delete_resource",
            tool_args={"resource_id": "test-resource"},
            project_id="test-project",
        )

        assert decision.allowed is False
        assert decision.requires_approval is False
        assert decision.access_level == ToolAccessLevel.ADMIN

    def test_evaluate_unknown_tool(self, engine: PolicyEngine) -> None:
        """Test evaluating an unknown tool."""
        decision = engine.evaluate(
            tool_name="unknown_tool",
            tool_args={},
            project_id="test-project",
        )

        assert decision.allowed is False
        assert "Unknown tool" in decision.reason

    def test_evaluate_missing_project_context(self, engine: PolicyEngine) -> None:
        """Test evaluating tool without project context."""
        decision = engine.evaluate(
            tool_name="fetch_trace",
            tool_args={"trace_id": "abc123"},
            project_id=None,  # Missing project
        )

        assert decision.allowed is False
        assert "project context" in decision.reason.lower()

    def test_evaluate_tool_without_project_requirement(
        self, engine: PolicyEngine
    ) -> None:
        """Test evaluating tool that doesn't require project context."""
        decision = engine.evaluate(
            tool_name="get_current_time",
            tool_args={},
            project_id=None,  # No project required
        )

        assert decision.allowed is True

    def test_get_tools_by_category(self, engine: PolicyEngine) -> None:
        """Test getting tools by category."""
        observability_tools = engine.get_tools_by_category(ToolCategory.OBSERVABILITY)

        assert len(observability_tools) > 0
        assert "fetch_trace" in observability_tools
        assert "list_log_entries" in observability_tools

    def test_get_tools_by_access_level(self, engine: PolicyEngine) -> None:
        """Test getting tools by access level."""
        write_tools = engine.get_tools_by_access_level(ToolAccessLevel.WRITE)

        assert len(write_tools) > 0
        assert "restart_pod" in write_tools
        assert "fetch_trace" not in write_tools

    def test_list_write_tools(self, engine: PolicyEngine) -> None:
        """Test listing write tools."""
        write_tools = engine.list_write_tools()

        assert len(write_tools) > 0
        assert all(t.access_level == ToolAccessLevel.WRITE for t in write_tools)

    def test_risk_assessment_with_force_flag(self, engine: PolicyEngine) -> None:
        """Test risk assessment includes force flag warning."""
        decision = engine.evaluate(
            tool_name="restart_pod",
            tool_args={"pod_name": "test-pod", "force": True},
            project_id="test-project",
        )

        assert decision.risk_assessment is not None
        assert "force" in decision.risk_assessment.lower()


class TestPolicyEngineSingleton:
    """Tests for singleton access."""

    def test_get_policy_engine_singleton(self) -> None:
        """Test that get_policy_engine returns singleton."""
        engine1 = get_policy_engine()
        engine2 = get_policy_engine()

        assert engine1 is engine2


class TestPolicyDecision:
    """Tests for PolicyDecision model."""

    def test_policy_decision_creation(self) -> None:
        """Test creating a policy decision."""
        decision = PolicyDecision(
            tool_name="test_tool",
            allowed=True,
            requires_approval=False,
            reason="Read-only operation",
            access_level=ToolAccessLevel.READ_ONLY,
        )

        assert decision.tool_name == "test_tool"
        assert decision.allowed is True
        assert decision.requires_approval is False

    def test_policy_decision_with_risk_assessment(self) -> None:
        """Test policy decision with risk assessment."""
        decision = PolicyDecision(
            tool_name="restart_pod",
            allowed=True,
            requires_approval=True,
            reason="Write operation",
            access_level=ToolAccessLevel.WRITE,
            risk_assessment="Medium risk - may cause brief downtime",
        )

        assert decision.risk_assessment is not None
        assert "risk" in decision.risk_assessment.lower()

    def test_policy_decision_immutable(self) -> None:
        """Test that policy decision is immutable."""
        decision = PolicyDecision(
            tool_name="test_tool",
            allowed=True,
            requires_approval=False,
            reason="Test",
            access_level=ToolAccessLevel.READ_ONLY,
        )

        with pytest.raises(ValidationError):  # Pydantic frozen model
            decision.allowed = False  # type: ignore[misc]
