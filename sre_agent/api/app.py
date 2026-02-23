"""SRE Agent API application factory.

This module creates and configures the FastAPI application with all routers
and middleware.
"""

import logging
import os
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from sre_agent.api.middleware import configure_middleware
from sre_agent.api.routers import (
    agent_graph_router,
    agent_graph_setup_router,
    agent_router,
    dashboards_router,
    evals_router,
    health_router,
    help_router,
    permissions_router,
    preferences_router,
    sessions_router,
    system_router,
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

    # Patch Pydantic TypeAdapter for google-adk compatibility
    _patch_pydantic()

    # Enable JSON Schema for Vertex AI compatibility
    _enable_json_schema_feature()

    # Initialize Vertex AI globally if needed
    _initialize_vertex_ai()

    # Create application
    app = FastAPI(title=title)

    # Configure middleware (CORS, auth, exception handling)
    configure_middleware(app)

    # Include routers
    app.include_router(health_router)
    app.include_router(agent_router)
    app.include_router(tools_router)
    app.include_router(sessions_router)
    app.include_router(system_router)
    app.include_router(preferences_router)
    app.include_router(permissions_router)
    app.include_router(help_router)
    app.include_router(dashboards_router)
    app.include_router(agent_graph_router)
    app.include_router(agent_graph_setup_router)
    app.include_router(evals_router)

    # Register tool test functions
    register_all_test_functions()
    logger.info("Tool configuration manager initialized")

    # Instrument FastAPI if tracing is enabled
    # We check the same env var as telemetry.py
    if os.environ.get("LANGFUSE_TRACING", "false").lower() == "true":
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            FastAPIInstrumentor.instrument_app(app)
            logger.info("✨ FastAPI OpenTelemetry instrumentation applied")
        except ImportError:
            logger.warning(
                "Could not import FastAPIInstrumentor. Is opentelemetry-instrumentation-fastapi installed?"
            )

    # Optionally mount ADK agent routes
    if include_adk_routes:
        _mount_adk_routes(app)

    # Mount React Agent Graph UI at /graph (before Flutter catch-all)
    if os.path.exists("agent_graph_web"):
        app.mount(
            "/graph",
            StaticFiles(directory="agent_graph_web", html=True),
            name="agent_graph",
        )
        logger.info("Mounted Agent Graph UI from 'agent_graph_web' at /graph")

    # Mount static files for the frontend if they exist
    # In Cloud Run, the build artifacts are copied to /app/web
    if os.path.exists("web"):
        app.mount("/", StaticFiles(directory="web", html=True), name="web")
        logger.info("Mounted static files from 'web' directory")

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
        logger.debug("✅ Applied Pydantic bridge for MCP ClientSession")
    except ImportError:
        pass


def _enable_json_schema_feature() -> None:
    """Enable JSON Schema for function declarations (Vertex AI compatibility)."""
    try:
        from google.adk.features import FeatureName, override_feature_enabled

        override_feature_enabled(FeatureName.JSON_SCHEMA_FOR_FUNC_DECL, True)
        logger.debug(
            "✅ Enabled JSON_SCHEMA_FOR_FUNC_DECL feature for Vertex AI compatibility"
        )
    except ImportError:
        logger.debug(
            "Could not enable JSON_SCHEMA_FOR_FUNC_DECL - "
            "google.adk.features not available"
        )


def _patch_pydantic() -> None:
    """Patch Pydantic TypeAdapter to avoid errors with BaseModel + config.

    This is a workaround for google-adk compatibility. The ADK library passes
    `config=pydantic.ConfigDict(arbitrary_types_allowed=True)` to TypeAdapter,
    which Pydantic forbids if the type is already a BaseModel.
    """
    try:
        import inspect

        import pydantic
        from pydantic import TypeAdapter

        original_init = TypeAdapter.__init__

        def new_init(
            self: Any,
            type: Any,
            *,
            config: Any = None,
            _parent_depth: int = 2,
            module: str | None = None,
        ) -> None:
            if config is not None:
                # Check if type is a BaseModel or similar
                if inspect.isclass(type) and issubclass(type, pydantic.BaseModel):
                    # Mask the config to avoid PydanticUserError
                    # The BaseModel's own config will be used instead.
                    config = None
            return original_init(
                self, type, config=config, _parent_depth=_parent_depth, module=module
            )

        TypeAdapter.__init__ = new_init  # type: ignore
        logger.info("Patched Pydantic TypeAdapter for google-adk compatibility")
    except (ImportError, AttributeError) as e:
        logger.warning(f"Failed to patch Pydantic TypeAdapter: {e}")


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
            location = os.getenv("GCP_LOCATION") or os.getenv(
                "GOOGLE_CLOUD_LOCATION", "us-central1"
            )

            if project_id:
                # google-genai SDK fails if both project/location AND API key are present.
                if os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"):
                    logger.info(
                        "Unsetting API keys to favor project-based authentication"
                    )
                    os.environ.pop("GOOGLE_API_KEY", None)
                    os.environ.pop("GEMINI_API_KEY", None)

                vertexai.init(project=project_id, location=location)
                logger.info(
                    f"Initialized Vertex AI for project {project_id} in {location}"
                )
        except Exception as e:
            logger.warning(f"Failed to initialize Vertex AI: {e}")
