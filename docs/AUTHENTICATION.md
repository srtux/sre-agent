# Authentication System Design

This document provides a comprehensive overview of the authentication and session management system implemented in the SRE Agent, covering both backend and frontend components.

## Overview

The SRE Agent uses a **Hybrid Authentication Strategy** that combines Google OAuth2 Access Tokens with stateful Backend Sessions. This approach ensures:
1. **Security**: Short-lived Google tokens are used for actual GCP API interactions.
2. **Persistence**: Backend session cookies maintain user identity and conversation state across browser refreshes, eliminating frequent SSO prompts.
3. **Seamless UX**: Local credential caching on the frontend minimizes interactive login flows.

---

## System Architecture

The following diagram illustrates the interaction between the Flutter Frontend, the FastAPI Backend, and Google's Identity services.

```mermaid
sequenceDiagram
    participant U as User
    participant F as Flutter Frontend
    participant B as FastAPI Backend
    participant G as Google Identity/GCP

    U->>F: Opens App
    F->>F: Check Local Token Cache
    alt Token Missing or Expired
        F->>G: Silent / Interactive Sign-In
        G-->>F: Return Access Token
        F->>F: Cache Token (local state)
    end

    F->>B: POST /api/auth/login (AccessToken)
    Note over B: Validate with Google
    B->>G: GET /tokeninfo
    G-->>B: Valid (email, scopes)
    B->>B: Create/Retrieve Session
    B->>B: Store AccessToken in Session State
    B-->>F: Set-Cookie: sre_session_id

    F->>B: API Request (GET /api/tools/...)
    Note right of F: Injects sre_session_id cookie + X-User-ID header
    B->>B: auth_middleware
    B->>B: Extract Cookie + User Hint
    B->>B: Retrieve Session & Cached Token
    B->>G: Re-validate Token (Background)
    B->>B: Set context_vars (Credentials)
    B->>G: Forward to GCP (using User Token)
    G-->>B: Data
    B-->>F: JSON Response
```

---

## Backend Implementation

### 1. Session Storage
Backend sessions are managed using the ADK `SessionService`.
- **Local Dev**: Uses `DatabaseSessionService` (SQLite) to persist sessions.
- **Agent Engine**: Uses `VertexAiSessionService` for cloud-native persistence.
- **Session State**: Stores the user's `access_token`, `user_email`, and `project_id`.

### 2. API Endpoints (`sre_agent/api/routers/system.py`)
- `POST /api/auth/login`:
    - Exchanges a Google Access Token for a session.
    - Sets an HTTP-only, secure cookie named `sre_session_id`.
- `POST /api/auth/logout`:
    - Deletes the session cookie to terminate the browser session.

### 3. Middleware Security (`sre_agent/api/middleware.py`)
The `auth_middleware` acts as the primary gatekeeper:
- **Header Auth**: Supports standard `Authorization: Bearer <token>` for programmatic access.
- **Cookie Auth**: Supports `sre_session_id` for browser sessions.
- **Validation**: Every request using a session cookie triggers a background validation of the cached Google token. If the token is expired, the request is permitted but treated as unauthenticated, forcing the frontend to perform a refresh.
- **Identity Propagation**: Sets `Credentials` and `current_user_id` ContextVars, which tools use to perform authorized actions.

---

## Frontend Implementation

### 1. Authentication Service (`autosre/lib/services/auth_service.dart`)
The `AuthService` manages the user lifecycle:
- **Google Sign-In**: Wraps the `google_sign_in` library.
- **Credential Caching**: Stores the `accessToken` and `expiryTime` in memory.
- **Backend Sync**: Proactively calls `/api/auth/login` whenever a new token is obtained to ensure the backend session stays in sync with the frontend credentials.

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

## Security Considerations

- **Secure Cookies**: Cookies are configured with `httponly=True` (preventing JS access) and `samesite='lax'` (protecting against CSRF while allowing seamless navigation).
- **Background Validation**: Unlike simple JWTs, our session tokens are re-validated with Google on the backend to ensure immediate revocation if the user's Google account is disabled or the token is revoked.
- **Scope Enforcement**: The system strictly enforces the `https://www.googleapis.com/auth/cloud-platform` scope; sessions created with insufficient scopes will be rejected during validation.

---

## Troubleshooting

- **401 Unauthorized**: Check if the browser is blocking third-party cookies or if the Google Access Token has expired.
- **Missing Projects**: Ensure the token was generated with the `cloud-platform` scope.
- **CORS Issues**: In development, ensure `SECURE_COOKIES=false` is set if running on `http://localhost`.
