# Backend Documentation

The SRE Agent backend is a FastAPI-based application that serves as the orchestration layer for the agent and the primary API for the Flutter frontend.

## API Structure

The backend is organized into modular routers under `sre_agent/api/routers/`.

### Core Routers

| Router | Description | Key Endpoints |
| :--- | :--- | :--- |
| **Agent** | Main chat and orchestration | `POST /agent`, `POST /api/genui/chat`, `GET /api/suggestions` |
| **System** | Auth and state management | `POST /api/auth/login`, `POST /api/auth/logout` |
| **Sessions** | Conversation history | `GET /api/sessions`, `DELETE /api/sessions/{id}`, `PATCH /api/sessions/{id}` |
| **Tools** | Discovery and config | `GET /api/tools/config`, `POST /api/tools/test/{name}` |
| **Preferences** | User settings | `GET /api/preferences`, `PUT /api/preferences` |

---

## Middleware & Security

The backend implements a multi-stage security pipeline in `sre_agent/api/middleware.py`.

### 1. Authentication Middleware (`auth_middleware`)
- **Header Extraction**: Processes `Authorization: Bearer <token>` for immediate identity.
- **Session Persistence**: Processes `sre_session_id` cookies for browser persistence.
- **EUC Verification**: Regularly validates access tokens against Google's tokeninfo endpoint to ensure identity has not been revoked.
- **Context Injection**: sets `Credentials` and `current_user_id` into `ContextVars` for downstream use by tools.

### 2. Telemetry Propagation
- Ensures that spans and traces from the backend itself are properly linked to the user's investigation if OpenTelemetry is enabled.

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
- **Credential Splicing**: It is responsible for taking the user's OAuth token (from the request) and injecting it into the remote session state just-in-time for analysis.

---

## Development vs Production Modes

The backend behavior shifts significantly based on environment variables:

- **Local (Dev)**:
    - `SRE_AGENT_ID` is unset.
    - Agent runs as a subprocess.
    - Logs go to stdout.
    - Sessions stored in local SQLite.
- **Remote (Prod)**:
    - `SRE_AGENT_ID` is set to the Vertex Engine resource ID (used by Proxy to connect).
    - `RUNNING_IN_AGENT_ENGINE` is set to `true` on the Backend.
    - **Session Namespace**: Both components use `app_name="sre_agent"` to share the same session database. This prevents "Session not found" errors caused by the Backend not knowing its own Resource ID.
    - Backend acts as a thin, stateful proxy.
    - Logs emitted to Cloud Logging with structured severity.
    - Sessions and memory stored in managed Vertex AI services.
