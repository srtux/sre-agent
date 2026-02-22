# Debugging Telemetry and Authentication Issues

This document explains the root causes of telemetry and authentication issues when running the SRE Agent in different environments, and provides solutions.

## Table of Contents

1. [System Architecture Overview](../architecture/system_overview.md)
2. [Backend Deep-Dive](../architecture/backend.md)
3. [Agent Orchestration](../concepts/agent_orchestration.md)
4. [Tools & Analysis Guide](../reference/tools.md)
5. [Frontend (Flutter) Architecture](../architecture/frontend.md)
6. [Authentication & Session Design](../architecture/authentication.md)
7. [Technical Learnings: Google SSO](../concepts/auth_learnings.md)
8. [Issue 1: Telemetry in Agent Engine](#issue-1-traces-not-emitting-from-cloud-run)
9. [Issue 2: End User Authentication](#issue-2-end-user-authentication)
10. [Issue 3: Token Encryption Mismatches](#issue-3-token-encryption-mismatches)
11. [Debug Tools](#debug-tools)
12. [API Endpoints Reference](#api-endpoints-reference)
13. [Configuration Checklist](#configuration-checklist)

---

## Issue 1: Traces Not Emitting from Cloud Run

### Problem Description

The SRE Agent emits traces when called from the **Vertex AI Agent Engine Playground UI**, but not when called from **Cloud Run** (the AutoSRE frontend).

### Root Cause Analysis

The issue stems from the different execution environments:

1. **Agent Engine Playground UI**: Calls the agent directly within Agent Engine. The Agent Engine runtime has its own TracerProvider that exports spans to Cloud Trace automatically.

2. **Cloud Run to Agent Engine**: When the frontend calls Cloud Run, which then calls Agent Engine:
   - Cloud Run's FastAPI server has its own TracerProvider (configured in `sre_agent/tools/common/telemetry.py`)
   - Agent Engine has a separate TracerProvider
   - **There is no trace context propagation** between Cloud Run and Agent Engine
   - The Agent Engine's telemetry may not be enabled

### Solutions

#### Solution 1: Enable Agent Engine Telemetry

When deploying the agent to Vertex AI Agent Engine, set the following environment variables:

```python
env_vars = {
    "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
    "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "true",  # Optional: captures prompts/responses
}
```

In your deployment code:

```python
from vertexai.preview import reasoning_engines

agent = reasoning_engines.ReasoningEngine.create(
    reasoning_engine=AdkApp(agent=root_agent),
    requirements=requirements,
    display_name="SRE Agent",
    env_vars={
        "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
    },
)
```

#### Solution 2: Propagate Trace Context (Advanced)

To correlate traces between Cloud Run and Agent Engine, you need to propagate W3C Trace Context headers. Currently, the `reasoning_engines.ReasoningEngine.stream()` API does not support custom headers for trace context propagation.

**Workaround**: The agent router emits `trace_info` events at the start of each stream response, allowing the frontend to deep-link to Cloud Trace:

```python
# sre_agent/api/routers/agent.py
trace_info = get_current_trace_info(project_id=effective_project_id)
if trace_info:
    yield json.dumps(trace_info) + "\n"
```

You can correlate traces by:
1. Checking the `X-Trace-ID` response header (set by tracing middleware)
2. Using the `X-Correlation-ID` header for cross-service request tracking
3. Matching timestamps in Cloud Trace

#### Solution 3: View Traces in Agent Engine Console

Even without propagation, Agent Engine traces can be viewed:

1. Navigate to **Vertex AI Agent Engine** in Google Cloud Console
2. Select your Agent Engine instance
3. Click the **Traces** tab
4. Choose **Session view** or **Span view**

### Debug Commands

Enable debug logging to understand telemetry state:

```bash
# Set environment variables
export DEBUG_TELEMETRY=true
export LOG_LEVEL=DEBUG

# Call the debug endpoint
curl http://localhost:8001/api/debug | jq
```

---

## Issue 2: End User Authentication

### Problem Description

The goal is to use end-user credentials (OAuth tokens) to make API requests from the agent, rather than using the agent's service account.

### Current Implementation (Google Sign-In + EUC Flow)

Auto SRE implements a complete End-User Credentials (EUC) flow using the `google_sign_in` Flutter package:

```
+---------------------------------------------------------------------------------+
|                      EUC FLOW (CURRENT IMPLEMENTATION)                          |
+---------------------------------------------------------------------------------+
|                                                                                 |
|  1. Browser: User signs in with Google Sign-In                                  |
|     +-> Uses google_sign_in package (authenticationEvents stream)               |
|     +-> Scopes: email, cloud-platform                                           |
|     +-> AuthService listens to GoogleSignInAuthenticationEvent                  |
|                                                                                 |
|  2. AuthService: Authorizes GCP scopes via authorizationClient                  |
|     +-> authorizationClient.authorizationForScopes() (silent)                   |
|     +-> authorizationClient.authorizeScopes() (interactive fallback)            |
|     +-> Access token cached in SharedPreferences (page refresh survival)        |
|                                                                                 |
|  3. Flutter Web: ProjectInterceptorClient sends request                         |
|     +-> Authorization: Bearer <access_token>                                    |
|     +-> X-GCP-Project-ID: <selected_project>                                   |
|     +-> X-User-ID: <user_email>                                                |
|     +-> X-Correlation-ID: <uuid>                                                |
|                                                                                 |
|  4. FastAPI Middleware (auth_middleware):                                        |
|     +-> Extracts token from Authorization header                                |
|     +-> Validates via X-ID-Token (fast, local) or access_token (cached)         |
|     +-> Creates Credentials(token=token)                                        |
|     +-> Sets ContextVar: _credentials_context                                   |
|     +-> Sets ContextVar: _project_id_context                                    |
|     +-> Sets ContextVar: _user_id_context                                       |
|     +-> Clears all ContextVars in finally block (prevents leakage)              |
|                                                                                 |
|  5a. LOCAL MODE (SRE_AGENT_ID not set):                                         |
|      +-> Agent runs in FastAPI process                                          |
|      +-> event_generator() re-sets ContextVars (because middleware              |
|          clears them before async generator starts yielding)                    |
|      +-> Tools use get_credentials_from_tool_context()                          |
|      +-> ContextVar contains user credentials                                   |
|                                                                                 |
|  5b. REMOTE MODE (SRE_AGENT_ID is set):                                         |
|      +-> AgentEngineClient creates session with state:                          |
|          * _user_access_token: <encrypted_token>                                |
|          * _user_project_id: <project_id>                                       |
|      +-> Tools read from tool_context.invocation_context.session.state          |
|      +-> Token decrypted via decrypt_token() before use                         |
|                                                                                 |
|  6. Tool Execution:                                                             |
|     +-> get_credentials_from_tool_context() checks:                             |
|         1. ContextVar (local mode)                                              |
|         2. Session state (remote mode, with token decryption)                   |
|         3. Default credentials (if STRICT_EUC_ENFORCEMENT=false)                |
|                                                                                 |
|  7. GCP API Calls:                                                              |
|     +-> Authenticated as the user, not service account                          |
|                                                                                 |
+---------------------------------------------------------------------------------+
```

**Important**: LLM credential injection is **disabled**. The agent does NOT inject user OAuth tokens into LLM calls. Only GCP API tool calls (Cloud Trace, Cloud Logging, Cloud Monitoring, BigQuery) use user credentials.

**Key Files:**
- `sre_agent/auth.py`: Credential extraction, ContextVars, session state, token encryption/decryption, `ContextAwareCredentials`
- `sre_agent/api/middleware.py`: Token extraction from headers, guest mode, dev mode bypass, session cookie fallback
- `sre_agent/api/routers/agent.py`: ContextVar re-propagation in `event_generator()`, token encryption on session creation
- `sre_agent/api/routers/system.py`: `/api/auth/login`, `/api/auth/logout`, `/api/auth/info`, `/api/config` endpoints
- `sre_agent/services/agent_engine_client.py`: Remote Agent Engine with EUC propagation
- `sre_agent/tools/clients/factory.py`: Client factory with EUC support
- `autosre/lib/services/auth_service.dart`: Google Sign-In, `authorizationClient`, token caching
- `autosre/lib/services/api_client.dart`: `ProjectInterceptorClient` (header injection)

### Debugging EUC Issues

**Check auth info endpoint:**
```bash
curl -H "Authorization: Bearer <token>" http://localhost:8001/api/auth/info | jq
```

**Response shows:**
```json
{
  "authenticated": true,
  "token_info": {
    "valid": true,
    "email": "user@example.com",
    "expires_in": 3540,
    "scopes": ["https://www.googleapis.com/auth/cloud-platform", "..."],
    "error": null
  },
  "project_id": "my-project"
}
```

**Check system config (auth enabled, guest mode):**
```bash
curl http://localhost:8001/api/config | jq
```

**Response shows:**
```json
{
  "google_client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
  "auth_enabled": true,
  "guest_mode_enabled": true
}
```

**Enable strict EUC enforcement:**
```bash
# Prevent fallback to service account
export STRICT_EUC_ENFORCEMENT=true
```

**Disable auth for local development:**
```bash
# Skip authentication entirely (dev only)
export ENABLE_AUTH=false
```

### Guest Mode

When guest mode is enabled (`ENABLE_GUEST_MODE=true`), users can bypass Google Sign-In and access the agent with synthetic demo data.

- Frontend sends `X-Guest-Mode: true` header
- Backend middleware sets synthetic credentials:
  - Project: `cymbal-shops-demo`
  - User: `guest@demo.autosre.dev`
  - Token: `guest-mode-token`
- Tools will use default credentials (ADC) since the guest token is not real

### Auth Middleware Credential Resolution Order

The `auth_middleware` in `sre_agent/api/middleware.py` resolves credentials in this order:

1. **Guest Mode Header**: `X-Guest-Mode: true` -- synthetic credentials
2. **Bearer Token**: `Authorization: Bearer <token>` -- user OAuth token
3. **Dev Mode Bypass**: `ENABLE_AUTH=false` -- dummy dev credentials
4. **Session Cookie**: `sre_session_id` cookie -- look up encrypted token from session state

### ContextVar Re-propagation in StreamingResponse

A critical subtlety: the `auth_middleware` clears ContextVars in its `finally` block after the request handler returns. However, for `StreamingResponse`, the async generator has not started yielding yet when the handler returns. This means ContextVars are empty when tools actually execute.

**Solution** (in `sre_agent/api/routers/agent.py`):
```python
async def event_generator() -> AsyncGenerator[str, None]:
    # Re-propagate auth context into the generator
    if access_token:
        set_current_credentials(Credentials(token=access_token))
    if effective_project_id:
        set_current_project_id(effective_project_id)
    if effective_user_id:
        set_current_user_id(effective_user_id)
    # ... rest of generator
```

If tools are getting `None` credentials in local mode, this re-propagation may have broken.

### Root Cause Analysis (Historical Context)

Several factors affect end-user authentication:

1. **ADK's Authentication Model**: ADK is designed for tool-level OAuth flows (interactive consent), not for propagating existing tokens from a frontend.

2. **Token Scopes**: The OAuth token must have the `cloud-platform` scope for broad GCP API access. The `AuthService` in Flutter requests:
   - `email`
   - `https://www.googleapis.com/auth/cloud-platform`

3. **MCP Server Configuration**: Google's MCP servers support OAuth tokens, but must be configured with `useClientOAuth: true`.

4. **Session State Propagation**: The current implementation passes tokens via session state, but:
   - ContextVars don't cross process boundaries (Cloud Run to Agent Engine)
   - Tokens are encrypted with Fernet before storage in session state
   - Encryption key mismatch between services causes silent auth failures

### Authentication Options

#### Option A: EUC with Google Sign-In (Current Default)

The current implementation uses Google Sign-In with `authorizationClient` for GCP scope authorization:

```dart
// autosre/lib/services/auth_service.dart
static final List<String> _scopes = [
  'email',
  'https://www.googleapis.com/auth/cloud-platform',
];

// Silent authorization attempt
var authz = await authzClient.authorizationForScopes(_scopes);
// Interactive fallback
if (authz == null && interactive) {
  authz = await authzClient.authorizeScopes(_scopes);
}
```

**Pros**:
- Proper OAuth flow with user consent
- Correct scopes for GCP APIs
- Token refresh handled by frontend
- Token caching survives page refreshes (SharedPreferences)

**Cons**:
- Requires OAuth consent screen setup
- Token expiry (55 min) requires refresh handling

#### Option B: Service Account with IAM Grants (Recommended for Simplicity)

Users grant the agent's service account permissions on their GCP project:

1. **Get the Agent's Service Account**: Use the permissions info endpoint.
2. **User Grants Permissions**: Users run gcloud commands or use the Cloud Console.
3. **Agent Accesses User's Project**: The agent uses its own identity.

See [Project Permission Setup](#project-permission-setup) below for detailed instructions.

**Pros**:
- Simple to implement
- No token management needed
- Clear permission model

**Cons**:
- Requires manual IAM setup by users
- Uses agent identity, not user identity

#### Option C: Hybrid Approach (Current Production Recommendation)

Combine both approaches:
1. Use EUC (Google Sign-In) for user identity verification and project-level access
2. Fall back to service account when EUC token is expired or unavailable
3. Use `STRICT_EUC_ENFORCEMENT=true` in high-security environments to disable fallback

### Project Permission Setup

For Option B, users need to grant the agent's service account access to their project.

#### Step 1: Identify the Agent's Service Account

Use the permissions info API:
```bash
curl http://localhost:8001/api/permissions/info | jq
```

Response:
```json
{
  "service_account": "sre-agent@YOUR_AGENT_PROJECT.iam.gserviceaccount.com",
  "roles": [
    "roles/cloudtrace.user",
    "roles/logging.viewer",
    "roles/monitoring.viewer",
    "roles/compute.viewer"
  ],
  "project_id": "your-agent-project"
}
```

#### Step 2: Check Current Permissions

```bash
curl "http://localhost:8001/api/permissions/check/USER_PROJECT_ID" | jq
```

Response:
```json
{
  "project_id": "user-project-123",
  "results": {
    "cloudtrace.user": {"status": "ok", "message": null},
    "logging.viewer": {"status": "missing", "message": "Permission Denied (403)"},
    "monitoring.viewer": {"status": "ok", "message": null}
  },
  "all_ok": false,
  "timestamp": "2026-02-15T00:00:00+00:00"
}
```

#### Step 3: Generate gcloud Commands

```bash
curl "http://localhost:8001/api/permissions/gcloud?project_id=USER_PROJECT_ID" | jq
```

Response includes ready-to-use gcloud commands and a one-liner.

#### Step 4: Grant Permissions (Manual)

**Option A: gcloud CLI**

```bash
# Set variables
USER_PROJECT_ID="user-project-123"
AGENT_SA="sre-agent@agent-project.iam.gserviceaccount.com"

# Grant roles
gcloud projects add-iam-policy-binding $USER_PROJECT_ID \
    --member="serviceAccount:$AGENT_SA" \
    --role="roles/cloudtrace.user"

gcloud projects add-iam-policy-binding $USER_PROJECT_ID \
    --member="serviceAccount:$AGENT_SA" \
    --role="roles/logging.viewer"

gcloud projects add-iam-policy-binding $USER_PROJECT_ID \
    --member="serviceAccount:$AGENT_SA" \
    --role="roles/monitoring.viewer"

gcloud projects add-iam-policy-binding $USER_PROJECT_ID \
    --member="serviceAccount:$AGENT_SA" \
    --role="roles/compute.viewer"
```

**Option B: Cloud Console**

1. Go to [IAM & Admin](https://console.cloud.google.com/iam-admin/iam)
2. Select the user's project
3. Click **Grant Access**
4. Enter the agent's service account email
5. Add the required roles
6. Click **Save**

---

## Issue 3: Token Encryption Mismatches

### Problem Description

Tokens stored in session state are encrypted with Fernet (symmetric encryption). If the encryption key differs between services (e.g., Cloud Run frontend proxy and Agent Engine backend), tokens cannot be decrypted.

### Symptoms

- Warning: `Failed to decrypt Fernet token. This strongly indicates an SRE_AGENT_ENCRYPTION_KEY mismatch`
- Tools receive `None` credentials despite user being authenticated
- 401 errors from downstream GCP APIs

### Root Cause

The `SRE_AGENT_ENCRYPTION_KEY` environment variable must be identical across all services that read or write session tokens:
- The Cloud Run instance running `server.py`
- The Agent Engine instance (if using remote mode)
- Any GKE deployment

### Solution

1. Generate a Fernet key:
   ```python
   from cryptography.fernet import Fernet
   print(Fernet.generate_key().decode())
   ```

2. Set it in all environments:
   ```bash
   export SRE_AGENT_ENCRYPTION_KEY="your-base64-fernet-key"
   ```

3. For GKE, store it in a Kubernetes secret:
   ```yaml
   # deploy/k8s/deployment.yaml
   - name: SRE_AGENT_ENCRYPTION_KEY
     valueFrom:
       secretKeyRef:
         name: autosre-secrets
         key: encryption_key
   ```

**Note**: If `SRE_AGENT_ENCRYPTION_KEY` is not set, the system generates a transient key that is valid only for the current process lifetime. Tokens encrypted with a transient key cannot be decrypted after a restart.

---

## Debug Tools

### Debug Endpoint

Access the debug endpoint to see telemetry and auth state:

```bash
curl http://localhost:8001/api/debug | jq
```

Response includes:
- Environment variables affecting telemetry (`GOOGLE_CLOUD_PROJECT`, `SRE_AGENT_ID`, `DISABLE_TELEMETRY`, etc.)
- Authentication state (ContextVar, session state, effective credentials)
- Debug mode status

### Debug Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG_TELEMETRY` | Enable detailed telemetry logging | `false` |
| `DEBUG_AUTH` | Enable detailed auth logging | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY` | Enable Agent Engine tracing | `false` |
| `ENABLE_AUTH` | Enable/disable authentication | `true` |
| `ENABLE_GUEST_MODE` | Enable guest mode (synthetic demo data) | `true` |
| `STRICT_EUC_ENFORCEMENT` | Block ADC fallback when no user token | `false` |
| `SRE_AGENT_ENCRYPTION_KEY` | Fernet key for token encryption | auto-generated (transient) |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID | required for auth |
| `SECURE_COOKIES` | Set Secure flag on session cookies | `false` |

### Debug Functions

Import and use debug functions in your code:

```python
from sre_agent.tools.common.debug import (
    log_telemetry_state,
    log_auth_state,
    log_mcp_auth_state,
    log_agent_engine_call_state,
    enable_debug_mode,
    get_debug_summary,
)

# Log telemetry state
state = log_telemetry_state("my_context")

# Log auth state with tool context
state = log_auth_state(tool_context, "in_my_tool")

# Log MCP headers that will be sent
state = log_mcp_auth_state(project_id, tool_context, "before_mcp_call")

# Log state before calling Agent Engine
state = log_agent_engine_call_state(
    user_message="query",
    session_id="session-123",
    user_access_token=token,
    project_id="my-project",
    context_label="before_remote_call",
)

# Enable all debug logging
enable_debug_mode()
```

### ContextAwareCredentials

For debugging credential propagation at the gRPC client level, the `ContextAwareCredentials` class in `sre_agent/auth.py` provides a proxy that dynamically resolves credentials from the current ContextVar. It logs detailed credential resolution when `LOG_LEVEL=DEBUG`:

```
ContextAwareCredentials: Using token from context (exists: True)
ContextAwareCredentials: Using token from ADC (exists: True, type: Credentials)
ContextAwareCredentials: ADC token missing or expired, refreshing...
```

---

## API Endpoints Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check (`{"status": "ok", "version": "..."}`) |
| `/api/debug` | GET | Telemetry and auth debug info |
| `/api/config` | GET | Public config (client ID, auth enabled, guest mode) |
| `/api/version` | GET | Build version metadata |
| `/api/auth/login` | POST | Exchange token for session cookie |
| `/api/auth/logout` | POST | Clear session cookie |
| `/api/auth/info` | GET | Current auth state and token validation |
| `/api/genui/chat` | POST | Main agent chat endpoint (also available at `/agent`) |
| `/api/suggestions` | GET | Contextual suggestions |
| `/api/permissions/info` | GET | Agent service account and required roles |
| `/api/permissions/check/{project_id}` | GET | Check agent permissions on a project |
| `/api/permissions/gcloud` | GET | Generate gcloud commands for granting permissions |

---

## Configuration Checklist

### For Agent Engine Telemetry

- [ ] Set `GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY=true` in deployment
- [ ] Optionally set `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true`
- [ ] Enable the Telemetry API in your project
- [ ] Enable the Logging API in your project

### For Cloud Run Telemetry

- [ ] Set `GOOGLE_CLOUD_PROJECT` environment variable
- [ ] Ensure service account has `roles/cloudtrace.agent` role
- [ ] Do not set `DISABLE_TELEMETRY=true`
- [ ] Configure `WEB_CONCURRENCY` to match allocated CPUs (default: 4)

### For End User Authentication

- [ ] Set `GOOGLE_CLIENT_ID` environment variable (both backend and frontend build)
- [ ] Add authorized JavaScript origins to OAuth consent screen (localhost:8080, Cloud Run URL)
- [ ] Ensure OAuth consent screen has `cloud-platform` scope
- [ ] If using token encryption: set `SRE_AGENT_ENCRYPTION_KEY` consistently across all services
- [ ] If using strict mode: set `STRICT_EUC_ENFORCEMENT=true`
- [ ] If disabling auth for dev: set `ENABLE_AUTH=false`

### For MCP Server Authentication

- [ ] Verify `x-goog-user-project` header is set correctly
- [ ] If using user tokens, ensure they have correct scopes
- [ ] Test with `DEBUG_AUTH=true` to see headers being sent

### For GKE Deployment

- [ ] Store `GOOGLE_CLIENT_ID` in Kubernetes secret (`autosre-secrets`)
- [ ] Store `SRE_AGENT_ENCRYPTION_KEY` in Kubernetes secret
- [ ] Configure `GEMINI_API_KEY` in Kubernetes secret
- [ ] Set `SRE_AGENT_ID` in ConfigMap (`autosre-config`)
- [ ] Set `GCP_PROJECT_ID` in ConfigMap

---

## References

- [Vertex AI Agent Engine Tracing](https://docs.cloud.google.com/agent-builder/agent-engine/manage/tracing)
- [ADK Authentication](https://google.github.io/adk-docs/tools-custom/authentication/)
- [BigQuery MCP Server](https://docs.cloud.google.com/bigquery/docs/use-bigquery-mcp)
- [Agent Identity](https://docs.cloud.google.com/agent-builder/agent-engine/agent-identity)
- [google_sign_in Flutter package](https://pub.dev/packages/google_sign_in)
