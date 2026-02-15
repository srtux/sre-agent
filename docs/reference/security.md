# Security & Encryption

Auto SRE handles sensitive data, including temporary End-User Credentials (EUC). This document outlines the complete security architecture, from authentication through data protection.

---

## Authentication Architecture

### End-User Credentials (EUC) Flow

The SRE Agent implements a multi-tenant authentication model where each user's own Google OAuth credentials are used to access their GCP projects. The agent never has standing access to user projects -- it acts on behalf of the authenticated user.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Flutter Web    │     │  FastAPI        │     │  ADK Agent      │
│  (Cloud Run)    │     │  (Cloud Run)    │     │  (Local/Engine) │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │ 1. Google Sign-In     │                       │
         │    (OAuth 2.0)        │                       │
         │    Scopes:            │                       │
         │    - email            │                       │
         │    - cloud-platform   │                       │
         │                       │                       │
         │ 2. Send Request       │                       │
         │    Headers:           │                       │
         │    - Authorization:   │                       │
         │      Bearer <token>   │                       │
         │    - X-GCP-Project-ID │                       │
         │    - X-ID-Token (opt) │                       │
         ├──────────────────────>│                       │
         │                       │ 3. Auth Middleware     │
         │                       │    - Extract token    │
         │                       │    - Validate (opt)   │
         │                       │    - Set ContextVar   │
         │                       │                       │
         │                       │ 4a. Local Execution   │
         │                       ├──────────────────────>│
         │                       │    ContextVar creds   │
         │                       │                       │
         │                       │ 4b. Agent Engine      │
         │                       ├──────────────────────>│
         │                       │    Session State:     │
         │                       │    _user_access_token │
         │                       │    _user_project_id   │
         │                       │                       │
         │                       │ 5. Tool Execution     │
         │                       │    get_credentials_   │
         │                       │    from_tool_context()│
         │                       │<──────────────────────┤
         │                       │                       │
         │ 6. Response           │                       │
         │<──────────────────────┤                       │
```

### Authentication Modes

| Mode | Trigger | Behavior |
|------|---------|----------|
| **Full OAuth** | `Authorization: Bearer <token>` header | User token extracted, validated, and set in ContextVar. Identity resolved via access token or ID token validation. |
| **ID Token Fast Path** | `X-ID-Token: <oidc-id-token>` header | OIDC JWT verified locally, skipping the tokeninfo API round-trip. Faster identity resolution. |
| **Guest Mode** | `X-Guest-Mode: true` header | Synthetic credentials injected, project set to `cymbal-shops-demo`, user set to `guest@demo.autosre.dev`. Tools return synthetic data. |
| **Dev Bypass** | `ENABLE_AUTH=false` env var | Dummy credentials injected (`dev@local.test`). **Never use in production.** |
| **Session Cookie** | `sre_session_id` cookie | Token retrieved from session store, decrypted, revalidated, then set in ContextVar. |

### Credential Resolution Order

When a tool needs to access a GCP API on behalf of the user, credentials are resolved in this order:

1. **ContextVar** (set by auth middleware in local/FastAPI mode)
2. **Session State** (for remote Agent Engine execution, since ContextVars do not cross process boundaries)
3. **Application Default Credentials (ADC)** -- fallback to the service account; **blocked** when `STRICT_EUC_ENFORCEMENT=true`

### Strict EUC Enforcement

When `STRICT_EUC_ENFORCEMENT=true`:
- The ADC fallback is disabled. If no user credentials are available (ContextVar or session state), the request fails with an error.
- This ensures every GCP API call is made with the authenticated user's credentials, enforcing least-privilege access.
- **Recommended** for production deployments. Set to `false` only for local development with `adk web`.

---

## SRE_AGENT_ENCRYPTION_KEY

The `SRE_AGENT_ENCRYPTION_KEY` is a 32-byte (AES-256) Fernet key used to encrypt OAuth access tokens before they are stored in session state (Firestore). This ensures that even if someone gains access to your Firestore database, user tokens remain encrypted and unusable.

### Current Implementation

- **Encryption**: Tokens are encrypted using the `cryptography.fernet` library.
- **Storage**: Encrypted tokens are stored in the session state under the key `_user_access_token`.
- **Decryption**: The Cloud Run proxy decrypts these tokens before calling GCP APIs on the user's behalf.

### Persistence

If `SRE_AGENT_ENCRYPTION_KEY` is not set, the agent generates a **transient key** at startup. This works for a single process, but:
1. Tokens will not be decryptable after a service restart.
2. In multi-instance deployments (Cloud Run), different instances will have different keys, causing random decryption failures.

**Recommendation**: Always set a static key for any environment where persistence or multi-instance scaling is required.

### Generating a Key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Production Configuration (GCP)

For production, we recommend using **GCP Secret Manager** instead of plain environment variables.

#### 1. Create the Secret

```bash
echo -n "your-generated-key" | gcloud secrets create sre-agent-encryption-key --data-file=-
```

#### 2. Update Deployment Configuration

The `deploy/deploy_web.py` script (Cloud Run) pulls this key from Secret Manager at **runtime**.

However, the `deploy/deploy.py` script (Agent Engine) pulls the key from your **local environment** at **deployment time**.

> [!CAUTION]
> **Key Synchronization Hazard**: You must ensure the key in your local `.env` file matches the key in Secret Manager *before* running any deployment scripts. If you update the secret, you must also update your `.env` and redeploy the backend.

```bash
# 1. Update Secret Manager (if changing key)
echo -n "new-key" | gcloud secrets versions add sre-agent-encryption-key --data-file=-

# 2. Update local .env
# SRE_AGENT_ENCRYPTION_KEY=new-key

# 3. Redeploy Backend (Agent Engine)
uv run python deploy/deploy.py --create
```

---

## End-User Credentials (EUC)

Auto SRE uses **End-User Credentials** flow. This means it never stores your password. It only uses short-lived OAuth access tokens granted during the Google Sign-In process on the frontend.

### Token Security

- **Access tokens** are short-lived (typically 1 hour) and refreshed by the frontend (Google Sign-In SDK).
- **Tokens in session state** are encrypted at rest using AES-256 Fernet encryption (see above).
- **Token validation** uses Google's tokeninfo endpoint with a local TTL cache to avoid repeated round-trips. The `X-ID-Token` header enables a faster local JWT verification path.
- Credentials are held in memory only during request processing. After each request, the auth middleware clears the ContextVar to prevent credential leakage between requests.
- Credentials are **never** persisted to disk.

### Credential Flow

1. **Frontend**: User signs in via Google OAuth. The Flutter `ProjectInterceptorClient` attaches `Authorization: Bearer <token>` and `X-GCP-Project-ID` headers to every request.
2. **Backend Middleware**: Extracts token and project ID from headers into Python `ContextVar` objects (thread/task-local).
3. **Tools**: Access credentials via `get_credentials_from_tool_context(tool_context)`. Client factories (`get_trace_client()`, etc.) automatically respect EUC.
4. **Agent Engine Mode**: Credentials are injected into ADK Session State (`_user_access_token`, `_user_project_id`) and encrypted before storage.

---

## Policy Engine & Tool Access Control

### Access Level Model

The **Policy Engine** (`sre_agent/core/policy_engine.py`) enforces a three-tier access control model for all tool calls:

| Access Level | Behavior | Example Tools |
|-------------|----------|---------------|
| `READ_ONLY` | Executes immediately without approval | `fetch_trace`, `list_log_entries`, `detect_metric_anomalies`, `generate_remediation_suggestions` |
| `WRITE` | Requires human approval before execution | `restart_pod`, `scale_deployment`, `rollback_deployment`, `acknowledge_alert`, `silence_alert` |
| `ADMIN` | Restricted -- requires approval | `delete_resource`, `modify_iam` |

### Policy Evaluation Flow

```
Tool Call --> PolicyEngine.evaluate() --> PolicyDecision
                |
                +-- READ_ONLY --> allowed=True, requires_approval=False
                +-- WRITE    --> allowed=True, requires_approval=True + risk_assessment
                +-- ADMIN    --> allowed=True, requires_approval=True + risk_assessment
```

**Note**: The policy engine is currently in **experimental mode**. Rejections are disabled to gather data, but warnings and approval requirements are still generated for WRITE and ADMIN tools. Unknown tools (not in the policy registry) are allowed by default with a warning logged.

### Tool Categories

Each tool is assigned a category that determines its risk profile:

| Category | Description | Risk Level |
|----------|-------------|------------|
| `OBSERVABILITY` | Trace, log, metric queries | Low |
| `ANALYSIS` | Pure analysis functions | Low |
| `ORCHESTRATION` | Sub-agent coordination | Low |
| `DISCOVERY` | Resource discovery | Low |
| `ALERTING` | Alert policies and incidents | Low-Medium |
| `REMEDIATION` | Suggestions, risk assessment | Low |
| `MEMORY` | Memory bank operations | Low |
| `INFRASTRUCTURE` | GKE, compute resources | Low (read-only) |
| `MUTATION` | Write operations (restarts, scaling, deletes) | Medium-Critical |

### Risk Assessment

For WRITE and ADMIN tools, the policy engine generates a risk assessment that includes:
- **Base risk level**: Defined per tool in the policy registry (`low`, `medium`, `high`, `critical`).
- **Argument analysis**: Checks for dangerous patterns like `force=True` or operations affecting multiple resources.
- **Recommendation**: Always recommends reviewing arguments before approval.

### Human-in-the-Loop Approval

Write operations that require human approval follow this workflow:

1. **Request**: The agent generates a `HumanApprovalRequest` with details of the proposed action, its reason, and a risk assessment.
2. **Pending**: The request is stored in the session's `ApprovalState` with status `PENDING`.
3. **Decision**: The user approves or rejects via the UI. The decision is recorded as a `HumanApprovalEvent`.
4. **Execution**: If approved, the tool is executed. If rejected or expired, the agent is informed and must propose an alternative.

Approval statuses: `PENDING`, `APPROVED`, `REJECTED`, `EXPIRED`, `CANCELLED`.

### Dynamic Tool Filtering

Tools can be disabled at runtime via the `/api/tools/config/{tool_name}` API or the Tool Configuration UI. The policy engine checks tool enablement status during evaluation. Disabled tools are skipped with a warning.

---

## Circuit Breaker Pattern

The circuit breaker (`sre_agent/core/circuit_breaker.py`) prevents cascading failures when tools or external GCP APIs are failing. Controlled by `SRE_AGENT_CIRCUIT_BREAKER=true` (default).

### States

| State | Behavior |
|-------|----------|
| **CLOSED** | Normal operation. Calls pass through. Failures increment the counter. |
| **OPEN** | Circuit is tripped after `failure_threshold` (default: 5) consecutive failures. Calls fail fast without execution for `recovery_timeout_seconds` (default: 60). |
| **HALF_OPEN** | After the recovery timeout, a limited number of calls (`half_open_max_calls`, default: 1) are allowed through to test recovery. If successful (`success_threshold`, default: 2), the circuit closes. If they fail, it reopens. |

### Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `failure_threshold` | 5 | Failures before opening |
| `recovery_timeout_seconds` | 60 | Seconds before trying half-open |
| `half_open_max_calls` | 1 | Max test calls in half-open state |
| `success_threshold` | 2 | Successes needed to close circuit |

The circuit breaker is applied per-tool, so one failing tool does not affect others.

---

## Middleware Security Stack

The middleware is applied in this order (outermost first):

### Tracing Middleware
- Assigns or propagates `X-Correlation-ID` and `X-Request-ID` for request correlation.
- Attaches OpenTelemetry trace context for distributed tracing.
- Injects `X-Correlation-ID` and `X-Trace-ID` response headers.
- Suppresses repetitive health check logs to reduce noise.

### Auth Middleware
- Extracts credentials from `Authorization: Bearer` headers, `X-ID-Token` headers, `X-Guest-Mode` headers, and session cookies.
- Sets credentials in Python `ContextVar` objects (thread-safe, async-safe).
- Extracts `X-GCP-Project-ID` header (or `project_id` query parameter fallback).
- **Critical**: Clears all credential ContextVars in a `finally` block after each request to prevent leakage between requests.

### CORS Middleware
- Default: Restricted to specific localhost origins (ports 3000, 5000, 8080, 50811).
- `CORS_ALLOW_ALL=true`: Opens to all origins (for containerized/GKE deployments).
- Methods: GET, POST, PUT, DELETE, OPTIONS.
- Credentials: Allowed.

### Global Exception Handler
- Catches unhandled exceptions and returns a sanitized `500` response.
- Prevents leaking stack traces or internal details to clients.
- Logs the full exception with stack trace server-side.

---

## Input Validation

### Pydantic Schema Enforcement

All API request and response models use strict Pydantic v2 schemas:

```python
class MySchema(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    field: str
```

- **`frozen=True`**: Models are immutable after creation.
- **`extra="forbid"`**: Unknown fields cause validation errors. This prevents the LLM from hallucinating extra fields that would silently pass through.

### Tool Output Validation

Tool outputs are validated and truncated by the `after_tool_callback` chain:
1. **Large Payload Handler**: Intercepts oversized results (>50 items or >100K chars) and auto-summarizes via sandbox.
2. **Truncation Guard**: Safety net that truncates outputs exceeding 200K characters.
3. **Memory Callback**: Stores findings for learning.

### Directory Traversal Protection

The help content endpoint (`GET /api/help/content/{content_id}`) implements defense-in-depth against directory traversal:

1. **Input sanitization**: Strips `..`, `/`, and `\` characters from the content ID.
2. **Path resolution**: Uses `Path.resolve()` to canonicalize the path after symlink resolution.
3. **Prefix verification**: Verifies the resolved path starts with the expected `DOCS_DIR` prefix.

---

## PII Masking & Data Redaction

Auto SRE implements automatic PII masking at multiple layers to ensure sensitive user data is redacted before being processed by LLMs.

### Layer 1: Log Pattern Analysis (Drain3)

**Location**: `sre_agent/tools/analysis/logs/patterns.py`

The `LogPatternExtractor` automatically masks sensitive patterns during log analysis using the Drain3 algorithm:

| Pattern | Replacement | Example |
|---------|-------------|---------|
| ISO timestamps | `<TIMESTAMP>` | `2026-02-02T10:30:00` -> `<TIMESTAMP>` |
| Dates | `<DATE>` | `2026-02-02` -> `<DATE>` |
| Times | `<TIME>` | `10:30:00` -> `<TIME>` |
| UUIDs | `<UUID>` | `550e8400-e29b-41d4-a716-446655440000` -> `<UUID>` |
| MongoDB ObjectIds | `<ID>` | `507f1f77bcf86cd799439011` -> `<ID>` |
| IPv4 addresses | `<IP>` | `192.168.1.100` -> `<IP>` |
| Durations | `<DURATION>` | `50ms`, `1.5ms` -> `<DURATION>` |
| Email addresses | `<EMAIL>` | `"user@domain.com"` -> `<EMAIL>` |

**Always active**: PII masking is not configurable -- it is always enabled during log pattern analysis to guarantee sensitive data is never sent to the LLM.

**Configurable parameters** (for pattern extraction, not PII):
- `depth`: Parse tree depth (default: 4)
- `sim_th`: Similarity threshold (default: 0.4)
- `max_children`: Max children per tree node (default: 100)
- `max_clusters`: Maximum pattern count (default: 1000)

### Layer 2: BigQuery SQL Masking

**Location**: `sre_agent/tools/analysis/bigquery/logs.py`

For large-scale log analysis, PII masking is performed server-side in BigQuery using nested `REGEXP_REPLACE()` SQL functions:

| Pattern | Replacement |
|---------|-------------|
| UUIDs | `<UUID>` |
| IPv4 addresses | `<IP>` |
| ISO timestamps | `<TIMESTAMP>` |
| Hex pointers | `<HEX>` |
| Numbers | `<NUM>` |
| Email addresses | `<EMAIL>` |

This ensures data is masked *before* it leaves BigQuery, minimizing data exposure.

### Layer 3: Credential Masking (Debug Logging)

**Location**: `sre_agent/tools/common/debug.py`

OAuth tokens and credentials are never fully logged. The debug utilities use prefix-only logging:
- Token values: First 20 characters + `"..."` suffix
- Token length is tracked for debugging without exposing the full value

**Functions**: `log_auth_state()`, `log_mcp_auth_state()`, `log_agent_engine_call_state()`

### Adding Custom PII Patterns

To add new masking patterns to the Drain3-based log analyzer, modify the `masking_instructions` list in `LogPatternExtractor.__init__()`:

```python
from drain3 import MaskingInstruction

config.masking_instructions.append(
    MaskingInstruction(r"\b\d{3}-\d{2}-\d{4}\b", "<SSN>")  # US SSN
)
```

For BigQuery masking, add a new `REGEXP_REPLACE()` wrapper in `sre_agent/tools/analysis/bigquery/logs.py`.

---

## GCP IAM & Permissions

### Required Roles

The SRE Agent (or the authenticated user's credentials) requires these IAM roles on target projects:

| Role | Purpose |
|------|---------|
| `roles/cloudtrace.user` | Read traces |
| `roles/logging.viewer` | Read logs |
| `roles/monitoring.viewer` | Read metrics, dashboards |
| `roles/compute.viewer` | Read GCE resources |
| `roles/container.viewer` | Read GKE clusters, nodes, pods |
| `roles/bigquery.dataViewer` | Read BigQuery tables (for fleet analysis) |
| `roles/bigquery.jobUser` | Run BigQuery queries |

### Permission Verification

The `GET /api/permissions/check/{project_id}` endpoint performs lightweight API calls to verify access:
- Attempts to list traces (verifies `cloudtrace.user`)
- Attempts to list logs (verifies `logging.viewer`)
- Attempts to list metrics (verifies `monitoring.viewer`)

Returns a per-role status report indicating which permissions are missing.

### Self-Service Onboarding

The `GET /api/permissions/gcloud` endpoint generates ready-to-execute `gcloud` commands for granting the required roles on a target project:
```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:sre-agent@HOST_PROJECT.iam.gserviceaccount.com" \
    --role="roles/cloudtrace.user"
```

---

## Privacy & Data Sovereignty

### 1. PII Masking
The agent includes specialized middleware that automatically redacts PII (emails, IP addresses, timestamps, UUIDs) from tool outputs before they are processed by the LLM. See [PII Masking & Data Redaction](#pii-masking--data-redaction) above for full details.

### 2. Regionalized Processing
Auto SRE can be configured to run in specific GCP regions via `GOOGLE_CLOUD_LOCATION`. All data processing (parsing, analysis, and session storage) stays within the configured region boundary to satisfy strict data residency requirements.

### 3. No Persistent PII Storage
- OAuth tokens are short-lived and encrypted at rest.
- Investigation data uses masked identifiers.
- Session data is scoped per-user and can be deleted on demand.

---

## Protected Access

By default, Cloud Run is deployed in **Authenticated Mode** (`--no-allow-unauthenticated`). This means only authorized users (with `roles/run.invoker`) can access the URL.

If your organization allows public access and you wish to enable it, you must explicitly use the `--allow-unauthenticated` flag:

```bash
uv run python deploy/deploy_web.py --allow-unauthenticated
```

When deployed in the default (Authenticated) mode:
1. The service is created with `--no-allow-unauthenticated`.
2. You will need to grant users the `roles/run.invoker` role to access the URL.
3. Direct browser access may require an IAP (Identity-Aware Proxy) or Load Balancer if not accessed via a Google-authenticated tunnel.

---

## Security-Relevant Environment Variables

| Variable | Security Impact | Recommended Production Value |
|----------|----------------|------------------------------|
| `STRICT_EUC_ENFORCEMENT` | Controls whether ADC fallback is allowed | `true` |
| `ENABLE_AUTH` | Controls whether authentication is enforced | `true` (default) |
| `ENABLE_GUEST_MODE` | Controls whether guest mode login is available | `false` (unless demo is needed) |
| `SRE_AGENT_ENCRYPTION_KEY` | Encryption key for session tokens | Set a persistent Fernet key |
| `SECURE_COOKIES` | Controls cookie Secure flag | `true` (default) |
| `CORS_ALLOW_ALL` | Controls CORS policy | `false` (default) |
| `SRE_AGENT_ENFORCE_POLICY` | Controls policy engine enforcement | `true` (default) |
| `SRE_AGENT_CIRCUIT_BREAKER` | Controls circuit breaker pattern | `true` (default) |
| `GITHUB_TOKEN` | Grants repository access for self-healing | Store in Secret Manager |
| `GOOGLE_CUSTOM_SEARCH_API_KEY` | Grants Google Custom Search access | Store in Secret Manager |
| `GOOGLE_CUSTOM_SEARCH_ENGINE_ID` | Identifies the search engine | Store in Secret Manager |
| `A2UI_DEBUG` | Verbose GenUI logging (may expose data) | `false` (default) |

---

## Security Checklist

### Production Deployment

- [ ] Set `STRICT_EUC_ENFORCEMENT=true` -- prevents ADC fallback
- [ ] Set `ENABLE_AUTH=true` (default) -- enforces OAuth
- [ ] Set `SRE_AGENT_ENCRYPTION_KEY` -- use a persistent Fernet key for token encryption
- [ ] Set `SECURE_COOKIES=true` (default) -- ensures cookie security
- [ ] Do not set `CORS_ALLOW_ALL=true` unless behind a reverse proxy with proper origin checks
- [ ] Do not set `ENABLE_AUTH=false` -- this bypasses all authentication
- [ ] Do not expose `/api/debug` endpoint -- restrict or disable in production
- [ ] Ensure `GOOGLE_CLIENT_ID` matches your OAuth consent screen
- [ ] Rotate `SRE_AGENT_ENCRYPTION_KEY` periodically (existing sessions will need to re-authenticate)
- [ ] Store `GITHUB_TOKEN`, `GOOGLE_CUSTOM_SEARCH_API_KEY`, and `GOOGLE_CUSTOM_SEARCH_ENGINE_ID` in Secret Manager, not in environment files
- [ ] Review and restrict `GITHUB_TOKEN` scope to minimum required permissions (`repo` scope for self-healing)

### Local Development

For `adk web` or local development:
```bash
ENABLE_AUTH=false
STRICT_EUC_ENFORCEMENT=false
SECURE_COOKIES=false
SRE_AGENT_EVAL_MODE=true  # Optional: use synthetic data
```

| Area | Control | Status |
|------|---------|--------|
| Token encryption | AES-256 Fernet at rest | Active |
| EUC enforcement | Configurable strict mode | Active |
| PII masking (logs) | Drain3 automatic masking | Always on |
| PII masking (BigQuery) | SQL-level REGEXP_REPLACE | Always on |
| Credential logging | Prefix-only (20 chars) | Always on |
| Secret management | GCP Secret Manager recommended | Configurable |
| Access control | Cloud Run authenticated mode | Default |
| CORS | Restricted by default | Configurable |
| Session cookies | `HttpOnly`, `Secure`, `SameSite` | Default |
| Secret scanning | `detect-secrets` in pre-commit | Active |
| Policy engine | Three-tier tool access control | Active (experimental) |
| Circuit breaker | Per-tool failure protection | Active |
| Directory traversal | Path sanitization + prefix check | Active |

---
*Last verified: 2026-02-15 -- Auto SRE Team*
