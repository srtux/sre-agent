# Google SSO & Session Persistence Learnings

This document summarizes the technical learnings and architectural patterns established during the implementation of session-based authentication for the SRE Agent.

## Technical Insights

### 1. Hybrid Authentication Strategy
Matching the short-lived Google Access Token with a longer-lived backend Session Cookie provides the best balance of security and UX.
- **Access Token**: Used for immediate GCP API calls.
- **Session Cookie**: Used to maintain the user's conversation state and identity across browser refreshes without triggering new Google login popups.

### 2. Flutter Web Platform Compatibility
A common pitfall is breaking unit tests (VM) when adding web-specific features like cookies.
- **Failure**: Importing `package:http/browser_client.dart` directly causes `dart:html` errors in VM tests.
- **Solution**: Use `kIsWeb` from `package:flutter/foundation.dart` and cast the client to `dynamic` or use conditional imports to set web-specific properties like `withCredentials = true`.

### 3. Backend Session Lookup Patterns
ADK's `SessionService` typically requires both a `session_id` and a `user_id`.
- **The Challenge**: When a browser sends only a cookie, the middleware doesn't initially know the `user_id`.
- **The Pattern**:
    - Frontend sends an identity hint (e.g., `X-User-ID: email@example.com`) in the request headers.
    - Middleware uses this hint to perform a robust lookup.
    - Middleware validates the *cached* token from the session state with Google to verify the identity is still valid.

## Best Practices Established

- **Secure Cookies**: Always set `httponly=True` and `samesite='lax'` (or `'strict'`) to prevent XSS and CSRF.
- **Token Mirroring**: The frontend should proactively "sync" its fresh Google token to the backend `/api/auth/login` endpoint whenever it refreshes its own credentials.
- **Middleware Identity Guard**: Middleware should not just trust the session existence; it must validate that the token stored *within* that session is still valid with the identity provider (Google).

## Pitfalls to Avoid

- **Hard Imports**: Never import `dart:html` or `browser_client.dart` in shared Flutter libraries.
- **Unawaited Futures**: Always await the backend session sync to ensure consistent auth state before proceeding with sensitive API calls.
- **Context Isolation**: Ensure `ContextVars` (like `_credentials_context`) are cleared or reset between requests (already handled by middleware).
