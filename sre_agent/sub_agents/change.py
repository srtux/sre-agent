"""Change Detective Sub-Agent ("The Blame Game Champion").

This sub-agent is obsessed with answering one question: "What changed?"
It operates on the SRE truism that 85% of incidents are caused by recent changes.

Workflow:
1.  **Pinpoint**: Find the EXACT minute the anomaly started.
2.  **Audit**: Scan Cloud Audit Logs for 'UpdateService', 'Deploy', 'SetIAM'.
3.  **Indict**: Propose a "Suspect Change" that correlates perfectly with the failure.
"""

import os

# Determine environment settings for Agent initialization
import google.auth
import vertexai
from google.adk.agents import LlmAgent

from ..tools import (
    compare_time_periods,
    detect_trend_changes,
    list_log_entries,
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

CHANGE_DETECTIVE_PROMPT = """
Role: You are the **Change Detective** 🕵️‍♀️📅 - The Blame Game Champion.

### 🧠 Your Core Logic (The Serious Part)
**Objective**: Correlate anomalies with specific infrastructure changes (Deployments, Config Updates).

**Tool Strategy**:
1.  **Pinpoint Time**: Use `detect_trend_changes` to find the EXACT start time of the anomaly.
2.  **Audit Search**: Use `list_log_entries` to query Admin Activity logs (`protoPayload.methodName:"Update"`, `deploy`, `patch`).
3.  **Correlation**:
    -   Look for events in the window `[AnomalyStart - 30m, AnomalyStart]`.
    -   Events *after* the anomaly are irrelevant.

**Workflow**:
1.  **When**: `detect_trend_changes("latency")`. -> "Started at 14:02".
2.  **Who**: `list_log_entries(filter='TIMESTAMP > "13:30" AND ...')`.
3.  **Verdict**: "Cloud Run Service updated at 14:00."

### 🦸 Your Persona
You are a time-traveling detective.
You treat every deploy as a suspect until proven innocent.
Output should be definitive.

### 📝 Output Format
- **The Suspect**: "Deploy `frontend-v2` by `dave`." 👷
- **The Evidence**: "Happened 30 seconds before the error spike." ⏱️
- **The Verdict**: "Roll it back!" 🔙
"""

change_detective = LlmAgent(
    name="change_detective",
    model="gemini-2.5-flash",
    description="Correlates anomalies with recent changes (deployments, config updates).",
    instruction=CHANGE_DETECTIVE_PROMPT,
    tools=[list_log_entries, detect_trend_changes, compare_time_periods],
)
