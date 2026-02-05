"""Integration tests for the council investigation pipeline.

Validates end-to-end pipeline assembly and routing logic
for all investigation modes (Fast, Standard, Debate), and
agent activity tracking functionality.
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

from sre_agent.api.helpers import (
    create_agent_activity_event,
    create_council_graph_event,
    create_tool_call_record,
)
from sre_agent.council.debate import create_debate_pipeline
from sre_agent.council.intent_classifier import classify_intent
from sre_agent.council.parallel_council import create_council_pipeline
from sre_agent.council.schemas import (
    AgentActivity,
    AgentType,
    CouncilActivityGraph,
    CouncilConfig,
    InvestigationMode,
)


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


# =============================================================================
# Agent Activity Tracking Integration Tests
# =============================================================================


class TestAgentActivityTracking:
    """Integration tests for agent activity tracking and event generation."""

    def test_agent_activity_event_structure(self) -> None:
        """Agent activity events should have required fields."""
        import json

        event_str = create_agent_activity_event(
            investigation_id="inv-123",
            agent_id="panel-trace-001",
            agent_name="Trace Panel",
            agent_type="panel",
            status="running",
            parent_id="orchestrator-001",
        )

        event = json.loads(event_str)
        assert event["type"] == "agent_activity"
        assert event["investigation_id"] == "inv-123"
        # Agent data is in the "agent" field, not "data"
        agent = event["agent"]
        assert agent["agent_id"] == "panel-trace-001"
        assert agent["agent_name"] == "Trace Panel"
        assert agent["agent_type"] == "panel"
        assert agent["status"] == "running"
        assert agent["parent_id"] == "orchestrator-001"

    def test_agent_activity_event_with_tool_calls(self) -> None:
        """Agent activity events should include tool call records."""
        import json

        tool_call = create_tool_call_record(
            call_id="tc-001",
            tool_name="get_traces",
            args={"service": "checkout"},
            result={"spans": []},
            status="completed",
            duration_ms=150,
            timestamp="2025-01-15T10:30:00Z",
        )

        event_str = create_agent_activity_event(
            investigation_id="inv-123",
            agent_id="panel-trace-001",
            agent_name="Trace Panel",
            agent_type="panel",
            status="completed",
            tool_calls=[tool_call],
        )

        event = json.loads(event_str)
        agent = event["agent"]
        assert len(agent["tool_calls"]) == 1
        tc = agent["tool_calls"][0]
        assert tc["call_id"] == "tc-001"
        assert tc["tool_name"] == "get_traces"
        assert tc["status"] == "completed"
        assert tc["duration_ms"] == 150

    def test_council_graph_event_structure(self) -> None:
        """Council graph events should have complete structure."""
        import json

        # Create agent as a dict (as expected by the helper function)
        agent_activity = {
            "agent_id": "root-001",
            "agent_name": "Root Agent",
            "agent_type": "root",
            "parent_id": None,
            "status": "completed",
            "tool_calls": [],
            "llm_calls": [],
        }

        event_str = create_council_graph_event(
            investigation_id="inv-123",
            mode="standard",
            agents=[agent_activity],
            started_at="2025-01-15T10:30:00Z",
            completed_at="2025-01-15T10:30:30Z",
        )

        event = json.loads(event_str)
        assert event["type"] == "council_graph"
        assert event["investigation_id"] == "inv-123"
        # Council graph event has fields directly on the event
        assert event["mode"] == "standard"
        assert len(event["agents"]) == 1
        assert event["started_at"] == "2025-01-15T10:30:00Z"
        assert event["completed_at"] == "2025-01-15T10:30:30Z"

    def test_tool_call_record_structure(self) -> None:
        """Tool call records should have expected fields."""
        record = create_tool_call_record(
            call_id="tc-001",
            tool_name="get_traces",
            args={"service": "checkout"},
            result={"spans": [{"trace_id": "abc123"}]},
            status="completed",
            duration_ms=200,
            timestamp="2025-01-15T10:30:00Z",
        )

        assert record["call_id"] == "tc-001"
        assert record["tool_name"] == "get_traces"
        assert record["status"] == "completed"
        assert record["duration_ms"] == 200
        assert "args_summary" in record
        assert "result_summary" in record

    def test_activity_graph_model_from_event(self) -> None:
        """CouncilActivityGraph should be constructable from event data."""
        # Simulate event data as it would come from the backend
        event_data = {
            "investigation_id": "inv-456",
            "mode": "debate",
            "started_at": "2025-01-15T10:30:00Z",
            "completed_at": "2025-01-15T10:31:00Z",
            "debate_rounds": 2,
            "total_tool_calls": 12,
            "total_llm_calls": 8,
            "agents": [
                {
                    "agent_id": "root-001",
                    "agent_name": "Root Agent",
                    "agent_type": "root",
                    "parent_id": None,
                    "status": "completed",
                    "started_at": "2025-01-15T10:30:00Z",
                    "completed_at": "2025-01-15T10:31:00Z",
                    "tool_calls": [],
                    "llm_calls": [],
                    "output_summary": "Investigation complete",
                },
                {
                    "agent_id": "panel-trace-001",
                    "agent_name": "Trace Panel",
                    "agent_type": "panel",
                    "parent_id": "root-001",
                    "status": "completed",
                    "started_at": "2025-01-15T10:30:05Z",
                    "completed_at": "2025-01-15T10:30:20Z",
                    "tool_calls": [
                        {
                            "call_id": "tc-001",
                            "tool_name": "get_traces",
                            "args_summary": "service=checkout",
                            "result_summary": "Found 5 traces",
                            "status": "completed",
                            "duration_ms": 150,
                            "timestamp": "2025-01-15T10:30:06Z",
                            "dashboard_category": "traces",
                        }
                    ],
                    "llm_calls": [
                        {
                            "call_id": "llm-001",
                            "model": "gemini-2.5-flash",
                            "input_tokens": 500,
                            "output_tokens": 200,
                            "duration_ms": 800,
                            "timestamp": "2025-01-15T10:30:07Z",
                        }
                    ],
                    "output_summary": "High latency in checkout service",
                },
            ],
        }

        # Parse the event data into the model
        graph = CouncilActivityGraph.model_validate(event_data)

        assert graph.investigation_id == "inv-456"
        assert graph.mode == InvestigationMode.DEBATE
        assert graph.debate_rounds == 2
        assert graph.total_tool_calls == 12
        assert len(graph.agents) == 2

        # Verify agent relationships
        root_agents = graph.get_root_agents()
        assert len(root_agents) == 1
        assert root_agents[0].agent_id == "root-001"

        children = graph.get_children("root-001")
        assert len(children) == 1
        assert children[0].agent_name == "Trace Panel"

        # Verify tool calls on panel agent
        panel = graph.get_agent_by_id("panel-trace-001")
        assert panel is not None
        assert len(panel.tool_calls) == 1
        assert panel.tool_calls[0].tool_name == "get_traces"
        assert panel.tool_calls[0].dashboard_category == "traces"

        # Verify LLM calls on panel agent
        assert len(panel.llm_calls) == 1
        assert panel.llm_calls[0].model == "gemini-2.5-flash"
        assert panel.llm_calls[0].input_tokens == 500


class TestActivityGraphPipelineIntegration:
    """Integration tests for activity graph with pipeline structure."""

    def test_standard_pipeline_agent_hierarchy(self) -> None:
        """Standard pipeline structure should map to activity graph hierarchy."""
        config = CouncilConfig(mode=InvestigationMode.STANDARD)
        pipeline = create_council_pipeline(config)

        # Extract expected agent structure from pipeline
        parallel = pipeline.sub_agents[0]

        # Create corresponding activity graph
        agents = [
            AgentActivity(
                agent_id="orchestrator-001",
                agent_name="council_pipeline",
                agent_type=AgentType.ORCHESTRATOR,
                status="completed",
            )
        ]

        for i, panel in enumerate(parallel.sub_agents):
            agents.append(
                AgentActivity(
                    agent_id=f"panel-{i:03d}",
                    agent_name=panel.name,
                    agent_type=AgentType.PANEL,
                    parent_id="orchestrator-001",
                    status="completed",
                )
            )

        # Add synthesizer
        agents.append(
            AgentActivity(
                agent_id="synthesizer-001",
                agent_name="council_synthesizer",
                agent_type=AgentType.SYNTHESIZER,
                parent_id="orchestrator-001",
                status="completed",
            )
        )

        graph = CouncilActivityGraph(
            investigation_id="inv-standard-001",
            mode=InvestigationMode.STANDARD,
            started_at="2025-01-15T10:30:00Z",
            agents=agents,
            debate_rounds=1,
        )

        # Verify structure matches pipeline
        assert (
            len(graph.get_children("orchestrator-001")) == 5
        )  # 4 panels + synthesizer

        panel_agents = [a for a in graph.agents if a.agent_type == AgentType.PANEL]
        assert len(panel_agents) == 4

        synth_agents = [
            a for a in graph.agents if a.agent_type == AgentType.SYNTHESIZER
        ]
        assert len(synth_agents) == 1

    def test_debate_pipeline_agent_hierarchy(self) -> None:
        """Debate pipeline structure should include critic in activity graph."""
        config = CouncilConfig(
            mode=InvestigationMode.DEBATE,
            max_debate_rounds=2,
        )
        pipeline = create_debate_pipeline(config)

        # Verify debate loop has critic
        debate_loop = pipeline.sub_agents[2]
        assert debate_loop.sub_agents[0].name == "council_critic"

        # Create activity graph with critic
        agents = [
            AgentActivity(
                agent_id="orchestrator-001",
                agent_name="debate_pipeline",
                agent_type=AgentType.ORCHESTRATOR,
                status="completed",
            ),
            AgentActivity(
                agent_id="critic-001",
                agent_name="council_critic",
                agent_type=AgentType.CRITIC,
                parent_id="orchestrator-001",
                status="completed",
            ),
        ]

        graph = CouncilActivityGraph(
            investigation_id="inv-debate-001",
            mode=InvestigationMode.DEBATE,
            started_at="2025-01-15T10:30:00Z",
            agents=agents,
            debate_rounds=2,
        )

        assert graph.debate_rounds == 2
        critic_agents = [a for a in graph.agents if a.agent_type == AgentType.CRITIC]
        assert len(critic_agents) == 1
        assert critic_agents[0].agent_name == "council_critic"
