"""Root Cause Analysis Sub-Agent.

This module consolidates the "Deep Dive" agents (Causality, Impact, Change)
into a single "Root Cause Analyst". This agent is responsible for the final
synthesis of why an incident occurred.
"""

from google.adk.agents import LlmAgent

# OPT-4: Import shared tool set from council/tool_registry (single source of truth)
from ..council.tool_registry import ROOT_CAUSE_ANALYST_TOOLS

# Initialize environment (shared across sub-agents)
from ..model_config import get_model_name
from ..prompt import (
    PROJECT_CONTEXT_INSTRUCTION,
    REACT_PATTERN_INSTRUCTION,
    STRICT_ENGLISH_INSTRUCTION,
)

# Initialize environment (shared across sub-agents)
from ._init_env import init_sub_agent_env

init_sub_agent_env()

# =============================================================================
# Prompts
# =============================================================================

ROOT_CAUSE_ANALYST_PROMPT = f"""
{STRICT_ENGLISH_INSTRUCTION}
{PROJECT_CONTEXT_INSTRUCTION}
{REACT_PATTERN_INSTRUCTION}

<role>Root Cause Analyst — multi-signal synthesis for causality, impact, and change detection.</role>

<objective>
Synthesize Traces, Logs, Metrics, and Changes to identify the root cause.
Answer: WHAT happened, WHO/WHAT changed, and HOW BAD is the impact.
</objective>

<tool_strategy>
1. **Causality**: `perform_causal_analysis` — identify the specific span/service responsible.
2. **Correlate**: `build_cross_signal_timeline` or `correlate_logs_with_trace` — confirm with other signals.
3. **Changes**: `detect_trend_changes` for timing, then `list_log_entries` (search "UpdateService", "Deploy").
4. **Blast Radius**: `analyze_upstream_downstream_impact` — identify affected downstream services.
5. **Remediation**: After root cause, call `generate_remediation_suggestions` and `get_gcloud_commands`.
</tool_strategy>

<output_format>
- **Root Cause**: The trigger (e.g., "Deployment v2.3 caused retry storm in Service A").
- **Evidence**: Trace, Log, and Metric data supporting the conclusion.
- **Impact**: Number and names of affected services.
- **Recommended Actions**: Specific remediation steps.
Tables: separator row on own line, matching column count.
</output_format>
"""

# =============================================================================
# Sub-Agent Definition
# =============================================================================

root_cause_analyst = LlmAgent(
    name="root_cause_analyst",
    model=get_model_name("deep"),
    description="""Root Cause Analyst - Synthesizes findings to find the root cause, impact, and triggers.

Capabilities:
- **Causality**: Correlates across signals (Trace + Log + Metric).
- **Change Detection**: Correlates anomalies with deployments/config changes.
- **Impact Analysis**: Assesses upstream/downstream blast radius.

Tools: perform_causal_analysis, build_cross_signal_timeline, detect_trend_changes

Use when: You need to know WHY it happened, WHO changed it, and HOW BAD it is.""",
    instruction=ROOT_CAUSE_ANALYST_PROMPT,
    tools=list(ROOT_CAUSE_ANALYST_TOOLS),  # OPT-4: shared tool set from tool_registry
)
