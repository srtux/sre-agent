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

*   **Standard Logging**: Captures all activity via stdout/stderr.

### Serverless Optimization
In cloud environments, we rely on Google Cloud's native logging and monitoring agents to capture stdout/stderr.

## 4. Telemetry Environments

### Local & Production
We use standard Python `logging` which is automatically captured by Google Cloud Logging (Agent Engine) or Cloud Run's log scraper.

### Evaluations
Logging is standard but can be silenced if needed via log levels.

## 5. Encryption Key Configuration

The `SRE_AGENT_ENCRYPTION_KEY` is critical for decrypting session state on the backend.
*   If this key is mismatched, the backend will fail to read credentials and trace IDs.
*   Always ensure the key in Cloud Secret Manager (`sre-agent-encryption-key`) matches the one used during deployment.

To maintain high signal-to-noise ratios, the agent uses standard Python logging filters where necessary.

## 7. Configuration Summary

| Variable | Description | Default |
| :--- | :--- | :--- |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, etc.) | `INFO` |
| `LOG_FORMAT` | Log output format (TEXT or JSON) | `TEXT` |
| `DISABLE_TELEMETRY` | Disable all tracing and metrics | `false` |
| `DISABLE_TELEMETRY` | Disable all tracing and metrics | `false` |
