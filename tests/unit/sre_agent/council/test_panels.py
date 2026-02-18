"""Tests for council panel factory functions.

Validates that each panel agent is correctly configured with:
- Correct name and model
- Correct tool set from the tool registry
- Correct output_key for session state writing
- Correct output_schema for structured output
"""

from typing import Any

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


class TestPanelCompletionCallback:
    """Tests for the _make_panel_completion_callback factory."""

    def _make_ctx(self, state: dict) -> "Any":
        from unittest.mock import MagicMock

        ctx = MagicMock()
        ctx.state = state
        return ctx

    def test_returns_callable(self) -> None:
        from sre_agent.council.panels import _make_panel_completion_callback

        cb = _make_panel_completion_callback("trace", "trace_finding")
        assert callable(cb)

    def test_returns_none_when_finding_absent(self) -> None:
        from unittest.mock import MagicMock

        from sre_agent.council.panels import _make_panel_completion_callback

        cb = _make_panel_completion_callback("trace", "trace_finding")
        ctx = self._make_ctx({})
        result = cb(ctx, MagicMock())
        assert result is None

    def test_writes_completion_to_state(self) -> None:
        import json
        from unittest.mock import MagicMock

        from sre_agent.council.panels import _make_panel_completion_callback
        from sre_agent.council.state import PANEL_COMPLETIONS

        finding = {
            "panel": "trace",
            "summary": "High latency detected",
            "severity": "warning",
            "confidence": 0.85,
            "evidence": [],
            "recommended_actions": [],
        }
        state: dict = {"trace_finding": json.dumps(finding)}
        ctx = self._make_ctx(state)
        cb = _make_panel_completion_callback("trace", "trace_finding")
        cb(ctx, MagicMock())
        assert PANEL_COMPLETIONS in ctx.state
        completions = ctx.state[PANEL_COMPLETIONS]
        assert "trace" in completions
        assert completions["trace"]["severity"] == "warning"
        assert completions["trace"]["confidence"] == 0.85
        assert "High latency" in completions["trace"]["summary"]

    def test_does_not_raise_on_malformed_json(self) -> None:
        from unittest.mock import MagicMock

        from sre_agent.council.panels import _make_panel_completion_callback

        state: dict = {"trace_finding": "NOT_VALID_JSON{{{"}
        ctx = self._make_ctx(state)
        cb = _make_panel_completion_callback("trace", "trace_finding")
        cb(ctx, MagicMock())

    def test_does_not_raise_on_exception(self) -> None:
        from unittest.mock import MagicMock

        from sre_agent.council.panels import _make_panel_completion_callback

        ctx = MagicMock()
        ctx.state = MagicMock(side_effect=RuntimeError("boom"))
        cb = _make_panel_completion_callback("trace", "trace_finding")
        cb(ctx, MagicMock())


class TestPanelOutputKeys:
    """Tests that panels use typed state constants for output_key."""

    def test_trace_panel_output_key(self) -> None:
        from sre_agent.council.panels import create_trace_panel
        from sre_agent.council.state import TRACE_FINDING

        assert create_trace_panel().output_key == TRACE_FINDING

    def test_metrics_panel_output_key(self) -> None:
        from sre_agent.council.panels import create_metrics_panel
        from sre_agent.council.state import METRICS_FINDING

        assert create_metrics_panel().output_key == METRICS_FINDING

    def test_logs_panel_output_key(self) -> None:
        from sre_agent.council.panels import create_logs_panel
        from sre_agent.council.state import LOGS_FINDING

        assert create_logs_panel().output_key == LOGS_FINDING

    def test_alerts_panel_output_key(self) -> None:
        from sre_agent.council.panels import create_alerts_panel
        from sre_agent.council.state import ALERTS_FINDING

        assert create_alerts_panel().output_key == ALERTS_FINDING

    def test_data_panel_output_key(self) -> None:
        from sre_agent.council.panels import create_data_panel
        from sre_agent.council.state import DATA_FINDING

        assert create_data_panel().output_key == DATA_FINDING


class TestPanelAfterAgentCallbacks:
    """Tests that all panels have after_agent_callback set."""

    def test_trace_panel_has_after_agent_callback(self) -> None:
        from sre_agent.council.panels import create_trace_panel

        assert create_trace_panel().after_agent_callback is not None

    def test_metrics_panel_has_after_agent_callback(self) -> None:
        from sre_agent.council.panels import create_metrics_panel

        assert create_metrics_panel().after_agent_callback is not None

    def test_logs_panel_has_after_agent_callback(self) -> None:
        from sre_agent.council.panels import create_logs_panel

        assert create_logs_panel().after_agent_callback is not None

    def test_alerts_panel_has_after_agent_callback(self) -> None:
        from sre_agent.council.panels import create_alerts_panel

        assert create_alerts_panel().after_agent_callback is not None

    def test_data_panel_has_after_agent_callback(self) -> None:
        from sre_agent.council.panels import create_data_panel

        assert create_data_panel().after_agent_callback is not None
