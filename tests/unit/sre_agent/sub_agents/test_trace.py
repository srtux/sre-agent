"""Unit tests for the trace sub-agent configuration.

Tests for trace_analyst and aggregate_analyzer LlmAgent instances.
"""

from google.adk.agents import LlmAgent

from sre_agent.sub_agents.trace import (
    AGGREGATE_ANALYZER_PROMPT,
    TRACE_ANALYST_PROMPT,
    aggregate_analyzer,
    trace_analyst,
)


class TestTraceAnalystAgent:
    """Tests for the trace_analyst LlmAgent instance."""

    def test_trace_analyst_is_llm_agent(self):
        """Verify trace_analyst is an LlmAgent instance."""
        assert isinstance(trace_analyst, LlmAgent)

    def test_trace_analyst_has_name(self):
        """Verify trace_analyst has a non-empty name."""
        assert trace_analyst.name
        assert trace_analyst.name == "trace_analyst"

    def test_trace_analyst_has_model(self):
        """Verify trace_analyst has a model configured."""
        assert trace_analyst.model is not None
        model_name = (
            trace_analyst.model
            if isinstance(trace_analyst.model, str)
            else str(trace_analyst.model)
        )
        assert len(model_name) > 0

    def test_trace_analyst_has_tools(self):
        """Verify trace_analyst has a non-empty tools list."""
        assert trace_analyst.tools
        assert len(trace_analyst.tools) > 0

    def test_trace_analyst_has_description(self):
        """Verify trace_analyst has a description."""
        assert trace_analyst.description
        assert "trace" in trace_analyst.description.lower()

    def test_trace_analyst_tools_include_trace_tools(self):
        """Verify trace_analyst tools include trace analysis tools."""
        tool_names = [
            getattr(t, "name", getattr(t, "__name__", str(t)))
            for t in trace_analyst.tools
        ]
        assert any("trace" in name.lower() for name in tool_names)


class TestAggregateAnalyzerAgent:
    """Tests for the aggregate_analyzer LlmAgent instance."""

    def test_aggregate_analyzer_is_llm_agent(self):
        """Verify aggregate_analyzer is an LlmAgent instance."""
        assert isinstance(aggregate_analyzer, LlmAgent)

    def test_aggregate_analyzer_has_name(self):
        """Verify aggregate_analyzer has a non-empty name."""
        assert aggregate_analyzer.name
        assert aggregate_analyzer.name == "aggregate_analyzer"

    def test_aggregate_analyzer_has_model(self):
        """Verify aggregate_analyzer has a model configured."""
        assert aggregate_analyzer.model is not None
        model_name = (
            aggregate_analyzer.model
            if isinstance(aggregate_analyzer.model, str)
            else str(aggregate_analyzer.model)
        )
        assert len(model_name) > 0

    def test_aggregate_analyzer_has_tools(self):
        """Verify aggregate_analyzer has a non-empty tools list."""
        assert aggregate_analyzer.tools
        assert len(aggregate_analyzer.tools) > 0

    def test_aggregate_analyzer_has_description(self):
        """Verify aggregate_analyzer has a description."""
        assert aggregate_analyzer.description
        assert len(aggregate_analyzer.description) > 0

    def test_aggregate_analyzer_tools_include_bigquery(self):
        """Verify aggregate_analyzer tools include BigQuery tools."""
        tool_names = [
            getattr(t, "name", getattr(t, "__name__", str(t)))
            for t in aggregate_analyzer.tools
        ]
        assert any(
            "sql" in name.lower()
            or "bigquery" in name.lower()
            or "aggregate" in name.lower()
            for name in tool_names
        )


class TestTraceAnalystPrompt:
    """Tests for the TRACE_ANALYST_PROMPT constant."""

    def test_prompt_is_non_empty_string(self):
        """Verify TRACE_ANALYST_PROMPT is a non-empty string."""
        assert isinstance(TRACE_ANALYST_PROMPT, str)
        assert len(TRACE_ANALYST_PROMPT) > 100

    def test_prompt_contains_role(self):
        """Verify prompt defines the agent role."""
        assert "<role>" in TRACE_ANALYST_PROMPT
        assert "Trace Analyst" in TRACE_ANALYST_PROMPT

    def test_prompt_contains_tool_strategy(self):
        """Verify prompt includes tool usage strategy."""
        assert "<tool_strategy>" in TRACE_ANALYST_PROMPT
        assert "analyze_trace_comprehensive" in TRACE_ANALYST_PROMPT

    def test_prompt_contains_output_format(self):
        """Verify prompt defines output format."""
        assert "<output_format>" in TRACE_ANALYST_PROMPT


class TestAggregateAnalyzerPrompt:
    """Tests for the AGGREGATE_ANALYZER_PROMPT constant."""

    def test_prompt_is_non_empty_string(self):
        """Verify AGGREGATE_ANALYZER_PROMPT is a non-empty string."""
        assert isinstance(AGGREGATE_ANALYZER_PROMPT, str)
        assert len(AGGREGATE_ANALYZER_PROMPT) > 100

    def test_prompt_contains_role(self):
        """Verify prompt defines the agent role."""
        assert "<role>" in AGGREGATE_ANALYZER_PROMPT
        assert "Data Analyst" in AGGREGATE_ANALYZER_PROMPT

    def test_prompt_contains_trace_filter_syntax(self):
        """Verify prompt includes trace filter syntax reference."""
        assert "<trace_filter_syntax>" in AGGREGATE_ANALYZER_PROMPT
        assert "latency:500ms" in AGGREGATE_ANALYZER_PROMPT

    def test_prompt_contains_output_format(self):
        """Verify prompt defines output format."""
        assert "<output_format>" in AGGREGATE_ANALYZER_PROMPT
