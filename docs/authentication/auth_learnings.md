# Authentication Architecture & Learnings

This document describes the authentication architecture of the SRE Agent, including the End-User Credentials (EUC) flow, token validation, encryption, the `ContextAwareCredentials` proxy, and the lessons learned during implementation.

---

## Architecture Overview

The SRE Agent uses a **multi-layer authentication strategy** that supports both local development and remote Agent Engine execution:

```
+-------------------+     +-------------------+     +-------------------+
|  Flutter Web      |     |  FastAPI          |     |  ADK Agent        |
|  (Cloud Run)      |     |  (Cloud Run)      |     |  (Local/Engine)   |
+--------+----------+     +--------+----------+     +--------+----------+
         |                         |                          |
         | 1. Google Sign-In       |                          |
         |    (OAuth 2.0)          |                          |
         |    Scopes:              |                          |
         |    - email              |                          |
         |    - cloud-platform     |                          |
         |                         |                          |
         | 2. Send Request         |                          |
         |    Headers:             |                          |
         |    - Authorization:     |                          |
         |      Bearer <token>     |                          |
         |    - X-GCP-Project-ID   |                          |
         +------------------------>|                          |
         |                         | 3. Middleware             |
         |                         |    - Extract token        |
         |                         |    - Validate (optional)  |
         |                         |    - Set ContextVar        |
         |                         |                          |
         |                         | 4a. Local Execution       |
         |                         +------------------------->|
         |                         |    ContextVar creds       |
         |                         |                          |
         |                         | 4b. Agent Engine          |
         |                         +------------------------->|
         |                         |    Session State:         |
         |                         |    _user_access_token     |
         |                         |    _user_project_id       |
         |                         |                          |
         |                         | 5. Tool Execution         |
         |                         |    get_credentials_       |
         |                         |    from_tool_context()    |
         |                         |<-------------------------+
         |                         |                          |
         | 6. Response             |                          |
         |<------------------------+                          |
```

---

## Key Components

### 1. Credential Propagation (`sre_agent/auth.py`)

The `auth.py` module is the single source of truth for credential management. It provides:

#### ContextVars (Thread-Safe Per-Request State)

| ContextVar | Purpose | Set By |
| :--- | :--- | :--- |
| `_credentials_context` | Google OAuth2 `Credentials` object | Middleware (`api/middleware.py`) |
| `_project_id_context` | GCP project ID | Middleware (from `X-GCP-Project-ID` header) |
| `_user_id_context` | User email | Middleware (from token validation) |
| `_correlation_id_context` | Request correlation ID | Middleware |
| `_trace_id_context` | OTel trace ID | Middleware |
| `_guest_mode_context` | Whether request is in guest mode | Middleware |

#### Session State Keys (for Agent Engine)

When running in remote Agent Engine mode, ContextVars do not cross process boundaries. Instead, credentials are passed through session state:

| Key | Purpose |
| :--- | :--- |
| `_user_access_token` | Encrypted OAuth access token |
| `_user_project_id` | User's target GCP project ID |
| `_trace_id` | OTel trace ID for distributed tracing |
| `_span_id` | OTel span ID |
| `_trace_flags` | OTel trace flags |

### 2. Credential Resolution Order

When a tool needs credentials, it calls `get_credentials_from_tool_context()`, which checks sources in this order:

1. **ContextVar** (set by middleware in local mode) -- fastest, no network call
2. **Session state** (for Agent Engine remote execution) -- decrypts stored token
3. **Application Default Credentials (ADC)** -- service account fallback (blocked by `STRICT_EUC_ENFORCEMENT=true`)

Project ID resolution (`get_project_id_from_tool_context()`) follows a similar cascade:
1. ContextVar (middleware-set)
2. Session state
3. Environment variables (`GOOGLE_CLOUD_PROJECT`, `GCP_PROJECT_ID`)
4. ADC discovery

### 3. ContextAwareCredentials Proxy

The `ContextAwareCredentials` class (`sre_agent/auth.py`) is a `google.auth.credentials.Credentials` subclass that dynamically delegates to the current execution context. This bridges the gap between:
- **Long-lived service clients** (gRPC channels, cached API clients) that are created once
- **Per-request user identity** that changes with every request

```python
# Singleton instance -- inject into API clients
GLOBAL_CONTEXT_CREDENTIALS = ContextAwareCredentials()

# When a client makes a request, ContextAwareCredentials:
# 1. Checks _credentials_context ContextVar
# 2. Falls back to explicitly set token
# 3. Falls back to ADC (with proactive refresh if expired)
```

The proxy supports `token`, `apply()`, `before_request()`, `refresh()`, and is `deepcopy`-safe for deployment serialization.

### 4. Token Validation

The auth module provides two validation methods:

| Method | Speed | Network | Use Case |
| :--- | :--- | :--- | :--- |
| `validate_id_token()` | Fast | Rarely (keys cached) | Identity verification via OIDC JWT |
| `validate_access_token()` | Slower | Always | Full scope/expiry check via Google tokeninfo |

Both methods use a **TTL cache** (`TOKEN_CACHE_TTL = 600` seconds / 10 minutes) to minimize recurring validation latency. The cache key is the token string; expired entries are evicted on access.

A synchronous variant `validate_access_token_sync()` is provided for environments where async is not available.

### 5. Token Encryption at Rest

When credentials are stored in session state (for Agent Engine mode), access tokens are **encrypted** using Fernet symmetric encryption (`sre_agent/auth.py`):

```python
encrypt_token(token) -> str    # Encrypt before storage
decrypt_token(encrypted) -> str  # Decrypt for use
```

| Configuration | Description |
| :--- | :--- |
| `SRE_AGENT_ENCRYPTION_KEY` | Fernet encryption key. **Must be the same** across all services that read/write session state. |
| Fallback | In local development, a transient key is auto-generated (tokens not decryptable after restart). |
| Mismatch detection | If a Fernet-encrypted token (`gAAAA...`) fails decryption, an empty string is returned to prevent sending encrypted gibberish as a Bearer token. |

### 6. Scope Enforcement

The agent requires the `https://www.googleapis.com/auth/cloud-platform` scope (`REQUIRED_SCOPES`) for GCP API access. The `has_required_scopes()` function validates that a token has all necessary scopes.

---

## Dual-Mode Execution

### Local Mode (`SRE_AGENT_ID` not set)

1. FastAPI middleware extracts `Authorization: Bearer <token>` and `X-GCP-Project-ID` headers
2. Token is validated (optionally) via `validate_access_token()` or `validate_id_token()`
3. Credentials, project ID, and user ID are set in ContextVars
4. Agent runs in-process; tools access credentials via `get_credentials_from_tool_context()`
5. After request: `clear_current_credentials()` resets all ContextVars

### Remote Mode (`SRE_AGENT_ID` set)

1. Same middleware extraction and validation
2. Access token is **encrypted** (`encrypt_token()`) and stored in session state
3. Request is forwarded to Vertex AI Agent Engine (`sre_agent/services/agent_engine_client.py`)
4. Agent Engine deserializes session state; tools call `get_credentials_from_session()`
5. Token is **decrypted** (`decrypt_token()`) and used for GCP API calls

---

## Hybrid Authentication Strategy

### Token Types

| Token | Lifetime | Purpose | Validation |
| :--- | :--- | :--- | :--- |
| **Access Token** | ~1 hour | GCP API authorization | `validate_access_token()` (network) |
| **ID Token (OIDC)** | ~1 hour | Identity verification | `validate_id_token()` (local signature) |
| **Session Cookie** | Configurable | Conversation state persistence | Backend session store |

The ID Token is preferred for identity verification because it can be validated locally (Google's public keys are cached), avoiding a network round-trip on every request.

---

## Flutter Web Platform Considerations

### Cross-Origin Credentials
- Flutter web clients must set `withCredentials = true` on HTTP clients for cookie-based auth
- Use `kIsWeb` from `package:flutter/foundation.dart` to conditionally set web-specific properties
- **Never** import `dart:html` or `browser_client.dart` in shared libraries (breaks VM tests)

### Token Refresh
- Frontend proactively syncs fresh Google tokens to the backend login endpoint when credentials refresh
- This ensures the backend always has a valid token for GCP API calls

### CORS Configuration
- Backend middleware (`sre_agent/api/middleware.py`) configures CORS to allow the Flutter frontend origin
- `Authorization` and `X-GCP-Project-ID` headers are explicitly allowed

---

## Best Practices Established

1. **Secure Cookies**: Always set `httponly=True` and `samesite='lax'` (or `'strict'`) to prevent XSS and CSRF.
2. **Token Mirroring**: The frontend proactively syncs its fresh Google token to the backend whenever it refreshes credentials.
3. **Identity Encryption**: Always encrypt access tokens before storing in session state. Use `SRE_AGENT_ENCRYPTION_KEY` (from Secret Manager in production).
4. **OIDC for Identity**: Use ID Tokens for identity verification and Access Tokens solely for resource authorization.
5. **Context Isolation**: `clear_current_credentials()` must be called after each request to prevent credential leakage between requests.
6. **Strict EUC**: In production, set `STRICT_EUC_ENFORCEMENT=true` to block ADC fallback, ensuring all requests use user credentials.

---

## Pitfalls to Avoid

1. **Hard Imports**: Never import `dart:html` or `browser_client.dart` in shared Flutter libraries. Use conditional imports.
2. **Unawaited Futures**: Always await backend session sync before proceeding with sensitive API calls.
3. **Context Isolation**: Ensure ContextVars are cleared between requests (handled by middleware, but verify in tests).
4. **Encryption Key Mismatch**: If `SRE_AGENT_ENCRYPTION_KEY` differs between FastAPI proxy and Agent Engine, tokens become undecryptable. The `decrypt_token()` function returns an empty string (rather than garbage) to fail safely.
5. **Token in Logs**: Never log raw access tokens. The `log_tool_call()` utility truncates long values.
6. **Guest Mode**: `_guest_mode_context` allows unauthenticated access for demo/evaluation purposes. Ensure it is not accidentally enabled in production.

---

## Environment Variables

| Variable | Purpose | Default |
| :--- | :--- | :--- |
| `STRICT_EUC_ENFORCEMENT` | Block ADC fallback; require EUC tokens | `false` |
| `SRE_AGENT_ENCRYPTION_KEY` | Fernet key for token encryption at rest | Auto-generated (dev only) |
| `GOOGLE_CLIENT_ID` | OAuth client ID for OIDC audience validation | Unset |
| `GOOGLE_CLOUD_PROJECT` | Default GCP project ID | Required |
| `SRE_AGENT_EVAL_MODE` | Skip auth warnings in evaluation mode | `false` |

---

## Related Documentation

- [Autonomous Reliability](autonomous_reliability.md) -- Policy engine and safety layer
- [GCP Enhancements](gcp_enhancements.md) -- Client factory pattern and EUC-aware clients
- [Configuration Reference](../reference/configuration.md) -- Full environment variable list

---

*Last verified: 2026-02-15 -- Auto SRE Team*
