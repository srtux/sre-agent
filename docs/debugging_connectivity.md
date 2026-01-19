# Debugging Connectivity Issues

This guide provides steps to troubleshoot and resolve connectivity issues between the **AutoSRE Frontend (Flutter)** and **SRE Agent Backend (Python/FastAPI)**.

## common Symptoms
- Frontend stuck on "Connecting to Agent..."
- `HTTP 404` errors on `/health` or `/` in backend logs.
- `GoogleSignInException` or crash on startup.
- "Connection refused" errors in browser console.

## Architecture Overview
The frontend connects to the backend via HTTP and WebSocket/SSE.
- **Base URL**: `http://127.0.0.1:8001` (Local Dev)
- **Health Check**: `GET /health` (Expected response: `{"status": "ok"}`)
- **Auth**: Google Sign-In (Implicit flow / IdToken)

## Production Support (Cloud Run)
In the unified Cloud Run deployment:
- The **Frontend** (Flutter) and **Backend Proxy** (`server.py`) run in the *same* container.
- `server.py` serves the Flutter static files at `/`.
- Calls to `/health` are relative to the current origin (e.g., `https://your-app.a.run.app/health`).
- **Result**: The connectivity check works identically in production because the Proxy handles the health check, even if the "Brain" (Agent) is remote on Vertex AI.

## Backend Proxy Routing
When deployed to Cloud Run, `server.py` acts as a smart proxy:
1.  **Check**: It checks for the `SRE_AGENT_ID` environment variable.
2.  **Route**:
    - If `SRE_AGENT_ID` is set: It connects to the **Vertex AI Agent Engine** using the Google Cloud SDK and streams the response back to the frontend.
    - If `SRE_AGENT_ID` is missing (Local Dev): It runs the agent logic **in-process** locally.
3.  **Benefit**: The frontend code never changes. It always talks to `/api/genui/chat` on its "local" server (the proxy), which handles the complexity of remote connection.

## Authentication Flow
The security model uses a **Two-Legged Authentication** strategy:

1.  **Leg 1: User to Cloud Run**
    *   **Credential**: Google Sign-In ID Token (User Identity).
    *   **Mechanism**: Frontend sends `Authorization: Bearer <token>`.
    *   **Validation**: `server.py` middleware extracts this token. (In strict setups, Cloud Run IAP handles this before the request hits the container).

2.  **Leg 2: Cloud Run to Agent Engine**
    *   **Credential**: Cloud Run Service Account (Machine Identity).
    *   **Mechanism**: `server.py` uses Application Default Credentials (ADC).
    *   **Permissions**: The Service Account is granted `roles/aiplatform.user` to invoke the Vertex Agent.

### Note on Tool Identity
The Agent supports two modes for Tool Identity:

1.  **Direct Mode (In-Process)**:
    - If you deploy the Agent **In-Process** (no `SRE_AGENT_ID` set), the `server.py` runs the agent locally.
    - **Credential Propagation**: The Agent **WILL** pass your Google Sign-In Token to the backend MCP tools (BigQuery, Logging).
    - **Result**: Queries run as **YOU**. You need explicit permissions to the underlying data.

2.  **Remote Mode (Agent Engine)**:
    - If you use `SRE_AGENT_ID`, the Agent runs on Vertex AI.
    - **Credential Propagation**: Your token is **dropped** at the proxy boundary.
    - **Result**: Tools run as the **Service Account**. Queries have "God Mode" (within the SA's scope) regardless of who you are.



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
# Expected: {"status": "ok"}
```
If you get `404 Not Found`, ensure `server.py` has the `/health` endpoint defined.

### 3. Check Frontend Logs
Run the frontend with verbose logging:
```bash
uv run flutter run -d chrome -v
```
Look for:
- `Connection refused`: Backend not running or blocked.
- `XMLHttpRequest error`: CORS issue or network unreachable.
- `GoogleSignInException`: Auth configuration mismatch.

### 4. Google Sign-In Issues
If the app crashes on startup with `GoogleSignInException`:
- Check `web/index.html` has the correct `google-signin-client_id` meta tag.
- Ensure `http://localhost:8080` (or your port) AND your production Cloud Run URL are added to "Authorized JavaScript origins" in Google Cloud Console.
- **FedCM**: Chrome's new FedCM might block silent sign-in. The app should catch this and log a warning instead of crashing.

### 5. CORS Configuration
Ensure `server.py` allows your frontend origin.
Default allows:
- `http://localhost:3000`
- `http://localhost:8080`
- `http://127.0.0.1:3000`
- `http://127.0.0.1:8080`

If using a custom port, add it to `_cors_origins` in `server.py` or set `CORS_ALLOW_ALL=true` (dev only).

## Automated Verification
Run the server tests to ensure APIs are correctly defined:
```bash
uv run pytest tests/sre_agent/test_server.py
```
