# Debugging Connectivity Issues

This guide provides steps to troubleshoot and resolve connectivity issues between the **AutoSRE Frontend (Flutter)** and **SRE Agent Backend (Python/FastAPI)**.

## Common Symptoms
- Frontend stuck on "Connecting to Agent..."
- `HTTP 404` errors on `/health` or `/` in backend logs.
- `GoogleSignInException` or crash on startup.
- "Connection refused" errors in browser console.
- `XMLHttpRequest error` in Flutter web (CORS issue).
- `ProjectNotSelectedException` when making API calls.
- Cloud Run 503 errors or OOM kills.

## Architecture Overview

The frontend connects to the backend via HTTP (NDJSON streaming).

- **Backend Base URL**: `http://127.0.0.1:8001` (Local Dev)
- **Frontend URL**: `http://localhost:8080` (Local Dev, Flutter Web)
- **Health Check**: `GET /health` (Expected response: `{"status": "ok", "version": "0.2.0"}`)
- **Main Chat Endpoint**: `POST /api/genui/chat` (also available as `POST /agent`)
- **Auth**: Google Sign-In (`google_sign_in` package) with `authorizationClient` for GCP scope authorization

### Local Development (`uv run poe dev`)

The `poe dev` command starts both services via `scripts/start_dev.py`:
1. **Backend**: `uv run poe web` (runs `server.py` with uvicorn on port 8001, single worker for dev)
2. **Frontend**: `flutter run -d chrome --web-hostname localhost --web-port 8080`

The backend waits 5 seconds to initialize before the frontend starts.

## Production Deployment (Cloud Run)

In the unified Cloud Run deployment:
- The **Frontend** (Flutter compiled to web) and **Backend** (`server.py` with FastAPI) run in the **same** container.
- The built Flutter web assets are served as static files from the `/web` directory.
- The FastAPI app mounts static files: `app.mount("/", StaticFiles(directory="web", html=True))`.
- Calls to `/health` are relative to the current origin (e.g., `https://your-app.a.run.app/health`).
- **Result**: The connectivity check works identically in production because everything is in one process.

### Cloud Run Resource Requirements

The application requires significant resources due to GCP SDKs, ADK, OpenTelemetry, and model libraries:

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| Memory | 8Gi | 16Gi |
| CPU | 2 | 4 |
| Workers (`WEB_CONCURRENCY`) | 1 | 4 (match CPU count) |

Each uvicorn worker forks a full copy of the Python process (~250-350 MB with all dependencies). The default configuration in `deploy/deploy_web.py` deploys with `--memory=16Gi --cpu=4`.

### Cloud Run OOM and 503 Errors

**Symptoms**:
- Container crashes with `Memory limit exceeded` in Cloud Run logs.
- Intermittent 503 Service Unavailable responses.
- Container restarts frequently under load.

**Root Causes**:
1. **Insufficient memory**: Each worker needs ~350 MB. With 4 workers + agent execution overhead, 8Gi minimum is required.
2. **Too many workers**: `WEB_CONCURRENCY` set higher than allocated CPUs causes memory pressure.
3. **Agent token budget**: Unbounded agent runs can consume excessive memory. Set `SRE_AGENT_TOKEN_BUDGET` to limit.

**Solutions**:
```bash
# Increase Cloud Run memory and CPU
gcloud run services update autosre \
    --memory=16Gi \
    --cpu=4 \
    --region=us-central1

# Or set worker count to match available CPUs
# In server.py, WEB_CONCURRENCY defaults to 4
export WEB_CONCURRENCY=2  # For 2 CPU allocation
```

For GKE deployments, set resource limits in `deploy/k8s/deployment.yaml`.

## Backend Routing (Dual-Mode Execution)

The `server.py` creates the FastAPI app via `create_app()` from `sre_agent/api/app.py`. The agent chat endpoint supports two modes:

1. **Local Mode** (`SRE_AGENT_ID` not set):
   - Agent runs directly in the FastAPI process.
   - Credentials passed via ContextVars.
   - Uses local session storage (SQLite or in-memory).
   - Ideal for development.

2. **Remote Mode** (`SRE_AGENT_ID` set):
   - Forwards requests to Vertex AI Agent Engine.
   - Credentials passed via session state (encrypted).
   - Uses VertexAiSessionService for persistence.
   - Used in production.

The frontend code never changes between modes. It always sends requests to `/api/genui/chat` on the same origin.

## Authentication Flow

The security model uses **Google Sign-In** with End-User Credentials (EUC):

### Step 1: Frontend Authentication

1. `AuthService.init()` fetches backend config (`/api/config`) to get `GOOGLE_CLIENT_ID` and check if auth is enabled.
2. `GoogleSignIn.initialize()` is called with the client ID.
3. `attemptLightweightAuthentication()` tries silent re-auth from browser session.
4. On success, `authorizationClient.authorizationForScopes()` obtains a GCP access token.
5. If silent auth fails, the GIS-rendered sign-in button triggers interactive auth.
6. Access tokens are cached in SharedPreferences (survive page refreshes).

### Step 2: Request Injection

`ProjectInterceptorClient` (in `autosre/lib/services/api_client.dart`) intercepts every HTTP request and adds:
- `Authorization: Bearer <access_token>` -- user's GCP access token
- `X-GCP-Project-ID: <project_id>` -- selected GCP project
- `X-User-ID: <user_email>` -- user's email for session lookup
- `X-Correlation-ID: <uuid>` -- for cross-service request tracing

### Step 3: Backend Processing

`auth_middleware` in `sre_agent/api/middleware.py` extracts headers and sets ContextVars. The credential resolution order is:
1. `X-Guest-Mode: true` header -- synthetic demo credentials
2. `Authorization: Bearer <token>` -- user OAuth token
3. `ENABLE_AUTH=false` env var -- dev mode bypass
4. `sre_session_id` cookie -- session-based auth

### Note on Tool Identity

The Agent supports two modes for Tool Identity:

1. **Local Mode (In-Process)**:
   - The `event_generator()` in `agent.py` re-propagates ContextVars (credentials, project ID, user ID) into the async generator.
   - Tools use `get_credentials_from_tool_context()` which reads from ContextVars.
   - **Result**: GCP API calls (Cloud Trace, Cloud Logging, Cloud Monitoring) run as **the user**.

2. **Remote Mode (Agent Engine)**:
   - The user's access token is encrypted and stored in session state.
   - Tools read the token from `tool_context.invocation_context.session.state`.
   - If the token is expired or decryption fails, tools fall back to the Agent Engine service account.
   - **Result**: Tools run as the **user** if the token is valid, otherwise as the **service account**.

---

## Troubleshooting Steps

### 1. Verify Backend is Running

Expected Output:
```bash
$ uv run poe web
...
INFO:     Uvicorn running on http://0.0.0.0:8001
```
Check if the process is actually listening:
```bash
lsof -i :8001
```

### 2. Verify Health Endpoint

Run this command to check if the backend is responsive:
```bash
curl http://localhost:8001/health
# Expected: {"status":"ok","version":"0.2.0"}
```
If you get `404 Not Found`, ensure `server.py` properly calls `create_app()` which includes `health_router`.

Check the version endpoint:
```bash
curl http://localhost:8001/api/version
# Expected: {"version":"0.2.0","git_sha":"...","build_timestamp":"..."}
```

### 3. Verify Auth Configuration

Check that the backend is serving the correct configuration:
```bash
curl http://localhost:8001/api/config | jq
# Expected: {"google_client_id":"...","auth_enabled":true,"guest_mode_enabled":true}
```

If `google_client_id` is empty, set the `GOOGLE_CLIENT_ID` environment variable.

If `auth_enabled` is `true` but you want to skip auth for local dev:
```bash
export ENABLE_AUTH=false
uv run poe web
```

### 4. Check Frontend Logs

Run the frontend with verbose logging:
```bash
cd autosre && flutter run -d chrome --web-hostname localhost --web-port 8080
```
Look for:
- `Connection refused`: Backend not running or blocked.
- `XMLHttpRequest error`: CORS issue or network unreachable.
- `GoogleSignInException`: Auth configuration mismatch.
- `ProjectNotSelectedException`: No GCP project selected in the UI.

### 5. Google Sign-In Issues

If the app crashes or fails to authenticate:

- **Missing Client ID**: Check that `GOOGLE_CLIENT_ID` is set as an environment variable or passed via `--dart-define=GOOGLE_CLIENT_ID=...` to Flutter.
- **Authorized JavaScript Origins**: Ensure `http://localhost:8080` (dev) AND your production Cloud Run URL are added to "Authorized JavaScript origins" in Google Cloud Console under APIs & Services > Credentials.
- **FedCM**: Chrome's Federated Credential Management API may block silent sign-in. The AuthService catches this and falls back to the GIS button.
- **Scope Authorization Failure**: If `authorizationForScopes()` returns null, the user may need to interactively authorize GCP scopes via `authorizeScopes()`.
- **Cached Token Expired**: If the page was refreshed and the cached token (from SharedPreferences) is expired, the `_ensureAccessToken()` will attempt to refresh silently.

### 6. CORS Configuration

The CORS configuration is in `sre_agent/api/middleware.py` (`configure_cors`).

Default allowed origins:
- `http://localhost:3000`
- `http://localhost:8080`
- `http://localhost:5000`
- `http://127.0.0.1:3000`
- `http://127.0.0.1:8080`
- `http://127.0.0.1:5000`
- `http://localhost:50811`
- `http://127.0.0.1:50811`

If using a custom port or running behind a different origin:
```bash
# Allow all origins (development only!)
export CORS_ALLOW_ALL=true
uv run poe web
```

**Warning**: Never set `CORS_ALLOW_ALL=true` in production.

### 7. Client Disconnection Handling

The backend monitors client disconnections via `raw_request.is_disconnected()` on a 100ms polling interval. When the client disconnects (e.g., user navigates away), the agent task is cancelled via `asyncio.CancelledError`.

**Symptom**: Agent keeps running after the user closes the tab.
**Check**: Look for `Client disconnected for session ... Cancelling agent task.` in backend logs. If absent, the disconnect checker may have failed to start.

### 8. Debug Endpoint

Use the debug endpoint for comprehensive diagnostics:
```bash
curl http://localhost:8001/api/debug | jq
```

This returns telemetry state, auth state, and configuration summary in a single response.

### 9. Permissions Check

If tools are failing with 403 errors, check the agent's permissions on the target project:
```bash
# Check current permissions
curl "http://localhost:8001/api/permissions/check/YOUR_PROJECT_ID" | jq

# Generate gcloud commands to fix
curl "http://localhost:8001/api/permissions/gcloud?project_id=YOUR_PROJECT_ID" | jq '.one_liner'
```

---

## Cloud Run Deployment Debugging

### Container Startup Issues

If the container fails to start on Cloud Run:

1. **Check Cloud Run logs** in Google Cloud Console for startup errors.
2. **Verify environment variables** are set (especially `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLIENT_ID`).
3. **Check Dockerfile**: The unified container uses `scripts/start_unified.sh` as the entrypoint.
4. **Port mismatch**: Cloud Run expects the app on `PORT=8080`. The Dockerfile sets this correctly.

### Static Files Not Loading

If the Flutter frontend shows a blank page:

1. **Check build artifacts**: The Docker build copies Flutter web output from `autosre/build/web` to `/app/web`.
2. **Check mount**: `create_app()` in `app.py` mounts static files only if `os.path.exists("web")` is true.
3. **Check priority**: Static file mounting happens LAST in `create_app()`, so API routes take precedence over static files.

### Connection Between Services

In Cloud Run unified deployment:
- Frontend and backend are in the SAME process -- no network hop.
- `SRE_AGENT_URL` is set to `http://127.0.0.1:8001` in the Dockerfile but is NOT used by the FastAPI app (it serves on `PORT` directly).
- If using remote mode (`SRE_AGENT_ID` set), the backend connects to Vertex AI Agent Engine via the Google Cloud SDK -- ensure the Cloud Run service account has `roles/aiplatform.user`.

---

## Automated Verification

Run the server tests to ensure APIs are correctly defined:
```bash
uv run pytest tests/server/test_server.py
```

Run the full test suite:
```bash
uv run poe test
```

Run Flutter tests:
```bash
cd autosre && flutter test
```

---

## Quick Reference: Environment Variables for Connectivity

| Variable | Purpose | Default |
|----------|---------|---------|
| `PORT` | Server port (Cloud Run) | `8001` (dev), `8080` (Cloud Run) |
| `HOST` | Server bind address | `0.0.0.0` |
| `WEB_CONCURRENCY` | Uvicorn worker count | `4` |
| `SRE_AGENT_ID` | Enables remote mode (Agent Engine) | unset = local |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID | required |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID | required for auth |
| `ENABLE_AUTH` | Enable/disable authentication | `true` |
| `ENABLE_GUEST_MODE` | Enable guest mode (demo data) | `true` |
| `CORS_ALLOW_ALL` | Allow all CORS origins (dev only) | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `SRE_AGENT_TOKEN_BUDGET` | Max token budget per agent run | unset (unlimited) |

---

## Key Source Files

| File | Purpose |
|------|---------|
| `server.py` | FastAPI app entry point, uvicorn configuration |
| `sre_agent/api/app.py` | `create_app()` factory, middleware setup, router registration |
| `sre_agent/api/middleware.py` | CORS, auth middleware, tracing middleware |
| `sre_agent/api/routers/agent.py` | Chat endpoint, dual-mode execution, event streaming |
| `sre_agent/api/routers/health.py` | `/health` and `/api/debug` endpoints |
| `sre_agent/api/routers/system.py` | `/api/config`, `/api/auth/*`, `/api/version` endpoints |
| `sre_agent/api/routers/permissions.py` | `/api/permissions/*` endpoints |
| `autosre/lib/services/auth_service.dart` | Google Sign-In, token management |
| `autosre/lib/services/api_client.dart` | `ProjectInterceptorClient` (header injection) |
| `autosre/lib/services/connectivity_service.dart` | Connectivity status monitoring |
| `scripts/start_dev.py` | Dev stack orchestrator (backend + frontend) |
| `deploy/deploy_web.py` | Cloud Run deployment script |
| `Dockerfile` | Unified container (Flutter + FastAPI) |
| `tests/server/test_server.py` | Server API tests |
