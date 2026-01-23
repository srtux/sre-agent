"""SRE Agent API application factory.

This module creates and configures the FastAPI application with all routers
and middleware.
"""

import logging
import os
from typing import TYPE_CHECKING

from fastapi import FastAPI

from sre_agent.api.middleware import configure_middleware
from sre_agent.api.routers import (
    agent_router,
    health_router,
    permissions_router,
    preferences_router,
    sessions_router,
    tools_router,
)
from sre_agent.tools.test_functions import register_all_test_functions

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def create_app(
    title: str = "SRE Agent Toolbox API",
    include_adk_routes: bool = True,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        title: Application title
        include_adk_routes: Whether to include ADK agent routes

    Returns:
        Configured FastAPI application
    """
    # Initialize telemetry early
    from sre_agent.tools.common.telemetry import setup_telemetry

    setup_telemetry()

    # Apply MCP Pydantic bridge patch
    _apply_mcp_patch()

    # Enable JSON Schema for Vertex AI compatibility
    _enable_json_schema_feature()

    # Create application
    app = FastAPI(title=title)

    # Configure middleware (CORS, auth, exception handling)
    configure_middleware(app)

    # Include routers
    app.include_router(health_router)
    app.include_router(agent_router)
    app.include_router(tools_router)
    app.include_router(sessions_router)
    app.include_router(preferences_router)
    app.include_router(permissions_router)

    # Register tool test functions
    register_all_test_functions()
    logger.info("Tool configuration manager initialized")

    # Optionally mount ADK agent routes
    if include_adk_routes:
        _mount_adk_routes(app)

    return app


def _apply_mcp_patch() -> None:
    """Apply Pydantic bridge for MCP ClientSession."""
    try:
        from typing import Any

        from mcp.client.session import ClientSession
        from pydantic_core import core_schema

        def _get_pydantic_core_schema(
            cls: type, source_type: Any, handler: Any
        ) -> core_schema.CoreSchema:
            return core_schema.is_instance_schema(cls)

        ClientSession.__get_pydantic_core_schema__ = classmethod(  # type: ignore
            _get_pydantic_core_schema
        )
        print("✅ Applied Pydantic bridge for MCP ClientSession")
    except ImportError:
        pass


def _enable_json_schema_feature() -> None:
    """Enable JSON Schema for function declarations (Vertex AI compatibility)."""
    try:
        from google.adk.features import FeatureName, override_feature_enabled

        override_feature_enabled(FeatureName.JSON_SCHEMA_FOR_FUNC_DECL, True)
        print(
            "✅ Enabled JSON_SCHEMA_FOR_FUNC_DECL feature for Vertex AI compatibility"
        )
    except ImportError:
        print(
            "⚠️ Could not enable JSON_SCHEMA_FOR_FUNC_DECL - "
            "google.adk.features not available"
        )


def _mount_adk_routes(app: FastAPI) -> None:
    """Mount ADK agent routes for the root agent.

    Note: The ADK's get_fast_api_app has a specific signature that expects
    agent_dir path. For now, we use direct routing via our own routers.
    """
    # ADK route mounting is handled via the agent router
    # The get_fast_api_app function signature doesn't match our usage pattern
    logger.info("ADK routes handled via agent router at /agent endpoint")


def _initialize_vertex_ai() -> None:
    """Initialize Vertex AI if Agent ID is present."""
    if os.getenv("SRE_AGENT_ID"):
        try:
            import vertexai

            project_id = os.getenv("GCP_PROJECT_ID") or os.getenv(
                "GOOGLE_CLOUD_PROJECT"
            )
            location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

            if project_id:
                vertexai.init(project=project_id, location=location)
                logger.info(
                    f"Initialized Vertex AI for project {project_id} in {location}"
                )
        except Exception as e:
            logger.warning(f"Failed to initialize Vertex AI: {e}")
