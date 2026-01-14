# 1. APPLY PATCHES AS EARLY AS POSSIBLE
try:
    from typing import TYPE_CHECKING, Any

    if TYPE_CHECKING:
        from google.adk.tools.tool_context import ToolContext

    from mcp.client.session import ClientSession
    from pydantic_core import core_schema

    def _get_pydantic_core_schema(
        cls: type, source_type: Any, handler: Any
    ) -> core_schema.CoreSchema:
        return core_schema.is_instance_schema(cls)

    ClientSession.__get_pydantic_core_schema__ = classmethod(_get_pydantic_core_schema)  # type: ignore
    print("✅ Applied Pydantic bridge for MCP ClientSession")
except ImportError:
    pass


import logging
import os
import sys
from collections.abc import AsyncGenerator
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from google.adk.cli.fast_api import get_fast_api_app
from pydantic import BaseModel

from sre_agent.agent import root_agent
from sre_agent.tools import (
    extract_log_patterns,
    fetch_trace,
    list_gcp_projects,
    list_log_entries,
)
from sre_agent.tools.analysis import genui_adapter

# 0. SET LOG LEVEL EARLY
os.environ["LOG_LEVEL"] = "DEBUG"

# 1.1 CONFIGURING LOGGING
# Configure root logger
# Note: sre_agent.tools.common.telemetry.setup_telemetry will re-configure this
# but we set LOG_LEVEL above to ensure it picks up DEBUG.
logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,  # Force reconfiguration
)

# Configure specific loggers
for logger_name in [
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
    "google.adk",
    "sre_agent",
]:
    logging.getLogger(logger_name).setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

# 2. INTERNAL IMPORTS
# (Imports moved to top-level)

app = FastAPI(title="SRE Agent Toolbox API")


@app.middleware("http")
async def log_requests(request: Request, call_next: Any) -> Any:
    """Middleware to log all HTTP requests."""
    logger.debug(f"👉 Request started: {request.method} {request.url}")
    try:
        response = await call_next(request)
        logger.debug(
            f"✅ Request finished: {request.method} {request.url} - Status: {response.status_code}"
        )
        return response
    except Exception as e:
        logger.error(
            f"❌ Request failed: {request.method} {request.url} - Error: {e}",
            exc_info=True,
        )
        raise


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global handler for unhandled exceptions."""
    logger.error(f"🔥 Global exception handler caught: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc)},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# HELPER: Create ToolContext
async def get_tool_context() -> "ToolContext":
    """Create a ToolContext with a dummy session/invocation."""
    from google.adk.agents.invocation_context import InvocationContext
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.adk.sessions.session import Session
    from google.adk.tools.tool_context import ToolContext

    # Create a minimal session
    session = Session(app_name="sre_agent", user_id="system", id="api-session")

    from google.adk.agents.run_config import RunConfig

    # Create session service
    session_service = InMemorySessionService()  # type: ignore

    # Create invocation context
    inv_ctx = InvocationContext(
        session=session,
        agent=root_agent,
        invocation_id="api-inv",
        session_service=session_service,
        run_config=RunConfig(),
    )

    return ToolContext(invocation_context=inv_ctx)


# 3. TOOL ENDPOINTS


@app.get("/api/tools/trace/{trace_id}")
async def get_trace(trace_id: str, project_id: Any | None = None) -> Any:
    """Fetch and summarize a trace."""
    try:
        # ctx = await get_tool_context()  # Not used currently but good to have if we need it
        result = await fetch_trace(
            trace_id=trace_id,
            project_id=project_id,
        )
        import json

        return json.loads(result)
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/tools/projects/list")
async def list_projects() -> Any:
    """List accessible GCP projects."""
    try:
        result = await list_gcp_projects()
        return result
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/tools/logs/analyze")
async def analyze_logs(payload: dict[str, Any]) -> Any:
    """Fetch logs and extract patterns."""
    try:
        # ctx = await get_tool_context()
        # 1. Fetch logs from Cloud Logging
        entries_json = await list_log_entries(
            filter_str=payload.get("filter"),
            project_id=payload.get("project_id"),
        )

        # Parse JSON result from list_log_entries since it returns a string
        import json

        entries_data = json.loads(entries_json)

        # Handle potential error response
        if "error" in entries_data:
            raise HTTPException(status_code=500, detail=entries_data["error"])

        log_entries = entries_data.get("entries", [])

        # 2. Extract patterns from the fetched entries
        result = await extract_log_patterns(
            log_entries=log_entries,
        )
        return result
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e)) from e


# 4. GENUI ENDPOINT (A2UI Protocol)


class ChatRequest(BaseModel):
    """Request model for GenUI chat."""

    messages: list[dict[str, Any]]


@app.post("/api/genui/chat")
async def genui_chat(request: ChatRequest) -> StreamingResponse:
    """Experimental GenUI endpoint.

    Receives a user message, runs logic via the SRE Agent,
    and streams back A2UI events (BeginRendering, SurfaceUpdate) + Text.
    """
    logger.info("Received GenUI chat request")
    user_message = request.messages[-1]["text"] if request.messages else ""

    async def event_generator() -> AsyncGenerator[str, None]:
        import json
        import uuid

        from google.genai import types

        # 1. Setup Context
        tool_ctx = await get_tool_context()
        # Access protected member as it is not exposed publicly
        inv_ctx = tool_ctx._invocation_context

        # Set user content
        inv_ctx.user_content = types.Content(
            role="user", parts=[types.Part(text=user_message)]
        )

        # Track surfaces to avoid duplicate beginRendering
        # Map tool_name -> surface_id
        active_surfaces = {}

        # 2. Run Agent
        # root_agent.run_async now expects an InvocationContext
        async for event in root_agent.run_async(inv_ctx):
            if not event.content or not event.content.parts:
                continue

            for part in event.content.parts:
                # Handle Text
                if part.text:
                    yield json.dumps({"type": "text", "content": part.text}) + "\n"

                # Handle Tool Responses (Function Responses)
                if part.function_response:
                    tool_name = part.function_response.name
                    # The response is typically a dict in 'response' field
                    result = part.function_response.response

                    # If result is a dict with 'result' key, unwrap it (common pattern)
                    if isinstance(result, dict) and "result" in result:
                        result = result["result"]

                    # Mapping Tool Results to A2UI Widgets
                    widget_map = {
                        "fetch_trace": "x-sre-trace-waterfall",
                        "analyze_critical_path": "x-sre-trace-waterfall",
                        "query_promql": "x-sre-metric-chart",
                        "list_time_series": "x-sre-metric-chart",
                        "extract_log_patterns": "x-sre-log-pattern-viewer",
                        "analyze_bigquery_log_patterns": "x-sre-log-pattern-viewer",
                        "generate_remediation_suggestions": "x-sre-remediation-plan",
                    }

                    if tool_name in widget_map:
                        component_name = widget_map[tool_name]

                        # Ensure we have a surface for this widget type
                        if tool_name not in active_surfaces:
                            surface_id = str(uuid.uuid4())
                            active_surfaces[tool_name] = surface_id

                            # Begin Rendering
                            yield (
                                json.dumps(
                                    {
                                        "type": "a2ui",
                                        "message": {
                                            "beginRendering": {
                                                "surfaceId": surface_id,
                                                "root": f"{tool_name}-root",
                                                "catalogId": "sre-catalog",
                                            }
                                        },
                                    }
                                )
                                + "\n"
                            )

                        surface_id = active_surfaces[tool_name]

                        # Transform data for the specific widget
                        data = result
                        if isinstance(result, str):
                            try:
                                data = json.loads(result)
                            except Exception:
                                pass

                        # Ensure data is a dictionary before transformation
                        if isinstance(data, dict):
                            # Data Transformation (Adapting tool outputs to Flutter models)
                            if component_name == "x-sre-trace-waterfall":
                                data = genui_adapter.transform_trace(data)
                            elif component_name == "x-sre-metric-chart":
                                data = genui_adapter.transform_metrics(data)
                            elif component_name == "x-sre-log-pattern-viewer":
                                # For Log patterns, we just need the list of patterns
                                if "top_patterns" in data:
                                    data = data["top_patterns"]
                            elif component_name == "x-sre-remediation-plan":
                                data = genui_adapter.transform_remediation(data)

                        # Surface Update
                        yield (
                            json.dumps(
                                {
                                    "type": "a2ui",
                                    "message": {
                                        "surfaceUpdate": {
                                            "surfaceId": surface_id,
                                            "components": [
                                                {
                                                    "id": f"{tool_name}-root",
                                                    "component": {component_name: data},
                                                }
                                            ],
                                        }
                                    },
                                }
                            )
                            + "\n"
                        )

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


# 5. MOUNT ADK AGENT

# This creates the FastAPI app with /copilotkit and other routes
adk_app = get_fast_api_app(
    agents_dir="sre_agent",
    web=False,  # We don't need the internal ADK React UI
)

# Mount the ADK app into our main app
app.mount("/adk", adk_app)

# Serve static files from 'web' directory if it exists
if os.path.exists("web"):
    logger.info("Mounting static files from 'web' directory")
    app.mount("/", StaticFiles(directory="web", html=True), name="web")

if __name__ == "__main__":
    # Run on PORT (default 8001)
    port = int(os.getenv("PORT", 8001))
    print(f"🚀 Starting SRE Agent + Tools API on http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
