# Authentication & EUC Pattern

The project employs a robust pattern for propagating End-User Credentials (EUC) from the frontend to the final GCP API calls.

## Hybrid Authentication Strategy
1. **SSO**: User logs in via Google SSO (OAuth2).
2. **Backend Sync**: Access token and OIDC ID Token are sent to `/api/auth/login`.
3. **Session Establishment**: Backend creates a session and returns a secure, HTTP-only `sre_session_id` cookie.
4. **Credential Persistence**: The user's Access Token is encrypted (AES-256) and stored in the session state.

## Propagation Logic
- **Middleware**: `auth_middleware` extracts the cookie/header, decrypts the token, and sets it in a `ContextVar` (task-local).
- **ID Token Verification**: Uses `id_token` for fast, local identity verification without network round-trips.
- **Interceptor (Frontend)**: `ProjectInterceptorClient` injects the `X-GCP-Project-ID` and `Authorization` headers into every request.
- **Managed Mode (Production)**: The proxy injects the decrypted credentials into the ADK Session State before forwarding calls to the managed Agent Engine.

## Security Controls
- **Strict EUC Enforcement**: In production, tools can be configured (`STRICT_EUC_ENFORCEMENT=true`) to reject calls that lack user credentials, preventing fallback to service account permissions.
- **Project Isolation**: Tools must always respect the `project_id` provided in the context. Hardcoding project IDs is forbidden.
