# API Module

This directory contains the modular FastAPI application layer for the SRE Agent, refactored from the monolithic `server.py` into routers, middleware, helpers, and dependency injection.

## Structure

```
api/
├── app.py              # FastAPI application factory (create_app)
├── middleware.py        # Auth, CORS, tracing middleware, global exception handler
├── dependencies.py      # Shared dependencies (session manager, tool context injection)
├── routers/             # HTTP route modules
│   ├── __init__.py      #   Router exports (all 8 routers)
│   ├── agent.py         #   Chat agent endpoint (SSE streaming, A2UI protocol)
│   ├── sessions.py      #   Session CRUD endpoints (list, create, get, delete, rename)
│   ├── tools.py         #   Tool configuration, testing, and management endpoints
│   ├── health.py        #   Health check and debug endpoints
│   ├── system.py        #   System info: /api/config, /api/version, /api/debug, /api/suggestions
│   ├── permissions.py   #   Project permission validation endpoints
│   ├── preferences.py   #   User preferences CRUD endpoints
│   └── help.py          #   Help content endpoints (/api/help/manifest, /api/help/content/{id})
└── helpers/             # Shared helpers for request/response processing
    ├── __init__.py      #   Helper exports (dashboard event streaming, memory events)
    ├── dashboard_queue.py  # Dashboard event queue management
    ├── memory_events.py #   Memory event processing and streaming
    └── tool_events.py   #   Tool event emission for dashboard data channel
```

## Application Factory (`app.py`)

`create_app()` builds and configures the FastAPI application:

1. Initializes OpenTelemetry via `setup_telemetry()`.
2. Applies the MCP Pydantic bridge patch for compatibility.
3. Patches Pydantic `TypeAdapter` for ADK 1.23.0 + Pydantic 2.12+ compatibility (do not remove until ADK is updated).
4. Enables JSON Schema feature for Vertex AI compatibility.
5. Registers all 8 routers (agent, sessions, tools, health, system, permissions, preferences, help).
6. Configures middleware (auth, CORS, tracing).
7. Optionally includes ADK agent routes for the A2UI protocol.
8. Registers tool test functions for runtime connectivity checks.

## Middleware (`middleware.py`)

Configures the following middleware in order:

- **Global Exception Handler**: Catches unhandled exceptions and returns structured 500 responses.
- **Tracing Middleware**: Captures or generates correlation IDs (`X-Correlation-ID` / `X-Request-ID`), propagates to ContextVars, adds OTel span attributes, and logs request durations.
- **Auth Middleware**: Validates `Authorization: Bearer <token>` headers, extracts user identity, sets project ID from `X-GCP-Project-ID` header into ContextVars. Supports both ID tokens and access tokens.
- **CORS Middleware**: Configures allowed origins for cross-origin requests from the Flutter frontend.

## Dependencies (`dependencies.py`)

Provides shared dependency injection:

- `get_session_manager()`: Returns the `ADKSessionManager` singleton.
- `get_tool_context()`: Creates a `ToolContext` with a dummy session/invocation for API endpoints that need to call tools directly (outside the agent loop).

## Routers

### `agent.py` -- Chat Agent
The primary chat endpoint. Handles SSE (Server-Sent Events) streaming of agent responses following the A2UI protocol. Routes requests to either the local in-process agent or the remote Vertex AI Agent Engine depending on configuration (`SRE_AGENT_ID`).

### `sessions.py` -- Session Management
CRUD operations for conversation sessions:
- List sessions for a user
- Create new sessions
- Get session details with message history
- Delete sessions
- Rename sessions

### `tools.py` -- Tool Configuration
Tool management and runtime testing:
- List all tools with their configuration and enabled status
- Update tool configuration (enable/disable)
- Run connectivity tests for individual tools
- Batch test execution

### `health.py` -- Health Checks
System health and readiness:
- `GET /health` -- Basic liveness check
- Debug information endpoints

### `system.py` -- System Information
Public configuration and system metadata:
- `GET /api/config` -- Frontend configuration (client ID, auth mode, guest mode)
- `GET /api/version` -- Version, git SHA, and build timestamp
- `GET /api/debug` -- Debug summary (auth state, telemetry state)
- `GET /api/suggestions` -- Contextual follow-up suggestions (LLM-generated from conversation history and active alerts)

### `permissions.py` -- Project Permissions
GCP project permission validation:
- Validate whether the authenticated user has required IAM permissions on a target GCP project
- Pre-flight checks before investigation

### `preferences.py` -- User Preferences
User preference management:
- Get and update user preferences (stored via Firestore or SQLite)
- Theme, notification, and display settings

### `help.py` -- Help Content
Documentation serving:
- `GET /api/help/manifest` -- Help topic manifest (JSON)
- `GET /api/help/content/{content_id}` -- Markdown content for a specific help topic
- Directory traversal protection via path validation

## Helpers (`helpers/`)

### `tool_events.py` -- Dashboard Data Channel
Emits `{"type": "dashboard", ...}` events during tool execution. These events are streamed to the frontend via SSE and consumed by the Mission Control dashboard panels (alerts, traces, metrics, logs, remediation, council activity).

### `dashboard_queue.py` -- Dashboard Event Queue
Manages the per-session queue of dashboard events. Events are enqueued during tool execution and dequeued by the SSE streaming endpoint.

### `memory_events.py` -- Memory Event Processing
Handles memory-related events during agent execution, including investigation state updates, finding persistence, and mistake learning callbacks.
