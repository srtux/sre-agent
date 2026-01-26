"""Middleware configuration for the SRE Agent API."""

import logging
import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Track if we have already logged a successful health check to reduce log noise
_HEALTH_SUCCESS_LOGGED = False


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global handler for unhandled exceptions."""
    logger.error(f"🔥 Global exception handler caught: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc)},
    )


async def tracing_middleware(request: Request, call_next: Any) -> Any:
    """Middleware for request tracing and correlation ID propagation."""
    import time
    import uuid

    from opentelemetry import trace

    from sre_agent.auth import set_correlation_id

    # 1. Capture or Generate Correlation ID
    correlation_id = (
        request.headers.get("X-Correlation-ID")
        or request.headers.get("X-Request-ID")
        or str(uuid.uuid4())
    )
    set_correlation_id(correlation_id)

    # 2. Add to OTel Span if active
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute("http.correlation_id", correlation_id)

    # 3. Log request start (Buffered - only logged on error)
    start_time = time.time()
    start_msg = f"🌐 Request Start: {request.method} {request.url.path} [Correlation-ID: {correlation_id}]"

    try:
        response = await call_next(request)

        # 4. Log request completion
        duration = (time.time() - start_time) * 1000

        # Suppress noisy health checks: log only the first success or any transition back to success
        is_health = request.url.path == "/health"
        should_log = True
        if is_health:
            global _HEALTH_SUCCESS_LOGGED
            if response.status_code < 400:
                if _HEALTH_SUCCESS_LOGGED:
                    should_log = False
                else:
                    _HEALTH_SUCCESS_LOGGED = True
            else:
                # On failure, reset the flag so the next success is logged as recovery
                _HEALTH_SUCCESS_LOGGED = False

        if should_log:
            logger.info(
                f"🌐 Request End: {request.method} {request.url.path} - {response.status_code} "
                f"({duration:.2f}ms) [Correlation-ID: {correlation_id}]"
            )

        # 5. Inject back into response headers for client visibility
        response.headers["X-Correlation-ID"] = correlation_id
        return response
    except Exception as e:
        # Request failed - Log the buffered start message first to aid debugging
        logger.info(start_msg)

        duration = (time.time() - start_time) * 1000
        logger.error(
            f"🌐 Request Failed: {request.method} {request.url.path} - {e} "
            f"({duration:.2f}ms) [Correlation-ID: {correlation_id}]"
        )
        raise


async def auth_middleware(request: Request, call_next: Any) -> Any:
    """Middleware to extract Authorization header and set credentials context."""
    from google.oauth2.credentials import Credentials

    from sre_agent.auth import (
        clear_current_credentials,
        decrypt_token,
        set_current_credentials,
        set_current_project_id,
    )

    try:
        auth_header = request.headers.get("Authorization")
        project_id_header = request.headers.get("X-GCP-Project-ID")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            # Create credentials from the token (Access Token)
            # Note: We trust the token format here; downstream APIs will fail if invalid.
            creds = Credentials(token=token)  # type: ignore[no-untyped-call]
            set_current_credentials(creds)
            logger.debug("Auth Middleware: Credentials set in ContextVar from Header")

            try:
                # Optimized Identity Check: Use id_token if provided in header
                from sre_agent.auth import (
                    set_current_user_id,
                    validate_access_token,
                    validate_id_token,
                )

                id_token_header = request.headers.get("X-ID-Token")
                if id_token_header:
                    token_info = await validate_id_token(id_token_header)
                else:
                    # Fallback to access_token validation (now cached)
                    token_info = await validate_access_token(token)

                if token_info.valid and token_info.email:
                    set_current_user_id(token_info.email)
                    # logger.debug(f"Auth Middleware: User identified as {token_info.email}")
                else:
                    logger.warning(
                        f"Auth Middleware: Identity check failed: {token_info.error}"
                    )
            except Exception as e:
                logger.warning(f"Auth Middleware: Identity check failed: {e}")
        else:
            # Fallback to session cookie
            session_id = request.cookies.get("sre_session_id")
            if session_id:
                logger.debug(f"Auth Middleware: Found session cookie: {session_id}")
                from sre_agent.auth import (
                    SESSION_STATE_ACCESS_TOKEN_KEY,
                    set_current_user_id,
                )
                from sre_agent.services import get_session_service

                session_manager = get_session_service()

                # Robust session lookup: try to find user_email from request headers/params first
                user_id_hint = (
                    request.headers.get("X-User-ID")
                    or request.query_params.get("user_id")
                    or ""
                )

                session = await session_manager.get_session(
                    session_id, user_id=user_id_hint
                )

                # If not found with hint, and hint was empty, we might be stuck
                # In local mode with DatabaseSessionService, we could theoretically query by ID only
                # but ADK doesn't expose that easily.
                # For now, we'll rely on the client providing user_id if possible, or 'default'.
                if not session and not user_id_hint:
                    session = await session_manager.get_session(
                        session_id, user_id="default"
                    )

                if session:
                    encrypted_token = session.state.get(SESSION_STATE_ACCESS_TOKEN_KEY)
                    if encrypted_token:
                        # Decrypt token for use
                        session_token = decrypt_token(encrypted_token)

                        # CRITICAL IMPROVEMENT: Validate cached token (now with local TTL cache)
                        from sre_agent.auth import validate_access_token

                        token_info = await validate_access_token(session_token)

                        if token_info.valid:
                            creds = Credentials(token=session_token)  # type: ignore[no-untyped-call]
                            set_current_credentials(creds)
                            logger.debug(
                                "Auth Middleware: Valid credentials set from Session Cookie"
                            )

                            user_email = (
                                session.state.get("user_email") or token_info.email
                            )
                            if user_email:
                                set_current_user_id(user_email)
                                # logger.debug(f"Auth Middleware: User identified as {user_email} from session")
                        else:
                            logger.warning(
                                f"Auth Middleware: Cached session token is invalid or expired: {token_info.error}"
                            )
                            # Optional: Clear credentials or take action

        # Extract GCP Project ID if provided in header
        if project_id_header:
            set_current_project_id(project_id_header)
        else:
            # Fallback to query parameter if not in header
            project_id_query = request.query_params.get("project_id")
            if project_id_query:
                set_current_project_id(project_id_query)
                logger.debug(
                    f"Auth Middleware: Project ID set from query: {project_id_query}"
                )

        response = await call_next(request)
        return response
    finally:
        # Clear credentials after request to prevent leakage between requests
        clear_current_credentials()


def configure_cors(app: FastAPI) -> None:
    """Configure CORS middleware for the application."""
    cors_origins = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:5000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:5000",
        "http://localhost:50811",  # From user logs
        "http://127.0.0.1:50811",  # From user logs
    ]
    # Allow all origins only if explicitly set (e.g., for containerized deployments)
    if os.getenv("CORS_ALLOW_ALL", "").lower() == "true":
        cors_origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )


def configure_middleware(app: FastAPI) -> None:
    """Configure all middleware for the application."""
    # Register exception handler
    app.add_exception_handler(Exception, global_exception_handler)

    # Configure CORS
    configure_cors(app)

    # Register auth middleware
    app.middleware("http")(auth_middleware)

    # Register tracing middleware (must be the last added to be the first executed - outermost)
    app.middleware("http")(tracing_middleware)
