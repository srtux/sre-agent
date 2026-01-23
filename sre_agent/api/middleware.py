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

    from sre_agent.auth import set_current_credentials, set_current_project_id

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        # Create credentials from the token (Access Token)
        # Note: We trust the token format here; downstream APIs will fail if invalid.
        creds = Credentials(token=token)  # type: ignore[no-untyped-call]
        set_current_credentials(creds)

    # Extract GCP Project ID if provided in header
    project_id_header = request.headers.get("X-GCP-Project-ID")
    if project_id_header:
        set_current_project_id(project_id_header)
    else:
        # Fallback to query parameter if not in header
        project_id_query = request.query_params.get("project_id")
        if project_id_query:
            set_current_project_id(project_id_query)

    response = await call_next(request)
    return response


def configure_cors(app: FastAPI) -> None:
    """Configure CORS middleware for the application."""
    cors_origins = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
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
