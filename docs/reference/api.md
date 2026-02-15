# API Reference

The SRE Agent exposes a FastAPI backend that serves as both a proxy for the Agent Engine and a host for the Flutter frontend.

**Base URL**: `http://localhost:8001` (development) or your Cloud Run URL (production).

---

## Authentication

Most endpoints require authentication via one of:
- **Session Cookie**: Set by `POST /api/auth/login` (browser-based flows).
- **Bearer Token**: `Authorization: Bearer <google-oauth-token>` header.
- **Guest Mode**: `X-Guest-Mode: true` header (demo/synthetic data only).

Additionally, GCP-scoped endpoints require:
- **Project Header**: `X-GCP-Project-ID: <your-gcp-project>` — injected automatically by the Flutter frontend's `ProjectInterceptorClient`.

Optionally, for faster identity verification:
- **ID Token Header**: `X-ID-Token: <oidc-id-token>` — bypasses the access token validation round-trip by performing local JWT verification.

When `ENABLE_AUTH=false` (local development only), authentication is bypassed and dummy credentials are injected.

---

## Middleware Stack

The following middleware is applied to all requests (outermost first):

1. **Tracing Middleware** — Assigns or propagates `X-Correlation-ID` and `X-Request-ID`, attaches OpenTelemetry trace context, logs request start/end with timing, and injects `X-Correlation-ID` and `X-Trace-ID` response headers.
2. **Auth Middleware** — Extracts `Authorization: Bearer` tokens, `X-ID-Token` headers, `X-Guest-Mode` headers, and `X-GCP-Project-ID` headers into Python `ContextVar` objects. Falls back to session cookies and dev-mode bypass (`ENABLE_AUTH=false`). Clears credentials after each request to prevent leakage.
3. **CORS Middleware** — Configurable origins (restricted by default, `CORS_ALLOW_ALL=true` opens all).
4. **Global Exception Handler** — Catches unhandled exceptions and returns a `500` JSON response.

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
- `502` — Upstream tool error (tool returned an error status)

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
| `X-ID-Token` | No | OIDC ID Token for faster identity verification |
| `Content-Type` | Yes | `application/json` |

**Request Body:**
```json
{
    "messages": [{"role": "user", "text": "Investigate high latency on service X"}],
    "session_id": "optional-session-id",
    "project_id": "optional-gcp-project-id",
    "user_id": "default"
}
```

**Response**: NDJSON stream (`Content-Type: application/x-ndjson`)

Each line is a JSON object representing an agent event:

| Event Type | Description | Example |
|------------|-------------|---------|
| `session` | Session ID initialization | `{"type": "session", "session_id": "uuid"}` |
| `trace_info` | Cloud Trace deep-link metadata | `{"type": "trace_info", "trace_id": "...", "project_id": "..."}` |
| `text` | Final natural language response | `{"type": "text", "content": "The root cause is..."}` |
| `thought` | Agent's internal reasoning (Chain-of-Thought) | `{"type": "text", "content": "\n\n**Thought**: I should check traces first...\n\n"}` |
| `tool_call` | Agent is invoking a tool | `{"type": "tool_call", "tool": "fetch_trace", "args": {...}, "call_id": "..."}` |
| `tool_response` | Result of a tool execution | `{"type": "tool_response", "tool": "fetch_trace", "result": {...}, "call_id": "..."}` |
| `dashboard` | Dashboard data channel event (decoupled from chat) | `{"type": "dashboard", "metrics": [...], "alerts": [...]}` |
| `a2ui` | GenUI A2UI protocol widget payload | `{"type": "a2ui", "message": {...}}` |
| `ui` | UI surface marker | `{"type": "ui", "surface_id": "..."}` |
| `memory` | Memory event for UI toasts | `{"type": "memory", "action": "...", "content": "..."}` |
| `error` | Error during processing | `{"type": "text", "content": "\n\n**Error:** ..."}` |

**Tool Output Format** (within `tool_response` events):
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
    "user_id": "default",
    "project_id": "optional-gcp-project-id",
    "title": "optional-session-title"
}
```

**Response** (`200 OK`):
```json
{
    "id": "uuid-string",
    "user_id": "default",
    "project_id": "my-project",
    "state": {}
}
```

#### `GET /api/sessions`
List all sessions for a user.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | string | `"default"` | User ID to filter sessions |

**Response** (`200 OK`):
```json
{
    "sessions": [
        {
            "id": "uuid",
            "state": {"title": "Session title"},
            "last_update_time": 1706868600.0
        }
    ]
}
```

#### `GET /api/sessions/{session_id}`
Retrieve a session with its full message history.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | string | `"default"` | User ID for session lookup |

**Response** (`200 OK`):
```json
{
    "id": "uuid",
    "user_id": "default",
    "state": {},
    "messages": [
        {"role": "user", "content": "Investigate latency", "timestamp": 1706868600.0}
    ],
    "last_update_time": 1706868600.0
}
```

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

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | string | `"default"` | User ID for session lookup |

#### `GET /api/sessions/{session_id}/history`
Get the message history reconstructed from ADK events.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_id` | string | `"default"` | User ID for session lookup |

---

### Authentication

#### `POST /api/auth/login`
Exchange a Google OAuth access token for a session cookie.

**Request Body:**
```json
{
    "access_token": "google-oauth-access-token",
    "id_token": "optional-oidc-id-token",
    "project_id": "optional-gcp-project-id"
}
```

**Response**: Sets `HttpOnly` session cookie (`sre_session_id`) and returns user info.
```json
{
    "status": "success",
    "session_id": "uuid",
    "email": "user@example.com"
}
```

#### `POST /api/auth/logout`
Clear the session cookie.

#### `GET /api/auth/info`
Returns current authentication status and token scopes.

**Headers:** `Authorization: Bearer <token>` and optionally `X-ID-Token: <id-token>`

**Response** (`200 OK`):
```json
{
    "authenticated": true,
    "token_info": {
        "valid": true,
        "email": "user@example.com",
        "expires_in": 3600,
        "scopes": ["openid", "email", "profile"],
        "error": null
    },
    "project_id": "my-project"
}
```

---

### Tools Management

#### `GET /api/tools/config`
Get all tool configurations. Supports optional query parameters.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `category` | string | `null` | Filter by tool category (e.g., `trace_fetch`, `mcp`, `sandbox`) |
| `enabled_only` | bool | `false` | If true, only return enabled tools |

**Response** (`200 OK`):
```json
{
    "tools": {
        "trace_fetch": [{"name": "fetch_trace", "display_name": "...", ...}],
        "mcp": [...]
    },
    "summary": {"total": 90, "enabled": 88, "disabled": 2, "testable": 20},
    "categories": ["discovery", "orchestration", "trace_fetch", ...]
}
```

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

**Request Body:**
```json
{
    "fetch_trace": true,
    "mcp_execute_sql": false
}
```

#### `POST /api/tools/test/{tool_name}`
Test a specific tool's connectivity and functionality.

#### `POST /api/tools/test-all`
Test all testable tools and return results.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `category` | string | `null` | Filter to test only tools in a specific category |

---

### Tools — Direct Query Endpoints (Explorer)

These endpoints bypass the agent orchestrator for structured queries (logs, traces, metrics, alerts, SQL) and are used by the frontend's Dashboard Explorer.

#### `GET /api/tools/trace/{trace_id}`
Fetch and summarize a specific trace by ID. Returns GenUI-compatible trace waterfall data.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_id` | string | `null` | GCP project override |

#### `POST /api/tools/traces/query`
Query traces by filter. Fetches a list of matching traces and retrieves full details for each (up to 5).

**Request Body:**
```json
{
    "filter": "+service:my-service",
    "minutes_ago": 60,
    "project_id": "optional",
    "limit": 10
}
```

#### `GET /api/tools/projects/list`
List accessible GCP projects using the caller's EUC.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | `null` | Optional filter query |

#### `POST /api/tools/logs/analyze`
Fetch logs from Cloud Logging and extract patterns using Drain3.

**Request Body:**
```json
{
    "filter": "severity>=ERROR",
    "project_id": "optional"
}
```

#### `POST /api/tools/logs/query`
Fetch raw log entries without pattern extraction (faster for explorer). Returns LogEntriesData-compatible format.

**Request Body:**
```json
{
    "filter": "severity>=WARNING",
    "minutes_ago": 60,
    "limit": 50,
    "project_id": "optional"
}
```

#### `POST /api/tools/metrics/query`
Query time series metrics. Returns MetricSeries-compatible format (metric_name, points, labels).

**Request Body:**
```json
{
    "filter": "metric.type=\"compute.googleapis.com/instance/cpu/utilization\"",
    "minutes_ago": 60,
    "project_id": "optional"
}
```

#### `POST /api/tools/metrics/promql`
Execute a PromQL query. Returns MetricSeries-compatible format.

**Request Body:**
```json
{
    "query": "rate(http_requests_total[5m])",
    "minutes_ago": 60,
    "project_id": "optional"
}
```

#### `POST /api/tools/alerts/query`
Query alerts/incidents. Returns IncidentTimelineData-compatible format.

**Request Body:**
```json
{
    "filter": "optional-filter",
    "minutes_ago": 60,
    "project_id": "optional"
}
```

#### `POST /api/tools/bigquery/query`
Execute a BigQuery SQL query and return tabular results.

**Request Body:**
```json
{
    "sql": "SELECT * FROM `project.dataset.table` LIMIT 10",
    "project_id": "optional"
}
```

**Response:**
```json
{
    "columns": ["col1", "col2"],
    "rows": [{"col1": "val1", "col2": "val2"}]
}
```

#### `GET /api/tools/bigquery/datasets`
List datasets in the BigQuery project.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_id` | string | `null` | GCP project override |

#### `GET /api/tools/bigquery/datasets/{dataset_id}/tables`
List tables in a BigQuery dataset.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_id` | string | `null` | GCP project override |

#### `GET /api/tools/bigquery/datasets/{dataset_id}/tables/{table_id}/schema`
Get the schema of a BigQuery table.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_id` | string | `null` | GCP project override |

---

### Tools — Natural Language Query Endpoint

#### `POST /api/tools/nl/query`
Translate a natural language query into a structured query and execute it. This is the only explorer endpoint that involves the LLM.

**Request Body:**
```json
{
    "query": "Show me errors from the payment service in the last 30 minutes",
    "domain": "logs",
    "natural_language": true,
    "minutes_ago": 60,
    "project_id": "optional"
}
```

**Supported domains:** `traces`, `logs`, `metrics`, `bigquery`

The LLM translates the natural language request into the appropriate structured query language (Cloud Trace filter, Cloud Logging filter, MQL/PromQL, or BigQuery SQL), then the structured query is executed directly against the GCP API.

---

### Preferences

#### `GET /api/preferences/project`
Get the selected GCP project for the current user.

#### `POST /api/preferences/project`
Set the selected GCP project.

**Request Body:**
```json
{
    "project_id": "my-project",
    "user_id": "default"
}
```

#### `GET /api/preferences/tools`
Get tool configuration preferences.

#### `POST /api/preferences/tools`
Set tool configuration preferences.

**Request Body:**
```json
{
    "enabled_tools": {"fetch_trace": true, "mcp_execute_sql": false},
    "user_id": "default"
}
```

#### `GET /api/preferences/projects/recent`
Get recently used projects.

#### `POST /api/preferences/projects/recent`
Set recently used projects.

**Request Body:**
```json
{
    "projects": [{"project_id": "proj-1", "display_name": "Project One"}],
    "user_id": "default"
}
```

#### `GET /api/preferences/projects/starred`
Get starred (pinned) projects for a user.

#### `POST /api/preferences/projects/starred`
Set starred (pinned) projects for a user.

**Request Body:**
```json
{
    "projects": [{"project_id": "proj-1", "display_name": "Project One"}],
    "user_id": "default"
}
```

#### `POST /api/preferences/projects/starred/toggle`
Toggle the starred state of a single project.

**Request Body:**
```json
{
    "project_id": "my-project",
    "display_name": "My Project",
    "starred": true,
    "user_id": "default"
}
```

---

### Permissions

#### `GET /api/permissions/info`
Get information about required IAM roles and service account.

**Response** (`200 OK`):
```json
{
    "service_account": "sre-agent@PROJECT.iam.gserviceaccount.com",
    "roles": [
        "roles/cloudtrace.user",
        "roles/logging.viewer",
        "roles/monitoring.viewer",
        "roles/compute.viewer"
    ],
    "project_id": "agent-host-project"
}
```

#### `GET /api/permissions/gcloud`
Generate `gcloud` commands for granting the agent required permissions on a project.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | string | Yes | Target GCP project ID |

**Response** (`200 OK`):
```json
{
    "project_id": "my-project",
    "service_account": "sre-agent@...",
    "commands": ["gcloud projects add-iam-policy-binding ..."],
    "one_liner": "gcloud ... && gcloud ..."
}
```

#### `GET /api/permissions/check/{project_id}`
Check if the agent has the required IAM permissions on a given project. Performs lightweight API calls to verify access to Cloud Trace, Cloud Logging, and Cloud Monitoring.

**Response** (`200 OK`):
```json
{
    "project_id": "my-project",
    "results": {
        "cloudtrace.user": {"status": "ok", "message": null},
        "logging.viewer": {"status": "ok", "message": null},
        "monitoring.viewer": {"status": "missing", "message": "Permission Denied (403)"}
    },
    "all_ok": false,
    "timestamp": "2026-02-15T10:00:00+00:00"
}
```

---

### Help System

#### `GET /api/help/manifest`
Retrieve the manifest of available help topics (Documentation-as-Code model).

#### `GET /api/help/content/{content_id}`
Retrieve rendered markdown content for a specific help topic. Includes directory traversal protection.

---

### System & Configuration

#### `GET /api/config`
Get public configuration for the frontend (Google Client ID, auth enabled flag, guest mode flag).

**Response** (`200 OK`):
```json
{
    "google_client_id": "xxx.apps.googleusercontent.com",
    "auth_enabled": true,
    "guest_mode_enabled": true
}
```

#### `GET /api/version`
Return build version metadata (version, git SHA, build timestamp).

**Response** (`200 OK`):
```json
{
    "version": "0.2.0",
    "git_sha": "abc1234",
    "build_timestamp": "2026-02-15T10:00:00Z"
}
```

#### `GET /api/suggestions`
Get contextual follow-up suggestions for the current user/session.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_id` | string | `null` | GCP project context |
| `session_id` | string | `null` | Current session ID |
| `user_id` | string | `"default"` | User ID |

**Response** (`200 OK`):
```json
{
    "suggestions": [
        "Analyze last hour's logs",
        "List active incidents",
        "Check for high latency"
    ]
}
```

---

### Health & Debug

#### `GET /health`
Returns `{"status": "ok", "version": "0.2.0"}` if the service is running. Use for load balancer health checks. Health check logs are suppressed after the first successful check to reduce noise.

#### `GET /api/debug`
Returns detailed internal state for debugging (telemetry status, auth context, active configuration). **Development only** — should be disabled or access-restricted in production.

---

## Endpoint Summary

| Method | Path | Router | Auth Required |
|--------|------|--------|--------------|
| POST | `/agent` | agent | Yes |
| POST | `/api/genui/chat` | agent | Yes |
| GET | `/api/suggestions` | agent / system | Yes |
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
| GET | `/api/version` | system | No |
| GET | `/api/tools/config` | tools | Yes |
| GET | `/api/tools/config/{name}` | tools | Yes |
| PUT | `/api/tools/config/{name}` | tools | Yes |
| POST | `/api/tools/config/bulk` | tools | Yes |
| POST | `/api/tools/test/{name}` | tools | Yes |
| POST | `/api/tools/test-all` | tools | Yes |
| GET | `/api/tools/trace/{id}` | tools | Yes |
| POST | `/api/tools/traces/query` | tools | Yes |
| GET | `/api/tools/projects/list` | tools | Yes |
| POST | `/api/tools/logs/analyze` | tools | Yes |
| POST | `/api/tools/logs/query` | tools | Yes |
| POST | `/api/tools/metrics/query` | tools | Yes |
| POST | `/api/tools/metrics/promql` | tools | Yes |
| POST | `/api/tools/alerts/query` | tools | Yes |
| POST | `/api/tools/bigquery/query` | tools | Yes |
| GET | `/api/tools/bigquery/datasets` | tools | Yes |
| GET | `/api/tools/bigquery/datasets/{id}/tables` | tools | Yes |
| GET | `/api/tools/bigquery/datasets/{did}/tables/{tid}/schema` | tools | Yes |
| POST | `/api/tools/nl/query` | tools | Yes |
| GET | `/api/preferences/project` | preferences | Yes |
| POST | `/api/preferences/project` | preferences | Yes |
| GET | `/api/preferences/tools` | preferences | Yes |
| POST | `/api/preferences/tools` | preferences | Yes |
| GET | `/api/preferences/projects/recent` | preferences | Yes |
| POST | `/api/preferences/projects/recent` | preferences | Yes |
| GET | `/api/preferences/projects/starred` | preferences | Yes |
| POST | `/api/preferences/projects/starred` | preferences | Yes |
| POST | `/api/preferences/projects/starred/toggle` | preferences | Yes |
| GET | `/api/permissions/info` | permissions | Yes |
| GET | `/api/permissions/gcloud` | permissions | Yes |
| GET | `/api/permissions/check/{id}` | permissions | Yes |
| GET | `/api/help/manifest` | help | No |
| GET | `/api/help/content/{id}` | help | No |
| GET | `/health` | health | No |
| GET | `/api/debug` | health | No |

---
*Last verified: 2026-02-15 — Auto SRE Team*
