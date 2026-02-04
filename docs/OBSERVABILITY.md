# Observability & Debugging Guide

This document explains the logging and tracing architecture of the SRE Agent, specifically designed for Google Cloud Observability.

## 1. Hybrid Telemetry Strategy (February 2026)

The SRE Agent utilizes a tiered observability approach, combining native ADK orchestration tracing with high-fidelity Google GenAI instrumentation.

### How it works:
1.  **Native GenAI Tracing**: Uses the `GoogleGenAiSdkInstrumentor` to capture the internal reasoning process of Gemini models.
2.  **Context Propagation**: In the `AgentEngineClient`, we extract the full OpenTelemetry `SpanContext` (Trace ID, Span ID) from the active request and propagate it to the Agent Engine.
3.  **Encrypted Injection**: This context is securely injected into the session state using internal keys (`_trace_id`, `_span_id`).
4.  **Multi-Receiver Coexistence**: Setting `OTEL_TO_CLOUD=true` enables simultaneous export to **Google Cloud Trace** and **Langfuse** (if configured).
5.  **Result**: A unified, high-fidelity trace tree in GCP that captures both infrastructural flow and AI reasoning prompts/responses.

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

For deep local debugging, we also support **Langfuse** tracing (configured via `LANGFUSE_TRACING=true`). This is disabled in Agent Engine to prioritize native Cloud Trace integration.

### Evaluations
Logging is standard but can be silenced if needed via log levels.

## 5. Encryption Key Configuration

The `SRE_AGENT_ENCRYPTION_KEY` is critical for decrypting session state on the backend.
*   If this key is mismatched, the backend will fail to read credentials and trace IDs.
*   Always ensure the key in Cloud Secret Manager (`sre-agent-encryption-key`) matches the one used during deployment.

To maintain high signal-to-noise ratios, the agent uses standard Python logging filters where necessary.

## 6. Configuration Summary

| Variable | Description | Default |
| :--- | :--- | :--- |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, etc.) | `INFO` |
| `LOG_FORMAT` | Log output format (TEXT or JSON) | `TEXT` |
| `OTEL_TO_CLOUD` | Enable Google Cloud Trace exporter | `false` |
| `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` | Capture prompts/responses in traces | `false` |
| `DISABLE_TELEMETRY` | Disable all tracing and metrics | `false` |

---
*Last verified: 2026-02-02 — Auto SRE Team*
