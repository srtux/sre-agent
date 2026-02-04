# Configuration Reference

This document details all environment variables used to configure the Auto SRE Agent.

## Core Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `GOOGLE_CLOUD_PROJECT` | The GCP Project ID where the agent is running. | Yes | - |
| `GOOGLE_CLOUD_LOCATION` | The GCP Region (e.g., `us-central1`). | Yes | - |
| `GOOGLE_CLIENT_ID` | OAuth 2.0 Client ID for the Flutter Frontend. | Yes | - |
| `SRE_AGENT_ENCRYPTION_KEY` | AES-256 key for encrypting session tokens. | Yes | - |

## Execution Modes

| Variable | Description | Default |
|----------|-------------|---------|
| `SRE_AGENT_ID` | If set, the backend forwards requests to this Vertex AI Agent Engine resource. **Note**: Used for connection only; session namespace is standardized to `sre_agent`.
    - `SRE_AGENT_ID` is set to the Vertex Engine resource ID (for connection).
    - `RUNNING_IN_AGENT_ENGINE=true` is set on the remote instance.
    - **Session Consistency**: Both Proxy and Backend use `app_name="sre_agent"` for `VertexAiSessionService` to ensure they share the same session namespace, overcoming the fact that the Backend doesn't know its own `SRE_AGENT_ID`. | - |
| `RUNNING_IN_AGENT_ENGINE` | Set to `true` by `deploy.py` on the Backend to trigger remote-mode behaviors (like using `VertexAiSessionService`) even when `SRE_AGENT_ID` is unset. | `false` |
| `STRICT_EUC_ENFORCEMENT` | If `true`, fails requests if user credentials in the context are missing. If `false`, falls back to Application Default Credentials (ADC). **Set to `false` for local `adk web` development.** | `false` |
| `ENABLE_AUTH` | If `false`, disables SSO and injects dummy/dev credentials. **Set to `false` ONLY for local testing to bypass authentication.** Can also be bypassed via the "Login as Guest" button on the UI login screen in debug mode. | `true` |
| `OTEL_TO_CLOUD` | If `true`, enables the Google Cloud Trace exporter for native OTel spans. | `false` |
| `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` | If `true`, captures the full content of prompts and responses in traces. | `false` |
| `CORS_ALLOW_ALL` | If `true`, allows all origins in FastAPI middleware. Useful for development. | `false` |
| `SECURE_COOKIES` | If `true`, session cookies are marked as `Secure`. Set to `false` for local `http` dev. | `true` |

## Telemetry & Debugging

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG_TELEMETRY` | Enable verbose OpenTelemetry logs. | `false` |
| `DEBUG_AUTH` | Enable verbose authentication logs. | `false` |
| `LOG_LEVEL` | Python logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). | `INFO` |
| `GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY` | Enable telemetry within the Agent Engine runtime. | `false` |

## External Integrations

| Variable | Description | Default |
|----------|-------------|---------|
| `LANGFUSE_TRACING` | Enable Langfuse tracing for local/agentic debugging. | `false` |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key. | - |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key. | - |
| `LANGFUSE_HOST` | Langfuse host URL (self-hosted or cloud). | `http://localhost:3000` |
| `TRACE_PROJECT_ID` | Override project for Cloud Trace queries (if different from host). | `GOOGLE_CLOUD_PROJECT` |
| `GEMINI_API_KEY` | Your Google API Key (if not using ADC/Service Account). | - |
| `GOOGLE_API_KEY` | Alias for `GEMINI_API_KEY`. | - |

### Deprecated Variables

The following variables are deprecated and will be removed in a future release.

| Variable | Status | Migration Path |
|----------|--------|---------------|
| `USE_ARIZE` | **Removed** | Delete from `.env`. Arize instrumentation has been fully replaced by native Google Cloud Trace + optional Langfuse tracing. Set `OTEL_TO_CLOUD=true` for Cloud Trace export and/or `LANGFUSE_TRACING=true` for Langfuse. |
| `ARIZE_SPACE_ID` | **Removed** | Delete from `.env`. No replacement needed. |
| `ARIZE_API_KEY` | **Removed** | Delete from `.env`. No replacement needed. |

> **Migration**: If you were previously using Arize for observability, switch to native Cloud Trace (`OTEL_TO_CLOUD=true`) for production tracing. For local development debugging, use Langfuse (`LANGFUSE_TRACING=true`). Both can run simultaneously.

## Council Architecture

| Variable | Description | Default |
|----------|-------------|---------|
| `SRE_AGENT_SLIM_TOOLS` | Reduce root agent to ~20 orchestration tools. Council panels retain full tool sets. | `false` |
| `SRE_AGENT_COUNCIL_ORCHESTRATOR` | Replace root LlmAgent with CouncilOrchestrator. Routes queries to parallel panels with debate support. | `false` |

## Storage & Sessions

| Variable | Description | Default |
|----------|-------------|---------|
| `USE_DATABASE_SESSIONS` | Force using SQLite sessions. | `true` |
| `SESSION_DB_PATH` | Path to the SQLite session database. | `.sre_agent_sessions.db` |
| `USE_FIRESTORE` | Backend for session storage in production. | `false` (Auto-detected in Cloud Run) |

## Server Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Listening port for the FastAPI server. | `8001` |
| `HOST` | Listening host for the FastAPI server. | `0.0.0.0` |

## Deployment Variables

Used by `deploy/` scripts.

| Variable | Description |
|----------|-------------|
| `GOOGLE_CLOUD_STORAGE_BUCKET` | Staging bucket for Agent Engine artifacts. |

---
*Last verified: 2026-02-02 — Auto SRE Team*
