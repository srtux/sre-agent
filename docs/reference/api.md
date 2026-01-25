# API Reference

The SRE Agent exposes a FastAPI backend that serves as both a proxy for the Agent Engine and a host for the Flutter frontend.

## Endpoints

### Agent Interface

#### `POST /agent`
The main entry point for interacting with the agent.

**Request Body (NDJSON):**
```json
{"query": "Start an investigation for service X"}
```

**Response (NDJSON Stream):**
The response is a stream of events representing the agent's thought process and actions.

| Event Type | Description |
|------------|-------------|
| `thought` | The agent's internal reasoning (CoT). |
| `call_tool` | The agent is executing a tool. |
| `tool_output` | The result of a tool execution. |
| `ui_event` | A GenUI widget payload (e.g., `show_trace_waterfall`, `show_metrics_chart`). |
| `text` | The final natural language response. |

### Session Management

#### `GET /api/sessions`
List all investigation sessions for the current user.

#### `GET /api/sessions/{session_id}`
Retrieve the full event history of a specific session.

### Authentication

#### `GET /api/auth/info`
Returns current authentication status and token scopes.
**Headers:** `Authorization: Bearer <token>`

### Health & Debug

#### `GET /health`
Returns `{"status": "ok"}` if the service is running.

#### `GET /api/debug`
Returns detailed internal state (telemetry, auth context) for debugging.
