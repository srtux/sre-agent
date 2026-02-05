"""Tests for council schema validation.

Validates Pydantic models for investigation modes, panel findings,
critic reports, council results, council configuration, and agent
activity tracking schemas.
"""

import pytest
from pydantic import ValidationError

from sre_agent.council.schemas import (
    AgentActivity,
    AgentType,
    CouncilActivityGraph,
    CouncilConfig,
    CouncilResult,
    CriticReport,
    InvestigationMode,
    LLMCallRecord,
    PanelFinding,
    PanelSeverity,
    ToolCallRecord,
)


class TestInvestigationMode:
    """Tests for InvestigationMode enum."""

    def test_all_modes_exist(self) -> None:
        """All three investigation modes should be defined."""
        assert InvestigationMode.FAST == "fast"
        assert InvestigationMode.STANDARD == "standard"
        assert InvestigationMode.DEBATE == "debate"

    def test_mode_from_string(self) -> None:
        """Modes should be constructable from string values."""
        assert InvestigationMode("fast") == InvestigationMode.FAST
        assert InvestigationMode("standard") == InvestigationMode.STANDARD
        assert InvestigationMode("debate") == InvestigationMode.DEBATE

    def test_invalid_mode_raises(self) -> None:
        """Invalid mode string should raise ValueError."""
        with pytest.raises(ValueError):
            InvestigationMode("invalid")


class TestPanelSeverity:
    """Tests for PanelSeverity enum."""

    def test_all_severities_exist(self) -> None:
        """All four severity levels should be defined."""
        assert PanelSeverity.CRITICAL == "critical"
        assert PanelSeverity.WARNING == "warning"
        assert PanelSeverity.INFO == "info"
        assert PanelSeverity.HEALTHY == "healthy"


class TestPanelFinding:
    """Tests for PanelFinding model."""

    def test_valid_finding(self) -> None:
        """A valid PanelFinding should be constructable."""
        finding = PanelFinding(
            panel="trace",
            summary="High latency in checkout service",
            severity=PanelSeverity.WARNING,
            confidence=0.85,
            evidence=["trace-id-123: 500ms", "p99 latency spike at 14:00"],
            recommended_actions=["Scale checkout-service pods"],
        )
        assert finding.panel == "trace"
        assert finding.confidence == 0.85
        assert len(finding.evidence) == 2

    def test_finding_with_defaults(self) -> None:
        """PanelFinding should work with default lists."""
        finding = PanelFinding(
            panel="metrics",
            summary="All metrics within normal range",
            severity=PanelSeverity.HEALTHY,
            confidence=0.95,
        )
        assert finding.evidence == []
        assert finding.recommended_actions == []

    def test_frozen_model(self) -> None:
        """PanelFinding should be immutable."""
        finding = PanelFinding(
            panel="trace",
            summary="test",
            severity=PanelSeverity.INFO,
            confidence=0.5,
        )
        with pytest.raises(ValidationError):
            finding.panel = "metrics"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError):
            PanelFinding(
                panel="trace",
                summary="test",
                severity=PanelSeverity.INFO,
                confidence=0.5,
                extra_field="not allowed",  # type: ignore[call-arg]
            )

    def test_confidence_out_of_range(self) -> None:
        """Confidence outside 0.0-1.0 should be rejected."""
        with pytest.raises(ValidationError):
            PanelFinding(
                panel="trace",
                summary="test",
                severity=PanelSeverity.INFO,
                confidence=1.5,
            )
        with pytest.raises(ValidationError):
            PanelFinding(
                panel="trace",
                summary="test",
                severity=PanelSeverity.INFO,
                confidence=-0.1,
            )

    def test_confidence_boundary_values(self) -> None:
        """Confidence at boundaries should be accepted."""
        low = PanelFinding(
            panel="trace",
            summary="test",
            severity=PanelSeverity.INFO,
            confidence=0.0,
        )
        high = PanelFinding(
            panel="trace",
            summary="test",
            severity=PanelSeverity.INFO,
            confidence=1.0,
        )
        assert low.confidence == 0.0
        assert high.confidence == 1.0

    def test_invalid_severity_rejected(self) -> None:
        """Invalid severity string should be rejected."""
        with pytest.raises(ValidationError):
            PanelFinding(
                panel="trace",
                summary="test",
                severity="unknown",  # type: ignore[arg-type]
                confidence=0.5,
            )


class TestCriticReport:
    """Tests for CriticReport model."""

    def test_valid_report(self) -> None:
        """A valid CriticReport should be constructable."""
        report = CriticReport(
            agreements=["Both trace and metrics show latency spike at 14:00"],
            contradictions=["Trace says healthy but logs show errors"],
            gaps=["No alert data analyzed"],
            revised_confidence=0.72,
        )
        assert len(report.agreements) == 1
        assert len(report.contradictions) == 1
        assert report.revised_confidence == 0.72

    def test_report_with_defaults(self) -> None:
        """CriticReport should work with default lists."""
        report = CriticReport(revised_confidence=0.9)
        assert report.agreements == []
        assert report.contradictions == []
        assert report.gaps == []

    def test_frozen_model(self) -> None:
        """CriticReport should be immutable."""
        report = CriticReport(revised_confidence=0.8)
        with pytest.raises(ValidationError):
            report.revised_confidence = 0.9  # type: ignore[misc]


class TestCouncilResult:
    """Tests for CouncilResult model."""

    def test_valid_result(self) -> None:
        """A full CouncilResult should be constructable."""
        finding = PanelFinding(
            panel="trace",
            summary="test",
            severity=PanelSeverity.WARNING,
            confidence=0.8,
        )
        critic = CriticReport(revised_confidence=0.75)
        result = CouncilResult(
            mode=InvestigationMode.DEBATE,
            panels=[finding],
            critic_report=critic,
            synthesis="Checkout service experiencing latency issues",
            overall_severity=PanelSeverity.WARNING,
            overall_confidence=0.75,
            rounds=2,
        )
        assert result.mode == InvestigationMode.DEBATE
        assert len(result.panels) == 1
        assert result.critic_report is not None
        assert result.rounds == 2

    def test_result_with_defaults(self) -> None:
        """CouncilResult should work with defaults for FAST mode."""
        result = CouncilResult(
            mode=InvestigationMode.FAST,
            synthesis="All healthy",
            overall_confidence=0.95,
        )
        assert result.panels == []
        assert result.critic_report is None
        assert result.overall_severity == PanelSeverity.INFO
        assert result.rounds == 1

    def test_result_frozen(self) -> None:
        """CouncilResult should be immutable."""
        result = CouncilResult(mode=InvestigationMode.FAST)
        with pytest.raises(ValidationError):
            result.mode = InvestigationMode.DEBATE  # type: ignore[misc]

    def test_result_serialization_roundtrip(self) -> None:
        """CouncilResult should serialize and deserialize cleanly."""
        finding = PanelFinding(
            panel="metrics",
            summary="High CPU",
            severity=PanelSeverity.CRITICAL,
            confidence=0.9,
            evidence=["cpu_usage > 95%"],
            recommended_actions=["Scale up"],
        )
        original = CouncilResult(
            mode=InvestigationMode.STANDARD,
            panels=[finding],
            synthesis="Critical CPU issue",
            overall_severity=PanelSeverity.CRITICAL,
            overall_confidence=0.9,
        )
        data = original.model_dump()
        restored = CouncilResult.model_validate(data)
        assert restored == original


class TestCouncilConfig:
    """Tests for CouncilConfig model."""

    def test_default_config(self) -> None:
        """Default config should use STANDARD mode with sensible defaults."""
        config = CouncilConfig()
        assert config.mode == InvestigationMode.STANDARD
        assert config.max_debate_rounds == 3
        assert config.confidence_threshold == 0.85
        assert config.timeout_seconds == 120

    def test_debate_config(self) -> None:
        """Debate config should accept custom parameters."""
        config = CouncilConfig(
            mode=InvestigationMode.DEBATE,
            max_debate_rounds=5,
            confidence_threshold=0.9,
            timeout_seconds=300,
        )
        assert config.mode == InvestigationMode.DEBATE
        assert config.max_debate_rounds == 5

    def test_invalid_debate_rounds(self) -> None:
        """Debate rounds outside 1-10 should be rejected."""
        with pytest.raises(ValidationError):
            CouncilConfig(max_debate_rounds=0)
        with pytest.raises(ValidationError):
            CouncilConfig(max_debate_rounds=11)

    def test_invalid_timeout(self) -> None:
        """Timeout outside 10-600 should be rejected."""
        with pytest.raises(ValidationError):
            CouncilConfig(timeout_seconds=5)
        with pytest.raises(ValidationError):
            CouncilConfig(timeout_seconds=700)

    def test_frozen_config(self) -> None:
        """CouncilConfig should be immutable."""
        config = CouncilConfig()
        with pytest.raises(ValidationError):
            config.mode = InvestigationMode.FAST  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError):
            CouncilConfig(unknown="value")  # type: ignore[call-arg]


# =============================================================================
# Agent Activity Tracking Schema Tests
# =============================================================================


class TestAgentType:
    """Tests for AgentType enum."""

    def test_all_types_exist(self) -> None:
        """All six agent types should be defined."""
        assert AgentType.ROOT == "root"
        assert AgentType.ORCHESTRATOR == "orchestrator"
        assert AgentType.PANEL == "panel"
        assert AgentType.CRITIC == "critic"
        assert AgentType.SYNTHESIZER == "synthesizer"
        assert AgentType.SUB_AGENT == "sub_agent"

    def test_type_from_string(self) -> None:
        """Types should be constructable from string values."""
        assert AgentType("root") == AgentType.ROOT
        assert AgentType("panel") == AgentType.PANEL
        assert AgentType("synthesizer") == AgentType.SYNTHESIZER

    def test_invalid_type_raises(self) -> None:
        """Invalid type string should raise ValueError."""
        with pytest.raises(ValueError):
            AgentType("unknown")


class TestToolCallRecord:
    """Tests for ToolCallRecord model."""

    def test_valid_record(self) -> None:
        """A valid ToolCallRecord should be constructable."""
        record = ToolCallRecord(
            call_id="tc-123",
            tool_name="get_traces",
            args_summary="service=checkout, time_range=1h",
            result_summary="Found 15 slow traces",
            status="completed",
            duration_ms=250,
            timestamp="2025-01-15T10:30:00Z",
            dashboard_category="traces",
        )
        assert record.call_id == "tc-123"
        assert record.tool_name == "get_traces"
        assert record.duration_ms == 250
        assert record.dashboard_category == "traces"

    def test_record_with_defaults(self) -> None:
        """ToolCallRecord should work with minimal required fields."""
        record = ToolCallRecord(call_id="tc-001", tool_name="list_alerts")
        assert record.args_summary == ""
        assert record.result_summary == ""
        assert record.status == "completed"
        assert record.duration_ms == 0
        assert record.timestamp == ""
        assert record.dashboard_category is None

    def test_negative_duration_rejected(self) -> None:
        """Negative duration should be rejected."""
        with pytest.raises(ValidationError):
            ToolCallRecord(call_id="tc-001", tool_name="test", duration_ms=-100)

    def test_extra_fields_forbidden(self) -> None:
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError):
            ToolCallRecord(
                call_id="tc-001",
                tool_name="test",
                extra="not allowed",  # type: ignore[call-arg]
            )

    def test_serialization_roundtrip(self) -> None:
        """ToolCallRecord should serialize and deserialize cleanly."""
        original = ToolCallRecord(
            call_id="tc-456",
            tool_name="query_metrics",
            args_summary="metric=cpu_usage",
            status="completed",
            duration_ms=150,
        )
        data = original.model_dump()
        restored = ToolCallRecord.model_validate(data)
        assert restored == original


class TestLLMCallRecord:
    """Tests for LLMCallRecord model."""

    def test_valid_record(self) -> None:
        """A valid LLMCallRecord should be constructable."""
        record = LLMCallRecord(
            call_id="llm-123",
            model="gemini-2.5-flash",
            input_tokens=1500,
            output_tokens=350,
            duration_ms=800,
            timestamp="2025-01-15T10:31:00Z",
        )
        assert record.call_id == "llm-123"
        assert record.model == "gemini-2.5-flash"
        assert record.input_tokens == 1500
        assert record.output_tokens == 350

    def test_record_with_defaults(self) -> None:
        """LLMCallRecord should work with minimal required fields."""
        record = LLMCallRecord(call_id="llm-001", model="gemini-2.5-pro")
        assert record.input_tokens == 0
        assert record.output_tokens == 0
        assert record.duration_ms == 0
        assert record.timestamp == ""

    def test_negative_tokens_rejected(self) -> None:
        """Negative token counts should be rejected."""
        with pytest.raises(ValidationError):
            LLMCallRecord(call_id="llm-001", model="test", input_tokens=-100)
        with pytest.raises(ValidationError):
            LLMCallRecord(call_id="llm-001", model="test", output_tokens=-50)

    def test_extra_fields_forbidden(self) -> None:
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError):
            LLMCallRecord(
                call_id="llm-001",
                model="test",
                extra="forbidden",  # type: ignore[call-arg]
            )


class TestAgentActivity:
    """Tests for AgentActivity model."""

    def test_valid_activity(self) -> None:
        """A valid AgentActivity should be constructable."""
        tool_call = ToolCallRecord(call_id="tc-1", tool_name="get_traces")
        llm_call = LLMCallRecord(call_id="llm-1", model="gemini-2.5-flash")
        activity = AgentActivity(
            agent_id="panel-trace-001",
            agent_name="Trace Panel",
            agent_type=AgentType.PANEL,
            parent_id="orchestrator-001",
            status="completed",
            started_at="2025-01-15T10:30:00Z",
            completed_at="2025-01-15T10:30:15Z",
            tool_calls=[tool_call],
            llm_calls=[llm_call],
            output_summary="Found latency issues in checkout service",
        )
        assert activity.agent_id == "panel-trace-001"
        assert activity.agent_type == AgentType.PANEL
        assert len(activity.tool_calls) == 1
        assert len(activity.llm_calls) == 1

    def test_activity_with_defaults(self) -> None:
        """AgentActivity should work with minimal required fields."""
        activity = AgentActivity(
            agent_id="root-001",
            agent_name="Root Agent",
            agent_type=AgentType.ROOT,
        )
        assert activity.parent_id is None
        assert activity.status == "pending"
        assert activity.tool_calls == []
        assert activity.llm_calls == []
        assert activity.output_summary == ""

    def test_root_agent_no_parent(self) -> None:
        """Root agents should have no parent."""
        activity = AgentActivity(
            agent_id="root-001",
            agent_name="Root Agent",
            agent_type=AgentType.ROOT,
            parent_id=None,
        )
        assert activity.parent_id is None

    def test_panel_with_parent(self) -> None:
        """Panel agents should reference their parent."""
        activity = AgentActivity(
            agent_id="panel-metrics-001",
            agent_name="Metrics Panel",
            agent_type=AgentType.PANEL,
            parent_id="orchestrator-001",
        )
        assert activity.parent_id == "orchestrator-001"

    def test_extra_fields_forbidden(self) -> None:
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError):
            AgentActivity(
                agent_id="test",
                agent_name="Test",
                agent_type=AgentType.ROOT,
                extra="forbidden",  # type: ignore[call-arg]
            )

    def test_serialization_roundtrip(self) -> None:
        """AgentActivity should serialize and deserialize cleanly."""
        tool_call = ToolCallRecord(
            call_id="tc-1", tool_name="get_traces", duration_ms=100
        )
        original = AgentActivity(
            agent_id="panel-001",
            agent_name="Test Panel",
            agent_type=AgentType.PANEL,
            parent_id="root",
            tool_calls=[tool_call],
            status="completed",
        )
        data = original.model_dump()
        restored = AgentActivity.model_validate(data)
        assert restored == original


class TestCouncilActivityGraph:
    """Tests for CouncilActivityGraph model."""

    def _make_root_agent(self) -> AgentActivity:
        """Create a root agent for testing."""
        return AgentActivity(
            agent_id="root-001",
            agent_name="Root Agent",
            agent_type=AgentType.ROOT,
        )

    def _make_panel_agent(self, name: str, parent_id: str) -> AgentActivity:
        """Create a panel agent for testing."""
        return AgentActivity(
            agent_id=f"panel-{name}-001",
            agent_name=f"{name.title()} Panel",
            agent_type=AgentType.PANEL,
            parent_id=parent_id,
        )

    def test_valid_graph(self) -> None:
        """A valid CouncilActivityGraph should be constructable."""
        root = self._make_root_agent()
        trace_panel = self._make_panel_agent("trace", "root-001")
        metrics_panel = self._make_panel_agent("metrics", "root-001")

        graph = CouncilActivityGraph(
            investigation_id="inv-123",
            mode=InvestigationMode.STANDARD,
            started_at="2025-01-15T10:30:00Z",
            completed_at="2025-01-15T10:30:30Z",
            agents=[root, trace_panel, metrics_panel],
            total_tool_calls=8,
            total_llm_calls=4,
            debate_rounds=1,
        )
        assert graph.investigation_id == "inv-123"
        assert len(graph.agents) == 3
        assert graph.total_tool_calls == 8

    def test_graph_with_defaults(self) -> None:
        """CouncilActivityGraph should work with minimal required fields."""
        graph = CouncilActivityGraph(
            investigation_id="inv-001",
            mode=InvestigationMode.FAST,
            started_at="2025-01-15T10:30:00Z",
        )
        assert graph.completed_at == ""
        assert graph.agents == []
        assert graph.total_tool_calls == 0
        assert graph.total_llm_calls == 0
        assert graph.debate_rounds == 1

    def test_get_agent_by_id(self) -> None:
        """get_agent_by_id should find the correct agent."""
        root = self._make_root_agent()
        panel = self._make_panel_agent("trace", "root-001")
        graph = CouncilActivityGraph(
            investigation_id="inv-001",
            mode=InvestigationMode.STANDARD,
            started_at="2025-01-15T10:30:00Z",
            agents=[root, panel],
        )

        found = graph.get_agent_by_id("root-001")
        assert found is not None
        assert found.agent_name == "Root Agent"

        not_found = graph.get_agent_by_id("nonexistent")
        assert not_found is None

    def test_get_children(self) -> None:
        """get_children should return direct children of an agent."""
        root = self._make_root_agent()
        trace = self._make_panel_agent("trace", "root-001")
        metrics = self._make_panel_agent("metrics", "root-001")
        logs = self._make_panel_agent("logs", "root-001")

        graph = CouncilActivityGraph(
            investigation_id="inv-001",
            mode=InvestigationMode.STANDARD,
            started_at="2025-01-15T10:30:00Z",
            agents=[root, trace, metrics, logs],
        )

        children = graph.get_children("root-001")
        assert len(children) == 3
        assert all(c.agent_type == AgentType.PANEL for c in children)

        no_children = graph.get_children("panel-trace-001")
        assert no_children == []

    def test_get_root_agents(self) -> None:
        """get_root_agents should return agents with no parent."""
        root = self._make_root_agent()
        panel = self._make_panel_agent("trace", "root-001")

        graph = CouncilActivityGraph(
            investigation_id="inv-001",
            mode=InvestigationMode.STANDARD,
            started_at="2025-01-15T10:30:00Z",
            agents=[root, panel],
        )

        roots = graph.get_root_agents()
        assert len(roots) == 1
        assert roots[0].agent_id == "root-001"

    def test_debate_mode_multiple_rounds(self) -> None:
        """Debate mode graphs should support multiple rounds."""
        graph = CouncilActivityGraph(
            investigation_id="inv-debate",
            mode=InvestigationMode.DEBATE,
            started_at="2025-01-15T10:30:00Z",
            debate_rounds=3,
        )
        assert graph.mode == InvestigationMode.DEBATE
        assert graph.debate_rounds == 3

    def test_extra_fields_forbidden(self) -> None:
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError):
            CouncilActivityGraph(
                investigation_id="inv-001",
                mode=InvestigationMode.FAST,
                started_at="2025-01-15T10:30:00Z",
                extra="forbidden",  # type: ignore[call-arg]
            )

    def test_serialization_roundtrip(self) -> None:
        """CouncilActivityGraph should serialize and deserialize cleanly."""
        root = self._make_root_agent()
        panel = self._make_panel_agent("trace", "root-001")

        original = CouncilActivityGraph(
            investigation_id="inv-001",
            mode=InvestigationMode.STANDARD,
            started_at="2025-01-15T10:30:00Z",
            agents=[root, panel],
            total_tool_calls=5,
        )

        data = original.model_dump()
        restored = CouncilActivityGraph.model_validate(data)
        assert restored.investigation_id == original.investigation_id
        assert len(restored.agents) == len(original.agents)
