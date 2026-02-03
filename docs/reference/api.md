# API Reference

The SRE Agent exposes a FastAPI backend that serves as both a proxy for the Agent Engine and a host for the Flutter frontend.

**Base URL**: `http://localhost:8001` (development) or your Cloud Run URL (production).

---

## Authentication

Most endpoints require authentication via one of:
- **Session Cookie**: Set by `POST /api/auth/login` (browser-based flows).
- **Bearer Token**: `Authorization: Bearer <google-oauth-token>` header.

Additionally, GCP-scoped endpoints require:
- **Project Header**: `X-GCP-Project-ID: <your-gcp-project>` — injected automatically by the Flutter frontend's `ProjectInterceptorClient`.

When `ENABLE_AUTH=false` (local development only), authentication is bypassed and dummy credentials are injected.

---

## Standard Error Response

All endpoints return errors in a consistent format:

```json
{
    "detail": "Human-readable error description"
}
```

HTTP status codes follow standard conventions:
- `400` — Bad request (invalid parameters)
- `401` — Unauthorized (missing or invalid credentials)
- `403` — Forbidden (insufficient permissions)
- `404` — Resource not found
- `500` — Internal server error

---

## Endpoints

### Agent Interface

#### `POST /agent`
#### `POST /api/genui/chat`

The main entry point for interacting with the agent. Both routes are equivalent.

**Headers:**
| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes | `Bearer <google-oauth-token>` |
| `X-GCP-Project-ID` | Yes | Target GCP project for investigation |
| `Content-Type` | Yes | `application/json` |

**Request Body:**
```json
{
    "query": "Investigate high latency on service X",
    "session_id": "optional-session-id"
}
```

**Response**: NDJSON stream (`Content-Type: application/x-ndjson`)

Each line is a JSON object representing an agent event:

| Event Type | Description | Example |
|------------|-------------|---------|
| `thought` | Agent's internal reasoning (Chain-of-Thought) | `{"type": "thought", "content": "I should check traces first..."}` |
| `call_tool` | Agent is invoking a tool | `{"type": "call_tool", "tool": "fetch_trace", "args": {...}}` |
| `tool_output` | Result of a tool execution | `{"type": "tool_output", "tool": "fetch_trace", "result": {...}}` |
| `ui_event` | GenUI widget payload for the Flutter frontend | `{"type": "ui_event", "widget": "trace_waterfall", "data": {...}}` |
| `dashboard` | Dashboard data channel event (decoupled from chat) | `{"type": "dashboard", "metrics": [...], "alerts": [...]}` |
| `text` | Final natural language response | `{"type": "text", "content": "The root cause is..."}` |
| `error` | Error during processing | `{"type": "error", "message": "..."}` |

**Tool Output Format** (within `tool_output` events):
```json
{
    "status": "success" | "error" | "partial",
    "result": {},
    "error": "message (only if status=error)",
    "metadata": {},
    "non_retryable": false
}
```

---

### Session Management

#### `POST /api/sessions`
Create a new investigation session.

**Request Body:**
```json
{
    "project_id": "optional-gcp-project-id"
}
```

**Response** (`200 OK`):
```json
{
    "session_id": "uuid-string",
    "created_at": "2026-02-02T10:00:00Z"
}
```

#### `GET /api/sessions`
List all sessions for the current user.

**Response** (`200 OK`):
```json
[
    {
        "session_id": "uuid",
        "title": "Session title",
        "created_at": "2026-02-02T10:00:00Z",
        "updated_at": "2026-02-02T10:30:00Z"
    }
]
```

#### `GET /api/sessions/{session_id}`
Retrieve a session with its full message history.

#### `PATCH /api/sessions/{session_id}`
Update session metadata (e.g., title).

**Request Body:**
```json
{
    "title": "New session title"
}
```

#### `DELETE /api/sessions/{session_id}`
Delete a session permanently.

#### `GET /api/sessions/{session_id}/history`
Get the message history reconstructed from ADK events.

---

### Authentication

#### `POST /api/auth/login`
Exchange a Google OAuth access token for a session cookie.

**Request Body:**
```json
{
    "access_token": "google-oauth-access-token"
}
```

**Response**: Sets `HttpOnly` session cookie and returns user info.

#### `POST /api/auth/logout`
Clear the session cookie.

#### `GET /api/auth/info`
Returns current authentication status and token scopes.

**Headers:** `Authorization: Bearer <token>`

**Response** (`200 OK`):
```json
{
    "authenticated": true,
    "email": "user@example.com",
    "scopes": ["openid", "email", "profile"]
}
```

---

### Tools Management

#### `GET /api/tools/config`
Get all tool configurations. Supports optional `?category=<category>` query parameter.

#### `GET /api/tools/config/{tool_name}`
Get configuration for a specific tool.

#### `PUT /api/tools/config/{tool_name}`
Update a tool's configuration (enable/disable).

**Request Body:**
```json
{
    "enabled": true
}
```

#### `POST /api/tools/config/bulk`
Bulk update multiple tool configurations.

#### `POST /api/tools/test/{tool_name}`
Test a specific tool's connectivity and functionality.

#### `POST /api/tools/test-all`
Test all testable tools and return results.

#### `GET /api/tools/trace/{trace_id}`
Fetch and summarize a specific trace by ID.

#### `GET /api/tools/projects/list`
List accessible GCP projects for the current user.

#### `POST /api/tools/logs/analyze`
Fetch logs from Cloud Logging and extract patterns.

---

### Preferences

#### `GET /api/preferences/project`
Get the selected GCP project for the current user.

#### `POST /api/preferences/project`
Set the selected GCP project.

#### `GET /api/preferences/tools`
Get tool configuration preferences.

#### `POST /api/preferences/tools`
Set tool configuration preferences.

#### `GET /api/preferences/projects/recent`
Get recently used projects.

#### `POST /api/preferences/projects/recent`
Set recently used projects.

---

### Permissions

#### `GET /api/permissions/info`
Get information about required IAM roles and service account.

#### `GET /api/permissions/gcloud`
Generate `gcloud` commands for granting the agent required permissions on a project.

#### `GET /api/permissions/check/{project_id}`
Check if the agent has the required IAM permissions on a given project.

---

### Help System

#### `GET /api/help/manifest`
Retrieve the manifest of available help topics (Documentation-as-Code model).

#### `GET /api/help/content/{content_id}`
Retrieve rendered markdown content for a specific help topic.

---

### System & Configuration

#### `GET /api/config`
Get public configuration for the frontend (Google Client ID, auth enabled flag, etc.).

**Response** (`200 OK`):
```json
{
    "google_client_id": "xxx.apps.googleusercontent.com",
    "auth_enabled": true
}
```

#### `GET /api/suggestions`
Get contextual follow-up suggestions for the current user/session.

---

### Health & Debug

#### `GET /health`
Returns `{"status": "ok"}` if the service is running. Use for load balancer health checks.

#### `GET /api/debug`
Returns detailed internal state for debugging (telemetry status, auth context, active configuration). **Development only** — should be disabled or access-restricted in production.

---

## Endpoint Summary

| Method | Path | Router | Auth Required |
|--------|------|--------|--------------|
| POST | `/agent` | agent | Yes |
| POST | `/api/genui/chat` | agent | Yes |
| GET | `/api/suggestions` | agent | Yes |
| POST | `/api/sessions` | sessions | Yes |
| GET | `/api/sessions` | sessions | Yes |
| GET | `/api/sessions/{id}` | sessions | Yes |
| PATCH | `/api/sessions/{id}` | sessions | Yes |
| DELETE | `/api/sessions/{id}` | sessions | Yes |
| GET | `/api/sessions/{id}/history` | sessions | Yes |
| POST | `/api/auth/login` | system | No |
| POST | `/api/auth/logout` | system | No |
| GET | `/api/auth/info` | system | Yes |
| GET | `/api/config` | system | No |
| GET | `/api/tools/config` | tools | Yes |
| GET | `/api/tools/config/{name}` | tools | Yes |
| PUT | `/api/tools/config/{name}` | tools | Yes |
| POST | `/api/tools/config/bulk` | tools | Yes |
| POST | `/api/tools/test/{name}` | tools | Yes |
| POST | `/api/tools/test-all` | tools | Yes |
| GET | `/api/tools/trace/{id}` | tools | Yes |
| GET | `/api/tools/projects/list` | tools | Yes |
| POST | `/api/tools/logs/analyze` | tools | Yes |
| GET | `/api/preferences/project` | preferences | Yes |
| POST | `/api/preferences/project` | preferences | Yes |
| GET | `/api/preferences/tools` | preferences | Yes |
| POST | `/api/preferences/tools` | preferences | Yes |
| GET | `/api/preferences/projects/recent` | preferences | Yes |
| POST | `/api/preferences/projects/recent` | preferences | Yes |
| GET | `/api/permissions/info` | permissions | Yes |
| GET | `/api/permissions/gcloud` | permissions | Yes |
| GET | `/api/permissions/check/{id}` | permissions | Yes |
| GET | `/api/help/manifest` | help | No |
| GET | `/api/help/content/{id}` | help | No |
| GET | `/health` | health | No |
| GET | `/api/debug` | health | No |

---
*Last verified: 2026-02-02 — Auto SRE Team*
