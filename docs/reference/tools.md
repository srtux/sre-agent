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
- `correlate_changes_with_incident`: Queries GCP Audit Logs to find and rank deployments/config changes by correlation score.

### 5. Remediation & Reporting
Moving from "What is wrong" to "How to fix it."
- `generate_remediation_suggestions`: Proposes GKE restarts, config changes, or rollback commands.
- `generate_postmortem`: Generates a structured, blameless Markdown postmortem based on the investigation findings.
- `synthesize_report`: Generates a high-level executive summary of the investigation.

### 6. Research (Online Intelligence)
Augments the agent's knowledge with up-to-date information from the web. Results are automatically saved to memory.
- `search_google`: Search Google via Custom Search JSON API. Supports site restriction (e.g., `cloud.google.com` for GCP docs only). Requires `GOOGLE_CUSTOM_SEARCH_API_KEY` and `GOOGLE_CUSTOM_SEARCH_ENGINE_ID`.
- `fetch_web_page`: Fetch a URL and extract readable text. Automatically strips HTML (scripts, styles, navigation). Supports HTML, JSON, and plain text.

See [Online Research & Self-Healing Architecture](../concepts/online_research_and_self_healing.md) for full documentation.

### 7. Memory & Self-Improvement
Tools for the agent's learning system. See [Memory Best Practices](../concepts/memory.md).
- `search_memory`: Semantic search over past findings and patterns.
- `add_finding_to_memory`: Explicitly store a discovery or insight.
- `record_tool_failure_pattern`: Share a corrected tool usage globally.
- `complete_investigation`: Mark investigation complete and learn the pattern.
- `get_recommended_investigation_strategy`: Retrieve proven tool sequences.
- `analyze_and_learn_from_traces`: Self-analyze past agent traces from BigQuery.

### 8. Agent Self-Analysis
Tools for inspecting the agent's own execution behavior.
- `list_agent_traces`: List recent agent runs from Vertex AI traces.
- `reconstruct_agent_interaction`: Rebuild the full span tree for an agent trace.
- `analyze_agent_token_usage`: Token usage breakdown by agent/model.
- `detect_agent_anti_patterns`: Find excessive retries, token waste, long chains, and redundant tool calls.

### 9. GitHub (Self-Healing)
Tools for interacting with source code repositories to fix identified root causes.
- `github_read_file`: Read contents of a specific file in the repository.
- `github_search_code`: Search for code patterns across the repository.
- `github_list_recent_commits`: List recent commits to identify recent changes.
- `github_create_pull_request`: Open a pull request with the applied fixes.

### 10. Sandbox Processing
Tools for processing large datasets in sandboxed environments to avoid context window limits.
- `summarize_metric_descriptors_in_sandbox`: Summarize metric descriptors in a sandboxed process.
- `summarize_time_series_in_sandbox`: Summarize time series data in a sandboxed process.
- `summarize_log_entries_in_sandbox`: Summarize log entries in a sandboxed process.
- `summarize_traces_in_sandbox`: Summarize trace data in a sandboxed process.
- `execute_custom_analysis_in_sandbox`: Run custom analysis code in a sandboxed process.
- `get_sandbox_status`: Check status of sandbox execution environment.

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
Tools must be synchronized across four locations:
1. **Exports**: `sre_agent/tools/__init__.py` (`__all__`)
2. **Logic Mapping**: `sre_agent/agent.py` (`TOOL_NAME_MAP`)
3. **Availability List**: `sre_agent/agent.py` (`base_tools`)
4. **Metadata Registry**: `sre_agent/tools/config.py` (`TOOL_DEFINITIONS`)
5. **Council Tool Sets** (if used by sub-agents): `sre_agent/council/tool_registry.py`

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
