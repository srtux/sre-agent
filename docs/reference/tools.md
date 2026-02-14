# Tools & Analysis Guide

The SRE Agent's power comes from its massive "Superpower" catalog of specialized tools. This document categorizes these capabilities and provides guidelines for extending the system.

## Tool Categories

### 1. Observability (Core Pixels)
Direct wrappers around GCP APIs for raw data retrieval.
- `fetch_trace`: Retrieve full span JSON.
- `list_log_entries`: Filtered log fetching.
- `list_time_series`: Raw metric retrieval.

### 2. SRE Analysis (The Brain)
High-level tools that perform multi-step analysis or statistical processing.
- `analyze_critical_path`: Calculates which spans determine the total duration.
- `extract_log_patterns`: Clusters millions of log lines into meaningful patterns using the Drain3 algorithm.
- `detect_metric_anomalies`: Uses seasonality and z-scores to identify statistical outliers.
- `analyze_multi_window_burn_rate`: Implements Google's multi-window alerting to distinguish between fast and slow burn rates.

### 3. BigQuery Fleet Analysis
Enables fleet-wide analysis by querying telemetry data exported to BigQuery.
- `analyze_aggregate_metrics`: Health overview of all services.
- `find_exemplar_traces`: Automatically separates "Fast" from "Slow" traces for comparison.

### 4. Cross-Signal Correlation
The "Holy Grail" of observability - linking different pillars.
- `correlate_metrics_with_traces_via_exemplars`: Jumps from a chart spike to the exact request that caused it.
- `correlate_logs_with_trace`: Injects logs into the trace timeline.
- `correlate_changes_with_incident`: Templets GCP Audit Logs to find and rank deployments/config changes by correlation score.

### 5. Remediation & Reporting
Moving from "What is wrong" to "How to fix it."
- `generate_remediation_suggestions`: Proposes GKE restarts, config changes, or rollback commands.
- `generate_postmortem`: Generates a structured, blameless Markdown postmortem based on the investigation findings.
- `synthesize_report`: Generates a high-level executive summary of the investigation.

### 6. Research (Online Intelligence)
Accessing documentation and external technical proof points.
- `search_google`: Perform web searches (default restricted to cloud.google.com).
- `fetch_web_page`: Extract readable content from documentation and forums.

---

## Tool Implementation Pattern

Every tool follows a strict implementation pattern to ensure compatibility with both the LLM and the GenUI frontend.

### 1. The `@adk_tool` Decorator
Tools must be decorated to be registered in the ADK registry.

### 2. Structured Return Type (`BaseToolResponse`)
Tools should return a consistent structure that includes:
- `status`: SUCCESS or ERROR.
- `result`: The actual analysis data.
- `metadata`: Used by the GenUI adapter to trigger specific widgets.

### 3. Argument Mapping
LLMs are sensitive to parameter naming and descriptions. SRE Agent tools use clear, descriptive arguments with detailed docstrings.

```python
@adk_tool
async def analyze_trace_patterns(
    trace_id: str,
    project_id: str | None = None
) -> BaseToolResponse:
    """Analyze a trace for known SRE anti-patterns (e.g. Circular Dependencies)."""
    # ... logic ...
```

---

## Tool Configuration Registry

The SRE Agent uses a dynamic configuration registry to manage the visibility and status of tools without requiring a full redeploy.

### Master Manifest (`sre_agent/tools/config.py`)
The `TOOL_DEFINITIONS` list is the definitive source of truth for tool metadata. Every configurable tool must have a `ToolConfig` entry here, defining its:
- **Name**: The unique identifier used by the LLM.
- **Display Name**: The human-readable name shown in the UI.
- **Category**: Helps the agent organize its "Superpower" catalog.
- **Enabled Status**: Tools can be toggled on/off at runtime via the management API.

### Registry Synchronization
Tools must be synchronized across three locations:
1. **Metadata Registry**: `sre_agent/tools/config.py` (`TOOL_DEFINITIONS`)
2. **Logic Mapping**: `sre_agent/agent.py` (`TOOL_NAME_MAP`)
3. **Availability List**: `sre_agent/agent.py` (`base_tools`)

---


## Extending the Catalog

To add a new tool:
1.  **Implement**: Write the logic in a specialized module (e.g., under `sre_agent/tools/analysis/`).
2.  **Decorate**: Use the `@adk_tool` decorator and return a `BaseToolResponse`.
3.  **Register (Metadata)**: Add a `ToolConfig` entry to `TOOL_DEFINITIONS` in `sre_agent/tools/config.py`.
4.  **Register (Logic)**: Map the tool name in `TOOL_NAME_MAP` and add the function to `base_tools` in `sre_agent/agent.py`.
5.  **Verify Sync**: Run the consistency test to ensure all registries are aligned:
    ```bash
    pytest tests/unit/sre_agent/test_tool_map_consistency.py
    ```
6.  **(Optional)**: Add a layout mapping in `genui_adapter.py` to enable a custom GenUI widget.

---
*Last verified: 2026-02-02 — Auto SRE Team*
