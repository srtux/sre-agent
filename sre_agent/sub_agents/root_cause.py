"""Root Cause Analysis Sub-Agent.

This module consolidates the "Deep Dive" agents (Causality, Impact, Change)
into a single "Root Cause Analyst". This agent is responsible for the final
synthesis of why an incident occurred.
"""

import os

# Determine environment settings for Agent initialization
import google.auth
import vertexai
from google.adk.agents import LlmAgent

from ..tools import (
    analyze_upstream_downstream_impact,
    build_cross_signal_timeline,
    build_service_dependency_graph,
    compare_time_periods,
    correlate_logs_with_trace,
    correlate_trace_with_metrics,
    detect_trend_changes,
    fetch_trace,
    list_log_entries,
    perform_causal_analysis,
)

project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT_ID")

# Fallback: Try to get project from Application Default Credentials
if not project_id:
    try:
        _, project_id = google.auth.default()
        if project_id:
            # Set env vars for downstream tools
            os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
            os.environ["GCP_PROJECT_ID"] = project_id
    except Exception:
        pass

location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "true").lower() == "true"

if use_vertex and project_id:
    try:
        vertexai.init(project=project_id, location=location)
    except Exception:
        pass

# =============================================================================
# Prompts
# =============================================================================

ROOT_CAUSE_ANALYST_PROMPT = """
Role: You are the **Root Cause Analyst** 🕵️‍♂️🧩 - The Investigator.

You combine the skills of a Causality Expert, Impact Assessor, and Change Detective.
Your job is to take the findings from Triage (Trace Analysis) and determine the Ultimate Root Cause.

### 🧠 Your Core Logic
**Objective**: Synthesize Traces, Logs, Metrics, and Changes to find the "Smoking Gun".

**Investigation Steps**:
1.  **Causality**: Use `perform_causal_analysis` to find the specific span/service responsible for latency/errors.
2.  **Correlate**: Use `build_cross_signal_timeline` or `correlate_logs_with_trace` to see if logs/metrics confirm the theory.
3.  **The "Who" (Changes)**: Use `detect_trend_changes` to find WHEN it started, then check for deployments/config changes using `list_log_entries` (look for "UpdateService", "Deploy").
4.  **The "Blast Radius"**: Use `analyze_upstream_downstream_impact` to see who else is affected.

### 🦸 Your Persona
You are a seasoned SRE detective. You don't guess; you deduce.
You are looking for the "First Domino".

### 📝 Output Format
-   **Root Cause**: "Deployment v2.3 caused a retry storm in Service A." 🎯
-   **Evidence**:
    -   Trace: "Service A latency +500ms."
    -   Log: "Connection Pool Exhausted."
    -   Change: "Deploy at 14:00."
-   **Impact**: "5 downstream services affected." 🌋
-   **Recommendation**: "Rollback v2.3 immediately." 🔙
"""

# =============================================================================
# Sub-Agent Definition
# =============================================================================

root_cause_analyst = LlmAgent(
    name="root_cause_analyst",
    model="gemini-2.5-pro",
    description="""Root Cause Analyst - Synthesizes findings to find the root cause, impact, and triggers.

Capabilities:
- **Causality**: Correlates across signals (Trace + Log + Metric).
- **Change Detection**: Correlates anomalies with deployments/config changes.
- **Impact Analysis**: Assesses upstream/downstream blast radius.

Tools: perform_causal_analysis, build_cross_signal_timeline, detect_trend_changes

Use when: You need to know WHY it happened, WHO changed it, and HOW BAD it is.""",
    instruction=ROOT_CAUSE_ANALYST_PROMPT,
    tools=[
        perform_causal_analysis,
        build_cross_signal_timeline,
        correlate_logs_with_trace,
        correlate_trace_with_metrics,
        analyze_upstream_downstream_impact,
        build_service_dependency_graph,
        detect_trend_changes,
        list_log_entries,
        compare_time_periods,
        fetch_trace,
    ],
)
