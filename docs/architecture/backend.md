# Backend Documentation

The SRE Agent backend is a FastAPI-based application that serves as the orchestration layer for the agent and the primary API for the Flutter frontend.

## API Structure

The backend is organized into modular routers under `sre_agent/api/routers/`.

### Core Routers

| Router | Description | Key Endpoints |
| :--- | :--- | :--- |
| **Agent** (`agent.py`) | Main chat and orchestration | `POST /agent`, `POST /api/genui/chat`, `GET /api/suggestions` |
| **System** (`system.py`) | Auth, config, and version | `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/config`, `GET /api/version` |
| **Sessions** (`sessions.py`) | Conversation history | `GET /api/sessions`, `DELETE /api/sessions/{id}`, `PATCH /api/sessions/{id}` |
| **Tools** (`tools.py`) | Tool config, testing, and direct query/exploration endpoints | See detailed table below |
| **Preferences** (`preferences.py`) | User settings | `GET /api/preferences`, `PUT /api/preferences` |
| **Health** (`health.py`) | Health and readiness checks | `GET /health`, `GET /ready` |
| **Help** (`help.py`) | Help center content | `GET /api/help/manifest`, `GET /api/help/content/{id}` |
| **Permissions** (`permissions.py`) | IAM permission checks | `GET /api/permissions` |

### Tools Router -- Query & Exploration Endpoints

The tools router (`sre_agent/api/routers/tools.py`) has been significantly expanded beyond tool configuration to provide **direct API access** to GCP telemetry data for the dashboard explorer. These endpoints bypass the agent orchestrator for structured queries and only route through the LLM for natural language query translation.

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/tools/trace/{trace_id}` | GET | Fetch and visualize a single trace |
| `/api/tools/traces/query` | POST | Query traces by filter |
| `/api/tools/projects/list` | GET | List accessible GCP projects |
| `/api/tools/logs/analyze` | POST | Fetch logs and extract patterns |
| `/api/tools/logs/query` | POST | Fetch raw log entries (fast, no pattern extraction) |
| `/api/tools/metrics/query` | POST | Query time series metrics |
| `/api/tools/metrics/promql` | POST | Execute PromQL queries |
| `/api/tools/alerts/query` | POST | Query alerts/incidents |
| `/api/tools/bigquery/query` | POST | Execute BigQuery SQL queries |
| `/api/tools/bigquery/datasets` | GET | List BigQuery datasets |
| `/api/tools/bigquery/datasets/{id}/tables` | GET | List tables in a dataset |
| `/api/tools/bigquery/datasets/{id}/tables/{tid}/schema` | GET | Get table schema |
| `/api/tools/nl/query` | POST | Natural language query translation and execution |
| `/api/tools/config` | GET | Get tool configurations (grouped by category) |
| `/api/tools/config/{name}` | GET | Get specific tool configuration |
| `/api/tools/config/{name}` | PUT | Enable/disable a specific tool |
| `/api/tools/config/bulk` | POST | Bulk enable/disable tools |
| `/api/tools/test/{name}` | POST | Test a tool's connectivity |
| `/api/tools/test-all` | POST | Test all testable tools |

The **natural language query endpoint** (`/api/tools/nl/query`) accepts a user query, domain (traces, logs, metrics, bigquery), and uses the LLM to translate natural language into the appropriate structured query language, then executes it directly against the GCP API.

---

## Middleware & Security

The backend implements a multi-stage security pipeline in `sre_agent/api/middleware.py`.

### 1. Authentication Middleware (`auth_middleware`)
- **Header Extraction**: Processes `Authorization: Bearer <token>` for immediate identity.
- **OIDC Identity**: Uses the `X-ID-Token` header for fast, local identity verification without network latency.
- **Session Persistence**: Processes `sre_session_id` cookies for browser persistence.
- **Token Decryption**: Decrypts the session's AES-256 encrypted `access_token` on-the-fly for request injection.
- **Validation Caching**: Implements a 10-minute TTL cache for Google token validation results to eliminate repeated API overhead.
- **Context Injection**: Sets `Credentials` and `current_user_id` into `ContextVars` for downstream use by tools.

### 2. Telemetry & Observability
The backend is fully instrumented using OpenTelemetry:
- **Native GenAI Tracing**: Uses the `GoogleGenAiSdkInstrumentor` to capture high-fidelity spans of the agent's internal reasoning.
- **Multi-Receiver Pattern**: Supports simultaneous export to Langfuse (via `LANGFUSE_TRACING=true`) and Google Cloud Trace (via `OTEL_TO_CLOUD=true`).
- **Context Propagation**: Ensures that spans from the FastAPI proxy are correctly linked to the user's investigation trace.

---

## Core Services

The backend logic is decoupled into services found in `sre_agent/services/`.

### Session Service (`session.py`)
- Manages the lifecycle of ADK sessions.
- **Storage Backends**:
    - `DatabaseSessionService`: Local SQLite storage for development.
    - `VertexAiSessionService`: Cloud-native persistence for production.
- **Memory Sync**: Periodically freezes investigation findings into the Vertex AI Memory Bank for long-term retrieval.

### Storage Service (`storage.py`)
- Handles persistent **User Preferences** (distinct from conversation history).
- **Firestore Backend**: Used in Cloud Run for production-grade persistence.
- **File Backend**: Local `.json` file for dev-mode simplicity.

### Agent Engine Client (`agent_engine_client.py`)
- Acts as the bridge to Vertex AI reasoning engines.
- **Credential Splicing**: Takes the user's OAuth token (from the request) and injects it into the remote session state just-in-time for analysis.
- **Note**: LLM credential injection is disabled. Vertex AI Gemini API rejects Google Sign-In (Web Client) access tokens. Gemini executes using the Service Account (ADC). Only tools use End-User Credentials.

### Memory Manager (`memory_manager.py`)
- Provides memory service lifecycle management.
- Integrates with the memory subsystem (`sre_agent/memory/`) which includes mistake learning, pattern advising, and content sanitization.

---

## Development vs Production Modes

The backend behavior shifts significantly based on environment variables:

- **Local (Dev)**:
    - `SRE_AGENT_ID` is unset.
    - Agent runs in-process within the FastAPI server.
    - Logs go to stdout.
    - Sessions stored in local SQLite.
    - Model: Gemini 2.5 Flash/Pro.
- **Remote (Prod)**:
    - `SRE_AGENT_ID` is set to the Vertex Engine resource ID (used by Proxy to connect).
    - `RUNNING_IN_AGENT_ENGINE` is set to `true` on the Backend.
    - **Session Namespace**: Both components use `app_name="sre_agent"` to share the same session database. This prevents "Session not found" errors caused by the Backend not knowing its own Resource ID.
    - Backend acts as a thin, stateful proxy.
    - Logs emitted to Cloud Logging with structured severity.
    - Sessions and memory stored in managed Vertex AI services.
    - Model: Gemini 2.5 Flash/Pro (GA models required by Agent Engine).

---

## Callback Pipeline

The agent uses a composite callback pipeline for tool processing:

1. **`before_tool_memory_callback`**: Tracks tool call sequences for pattern learning.
2. **`composite_after_tool_callback`** (runs in order):
   - **Large payload handler** (`core/large_payload_handler.py`): Auto-summarizes oversized results via sandbox before they consume context window space.
   - **Truncation guard** (`core/tool_callbacks.py`): Hard safety net for anything that slipped through.
   - **Memory recording** (`memory/callbacks.py`): Persists tool outcomes for continuous learning.
3. **`on_tool_error_memory_callback`**: Records tool exceptions to memory.
4. **`after_agent_memory_callback`**: Automatic memory persistence after each agent turn.
5. **`before_model_callback` / `after_model_callback`**: Cost/token tracking and budget enforcement.
