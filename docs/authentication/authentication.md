# Authentication System Design

This document provides a comprehensive overview of the authentication and session management system implemented in the SRE Agent, covering both backend and frontend components.

## Overview

The SRE Agent uses a **Hybrid Authentication Strategy** that combines Google OAuth2 Access Tokens with stateful Backend Sessions. This approach ensures:
1. **Security**: Short-lived Google tokens are used for actual GCP API interactions.
2. **Persistence**: Backend session cookies maintain user identity and conversation state across browser refreshes, eliminating frequent SSO prompts.
3. **Seamless UX**: Local credential caching on the frontend minimizes interactive login flows.

## Local Development Bypass

For local testing, authentication can be bypassed by either:
1. **Environment Variable**: Set `ENABLE_AUTH=false` when starting the server:
   ```bash
   ENABLE_AUTH=false uv run poe dev
   ```
2. **Login as Guest**: Use the **"Login as Guest"** button on the UI login screen.
   - This allows you to skip the SSO flow even if `ENABLE_AUTH` is not explicitly set to false on the backend.
   - The frontend will send a `dev-mode-bypass-token` which the backend will accept if configured for ADC fallback.

In bypass/guest mode:
- **Frontend**: The app skips the Google Sign-In flow and assumes a "Guest" user identity.
- **Backend**: Falls back to **Application Default Credentials (ADC)** for GCP API access.
- **Security Check**: These bypass modes are strictly for development and should never be enabled in production environments exposed to the internet.

---

## System Architecture

The following diagram illustrates the interaction between the Flutter Frontend, the FastAPI Backend, and Google's Identity services.

```mermaid
sequenceDiagram
    participant U as User
    participant F as Flutter Frontend
    participant B as Cloud Run Proxy (FastAPI)
    participant G as Google APIs / Vertex AI
    participant I as Google Identity (OIDC)

    U->>F: Opens App
    F->>F: Check Local Token Cache
    alt Tokens Missing or Expired
        F->>I: Silent / Interactive Sign-In
        I-->>F: Return AccessToken & idToken (OIDC)
        F->>F: Cache Tokens (local state)
    end

    F->>B: POST /api/auth/login (AccessToken, idToken)
    Note over B: Optimized Identity Check
    B->>B: Local idToken Verification (Claims)
    B->>B: Create/Retrieve Session
    B->>B: Encrypt AccessToken (AES-256)
    B->>B: Store Encrypted Token in Session State
    B-->>F: Set-Cookie: sre_session_id

    F->>B: API Request (GET /api/agent/...)
    Note right of F: Injects sre_session_id cookie + X-ID-Token header
    B->>B: auth_middleware
    B->>B: Local idToken Verification (Identity)
    B->>B: Extract Cookie & Retrieve Session
    B->>B: Decrypt Cached AccessToken
    B->>B: Check Validation Cache (TTL 10m)
    alt Cache Miss
        B->>I: Background Validate with Google
        B->>B: Update Validation Cache
    end
    B->>B: Set context_vars (Credentials)
    B->>G: Forward Query (using User AccessToken)
    G-->>B: Data Stream
    B-->>F: NDJSON Response Stream
```

---

## Backend Implementation

### 1. Session Storage
Backend sessions are managed using the ADK `SessionService`.
- **Local Dev**: Uses `DatabaseSessionService` (SQLite) to persist sessions.
- **Agent Engine**: Uses `VertexAiSessionService` for cloud-native persistence.
    - **Note**: Uses a fixed `app_name="sre_agent"` to ensure consistency between the Cloud Run proxy and the Agent Engine backend (which lacks `SRE_AGENT_ID`).
- **Session State**: Stores the **encrypted** user's `access_token`, `user_email`, and `project_id`.
- **Encryption**: Tokens are encrypted at rest using AES-256 (Fernet).

### 2. API Endpoints (`sre_agent/api/routers/system.py`)
- `POST /api/auth/login`:
    - Exchanges a Google Access Token for a session.
    - Sets an HTTP-only, secure cookie named `sre_session_id`.
- `POST /api/auth/logout`:
    - Deletes the session cookie to terminate the browser session.

### 3. Middleware Security (`sre_agent/api/middleware.py`)
The `auth_middleware` acts as the primary gatekeeper:
- **Header Auth**: Supports standard `Authorization: Bearer <token>` + `X-ID-Token`.
- **Identity (OIDC)**: Uses the `id_token` for fast, local identity verification (signature checking) without network latency.
- **Cookie Auth**: Supports `sre_session_id` for browser sessions.
- **Token Decryption**: Decrypts the session's `access_token` on-the-fly for request injection.
- **Validation Caching**: Implements a 10-minute TTL cache for Google token validation results to eliminate repeated API overhead.
- **Identity Propagation**: Sets `Credentials` and `current_user_id` ContextVars, which tools use to perform authorized actions.

---

## Frontend Implementation

### 1. Authentication Service (`autosre/lib/services/auth_service.dart`)
The `AuthService` manages the user lifecycle:
- **Google Sign-In**: Wraps the `google_sign_in` library.
- **Credential Caching**: Stores the `accessToken` and `expiryTime` both in memory and in `SharedPreferences` for cross-refresh persistence.
- **Backend Sync**: Proactively calls `/api/auth/login` whenever a new token is obtained to ensure the backend session stays in sync with the frontend credentials.

### SSO Single-Popup Flow

The auth flow is designed so users see **at most one** consent screen:

1. **`init()`** fetches backend config, initialises `GoogleSignIn`, and calls `attemptLightweightAuthentication()` for silent session restoration.
2. On silent restore: cached tokens from `SharedPreferences` are loaded. If still valid, no popup is shown.
3. On fresh sign-in: the `authenticationEvents` listener fires, and **`_proactivelyAuthorizeScopes()`** is called immediately -- this requests both `email` and `cloud-platform` scopes in the same interaction, preventing a second popup.
4. Access tokens are cached in `SharedPreferences` (`auth_access_token`, `auth_access_token_expiry`, `auth_id_token`) so page refreshes restore the session without any popup.
5. On sign-out, cached tokens are cleared.

### Session Persistence on Refresh

| Layer | Mechanism |
|-------|-----------|
| Browser | `attemptLightweightAuthentication()` restores `GoogleSignInAccount` from browser storage |
| Frontend | `SharedPreferences` stores access/ID tokens with expiry |
| Backend | `sre_session_id` HTTP-only cookie carries the session across requests |

This three-layer strategy ensures the user stays logged in across page refreshes as long as tokens haven't expired.

### 2. HTTP Interceptor (`autosre/lib/services/api_client.dart`)
The `ProjectInterceptorClient` ensures every request is properly decorated:
- **Authorization Header**: Injected from the local cache.
- **X-GCP-Project-ID**: Injected based on the user's selection.
- **X-User-ID**: Injected as an identity "hint" to help the backend middleware perform robust session lookups when only cookies are present.
- **withCredentials**: Specifically enabled for Web platforms to allow cross-origin cookie propagation.

### 3. Cross-Platform Handling
To maintain compatibility between Flutter Web (production) and VM (unit tests):
- Uses `kIsWeb` constant.
- Dynamically sets `withCredentials` on `http.Client()` to avoid hard dependencies on `dart:html` or `browser_client.dart`, which would break non-web environments.

---

## LLM Credential Injection (Disabled)

A critical architectural decision: the system **does not inject End-User Credentials into the Vertex AI Gemini client**. Vertex AI's `GenerateContent` API rejects Google Sign-In (Web Client) access tokens with a `401 ACCESS_TOKEN_TYPE_UNSUPPORTED` error.

- **Gemini LLM**: Executes using the **Service Account (ADC)** -- Application Default Credentials from the Cloud Run or Agent Engine service account.
- **Tools**: Continue to use **End-User Credentials (EUC)** by explicitly calling `get_credentials_from_tool_context()`. This ensures tools respect the user's IAM permissions when accessing GCP resources.

The relevant code (commented out) can be found in `sre_agent/agent.py` in the `_inject_global_credentials()` function.

---

## Security Considerations

- **Secure Cookies**: Cookies are configured with `httponly=True` (preventing JS access) and `samesite='lax'` (protecting against CSRF while allowing seamless navigation).
- **Encryption at Rest**: All access tokens stored in the session database are encrypted with AES-256. The `SRE_AGENT_ENCRYPTION_KEY` environment variable must be set in production.
- **Local OIDC Validation**: Using `id_token` for local verification ensures identity is proven by Google's cryptography without relying on shared secrets or repeated network lookups.
- **Background Validation**: Access tokens are periodically re-validated with Google (using a 10-minute cache) to ensure they haven't been revoked.
- **Scope Enforcement**: The system strictly enforces the `https://www.googleapis.com/auth/cloud-platform` scope; sessions created with insufficient scopes will be rejected.
- **LLM Isolation**: Gemini executes on ADC, not user tokens, preventing token type mismatches and ensuring the LLM cannot escalate privileges.

---

## Project Selector & User Preferences

See [Project Selector Guide](../guides/project_selector.md) for details on:
- How the project picker lists, searches, and selects GCP projects.
- How starred and recent projects are persisted per-user in Firestore.
- How the selected project propagates into agent prompts and tool invocations.

## Troubleshooting

- **401 Unauthorized**: Check if the browser is blocking third-party cookies or if the Google Access Token has expired.
- **Two Login Popups**: This was caused by scopes being requested in two steps. The fix consolidates scope authorization into `_proactivelyAuthorizeScopes()` which runs right after sign-in.
- **Session Lost on Refresh**: Ensure `SharedPreferences` is working (check browser localStorage). The `auth_access_token` key should be present after login.
- **Missing Projects**: Ensure the token was generated with the `cloud-platform` scope.
- **CORS Issues**: In development, ensure `SECURE_COOKIES=false` is set if running on `http://localhost`.
