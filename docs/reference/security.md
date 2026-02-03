# Security & Encryption

Auto SRE handles sensitive data, including temporary End-User Credentials (EUC). This document outlines how we secure this data and how to configure encryption for production.

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

- **Strict EUC Enforcement**: When `STRICT_EUC_ENFORCEMENT=true`, the agent will explicitly fail if no user token is present, preventing any fallback to the Service Account's credentials. This is the recommended setting for production to ensure per-user data isolation.

### Credential Flow

1. **Frontend**: User signs in via Google OAuth. The Flutter `ProjectInterceptorClient` attaches `Authorization: Bearer <token>` and `X-GCP-Project-ID` headers to every request.
2. **Backend Middleware**: Extracts token and project ID from headers into Python `ContextVar` objects (thread/task-local).
3. **Tools**: Access credentials via `get_credentials_from_tool_context(tool_context)`. Client factories (`get_trace_client()`, etc.) automatically respect EUC.
4. **Agent Engine Mode**: Credentials are injected into ADK Session State (`_user_access_token`, `_user_project_id`) and encrypted before storage.

---

## PII Masking & Data Redaction

Auto SRE implements automatic PII masking at multiple layers to ensure sensitive user data is redacted before being processed by LLMs.

### Layer 1: Log Pattern Analysis (Drain3)

**Location**: `sre_agent/tools/analysis/logs/patterns.py`

The `LogPatternExtractor` automatically masks sensitive patterns during log analysis using the Drain3 algorithm:

| Pattern | Replacement | Example |
|---------|-------------|---------|
| ISO timestamps | `<TIMESTAMP>` | `2026-02-02T10:30:00` → `<TIMESTAMP>` |
| Dates | `<DATE>` | `2026-02-02` → `<DATE>` |
| Times | `<TIME>` | `10:30:00` → `<TIME>` |
| UUIDs | `<UUID>` | `550e8400-e29b-41d4-a716-446655440000` → `<UUID>` |
| MongoDB ObjectIds | `<ID>` | `507f1f77bcf86cd799439011` → `<ID>` |
| IPv4 addresses | `<IP>` | `192.168.1.100` → `<IP>` |
| Durations | `<DURATION>` | `50ms`, `1.5ms` → `<DURATION>` |
| Email addresses | `<EMAIL>` | `"user@domain.com"` → `<EMAIL>` |

**Always active**: PII masking is not configurable — it is always enabled during log pattern analysis to guarantee sensitive data is never sent to the LLM.

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

## Security Checklist

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

---
*Last verified: 2026-02-02 — Auto SRE Team*
