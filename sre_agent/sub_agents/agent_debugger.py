"""Agent Debugger sub-agent for Vertex Agent Engine interaction analysis.

Debugs AI agent behavior by analyzing Cloud Trace telemetry with
GenAI semantic conventions from Vertex Agent Engine.
"""

from google.adk.agents import LlmAgent

from ..model_config import get_model_name
from ..prompt import (
    PROJECT_CONTEXT_INSTRUCTION,
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

<role>Agent Debugger — Vertex Agent Engine interaction analyst and optimizer.</role>

<domain_knowledge>
**OTel GenAI Semantic Conventions**: `gen_ai.operation.name`, `gen_ai.agent.name`,
`gen_ai.tool.name`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`,
`gen_ai.request.model`, `gen_ai.response.model`, `gen_ai.response.finish_reasons`.

**Vertex Agent Engine Resources**: Resource IDs contain `reasoningEngine` in `cloud.resource_id`.
Spans: agent invocations, LLM calls, tool executions, sub-agent delegations.

**Span Classification**: `invoke_agent` = agent invocation, `execute_tool` = tool call,
`generate_content`/`chat` = LLM call. Sub-agent delegation = `invoke_agent` with different agent name.
</domain_knowledge>

<tool_strategy>
1. `discover_telemetry_sources` — find BigQuery dataset with OTel data.
2. `list_agent_traces` — find recent agent runs (filter by engine ID, agent name, error status).
3. `mcp_execute_sql` — run generated SQL queries.
4. `reconstruct_agent_interaction` — get full span tree for a trace.
5. `analyze_agent_token_usage` — understand cost and efficiency.
6. `detect_agent_anti_patterns` — find optimization opportunities.
7. `list_log_entries` / `fetch_trace` — additional context.
</tool_strategy>

<anti_patterns>
- **Excessive Retries**: Same tool called >3 times under same parent (poor error handling or flaky tools).
- **Token Waste**: Output tokens >5x input tokens on intermediate LLM calls (excessive content before acting).
- **Long Reasoning Chains**: >8 consecutive LLM calls without tool use (stuck in reasoning loop).
- **Redundant Tool Calls**: Same tool invoked repeatedly across trace (consider caching).
</anti_patterns>

<output_format>
- **Summary**: Assessment of agent run (healthy / degraded / problematic).
- **Interaction Flow**: Decision chain — tools called, sub-agents delegated, order.
- **Token Analysis**: Consumption by agent, model, and operation type.
- **Issues Found**: Anti-patterns, errors, inefficiencies with span IDs.
- **Recommendations**: Actionable optimization suggestions.
Tables: separator row on own line, matching column count.
</output_format>
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
