"""Tests for council panel factory functions.

Validates that each panel agent is correctly configured with:
- Correct name and model
- Correct tool set from the tool registry
- Correct output_key for session state writing
- Correct output_schema for structured output
"""

from google.adk.agents import LlmAgent

from sre_agent.council.panels import (
    create_alerts_panel,
    create_logs_panel,
    create_metrics_panel,
    create_trace_panel,
)
from sre_agent.council.schemas import PanelFinding
from sre_agent.council.tool_registry import (
    ALERTS_PANEL_TOOLS,
    LOGS_PANEL_TOOLS,
    METRICS_PANEL_TOOLS,
    TRACE_PANEL_TOOLS,
)


class TestCreateTracePanel:
    """Tests for trace panel creation."""

    def test_returns_llm_agent(self) -> None:
        """Factory should return an LlmAgent instance."""
        panel = create_trace_panel()
        assert isinstance(panel, LlmAgent)

    def test_correct_name(self) -> None:
        """Trace panel should have the expected name."""
        panel = create_trace_panel()
        assert panel.name == "trace_panel"

    def test_correct_output_key(self) -> None:
        """Trace panel should write findings to 'trace_finding'."""
        panel = create_trace_panel()
        assert panel.output_key == "trace_finding"

    def test_correct_output_schema(self) -> None:
        """Trace panel should use PanelFinding as output schema."""
        panel = create_trace_panel()
        assert panel.output_schema == PanelFinding

    def test_has_tools(self) -> None:
        """Trace panel should have tools assigned."""
        panel = create_trace_panel()
        assert len(panel.tools) > 0

    def test_tool_count_matches_registry(self) -> None:
        """Trace panel tools should match the registry definition."""
        panel = create_trace_panel()
        assert len(panel.tools) == len(TRACE_PANEL_TOOLS)

    def test_creates_independent_instances(self) -> None:
        """Each call should create a new independent agent."""
        panel1 = create_trace_panel()
        panel2 = create_trace_panel()
        assert panel1 is not panel2


class TestCreateMetricsPanel:
    """Tests for metrics panel creation."""

    def test_returns_llm_agent(self) -> None:
        """Factory should return an LlmAgent instance."""
        panel = create_metrics_panel()
        assert isinstance(panel, LlmAgent)

    def test_correct_name(self) -> None:
        """Metrics panel should have the expected name."""
        panel = create_metrics_panel()
        assert panel.name == "metrics_panel"

    def test_correct_output_key(self) -> None:
        """Metrics panel should write findings to 'metrics_finding'."""
        panel = create_metrics_panel()
        assert panel.output_key == "metrics_finding"

    def test_correct_output_schema(self) -> None:
        """Metrics panel should use PanelFinding as output schema."""
        panel = create_metrics_panel()
        assert panel.output_schema == PanelFinding

    def test_tool_count_matches_registry(self) -> None:
        """Metrics panel tools should match the registry definition."""
        panel = create_metrics_panel()
        assert len(panel.tools) == len(METRICS_PANEL_TOOLS)


class TestCreateLogsPanel:
    """Tests for logs panel creation."""

    def test_returns_llm_agent(self) -> None:
        """Factory should return an LlmAgent instance."""
        panel = create_logs_panel()
        assert isinstance(panel, LlmAgent)

    def test_correct_name(self) -> None:
        """Logs panel should have the expected name."""
        panel = create_logs_panel()
        assert panel.name == "logs_panel"

    def test_correct_output_key(self) -> None:
        """Logs panel should write findings to 'logs_finding'."""
        panel = create_logs_panel()
        assert panel.output_key == "logs_finding"

    def test_correct_output_schema(self) -> None:
        """Logs panel should use PanelFinding as output schema."""
        panel = create_logs_panel()
        assert panel.output_schema == PanelFinding

    def test_tool_count_matches_registry(self) -> None:
        """Logs panel tools should match the registry definition."""
        panel = create_logs_panel()
        assert len(panel.tools) == len(LOGS_PANEL_TOOLS)


class TestCreateAlertsPanel:
    """Tests for alerts panel creation."""

    def test_returns_llm_agent(self) -> None:
        """Factory should return an LlmAgent instance."""
        panel = create_alerts_panel()
        assert isinstance(panel, LlmAgent)

    def test_correct_name(self) -> None:
        """Alerts panel should have the expected name."""
        panel = create_alerts_panel()
        assert panel.name == "alerts_panel"

    def test_correct_output_key(self) -> None:
        """Alerts panel should write findings to 'alerts_finding'."""
        panel = create_alerts_panel()
        assert panel.output_key == "alerts_finding"

    def test_correct_output_schema(self) -> None:
        """Alerts panel should use PanelFinding as output schema."""
        panel = create_alerts_panel()
        assert panel.output_schema == PanelFinding

    def test_tool_count_matches_registry(self) -> None:
        """Alerts panel tools should match the registry definition."""
        panel = create_alerts_panel()
        assert len(panel.tools) == len(ALERTS_PANEL_TOOLS)


class TestPanelUniqueness:
    """Tests for panel agent differentiation."""

    def test_different_output_keys(self) -> None:
        """All panels should have different output keys."""
        trace = create_trace_panel()
        metrics = create_metrics_panel()
        logs = create_logs_panel()
        alerts = create_alerts_panel()
        keys = {
            trace.output_key,
            metrics.output_key,
            logs.output_key,
            alerts.output_key,
        }
        assert len(keys) == 4

    def test_different_names(self) -> None:
        """All panels should have different names."""
        trace = create_trace_panel()
        metrics = create_metrics_panel()
        logs = create_logs_panel()
        alerts = create_alerts_panel()
        names = {trace.name, metrics.name, logs.name, alerts.name}
        assert len(names) == 4
