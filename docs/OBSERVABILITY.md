# Observability & Debugging Guide

This document explains the logging and tracing architecture of the SRE Agent, specifically designed for Google Cloud Observability.

## 1. End-to-End Tracing & Correlation (Context Hijacking)

The SRE Agent uses a custom "REST-Bridge" pattern to correlate logs and traces across Cloud Run (Frontend) and Agent Engine (Backend).

### How it works:
1.  **Context Capture**: In the `AgentEngineClient`, we extract the full OpenTelemetry `SpanContext` (Trace ID, Span ID, and Trace Flags) from the active request.
2.  **Encrypted Injection**: This context is injected into the ADK Session State using internal keys (`_trace_id`, `_span_id`, `_trace_flags`).
3.  **Context Restoration**: On the Agent Engine side (via `emojify_agent`), we:
    *   Initialize the global `set_trace_id` for log correlation.
    *   Reconstruct a valid `NonRecordingSpan` using the propagated IDs.
    *   **CRITICAL**: We ensure the `span_id` is **non-zero**. If the frontend span is missing, we derive a deterministic non-zero ID from the Trace ID.
4.  **Result**: A single, unified trace tree in **Google Cloud Trace** that spans multiple services.

## 2. Structured Logging (JSON)

We use JSON logging in production to ensure severities and metadata are correctly parsed by GCP.

### Log Correlation:
All logs use a custom `JsonFormatter` that automatically adds:
*   `logging.googleapis.com/trace`: Fully qualified GCP trace resource.
*   `logging.googleapis.com/spanId`: The current OTel span ID.
*   `trace_id`: The raw hex trace ID.

### Configuration
*   **Environment Variable**: `LOG_FORMAT=JSON`
*   **Severity**: Logs are emitted to `stderr` (standard for Cloud Run) with a `severity` field.

## 3. Instrumentation Layers

The agent uses multiple OTel instrumentors to provide full visibility into its operations:

*   **FastAPI**: Inbound request lifecycle.
*   **gRPC**: Outbound calls to Vertex AI and Agent Engine.
*   **Vertex AI**: Low-level visibility into Gemini model iterations/prompts.
*   **Google ADK**: High-level visibility into agent steps and tool calls.
*   **Requests / HTTPX / URLLib3**: Generic network operations.

### Serverless Optimization
In cloud environments, we set `schedule_delay_millis=1000` (1 second) in the `BatchSpanProcessor`. This ensures spans are exported quickly before serverless instances are paused or terminated.

## 4. Telemetry Environments

### Local Development (Arize AX)
For local development, we prioritize **Arize AX** (Phoenix) for LLM observability.
*   **Enabled by**: `USE_ARIZE=true`
*   **Restriction**: Arize is **EXPLICITLY DISABLED** when running in GCP (Cloud Run or Agent Engine) to avoid performance overhead and duplicate tracing. The platform will automatically fall back to Google Cloud Trace.

### Production (Google Cloud Trace)
In production, telemetry is exported directly to Google Cloud via OTLP over gRPC.
*   **Required Role**: `roles/cloudtrace.agent`
*   **Project ID**: Standardized via `GOOGLE_CLOUD_PROJECT`.

### Evaluations
Telemetry is **DISABLED** by default for automated evaluations (`run_eval.py`) to prevent noise and background process hangs. This is controlled via `OTEL_SDK_DISABLED=true`.

## 5. Encryption Key Configuration

The `SRE_AGENT_ENCRYPTION_KEY` is critical for decrypting session state on the backend.
*   If this key is mismatched, the backend will fail to read credentials and trace IDs.
*   Always ensure the key in Cloud Secret Manager (`sre-agent-encryption-key`) matches the one used during deployment.

## 6. Telemetry Resilience & Noise Filtering

To maintain high signal-to-noise ratios in logs, the agent implements a `_TelemetryNoiseFilter` that suppresses harmless but distracting internal SDK warnings:

*   **MetricReader Registration**: Suppresses `Cannot call collect on a MetricReader until it is registered` warnings caused by race conditions during provider initialization.
*   **GenAI Parts**: Filters out `Warning: there are non-text parts in the response` from the Vertex AI and ADK libraries.
*   **OTLP Export Suppression**: When `SUPPRESS_OTEL_ERRORS=true` (default), persistent gRPC export failures are silenced to prevent log flooding during temporary network issues or local runs without credentials.

## 7. Configuration Summary

| Variable | Description | Default |
| :--- | :--- | :--- |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, etc.) | `INFO` |
| `LOG_FORMAT` | Log output format (TEXT or JSON) | `TEXT` |
| `DISABLE_TELEMETRY` | Disable all tracing and metrics | `false` |
| `SUPPRESS_OTEL_ERRORS` | Silence OTLP export errors | `true` |
| `USE_ARIZE` | Enable Arize Phoenix for local dev | `false` |
