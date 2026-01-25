# Google SSO & Session Persistence Learnings

This document summarizes the technical learnings and architectural patterns established during the implementation of session-based authentication for the SRE Agent.

## Technical Insights

### 1. Hybrid Authentication Strategy
Matching the short-lived Google Access Token with a longer-lived backend Session Cookie provides the best balance of security and UX.
- **Access Token**: Used for immediate GCP API calls.
- **ID Token (OIDC)**: Used for fast, local identity verification without network round-trips.
- **Session Cookie**: Used to maintain the user's conversation state and identity across browser refreshes without triggering new Google login popups.

### 2. Flutter Web Platform Compatibility
A common pitfall is breaking unit tests (VM) when adding web-specific features like cookies.
- **Failure**: Importing `package:http/browser_client.dart` directly causes `dart:html` errors in VM tests.
- **Solution**: Use `kIsWeb` from `package:flutter/foundation.dart` and cast the client to `dynamic` or use conditional imports to set web-specific properties like `withCredentials = true`.

### 3. Backend Session Lookup Patterns
ADK's `SessionService` typically requires both a `session_id` and a `user_id`.
- **The Challenge**: When a browser sends only a cookie, the middleware doesn't initially know the `user_id`.
- **The Pattern**:
    - Frontend sends an identity hint + OIDC credential (e.g., `X-ID-Token: <JWT>`) in the request headers.
    - Middleware performs **local signature validation** of the ID token to verify identity instantly.
    - Middleware decrypts the **at-rest encrypted** access token from the session state.
    - Middleware uses a **TTL cache** for Google token validation results to minimize recurring latency.

## Best Practices Established

- **Secure Cookies**: Always set `httponly=True` and `samesite='lax'` (or `'strict'`) to prevent XSS and CSRF.
- **Token Mirroring**: The frontend should proactively "sync" its fresh Google token to the backend `/api/auth/login` endpoint whenever it refreshes its own credentials.
- **Identity Encryption**: Always encrypt sensitive credentials (like OAuth access tokens) before storing them in potentially less secure storage like SQLite or logs.
- **OIDC for Identity**: Use ID Tokens for identity verification and Access Tokens solely for resource authorization.

## Pitfalls to Avoid

- **Hard Imports**: Never import `dart:html` or `browser_client.dart` in shared Flutter libraries.
- **Unawaited Futures**: Always await the backend session sync to ensure consistent auth state before proceeding with sensitive API calls.
- **Context Isolation**: Ensure `ContextVars` (like `_credentials_context`) are cleared or reset between requests (already handled by middleware).
