# Telemetry and Observability in SRE Agent

This document describes the telemetry and observability architecture for the SRE Agent, including how it handles Tracing, Metrics, and Logging.

## Overview

The SRE Agent uses [OpenTelemetry (OTel)](https://opentelemetry.io/) for high-quality observability. It supports multiple backends and is designed to work in both local development and hosted (Agent Engine / Cloud Run) environments.

### Key Components

1.  **Tracing**: Captures tool calls, LLM iterations, and overall request flows.
2.  **Metrics**: (WIP) Tracks performance and usage metrics.
3.  **Logging**: Structured logging with OpenTelemetry correlation (Trace ID / Span ID).
4.  **Emoji Filters**: A custom logging filter adds emojis to the console output for better visibility of system events (LLM calls 🧠, Tool calls 🛠️, API calls 🌐).

---

## Configuration

Telemetry is configured via environment variables.

### General Settings

*   `LOG_LEVEL`: One of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. (Default: `INFO`).
*   `LOG_FORMAT`: `TEXT` (default) for readable console logs, or `JSON` for structured logs in production.
*   `DISABLE_TELEMETRY`: Set to `true` to completely disable OTel exporters. **Highly recommended for hermetic tests.**

### Google Cloud (OTLP)

The agent can export traces and metrics directly to Google Cloud Observability using the OTLP protocol over gRPC.

*   `GOOGLE_CLOUD_PROJECT`: The project to send telemetry to.
*   `OTEL_TRACES_EXPORTER`: Set to `otlp` (default) or `none`.
*   `OTEL_METRICS_EXPORTER`: Set to `otlp` (default) or `none`.

### Arize AX

The agent has built-in support for [Arize AX](https://arize.com/) for LLM observability.

*   `USE_ARIZE`: Set to `true` to enable Arize.
*   `ARIZE_SPACE_ID`: Your Arize Space ID.
*   `ARIZE_API_KEY`: Your Arize API Key.
*   `ARIZE_PROJECT_NAME`: The name of the project in Arize (Default: `AutoSRE`).

> **Note**: When `USE_ARIZE` is enabled, the agent prioritize Arize for tracing and will skip Google Cloud Trace setup to avoid duplicate spans.

---

## Technical Details

### Initialization Flow

Telemetry is initialized early in the application lifecycle (usually in `sre_agent.api.app:create_app`).

1.  **Early Logging**: Handlers are configured first.
2.  **Hermetic Check**: If `DISABLE_TELEMETRY` is set, setup returns early.
3.  **Arize Setup**: If enabled, Arize is initialized and claimed as the global TracerProvider.
4.  **GCP OTLP Setup**: If Arize is disabled and exporters are not `none`, the Google Cloud OTLP exporters are configured.
5.  **Log Correlation**: `LoggingInstrumentor` is applied to inject `trace_id` and `span_id` into all log records.

### Testing and Hermeticity

To ensure tests are hermetic and don't leak telemetry to external services, the `pyproject.toml` configuration enforces `DISABLE_TELEMETRY=true` for the `pytest` task.

```toml
[tool.poe.tasks]
test = { cmd = "pytest ...", env = { DISABLE_TELEMETRY = "true", ... } }
```

### Context Propagation

Tools should use the `ArizeSessionContext` (via `using_arize_session`) to ensure that traces are correctly grouped by session and user when running locally.

```python
from sre_agent.tools.common.telemetry import using_arize_session

with using_arize_session(session_id="...", user_id="..."):
    # Traces here will have session/user attributes
    ...
```
