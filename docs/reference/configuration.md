# Configuration Reference

This document details all environment variables used to configure the Auto SRE Agent.

## Core Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `GOOGLE_CLOUD_PROJECT` | The GCP Project ID where the agent is running. Also accepted as `GCP_PROJECT_ID`. | Yes | - |
| `GOOGLE_CLOUD_LOCATION` | The GCP Region (e.g., `us-central1`). Also accepted as `GCP_LOCATION`. | Yes | `us-central1` |
| `GOOGLE_CLIENT_ID` | OAuth 2.0 Client ID for the Flutter Frontend. | Yes | - |
| `SRE_AGENT_ENCRYPTION_KEY` | AES-256 Fernet key for encrypting session tokens. If unset, a transient key is generated at startup (not suitable for multi-instance). | Yes (prod) | Transient |
| `GOOGLE_GENAI_USE_VERTEXAI` | If `1` or `true`, use Vertex AI for Gemini. If `0`, use Google AI Studio. | No | `true` |

## Execution Modes

| Variable | Description | Default |
|----------|-------------|---------|
| `SRE_AGENT_ID` | If set, the backend forwards requests to this Vertex AI Agent Engine resource. Used for connection only; session namespace is standardized to `sre_agent`. | - |
| `RUNNING_IN_AGENT_ENGINE` | Set to `true` by `deploy.py` on the Backend to trigger remote-mode behaviors (like using `VertexAiSessionService`) even when `SRE_AGENT_ID` is unset. | `false` |
| `SRE_AGENT_DEPLOYMENT_MODE` | Set to `true` during deployment to skip module-level initialization of the Vertex AI SDK. | `false` |
| `STRICT_EUC_ENFORCEMENT` | If `true`, fails requests if user credentials in the context are missing. If `false`, falls back to Application Default Credentials (ADC). **Set to `false` for local `adk web` development.** | `false` |
| `ENABLE_AUTH` | If `false`, disables SSO and injects dummy/dev credentials. **Set to `false` ONLY for local testing to bypass authentication.** Can also be bypassed via the "Login as Guest" button on the UI login screen. | `true` |
| `ENABLE_GUEST_MODE` | If `true`, enables the guest-mode login button on the frontend. Guest mode injects synthetic credentials and a demo project (`cymbal-shops-demo`). | `true` |
| `CORS_ALLOW_ALL` | If `true`, allows all origins in FastAPI CORS middleware. Useful for development. | `false` |
| `SECURE_COOKIES` | If `true`, session cookies are marked as `Secure`. Set to `false` for local `http` dev. | `true` |

## Telemetry & Debugging

| Variable | Description | Default |
|----------|-------------|---------|
| `OTEL_TO_CLOUD` | If `true`, enables the Google Cloud Trace exporter for native OTel spans. | `false` |
| `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` | If `true`, captures the full content of prompts and responses in traces. | `false` |
| `OTEL_SERVICE_NAME` | Service name used in OTel resource attributes. | `sre-agent` |
| `DEBUG_TELEMETRY` | Enable verbose OpenTelemetry logs. | `false` |
| `DEBUG_AUTH` | Enable verbose authentication logs. | `false` |
| `DISABLE_TELEMETRY` | Disable all telemetry (useful in tests). | `false` |
| `LOG_LEVEL` | Python logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). | `INFO` |
| `LOG_FORMAT` | Log format: `COLOR` for local development, `JSON` for Cloud Run production, `TEXT` for plain output. | `COLOR` |
| `A2UI_DEBUG` | Enable verbose A2UI GenUI protocol debug logging. | `false` |
| `GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY` | Enable telemetry within the Agent Engine runtime. | `false` |

## External Integrations

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Your Google API Key (if not using ADC/Service Account). | - |
| `GOOGLE_API_KEY` | Alias for `GEMINI_API_KEY`. Used when `GOOGLE_GENAI_USE_VERTEXAI=0`. | - |
| `LANGFUSE_TRACING` | Enable Langfuse tracing for local/agentic debugging. Disabled automatically when `RUNNING_IN_AGENT_ENGINE=true`. | `false` |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key. | - |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key. | - |
| `LANGFUSE_HOST` | Langfuse host URL (self-hosted or cloud). | `http://localhost:3000` |
| `TRACE_PROJECT_ID` | Override project for Cloud Trace queries (if different from host). | `GOOGLE_CLOUD_PROJECT` |
| `GOOGLE_CUSTOM_SEARCH_API_KEY` | API key for Google Custom Search (enables `search_google` tool). Create at: GCP Console > APIs & Services > Credentials. | - |
| `GOOGLE_CUSTOM_SEARCH_ENGINE_ID` | Programmable Search Engine ID (cx) for the `search_google` tool. Create at: [programmablesearchengine.google.com](https://programmablesearchengine.google.com/). | - |
| `GITHUB_TOKEN` | GitHub Personal Access Token for agent self-healing tools (read/write repository access, PR creation). Create at: [github.com/settings/tokens](https://github.com/settings/tokens) (needs `repo` scope). | - |
| `GITHUB_REPO` | GitHub repository in `owner/repo` format for the agent's source code. | `srtux/sre-agent` |

### MCP Server Overrides

| Variable | Description | Default |
|----------|-------------|---------|
| `BIGQUERY_MCP_SERVER` | Override the BigQuery MCP server command. | Built-in default |
| `LOGGING_MCP_SERVER` | Override the Cloud Logging MCP server command. | Built-in default |
| `MONITORING_MCP_SERVER` | Override the Cloud Monitoring MCP server command. | Built-in default |

### Deprecated Variables

The following variables are deprecated and will be removed in a future release.

| Variable | Status | Migration Path |
|----------|--------|---------------|
| `USE_ARIZE` | **Removed** | Delete from `.env`. Arize instrumentation has been fully replaced by native Google Cloud Trace + optional Langfuse tracing. Set `OTEL_TO_CLOUD=true` for Cloud Trace export and/or `LANGFUSE_TRACING=true` for Langfuse. |
| `ARIZE_SPACE_ID` | **Removed** | Delete from `.env`. No replacement needed. |
| `ARIZE_API_KEY` | **Removed** | Delete from `.env`. No replacement needed. |

> **Migration**: If you were previously using Arize for observability, switch to native Cloud Trace (`OTEL_TO_CLOUD=true`) for production tracing. For local development debugging, use Langfuse (`LANGFUSE_TRACING=true`). Both can run simultaneously.

## Agent Behavior

| Variable | Description | Default |
|----------|-------------|---------|
| `SRE_AGENT_TOKEN_BUDGET` | Maximum token budget per request. Enforced by `before_model_callback` in `model_callbacks.py`. If unset, no budget limit is applied. | - |
| `SRE_AGENT_ENFORCE_POLICY` | Enable policy engine enforcement for tool calls. When `true`, the policy engine validates tool access levels before execution. | `true` |
| `SRE_AGENT_LOCAL_EXECUTION` | Enable sandboxed local execution mode for code analysis tools. | `false` |
| `SRE_AGENT_CIRCUIT_BREAKER` | Enable circuit breaker pattern on tool calls (three-state: CLOSED/OPEN/HALF_OPEN). Prevents cascade failures when tools are repeatedly failing. | `true` |
| `USE_MOCK_MCP` | Use mock MCP tool implementations in tests instead of real BigQuery/Monitoring connections. | `false` |
| `SRE_AGENT_EVAL_MODE` | Enable evaluation mode. In eval mode, tools return synthetic data instead of making real GCP API calls. Used by the `eval/` framework. | `false` |

## Council Architecture

| Variable | Description | Default |
|----------|-------------|---------|
| `SRE_AGENT_SLIM_TOOLS` | Reduce root agent to ~20 orchestration tools. Council panels retain full tool sets. | `true` |
| `SRE_AGENT_COUNCIL_ORCHESTRATOR` | Replace root LlmAgent with CouncilOrchestrator. Routes queries to parallel panels with debate support. | `false` |
| `SRE_AGENT_ADAPTIVE_CLASSIFIER` | Enable LLM-augmented intent classification for council mode selection (experimental). Falls back to rule-based classifier when disabled. | `false` |
| `SRE_AGENT_CONTEXT_CACHING` | Enable Vertex AI context caching for static prompt prefixes (75% cost reduction). | `false` |
| `SRE_AGENT_CONTEXT_CACHE_TTL` | TTL in seconds for cached context. | `3600` |

## Large Payload Handler

| Variable | Description | Default |
|----------|-------------|---------|
| `SRE_AGENT_LARGE_PAYLOAD_ENABLED` | Enable automatic sandbox processing for oversized tool outputs. When enabled, results that exceed thresholds are auto-summarized through the sandbox instead of being truncated. | `true` |
| `SRE_AGENT_LARGE_PAYLOAD_THRESHOLD_ITEMS` | List-item count above which sandbox processing triggers. | `50` |
| `SRE_AGENT_LARGE_PAYLOAD_THRESHOLD_CHARS` | Serialized-JSON character count above which processing triggers (approx 25-40k tokens). | `100000` |

## Sandbox Execution

| Variable | Description | Default |
|----------|-------------|---------|
| `SANDBOX_ENABLED` | Explicit override for sandbox availability. When unset, sandbox is auto-detected based on Agent Engine presence. | Auto-detected |
| `SANDBOX_RESOURCE_NAME` | Override the sandbox resource name (for connecting to a specific sandbox instance). | Auto-derived from `SRE_AGENT_ID` |
| `REASONING_ENGINE_RESOURCE_NAME` | Set by Agent Engine runtime. Used for sandbox auto-detection and session namespace. | - |

## Storage & Sessions

| Variable | Description | Default |
|----------|-------------|---------|
| `USE_DATABASE_SESSIONS` | Force using SQLite sessions. | `true` |
| `SESSION_DB_PATH` | Path to the SQLite session database. | `.sre_agent_sessions.db` |
| `USE_FIRESTORE` | Backend for session storage in production. | `false` (Auto-detected in Cloud Run via `K_SERVICE`) |
| `TOOL_CONFIG_PATH` | Path to the tool configuration JSON persistence file. | `.tool_config.json` |

## Server Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Listening port for the FastAPI server. | `8001` |
| `HOST` | Listening host for the FastAPI server. | `0.0.0.0` |

## Build & Deployment Variables

Used by `deploy/` scripts and CI/CD.

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_CLOUD_STORAGE_BUCKET` | Staging bucket for Agent Engine artifacts. | - |
| `BUILD_SHA` | Git commit SHA injected at build time by Cloud Build / Docker. Shown in `/api/version`. | - |
| `BUILD_TIMESTAMP` | Build timestamp injected at build time. Shown in `/api/version`. | - |
| `AGENT_ENGINE_LOCATION` | Override location for Agent Engine session service (if different from `GOOGLE_CLOUD_LOCATION`). | `GOOGLE_CLOUD_LOCATION` |

## Evaluation Variables

Used by the `eval/` framework.

| Variable | Description | Default |
|----------|-------------|---------|
| `EVAL_PROJECT_ID` | GCP project ID to use for evaluation runs (if different from `GOOGLE_CLOUD_PROJECT`). | `GOOGLE_CLOUD_PROJECT` |
| `SRE_AGENT_EVAL_MODE` | Enable evaluation mode (tools return synthetic data). | `false` |
| `TEST_PROJECT_ID` | Fallback project ID used during test execution. | - |

## BigQuery CA Data Agent

| Variable | Description | Default |
|----------|-------------|---------|
| `SRE_AGENT_CA_AGENT_ID` | Resource ID for the Conversational Analytics Data Agent. | Default built-in ID |

---
*Last verified: 2026-02-21
