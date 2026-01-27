# Observability & Debugging Guide

This document explains the logging and tracing architecture of the SRE Agent, specifically designed for Google Cloud Observability.

## 1. End-to-End Tracing & Correlation

The SRE Agent uses a hybrid approach to correlate logs and traces across Cloud Run (Frontend) and Agent Engine (Backend).

### How it works:
1.  **Trace ID Capture**: When the Cloud Run frontend makes a request to the Agent Engine, it captures the current OpenTelemetry Trace ID.
2.  **Session Propagation**: This Trace ID is injected into the ADK Session State as `_trace_id`.
3.  **Context Injection**: The Agent Engine (via `RunnerAgentAdapter` or `emojify_agent` wrapper) extracts `_trace_id` and:
    *   Sets it in a thread-local context (`sre_agent.auth.set_trace_id`).
    *   Injects it into the OpenTelemetry context (`opentelemetry.context.attach`) so any internal spans become children of the frontend request.

### Log Correlation:
All logs use a custom `JsonFormatter` that automatically adds the `logging.googleapis.com/trace` field.
*   **Field Name**: `logging.googleapis.com/trace`
*   **Format**: `projects/{PROJECT_ID}/traces/{TRACE_ID}`
*   **Benefit**: This allows the Logs Explorer to automatically group logs from both services when you click "View in Trace" or "Show nested logs".

## 2. Structured Logging (JSON)

We use JSON logging in production to ensure severities and metadata are correctly parsed by GCP.

### Configuration
*   **Environment Variable**: `LOG_FORMAT=JSON`
*   **Severity**: Logs are emitted to `stderr` (standard for Cloud Run) with a `severity` field (e.g., `ERROR`, `WARNING`, `INFO`).

### Adding Instrumentation
When adding new tools or services, always use the standard `logging` library. If you need to access the current trace ID in your code:

```python
from sre_agent.auth import get_trace_id
current_trace = get_trace_id()
```

## 3. Debugging "Invalid JSON" Errors

If you see an error like `Agent Engine stream returned invalid JSON format`, it usually means the backend crashed before it could send valid ADK events.

**To debug:**
1.  Go to the **Cloud Logs Explorer**.
2.  Filter by `resource.type="aws_lambda_function"` (used by Reasoning Engine) or search for `RunnerAdapter failed`.
3.  Check for `ERROR` severity logs. The new `JsonFormatter` ensures these are correctly flagged.
4.  The `RunnerAgentAdapter` now yields a proper Error Event before failing, which should resolve the malformed JSON issue by providing a protocol-compliant error message to the frontend.

## 4. Encryption Key Configuration

The `SRE_AGENT_ENCRYPTION_KEY` is critical for decrypting session state on the backend.
*   If this key is mismatched, the backend will fail to read credentials, leading to authentication errors.
*   Always ensure the key in Cloud Secret Manager (`sre-agent-encryption-key`) matches the one used during deployment.
