# Observability & Debugging Guide

This document explains the logging, tracing, and monitoring architecture of the SRE Agent, designed for Google Cloud Observability.

## 1. Hybrid Telemetry Strategy (February 2026)

The SRE Agent utilizes a tiered observability approach, combining native ADK orchestration tracing with high-fidelity Google GenAI instrumentation.

### How it works:
1.  **Native GenAI Tracing**: Uses the `GoogleGenAiSdkInstrumentor` (from `opentelemetry.instrumentation.google_genai`) to capture the internal reasoning process of Gemini models. This instrumentor is always enabled via `setup_telemetry()` in `sre_agent/tools/common/telemetry.py`.
2.  **Context Propagation**: In the `AgentEngineClient` and `RunnerAdapter`, the full OpenTelemetry `SpanContext` (Trace ID, Span ID) is extracted from the active request via `bridge_otel_context()` and propagated to the Agent Engine.
3.  **Encrypted Injection**: This context is securely injected into the session state using internal keys (`_trace_id`, `_span_id`).
4.  **Multi-Receiver Coexistence**: The telemetry system supports simultaneous export to **Google Cloud Trace** (via `OTEL_TO_CLOUD=true`) and **Langfuse** (via `LANGFUSE_TRACING=true`). Both are disabled in Agent Engine to avoid conflicts with native platform exporters.
5.  **Result**: A unified, high-fidelity trace tree in GCP that captures both infrastructural flow and AI reasoning prompts/responses.

### Platform-Aware Initialization
The `setup_telemetry()` function detects the execution environment:
- If `RUNNING_IN_AGENT_ENGINE=true`: Skips manual OTel and Langfuse setup (native platform tracing is used).
- If OTel is already initialized (`is_otel_initialized()` returns `True`): Skips manual provider creation.
- Otherwise: Sets up Langfuse and/or Google Cloud Trace exporters based on environment variables.

The `GoogleGenAiSdkInstrumentor` is always instrumented regardless of environment, as it is idempotent.

## 2. Structured Logging (JSON)

JSON logging is used in production to ensure severities and metadata are correctly parsed by GCP.

### Log Correlation:
All logs use a custom `JsonFormatter` (defined in `sre_agent/tools/common/telemetry.py`) that automatically adds:
*   `logging.googleapis.com/trace`: Fully qualified GCP trace resource (format: `projects/{PROJECT_ID}/traces/{TRACE_ID}`).
*   `logging.googleapis.com/spanId`: The current OTel span ID.
*   `logging.googleapis.com/sourceLocation`: File, line, and function for each log entry.
*   `severity`: Standard GCP severity level (DEBUG, INFO, WARNING, ERROR, CRITICAL).

The `JsonFormatter` also includes:
*   **OTel span context extraction**: Reads trace/span IDs from the active OpenTelemetry span.
*   **Fallback to ContextVar**: If OTel span is unavailable, falls back to `get_trace_id()` from `sre_agent/auth.py`.
*   **Correlation ID support**: Includes `correlation_id` if set on the log record.
*   **Exception serialization**: Formats exception info as a string in the JSON payload.

### Color-Coded Local Logging
For local development, a `ColorFormatter` provides ANSI-colored output:
- DEBUG: Cyan
- INFO: Green
- WARNING: Yellow
- ERROR: Red
- CRITICAL: Bold Red

The format is selected via `LOG_FORMAT` environment variable: `JSON` for production, `COLOR` (default) for local development.

### Configuration
*   **Environment Variable**: `LOG_FORMAT=JSON` (production) or `LOG_FORMAT=COLOR` (default, local)
*   **Severity**: Logs are emitted to `stdout` via `StreamHandler` with appropriate severity fields.
*   **Chatty Logger Silencing**: `google.auth`, `urllib3`, `grpc`, `httpcore`, `httpx`, and `aiosqlite` are silenced to WARNING level.

## 3. Instrumentation Layers

### Layer 1: Standard Python Logging
All application activity is captured via Python's `logging` module. In cloud environments, Google Cloud's native logging agents capture stdout/stderr automatically.

### Layer 2: Google GenAI SDK Instrumentation
The `GoogleGenAiSdkInstrumentor` from `opentelemetry.instrumentation.google_genai` captures:
- LLM prompts and responses (when `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true`)
- Model invocation latency
- Token usage per call

This bridges to ADK's internal capture via `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS`.

### Layer 3: Google Cloud Trace (Optional)
When `OTEL_TO_CLOUD=true`, the system configures:
- A `TracerProvider` with `CloudTraceSpanExporter` (from `opentelemetry.exporter.cloud_trace`)
- `BatchSpanProcessor` for efficient span export
- Resource attributes: `service.name` from `OTEL_SERVICE_NAME` (default: `sre-agent`)

### Layer 4: Langfuse Tracing (Optional, Local Only)
When `LANGFUSE_TRACING=true`, the system configures:
- OTLP exporter pointed at the Langfuse endpoint (`{LANGFUSE_HOST}/api/public/otel/v1/traces`)
- Basic auth using `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY`
- `GoogleADKInstrumentor` from `openinference.instrumentation.google_adk` for ADK-specific spans
- Session and user grouping via `set_langfuse_session()`, `set_langfuse_user()`
- Metadata and tags via `set_langfuse_metadata()`, `add_langfuse_tags()`
- Score/feedback reporting via `send_langfuse_score()`

### Layer 5: OTel Context Bridging
The `bridge_otel_context()` function in `telemetry.py` enables cross-process trace correlation:
- Accepts a 32-char hex trace ID and optional 16-char hex span ID
- Creates a `NonRecordingSpan` with the provided `SpanContext`
- Attaches it to the current OpenTelemetry context
- Used by `agent.py` and `runner_adapter.py` to link frontend traces to backend agent execution

### Serverless Optimization
In cloud environments (Cloud Run, Agent Engine), we rely on Google Cloud's native logging and monitoring agents to capture stdout/stderr. Manual OTel initialization is skipped when `RUNNING_IN_AGENT_ENGINE=true`.

## 4. Cost and Token Tracking

The `model_callbacks.py` module (`sre_agent/core/model_callbacks.py`) provides:
- **Per-agent token tracking**: Input/output tokens counted per agent invocation
- **Cost estimation**: Based on model-specific pricing (Gemini Flash vs Pro)
- **Token budget enforcement**: Configurable via `SRE_AGENT_TOKEN_BUDGET` environment variable
- **Budget exceeded detection**: `is_budget_exceeded()` check prevents runaway investigations
- **Summary reporting**: Aggregate cost and token usage across all agents in an investigation

## 5. Dashboard Query Language Support

The Flutter dashboard now supports multiple query languages across its observability panels:

### Supported Panels and Languages
| Panel | Native Query Language | NL Support |
|-------|----------------------|------------|
| Traces | Cloud Trace filter syntax | Yes (via agent) |
| Logs | Cloud Logging filter syntax | Yes (via agent) |
| Metrics | ListTimeSeries filter / PromQL | Yes (via agent) |
| Charts | Metric type selectors | Yes (via agent) |

### Key Components
- **`query_language_toggle.dart`**: Compact toggle widget for switching between query languages (e.g., ListTimeSeries filter vs PromQL in the metrics panel).
- **`query_autocomplete_overlay.dart`**: Provides context-aware autocomplete suggestions as users type queries.
- **`query_helpers.dart`**: Utility functions for query construction and validation.
- **`query_language_badge.dart`**: Visual indicator showing which query language is active.
- **`manual_query_bar.dart`**: Input widget for direct query entry across all panels.
- **`explorer_query_service.dart`**: Routes queries -- direct telemetry queries go to GCP APIs; natural language queries are routed to the agent chat for translation.

### NL Query Routing
Natural language queries typed into dashboard panels are routed to the agent's chat interface, where the LLM translates them into the appropriate query language. Direct queries (MQL, Cloud Logging filter, etc.) bypass the agent and go straight to the relevant GCP API.

## 6. Encryption Key Configuration

The `SRE_AGENT_ENCRYPTION_KEY` is critical for decrypting session state on the backend.
*   If this key is mismatched between environment services, the backend will fail to read credentials and trace IDs.
*   A transient key is generated if not set, but tokens will not be decryptable after restart.
*   Always ensure the key in Cloud Secret Manager (`sre-agent-encryption-key`) matches the one used during deployment.

To maintain high signal-to-noise ratios, the agent uses standard Python logging filters where necessary.

## 7. Configuration Summary

| Variable | Description | Default |
| :--- | :--- | :--- |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) | `INFO` |
| `LOG_FORMAT` | Log output format (`COLOR` or `JSON`) | `COLOR` |
| `OTEL_TO_CLOUD` | Enable Google Cloud Trace exporter (local only) | `false` |
| `OTEL_SERVICE_NAME` | Service name for OTel resource attributes | `sre-agent` |
| `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` | Capture prompts/responses in traces | `false` |
| `OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED` | Enable OTel logging instrumentation | `false` |
| `DISABLE_TELEMETRY` | Disable all tracing and metrics | `false` |
| `RUNNING_IN_AGENT_ENGINE` | Skip manual OTel setup (use platform tracing) | `false` |
| `LANGFUSE_TRACING` | Enable Langfuse OTel tracing (local only) | `false` |
| `LANGFUSE_PUBLIC_KEY` | Langfuse API public key | unset |
| `LANGFUSE_SECRET_KEY` | Langfuse API secret key | unset |
| `LANGFUSE_HOST` | Langfuse server URL | `http://localhost:3000` |
| `SRE_AGENT_ENCRYPTION_KEY` | Encryption key for session state | auto-generated |
| `SRE_AGENT_TOKEN_BUDGET` | Max token budget per request | unset (unlimited) |


## 8. Agent Graph Visualization

The SRE Agent includes a topology graph visualization powered by BigQuery Materialized Views and the Sugiyama layout algorithm.
For detailed setup instructions, architecture, and query logic, see:
[Agent Graph Setup Guide](agent_ops/visualization_setup.md)

## 9. Multi-Agent Observability (AgentOps)

Beyond the BigQuery-powered Agent Graph, the AgentOps Dashboard provides fleet-wide operational monitoring for the multi-agent system:

- **KPI Cards**: Total sessions, average turns, root invocations, error rate with trend indicators
- **Interaction Metrics**: Latency over time (P50/P95), QPS and error rate charts, token usage stacked area charts
- **Model Performance**: Per-model call counts, P95 latency, error rates, quota exits, token consumption
- **Tool Performance**: Per-tool call counts, P95 latency, error rates
- **Agent Logs**: Full-width virtualized log stream with color-coded severity badges

The dashboard is the fifth tab in the AgentOps UI alongside Agents, Tools, Agent Graph, and Trajectory Flow.

For the complete conceptual overview of multi-agent observability, see:
- [Multi-Agent Observability Concepts](agent_ops/observability_theory.md)
- [AgentOps Dashboard Guide](agent_ops/dashboard.md)
- [Agent Graph Deep Dive](agent_ops/architecture.md)

---
*Last verified: 2026-02-21
