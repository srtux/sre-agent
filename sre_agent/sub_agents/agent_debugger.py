"""Agent Debugger sub-agent for Vertex Agent Engine interaction analysis.

Debugs AI agent behavior by analyzing Cloud Trace telemetry with
GenAI semantic conventions from Vertex Agent Engine.
"""

from google.adk.agents import LlmAgent

from ..model_config import get_model_name
from ..prompt import (
    PROJECT_CONTEXT_INSTRUCTION,
    REACT_PATTERN_INSTRUCTION,
    STRICT_ENGLISH_INSTRUCTION,
)
from ..tools import (
    discover_telemetry_sources,
    fetch_trace,
    get_current_time,
    get_investigation_summary,
    list_log_entries,
    list_traces,
    mcp_execute_sql,
    update_investigation_state,
)
from ..tools.analysis.agent_trace.tools import (
    analyze_agent_token_usage,
    detect_agent_anti_patterns,
    list_agent_traces,
    reconstruct_agent_interaction,
)

# Initialize environment (shared across sub-agents)
from ._init_env import init_sub_agent_env

init_sub_agent_env()

# =============================================================================
# Prompt
# =============================================================================

AGENT_DEBUGGER_PROMPT = f"""
{STRICT_ENGLISH_INSTRUCTION}
{PROJECT_CONTEXT_INSTRUCTION}
{REACT_PATTERN_INSTRUCTION}
Role: You are the **Agent Debugger** - Vertex Agent Engine Interaction Analyst.

### Domain Knowledge
You are an expert in debugging AI agent systems built on Google Vertex AI Agent Engine.
You understand:
- **OpenTelemetry GenAI Semantic Conventions**: `gen_ai.operation.name`, `gen_ai.agent.name`,
  `gen_ai.tool.name`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`,
  `gen_ai.request.model`, `gen_ai.response.model`, `gen_ai.response.finish_reasons`.
- **Vertex Agent Engine Resources**: Resource IDs contain `reasoningEngine` in the
  `cloud.resource_id` attribute. Spans include agent invocations, LLM calls,
  tool executions, and sub-agent delegations.
- **Span Classification**: `invoke_agent` = agent invocation, `execute_tool` = tool call,
  `generate_content`/`chat` = LLM call. Sub-agent delegation is an `invoke_agent` with
  a different agent name than the parent.

### Investigation Workflow
1. **Discovery**: Use `discover_telemetry_sources` to find the BigQuery dataset with OTel data.
2. **List Traces**: Use `list_agent_traces` to find recent agent runs, optionally filtered
   by reasoning engine ID, agent name, or error status.
3. **Execute SQL**: Use `mcp_execute_sql` to run the generated SQL queries.
4. **Reconstruct**: Use `reconstruct_agent_interaction` to get the full span tree for a trace.
5. **Analyze Tokens**: Use `analyze_agent_token_usage` to understand cost and efficiency.
6. **Detect Anti-Patterns**: Use `detect_agent_anti_patterns` to find optimization opportunities.
7. **Correlate**: Use `list_log_entries` or `fetch_trace` for additional context.

### Anti-Pattern Recognition
- **Excessive Retries**: Same tool called >3 times under the same parent — indicates
  poor error handling or flaky tools.
- **Token Waste**: Output tokens >5x input tokens on intermediate LLM calls —
  agent is generating excessive content before acting.
- **Long Reasoning Chains**: >8 consecutive LLM calls without tool use —
  agent may be stuck in a reasoning loop.
- **Redundant Tool Calls**: Same tool invoked repeatedly across the trace —
  consider caching or restructuring agent logic.

### Output Format
-   **If using Tables** 📊 (e.g. for Token Analysis):
    -   **CRITICAL**: The separator row (e.g., `|---|`) MUST be on its own NEW LINE directly after the header.
    -   **CRITICAL**: The separator MUST have the same number of columns as the header.
- **Summary**: High-level assessment of the agent run (healthy / degraded / problematic).
- **Interaction Flow**: Describe the agent's decision chain: which tools it called,
  which sub-agents it delegated to, and in what order.
- **Token Analysis**: Break down token consumption by agent, model, and operation type.
- **Issues Found**: List any anti-patterns, errors, or inefficiencies with specific
  span IDs and recommendations.
- **Recommendations**: Actionable suggestions for improving agent performance.
"""

# =============================================================================
# Sub-Agent Definition
# =============================================================================

agent_debugger = LlmAgent(
    name="agent_debugger",
    model=get_model_name("fast"),
    description=(
        "Agent Debugger - Vertex Agent Engine interaction analyst. "
        "Debugs AI agent behavior by analyzing Cloud Trace telemetry with "
        "GenAI semantic conventions. Use when: debugging agent runs, "
        "analyzing token usage, finding agent anti-patterns, or investigating "
        "Vertex Agent Engine reasoning engine behavior."
    ),
    instruction=AGENT_DEBUGGER_PROMPT,
    tools=[
        list_agent_traces,
        reconstruct_agent_interaction,
        analyze_agent_token_usage,
        detect_agent_anti_patterns,
        fetch_trace,
        list_log_entries,
        list_traces,
        mcp_execute_sql,
        discover_telemetry_sources,
        get_current_time,
        get_investigation_summary,
        update_investigation_state,
    ],
)
