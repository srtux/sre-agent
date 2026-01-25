"""Middleware configuration for the SRE Agent API."""

import logging
import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global handler for unhandled exceptions."""
    logger.error(f"🔥 Global exception handler caught: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc)},
    )


async def auth_middleware(request: Request, call_next: Any) -> Any:
    """Middleware to extract Authorization header and set credentials context."""
    from google.oauth2.credentials import Credentials

    from sre_agent.auth import (
        clear_current_credentials,
        set_current_credentials,
        set_current_project_id,
    )

    try:
        auth_header = request.headers.get("Authorization")
        project_id_header = request.headers.get("X-GCP-Project-ID")

        logger.debug(
            f"Auth Middleware: Authorization header present: {auth_header is not None}"
        )
        logger.debug(f"Auth Middleware: X-GCP-Project-ID header: {project_id_header}")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            # Create credentials from the token (Access Token)
            # Note: We trust the token format here; downstream APIs will fail if invalid.
            creds = Credentials(token=token)  # type: ignore[no-untyped-call]
            set_current_credentials(creds)
            logger.debug("Auth Middleware: Credentials set in ContextVar from Header")

            try:
                # Validate token to extract user identity (email)
                # TODO: Implement caching to avoid latency on every request
                from sre_agent.auth import set_current_user_id, validate_access_token

                token_info = await validate_access_token(token)
                if token_info.valid and token_info.email:
                    set_current_user_id(token_info.email)
                    logger.debug(
                        f"Auth Middleware: User identified as {token_info.email}"
                    )
                else:
                    logger.warning(
                        f"Auth Middleware: Token validation failed: {token_info.error}"
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
                    session_token = session.state.get(SESSION_STATE_ACCESS_TOKEN_KEY)
                    if session_token:
                        # CRITICAL IMPROVEMENT: Validate cached token
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
                                logger.debug(
                                    f"Auth Middleware: User identified as {user_email} from session"
                                )
                        else:
                            logger.warning(
                                f"Auth Middleware: Cached session token is invalid: {token_info.error}"
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
