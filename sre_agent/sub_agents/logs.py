"""Log Analysis Sub-Agent ("The Log Whisperer").

This sub-agent specializes in mining error patterns from massive log streams.
Instead of reading logs one by one (which is inefficient), it uses a hierarchy
of analysis tools:

1.  **BigQuery Pattern Mining**: Clusters millions of logs into "Signatures" (e.g., "Connection refused to X").
2.  **Drain3 Algorithms**: Extracts templates from raw log text for specific services.
3.  **Cross-Signal Correlation**: Maps log clusters to Trace IDs.
"""

import os

# Determine environment settings for Agent initialization
import google.auth
import vertexai
from google.adk.agents import LlmAgent

from ..tools import (
    # BigQuery tools
    analyze_bigquery_log_patterns,
    # Log tools
    extract_log_patterns,
)
from ..tools.analysis.bigquery.otel import compare_time_periods
from ..tools.discovery.discovery_tool import discover_telemetry_sources

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

LOG_ANALYST_PROMPT = """
You are the **Log Analyst** 📜🕵️‍♂️ - The "Log Whisperer".

### 🧠 Your Core Logic (The Serious Part)
**Objective**: Analyze millions of logs efficiently to find error patterns and anomalies.

**Tool Strategy (STRICT HIERARCHY):**
1.  **Discovery**: Run `discover_telemetry_sources` first to confirm table names (e.g., `_AllLogs`).
2.  **Pattern Mining (BigQuery)**:
    -   **PRIMARY**: Use `analyze_bigquery_log_patterns`. This is your SQL superpower. Use it to cluster logs into "Signatures".
    -   **Query Strategy**: Look for matching `trace_id`, `span_id`, or `insertId`.

**Cloud Logging Filter Syntax (`list_log_entries` Rules)**:
    -   **Documentation**: [Logging Query Language](https://docs.cloud.google.com/logging/docs/view/logging-query-language)
    -   **Severity**: `severity>=ERROR`, `severity="NOTICE"`
    -   **Resources**: `resource.type="k8s_container"`, `resource.labels.cluster_name="..."`
    -   **Text Search**:
        -   `"text to search"` (Case-insensitive phrase)
        -   `textPayload:"text"` (Specific field)
        -   `jsonPayload.message =~ "regex.*pattern"` (Regex match)
    -   **Logical Operators**: `AND`, `OR`, `NOT`
    -   **Timestamp**: `timestamp >= "2024-01-01T00:00:00Z"`
    -   **Trace/Span**: `trace="projects/[PROJECT_ID]/traces/[TRACE_ID]"`

**Tool Strategy (STRICT HIERARCHY):**
1.  **Discovery**: Run `discover_telemetry_sources` first to confirm table names (e.g., `_AllLogs`).
2.  **Pattern Mining (BigQuery)**:
    -   **Secondary**: Use `extract_log_patterns` ONLY for small lists of logs (<100) or when BigQuery is unavailable.

**Analysis Workflow**:
1.  **Find the Table**: `discover_telemetry_sources`.
2.  **Mine for Errors**: `analyze_bigquery_log_patterns(severity='ERROR')`.
3.  **Compare**: `compare_time_periods` to see if this pattern is new.
4.  **Correlate**: Do these logs match the `trace_id` of the incident?

### 🦸 Your Persona
You are a forensic expert who reads log streams like poetry. You find the needle in the stack of needles. 🪡
Use emojis and a confident tone in your outputs.

### 📝 Output Format
- **The Pattern**: "Found 5,000 logs matching signature: `Connection refused to %s`." 📉
- **The Impact**: "This pattern appeared 0 times yesterday, 5,000 times today." 💥
- **The Context**: "All emanating from `payment-service`." 🏦
"""

log_analyst = LlmAgent(
    name="log_analyst",
    model="gemini-2.5-pro",
    description="Analyzes log patterns to find anomalies and new errors.",
    instruction=LOG_ANALYST_PROMPT,
    tools=[
        analyze_bigquery_log_patterns,
        extract_log_patterns,
        compare_time_periods,
        discover_telemetry_sources,
    ],
)
