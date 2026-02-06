# Project Selector

The project selector provides a cloud-console-style picker that lets users choose which GCP project the agent should investigate. The selected project is propagated throughout the system -- into API headers, agent prompts, and tool invocations.

## User Experience

The project selector appears in the AppBar of the Conversation page.  It provides:

| Section     | Description |
|-------------|-------------|
| **Starred** | Projects the user has explicitly pinned (persisted in Firestore). |
| **Recent**  | Last 10 projects the user has selected (persisted in Firestore). |
| **All**     | Full list returned by `projects:search` (capped at the first 10 when not searching). |
| **Search**  | Debounced (500 ms) backend search; also allows entering an arbitrary project ID. |

Star toggling is immediate (optimistic UI) and persisted via `POST /api/preferences/projects/starred/toggle`.

## Data Flow

```
User selects project
       |
       v
ProjectService.selectProjectInstance(project)
  +-- Updates ValueNotifier (UI rebuilds)
  +-- Persists to SharedPreferences (local)
  +-- POST /api/preferences/project (backend, Firestore)
  +-- Updates recent-projects list (local + backend)

Every API call
       |
       v
ProjectInterceptorClient.send()
  +-- Injects X-GCP-Project-ID header  <-- primary EUC propagation
  +-- Injects Authorization header (Bearer token)
  +-- Injects X-User-ID header

Backend middleware
       |
       v
auth_middleware() extracts headers and sets ContextVars:
  - set_current_credentials(creds)
  - set_current_project_id(project_id)
  - set_current_user_id(user_email)

Agent prompt injection
       |
       v
agent.py builds DomainContext(project_id=...)
  +-- Injected into user message: [CURRENT PROJECT: <id>]
  +-- Passed to prompt_composer: "All queries must target this project..."
  +-- Passed to runner: prepended to every turn

Tool invocation
       |
       v
Tools call get_project_id_from_tool_context() to scope GCP API calls.
Tools call get_credentials_from_tool_context() to use EUC.
```

## Backend API Endpoints

### Project Listing

```
GET /api/tools/projects/list?query=<search>
```

Uses the caller's EUC (End-User Credentials from the `Authorization` header) to call the Cloud Resource Manager `projects:search` API.  Returns:

```json
{"projects": [{"project_id": "...", "display_name": "...", "project_number": "..."}]}
```

### Preferences (per-user, Firestore-backed)

User identity is resolved from the auth middleware's ContextVar (`get_current_user_id()`) so preferences are scoped to the authenticated user, not a shared "default" key.

| Method | Path | Description |
|--------|------|-------------|
| GET    | `/api/preferences/project` | Get selected project for the authenticated user |
| POST   | `/api/preferences/project` | Set selected project (`{"project_id": "..."}`) |
| GET    | `/api/preferences/projects/recent` | Get recent projects list |
| POST   | `/api/preferences/projects/recent` | Set recent projects list |
| GET    | `/api/preferences/projects/starred` | Get starred (pinned) projects |
| POST   | `/api/preferences/projects/starred` | Replace entire starred list |
| POST   | `/api/preferences/projects/starred/toggle` | Add/remove a single starred project |

Toggle request body:
```json
{
  "project_id": "my-project",
  "display_name": "My Project",
  "starred": true
}
```

### Storage Backend

Preferences are stored via `StorageService` which auto-selects:
- **Firestore** (`user_preferences` collection) when running on Cloud Run / GKE (`K_SERVICE` or `USE_FIRESTORE` env var set).
- **Local JSON file** (`.sre_agent_preferences.json`) in development.

Keys are scoped per-user: `<user_email>:starred_projects`, `<user_email>:recent_projects`, etc.

## Frontend Implementation

### Key Files

| File | Purpose |
|------|---------|
| `lib/services/project_service.dart` | State management, API calls, starred/recent logic |
| `lib/services/api_client.dart` | `ProjectInterceptorClient` -- injects headers |
| `lib/pages/conversation_page.dart` | `_ProjectSelectorDropdown` widget |

### ProjectService

Singleton service using `ValueNotifier` for reactive state:

- `projects` -- all fetched projects
- `recentProjects` -- last 10 selected
- `starredProjects` -- user-pinned projects
- `selectedProject` -- currently active project
- `isLoading`, `error` -- loading/error state

### Response Parsing

The frontend handles multiple response formats from the backend:

1. Plain list: `[{"project_id": ...}]`
2. Wrapped dict: `{"projects": [...]}`
3. BaseToolResponse envelope: `{"status": "success", "result": {"projects": [...]}}`

This ensures compatibility regardless of whether the backend returns a raw tool response or an unwrapped result.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Empty project list | `BaseToolResponse` envelope not unwrapped | Fixed in `tools.py` -- endpoint now returns `result` dict directly |
| All users share same preferences | Preferences keyed to "default" | Fixed -- uses `get_current_user_id()` from auth ContextVar |
| Projects don't load at all | EUC not propagated to `list_gcp_projects` | Check `X-GCP-Project-ID` and `Authorization` headers are being sent |
| Selected project not in agent context | Session state missing project ID | Check that `X-GCP-Project-ID` header is set by `ProjectInterceptorClient` |
