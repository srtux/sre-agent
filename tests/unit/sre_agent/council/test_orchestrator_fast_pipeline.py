"""Tests for the CouncilOrchestrator signal-type-aware fast pipeline.

Validates that:
- _create_fast_pipeline routes to the correct panel based on signal type
- Each signal type creates the expected panel agent
- Default signal type creates trace panel
"""

from google.adk.agents import LlmAgent

from sre_agent.council.intent_classifier import SignalType
from sre_agent.council.orchestrator import CouncilOrchestrator


class TestFastPipelineRouting:
    """Tests for signal-type-aware FAST mode panel routing."""

    def test_trace_signal_creates_trace_panel(self) -> None:
        """TRACE signal should create the trace panel."""
        orchestrator = CouncilOrchestrator(name="test")
        panel = orchestrator._create_fast_pipeline(SignalType.TRACE)
        assert isinstance(panel, LlmAgent)
        assert panel.name == "trace_panel"

    def test_metrics_signal_creates_metrics_panel(self) -> None:
        """METRICS signal should create the metrics panel."""
        orchestrator = CouncilOrchestrator(name="test")
        panel = orchestrator._create_fast_pipeline(SignalType.METRICS)
        assert isinstance(panel, LlmAgent)
        assert panel.name == "metrics_panel"

    def test_logs_signal_creates_logs_panel(self) -> None:
        """LOGS signal should create the logs panel."""
        orchestrator = CouncilOrchestrator(name="test")
        panel = orchestrator._create_fast_pipeline(SignalType.LOGS)
        assert isinstance(panel, LlmAgent)
        assert panel.name == "logs_panel"

    def test_alerts_signal_creates_alerts_panel(self) -> None:
        """ALERTS signal should create the alerts panel."""
        orchestrator = CouncilOrchestrator(name="test")
        panel = orchestrator._create_fast_pipeline(SignalType.ALERTS)
        assert isinstance(panel, LlmAgent)
        assert panel.name == "alerts_panel"

    def test_default_creates_trace_panel(self) -> None:
        """Default (no signal) should create the trace panel."""
        orchestrator = CouncilOrchestrator(name="test")
        panel = orchestrator._create_fast_pipeline()
        assert isinstance(panel, LlmAgent)
        assert panel.name == "trace_panel"

    def test_each_panel_has_output_key(self) -> None:
        """All panels created by fast pipeline should have an output_key."""
        orchestrator = CouncilOrchestrator(name="test")
        for signal_type in SignalType:
            panel = orchestrator._create_fast_pipeline(signal_type)
            assert isinstance(panel, LlmAgent)
            assert panel.output_key is not None
            assert "_finding" in panel.output_key

    def test_each_panel_has_tools(self) -> None:
        """All panels should have at least one tool."""
        orchestrator = CouncilOrchestrator(name="test")
        for signal_type in SignalType:
            panel = orchestrator._create_fast_pipeline(signal_type)
            assert isinstance(panel, LlmAgent)
            assert len(panel.tools) > 0
