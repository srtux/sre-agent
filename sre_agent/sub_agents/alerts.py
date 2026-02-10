"""Alert Analyst Sub-Agent ("The First Responder").

Rapid triage of active incidents:
1. Triage: Is the house on fire? (Critical vs Info).
2. Context: Which policy triggered this?
3. Routing: Who should investigate next?
"""

from google.adk.agents import LlmAgent

# Initialize environment (shared across sub-agents)
from ..model_config import get_model_name
from ..prompt import (
    PROJECT_CONTEXT_INSTRUCTION,
    REACT_PATTERN_INSTRUCTION,
    STRICT_ENGLISH_INSTRUCTION,
)
# OPT-4: Import shared tool set from council/tool_registry (single source of truth)
from ..council.tool_registry import ALERT_ANALYST_TOOLS

# Initialize environment (shared across sub-agents)
from ._init_env import init_sub_agent_env

init_sub_agent_env()

ALERT_ANALYST_PROMPT = f"""
{STRICT_ENGLISH_INSTRUCTION}
{PROJECT_CONTEXT_INSTRUCTION}
{REACT_PATTERN_INSTRUCTION}

<role>Alert Analyst — rapid incident triage and classification specialist.</role>

<objective>Rapidly triage active alerts and link them to policies to determine severity and context.</objective>

<tool_strategy>
1. **Check Active Alerts**: Run `list_alerts` immediately. Active alerts are the priority signal.
2. **Contextualize**: Use `list_alert_policies` for policy details. Use `get_alert` for deep inspection.
3. **Discover**: Use `discover_telemetry_sources` to find related metrics/logs.
4. **Remediate**: For well-known issues (OOM, Disk Full), call `generate_remediation_suggestions` immediately.
</tool_strategy>

<workflow>
1. Triage: Are there active alerts? → 2. Policy Mapping: What was violated?
3. Severity: P1 (page) or P4 (ticket)? → 4. Handoff: Which specialist investigates next?
</workflow>

<output_format>
- **Active Alert**: Alert name, state, start time.
- **Policy**: Triggering policy and condition.
- **Recommendation**: Which specialist sub-agent should investigate deeper.
Tables: separator row on own line, matching column count.
</output_format>
"""

alert_analyst = LlmAgent(
    name="alert_analyst",
    model=get_model_name("fast"),
    description="Analyzes active alerts and incidents from Cloud Monitoring.",
    instruction=ALERT_ANALYST_PROMPT,
    tools=list(ALERT_ANALYST_TOOLS),  # OPT-4: shared tool set from tool_registry
)
