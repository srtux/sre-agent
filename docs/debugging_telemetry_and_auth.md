# Debugging Telemetry and Authentication Issues

This document explains the root causes of telemetry and authentication issues when running the SRE Agent in different environments, and provides solutions.

## Table of Contents

1. [Issue 1: Traces Not Emitting from Cloud Run](#issue-1-traces-not-emitting-from-cloud-run)
2. [Issue 2: End User Authentication](#issue-2-end-user-authentication)
3. [Debug Tools](#debug-tools)
4. [Configuration Checklist](#configuration-checklist)

---

## Issue 1: Traces Not Emitting from Cloud Run

### Problem Description

The SRE Agent emits traces when called from the **Vertex AI Agent Engine Playground UI**, but not when called from **Cloud Run** (the AutoSRE frontend).

### Root Cause Analysis

The issue stems from the different execution environments:

1. **Agent Engine Playground UI**: Calls the agent directly within Agent Engine. The Agent Engine runtime has its own TracerProvider that exports spans to Cloud Trace automatically.

2. **Cloud Run → Agent Engine**: When the frontend calls Cloud Run, which then calls Agent Engine:
   - Cloud Run's FastAPI server has its own TracerProvider (configured in `telemetry.py`)
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

**Workaround**: The debug logging added to the codebase will help you understand the trace context at each stage. You can correlate traces by:
1. Logging the trace ID from Cloud Run
2. Matching timestamps in Cloud Trace

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

### Current Implementation (EUC Flow)

Auto SRE now implements a complete End-User Credentials (EUC) flow:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          EUC FLOW (IMPLEMENTED)                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  1. Browser: User signs in with Google OAuth                                    │
│     └─► Scopes: email, cloud-platform                                           │
│                                                                                  │
│  2. Flutter Web: ProjectInterceptorClient sends request                         │
│     ├─► Authorization: Bearer <access_token>                                    │
│     └─► X-GCP-Project-ID: <selected_project>                                    │
│                                                                                  │
│  3. FastAPI Middleware (auth_middleware):                                       │
│     ├─► Extracts token from Authorization header                                │
│     ├─► Creates Credentials(token=token)                                        │
│     ├─► Sets ContextVar: _credentials_context                                   │
│     └─► Sets ContextVar: _project_id_context                                    │
│                                                                                  │
│  4a. LOCAL MODE (SRE_AGENT_ID not set):                                         │
│      └─► Agent runs in FastAPI process                                          │
│      └─► Tools use get_credentials_from_tool_context()                          │
│      └─► ContextVar contains user credentials                                   │
│                                                                                  │
│  4b. REMOTE MODE (SRE_AGENT_ID is set):                                         │
│      └─► AgentEngineClient creates session with state:                          │
│          • _user_access_token: <access_token>                                   │
│          • _user_project_id: <project_id>                                       │
│      └─► Tools read from tool_context.invocation_context.session.state          │
│                                                                                  │
│  5. Tool Execution:                                                             │
│     └─► get_credentials_from_tool_context() checks:                             │
│         1. ContextVar (local mode)                                              │
│         2. Session state (remote mode)                                          │
│         3. Default credentials (if STRICT_EUC_ENFORCEMENT=false)                │
│                                                                                  │
│  6. GCP API Calls:                                                              │
│     └─► Authenticated as the user, not service account                          │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Key Files:**
- `sre_agent/auth.py`: Credential extraction, ContextVars, session state
- `sre_agent/api/middleware.py`: Token extraction from headers
- `sre_agent/services/agent_engine_client.py`: Remote Agent Engine with EUC
- `sre_agent/tools/clients/factory.py`: Client factory with EUC support
- `autosre/lib/services/api_client.dart`: ProjectInterceptorClient

### Debugging EUC Issues

**Check auth info endpoint:**
```bash
curl -H "Authorization: Bearer <token>" http://localhost:8001/api/auth/info | jq
```

**Response shows:**
```json
{
  "authenticated": true,
  "token_preview": "ya29.a0A...",
  "token_info": {
    "valid": true,
    "email": "user@example.com",
    "expires_in": 3540,
    "scopes": ["https://www.googleapis.com/auth/cloud-platform", ...]
  },
  "project_id": "my-project"
}
```

**Enable strict EUC enforcement:**
```bash
# Prevent fallback to service account
export STRICT_EUC_ENFORCEMENT=true
```

### Root Cause Analysis (Historical Context)

Several factors affect end-user authentication:

1. **ADK's Authentication Model**: ADK is designed for tool-level OAuth flows (interactive consent), not for propagating existing tokens from a frontend.

2. **Token Scopes**: The OAuth token from Google Identity Platform (used for user sign-in) may not have the required GCP API scopes:
   - Cloud Trace: `https://www.googleapis.com/auth/trace.readonly`
   - Cloud Logging: `https://www.googleapis.com/auth/logging.read`
   - Cloud Monitoring: `https://www.googleapis.com/auth/monitoring.read`
   - BigQuery: `https://www.googleapis.com/auth/bigquery.readonly`

3. **MCP Server Configuration**: Google's MCP servers support OAuth tokens, but must be configured with `useClientOAuth: true`.

4. **Session State Propagation**: The current implementation passes tokens via session state, but:
   - ContextVars don't cross process boundaries (Cloud Run → Agent Engine)
   - Session state propagation depends on the ADK version and Agent Engine configuration

### Authentication Options

#### Option A: ADK Interactive OAuth Flow (Recommended for Full User Context)

Use ADK's built-in authentication mechanism for tools that need user-specific access:

```python
from google.adk.auth import AuthCredential, AuthCredentialTypes, OAuth2Auth
from google.adk.tools import ToolContext

# Configure OAuth for GCP APIs
auth_credential = AuthCredential(
    auth_type=AuthCredentialTypes.OAUTH2,
    oauth2=OAuth2Auth(
        client_id="YOUR_CLIENT_ID.apps.googleusercontent.com",
        client_secret="YOUR_CLIENT_SECRET",
    )
)

# In your tool, check for credentials or request them
def my_gcp_tool(query: str, tool_context: ToolContext) -> dict:
    # Check if we have cached credentials
    cached = tool_context.state.get("gcp_tokens")
    if cached:
        # Use cached credentials
        ...

    # Otherwise, request authentication
    tool_context.request_credential(auth_config)
    return {"pending": True, "message": "Please authenticate..."}
```

**Pros**:
- Proper OAuth flow with user consent
- Correct scopes for GCP APIs
- Tokens are refreshable

**Cons**:
- Requires user interaction
- More complex frontend integration

#### Option B: Service Account with IAM Grants (Recommended for Simplicity)

Users grant the agent's service account permissions on their GCP project:

1. **Get the Agent's Service Account**: The agent running in Agent Engine has a service account identity.

2. **User Grants Permissions**: Users run gcloud commands or use the Cloud Console to grant permissions.

3. **Agent Accesses User's Project**: The agent can then access the user's project using its own identity.

See [Project Permission Setup](#project-permission-setup) below for detailed instructions.

**Pros**:
- Simple to implement
- No token management needed
- Clear permission model

**Cons**:
- Requires manual IAM setup by users
- Uses agent identity, not user identity

#### Option C: Hybrid Approach

Combine both approaches:
1. Use service account for initial access (listing projects, basic queries)
2. Use ADK OAuth flow for sensitive operations (BigQuery queries on user data)

### Project Permission Setup

For Option B, users need to grant the agent's service account access to their project.

#### Step 1: Identify the Agent's Service Account

The agent's service account follows this pattern:
```
sre-agent@YOUR_AGENT_PROJECT.iam.gserviceaccount.com
```

Or if using Agent Identity (Preview):
```
agent-AGENT_ID@YOUR_AGENT_PROJECT.iam.gserviceaccount.com
```

#### Step 2: Required IAM Roles

Grant these roles on the **user's project**:

| Role | Purpose |
|------|---------|
| `roles/cloudtrace.user` | View traces |
| `roles/logging.viewer` | View logs |
| `roles/monitoring.viewer` | View metrics and dashboards |
| `roles/bigquery.dataViewer` | Query BigQuery tables |
| `roles/bigquery.jobUser` | Run BigQuery jobs |

#### Step 3: Grant Permissions (User Action)

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
    --role="roles/bigquery.dataViewer"

gcloud projects add-iam-policy-binding $USER_PROJECT_ID \
    --member="serviceAccount:$AGENT_SA" \
    --role="roles/bigquery.jobUser"
```

**Option B: Cloud Console**

1. Go to [IAM & Admin](https://console.cloud.google.com/iam-admin/iam)
2. Select the user's project
3. Click **Grant Access**
4. Enter the agent's service account email
5. Add the required roles
6. Click **Save**

---

## Debug Tools

### Debug Endpoint

Access the debug endpoint to see telemetry and auth state:

```bash
curl http://localhost:8001/api/debug | jq
```

Response includes:
- OpenTelemetry tracer provider configuration
- Current span context (trace ID, span ID)
- Environment variables affecting telemetry
- Authentication state (ContextVar, session state, effective credentials)

### Debug Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG_TELEMETRY` | Enable detailed telemetry logging | `false` |
| `DEBUG_AUTH` | Enable detailed auth logging | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY` | Enable Agent Engine tracing | `false` |

### Debug Functions

Import and use debug functions in your code:

```python
from sre_agent.tools.common.debug import (
    log_telemetry_state,
    log_auth_state,
    log_mcp_auth_state,
    log_agent_engine_call_state,
    enable_debug_mode,
)

# Log telemetry state
state = log_telemetry_state("my_context")

# Log auth state with tool context
state = log_auth_state(tool_context, "in_my_tool")

# Log MCP headers that will be sent
state = log_mcp_auth_state(project_id, tool_context, "before_mcp_call")

# Enable all debug logging
enable_debug_mode()
```

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
- [ ] Don't set `DISABLE_TELEMETRY=true`

### For End User Authentication

- [ ] Decide on authentication approach (Option A, B, or C)
- [ ] If using service account approach:
  - [ ] Document the agent's service account
  - [ ] Create user-facing instructions for granting permissions
  - [ ] Consider creating a permissions check endpoint

### For MCP Server Authentication

- [ ] Verify `x-goog-user-project` header is set correctly
- [ ] If using user tokens, ensure they have correct scopes
- [ ] Test with `DEBUG_AUTH=true` to see headers being sent

---

## References

- [Vertex AI Agent Engine Tracing](https://docs.cloud.google.com/agent-builder/agent-engine/manage/tracing)
- [ADK Authentication](https://google.github.io/adk-docs/tools-custom/authentication/)
- [BigQuery MCP Server](https://docs.cloud.google.com/bigquery/docs/use-bigquery-mcp)
- [Agent Identity](https://docs.cloud.google.com/agent-builder/agent-engine/agent-identity)
