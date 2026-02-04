"""Integration tests for the council investigation pipeline.

Validates end-to-end pipeline assembly and routing logic
for all investigation modes (Fast, Standard, Debate).
"""

import os
from unittest.mock import patch

from google.adk.agents import (
    BaseAgent,
    LlmAgent,
    LoopAgent,
    ParallelAgent,
    SequentialAgent,
)

from sre_agent.council.debate import create_debate_pipeline
from sre_agent.council.intent_classifier import classify_intent
from sre_agent.council.parallel_council import create_council_pipeline
from sre_agent.council.schemas import CouncilConfig, InvestigationMode


class TestCouncilPipelineIntegration:
    """Integration tests for the full council pipeline assembly."""

    def test_standard_pipeline_full_structure(self) -> None:
        """Standard pipeline should have complete structure: ParallelAgent → Synthesizer."""
        config = CouncilConfig(mode=InvestigationMode.STANDARD)
        pipeline = create_council_pipeline(config)

        assert isinstance(pipeline, SequentialAgent)
        assert pipeline.name == "council_pipeline"

        # Stage 1: ParallelAgent with 4 panels
        parallel = pipeline.sub_agents[0]
        assert isinstance(parallel, ParallelAgent)
        panel_names = sorted(a.name for a in parallel.sub_agents)
        assert panel_names == [
            "alerts_panel",
            "logs_panel",
            "metrics_panel",
            "trace_panel",
        ]

        # Each panel should have tools and output_key
        for panel in parallel.sub_agents:
            assert isinstance(panel, LlmAgent)
            assert panel.output_key is not None
            assert panel.output_schema is not None
            assert len(panel.tools) > 0

        # Stage 2: Synthesizer
        synthesizer = pipeline.sub_agents[1]
        assert isinstance(synthesizer, LlmAgent)
        assert synthesizer.output_key == "council_synthesis"

    def test_debate_pipeline_full_structure(self) -> None:
        """Debate pipeline should have: initial panels → synthesizer → debate loop."""
        config = CouncilConfig(
            mode=InvestigationMode.DEBATE,
            max_debate_rounds=3,
            confidence_threshold=0.85,
        )
        pipeline = create_debate_pipeline(config)

        assert isinstance(pipeline, SequentialAgent)
        assert pipeline.name == "debate_pipeline"
        assert len(pipeline.sub_agents) == 3

        # Stage 1: Initial parallel panels
        initial_panels = pipeline.sub_agents[0]
        assert isinstance(initial_panels, ParallelAgent)
        assert len(initial_panels.sub_agents) == 4

        # Stage 2: Initial synthesizer
        synthesizer = pipeline.sub_agents[1]
        assert isinstance(synthesizer, LlmAgent)
        assert synthesizer.output_key == "council_synthesis"

        # Stage 3: Debate loop
        debate_loop = pipeline.sub_agents[2]
        assert isinstance(debate_loop, LoopAgent)
        assert debate_loop.max_iterations == 3
        assert debate_loop.before_agent_callback is not None

        # Loop sub-agents: critic → panels → synthesizer
        assert len(debate_loop.sub_agents) == 3
        assert debate_loop.sub_agents[0].name == "council_critic"
        assert isinstance(debate_loop.sub_agents[1], ParallelAgent)
        assert len(debate_loop.sub_agents[1].sub_agents) == 4
        assert debate_loop.sub_agents[2].name == "council_synthesizer"


class TestIntentToModeRouting:
    """Integration tests for intent → mode → pipeline routing."""

    def test_fast_intent_routes_correctly(self) -> None:
        """Fast queries should classify as FAST mode."""
        mode = classify_intent("quick status check on API")
        assert mode == InvestigationMode.FAST

    def test_standard_intent_routes_correctly(self) -> None:
        """Analysis queries should classify as STANDARD mode."""
        mode = classify_intent("analyze the latency for checkout-service")
        assert mode == InvestigationMode.STANDARD

    def test_debate_intent_routes_correctly(self) -> None:
        """Incident queries should classify as DEBATE mode."""
        mode = classify_intent("root cause of the production outage")
        assert mode == InvestigationMode.DEBATE

    def test_mode_creates_correct_pipeline(self) -> None:
        """Each mode should create the correct pipeline type."""
        for mode, expected_type in [
            (InvestigationMode.STANDARD, SequentialAgent),
            (InvestigationMode.DEBATE, SequentialAgent),
        ]:
            config = CouncilConfig(mode=mode)
            if mode == InvestigationMode.DEBATE:
                pipeline = create_debate_pipeline(config)
            else:
                pipeline = create_council_pipeline(config)
            assert isinstance(pipeline, expected_type)


class TestFeatureFlags:
    """Integration tests for feature flag behavior."""

    @patch.dict(os.environ, {"SRE_AGENT_SLIM_TOOLS": "true"})
    def test_slim_tools_reduces_count(self) -> None:
        """SRE_AGENT_SLIM_TOOLS=true should reduce tool count."""
        from sre_agent.agent import base_tools, get_enabled_base_tools, slim_tools

        tools = get_enabled_base_tools()
        assert len(tools) == len(slim_tools)
        assert len(tools) < len(base_tools)

    @patch.dict(os.environ, {"SRE_AGENT_COUNCIL_ORCHESTRATOR": "true"})
    def test_council_orchestrator_returns_base_agent(self) -> None:
        """SRE_AGENT_COUNCIL_ORCHESTRATOR=true should return CouncilOrchestrator."""
        from sre_agent.agent import create_configured_agent

        agent = create_configured_agent()
        # The agent is emojified, so check the underlying type
        assert isinstance(agent, BaseAgent)


class TestPanelToolIsolation:
    """Integration tests verifying panel tool isolation."""

    def test_trace_panel_has_trace_tools(self) -> None:
        """Trace panel should have trace-specific tools."""
        from sre_agent.council.panels import create_trace_panel

        panel = create_trace_panel()
        tool_names = {getattr(t, "__name__", str(t)) for t in panel.tools}
        assert "analyze_trace_comprehensive" in tool_names
        assert "fetch_trace" in tool_names
        # Should NOT have metrics-only tools
        assert "detect_metric_anomalies" not in tool_names

    def test_metrics_panel_has_metrics_tools(self) -> None:
        """Metrics panel should have metrics-specific tools."""
        from sre_agent.council.panels import create_metrics_panel

        panel = create_metrics_panel()
        tool_names = {getattr(t, "__name__", str(t)) for t in panel.tools}
        assert "query_promql" in tool_names
        assert "detect_metric_anomalies" in tool_names
        # Should NOT have alert-only tools
        assert "list_alerts" not in tool_names

    def test_logs_panel_has_log_tools(self) -> None:
        """Logs panel should have log-specific tools."""
        from sre_agent.council.panels import create_logs_panel

        panel = create_logs_panel()
        tool_names = {getattr(t, "__name__", str(t)) for t in panel.tools}
        assert "list_log_entries" in tool_names
        assert "analyze_bigquery_log_patterns" in tool_names
        # Should NOT have alert-only tools
        assert "list_alerts" not in tool_names
        assert "get_alert" not in tool_names

    def test_alerts_panel_has_alert_tools(self) -> None:
        """Alerts panel should have alert-specific tools."""
        from sre_agent.council.panels import create_alerts_panel

        panel = create_alerts_panel()
        tool_names = {getattr(t, "__name__", str(t)) for t in panel.tools}
        assert "list_alerts" in tool_names
        assert "list_alert_policies" in tool_names
        assert "get_alert" in tool_names
        # Should NOT have log-analysis-only tools
        assert "analyze_bigquery_log_patterns" not in tool_names
        assert "extract_log_patterns" not in tool_names
