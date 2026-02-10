from sre_agent.sub_agents.logs import LOG_ANALYST_PROMPT
from sre_agent.sub_agents.trace import AGGREGATE_ANALYZER_PROMPT, aggregate_analyzer


def test_logs_prompt_syntax():
    """Verify that the logs prompt contains the correct query syntax instructions."""
    # Check for Logging Query Language section
    assert "<log_filter_syntax>" in LOG_ANALYST_PROMPT
    assert "severity>=ERROR" in LOG_ANALYST_PROMPT
    assert 'resource.type="k8s_container"' in LOG_ANALYST_PROMPT
    assert "jsonPayload.message =~" in LOG_ANALYST_PROMPT
    assert "logging-query-language" in LOG_ANALYST_PROMPT


def test_trace_prompt_syntax():
    """Verify that the trace prompt contains the correct filter syntax instructions."""
    # Check for Trace Filter Syntax section
    assert "<trace_filter_syntax>" in AGGREGATE_ANALYZER_PROMPT
    assert "latency:500ms" in AGGREGATE_ANALYZER_PROMPT
    assert "root:recog" in AGGREGATE_ANALYZER_PROMPT
    assert "error:true" in AGGREGATE_ANALYZER_PROMPT
    assert "trace-filters" in AGGREGATE_ANALYZER_PROMPT

    # Verify proper tool usage guidance
    assert "list_traces" in AGGREGATE_ANALYZER_PROMPT
    assert "proper filters" in AGGREGATE_ANALYZER_PROMPT


def test_trace_tools_availability():
    """Verify that list_traces is available to the aggregate analyzer."""
    tool_names = [tool.__name__ for tool in aggregate_analyzer.tools]
    assert "list_traces" in tool_names
    assert "find_exemplar_traces" in tool_names
    assert "mcp_execute_sql" in tool_names
