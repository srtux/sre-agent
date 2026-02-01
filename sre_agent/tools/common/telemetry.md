# Telemetry and Observability in SRE Agent

This document describes the telemetry and observability architecture for the SRE Agent.

## Minimalist Telemetry Standard (January 2026)

As of January 2026, the SRE Agent has moved to a **Minimalist Telemetry Standard**. We have completely removed all manual/custom OpenTelemetry (OTel) and Arize instrumentation from the codebase.

### Core Principles

1.  **Reliance on Native ADK Instrumentation**: The agent now defers entirely to the [Google Agent Development Kit (ADK)](https://github.com/google/adk) and its native integration with the **Vertex AI Agent Engine**.
2.  **No Manual Spans**: Tools and sub-agents no longer call `tracer.start_as_current_span()` or manually set OTel attributes.
3.  **Automatic High-Fidelity Tracing**: By setting the environment variable `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true`, the ADK automatically captures all prompts, responses, and tool calls with full fidelity, exporting them to Cloud Trace via the Agent Engine service.
4.  **Standardized Response Logging**: Instead of manual instrumentation, the `@adk_tool` decorator and `BaseToolResponse` structure provide consistent visibility into tool execution via standard logging.

---

## Configuration

Telemetry is now primarily configured via environment variables that affect the Underlying ADK and runtime.

### General Settings

*   `LOG_LEVEL`: One of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. (Default: `INFO`).
*   `LOG_FORMAT`: `TEXT` (default) for readable console logs, or `JSON` for structured logs in production.
*   `DISABLE_TELEMETRY`: Set to `true` during tests to prevent unnecessary export overhead.

### ADK / Agent Engine native Tracing

To enable full visibility into agent reasoning:

*   `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true`: Enables high-fidelity prompt/response capture in Cloud Trace.
*   `SUPPRESS_OTEL_ERRORS=true`: Suppresses non-critical OTLP export warnings to keep logs clean.

---

## Technical Architecture

### Tool Visibility

Every tool marked with `@adk_tool` automatically benefits from:
1.  **Standard Logging**: Input arguments and output status are logged to `stdout`.
2.  **Native Span Generation**: When running in Agent Engine, tool calls are automatically converted into spans by the platform.

### Standardized Tool Responses

All tools must return a `BaseToolResponse`. This ensures that even without manual OTel code, the agent's performance and error rates can be monitored via the logical status of these objects.

```python
from sre_agent.schema import BaseToolResponse, ToolStatus

@adk_tool
async def my_tool(...) -> BaseToolResponse:
    # Logic here
    return BaseToolResponse(
        status=ToolStatus.SUCCESS,
        result={"data": ...}
    )
```

### Removal of Legacy Components

The following legacy components have been **removed**:
*   `ArizeAxExporter` and all `arize` package dependencies.
*   `setup_telemetry()` logic for manual `MetricReader` and `TraceProvider` registration.
*   Manual `opentelemetry-api` and `opentelemetry-sdk` direct imports in tools.

---

## LangSmith Tracing (Local & Debugging)

While we prefer native ADK tracing for production, **LangSmith** is supported for local development to visualize complex agent reasoning chains and tool use.

### Enabling LangSmith

1.  **Dependencies**: Ensure dev dependencies are installed (`uv sync`).
2.  **Environment Variables**:
    *   `LANGSMITH_TRACING=true`
    *   `LANGSMITH_API_KEY=<your-api-key>`
    *   `LANGSMITH_PROJECT=sre-agent` (Optional, defaults to `sre-agent`)

### Features

*   **Full Trace Trees**: Visualizes the complete execution path from user input -> agent reasoning -> tool calls -> final response.
*   **Thread View**: Groups interactions by session ID, allowing you to see the full conversation history.
*   **Metadata**: Automatically captures user ID and session tags if available.

**Note**: LangSmith tracing is currently disabled when running inside Agent Engine to strictly adhere to the native ADK telemetry standard.

---

## Observability Best Practices

1.  **Use Logging for Context**: Instead of a manual span attribute, use `logger.info()` or `logger.debug()`. These are automatically correlated with the active trace by the Agent Engine logging service.
2.  **Trust the Decorator**: Let `@adk_tool` handle the standard execution tracing.
3.  **Monitor via BigQuery**: For historical analysis, use BigQuery tools to query the `_AllSpans` table (where ADK exports spans) rather than searching for manual instrumentation code.
