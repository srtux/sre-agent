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

# 0. SET LOG LEVEL EARLY
os.environ["LOG_LEVEL"] = "DEBUG"

import uvicorn  # noqa: E402
from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from google.adk.cli.fast_api import get_fast_api_app  # noqa: E402

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
# Re-ordering imports to satisfy linter while maintaining logical grouping for patching
if True:  # Indent internal imports to avoid E402 if strict, but for now we just move them or accept suppression.
    # Actually, best way to handle patch-first pattern is typically to put ignores,
    # or just move standard imports up if possible.
    # But since we need to patch BEFORE other imports, we use noqa.
    pass

from sre_agent.agent import root_agent  # noqa: E402
from sre_agent.tools import (  # noqa: E402
    extract_log_patterns,
    fetch_trace,
    list_gcp_projects,
    list_log_entries,
)

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

    # Create session service
    session_service = InMemorySessionService()  # type: ignore

    # Create invocation context
    inv_ctx = InvocationContext(
        session=session,
        agent=root_agent,
        invocation_id="api-inv",
        session_service=session_service,
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


# 4. MOUNT ADK AGENT

# This creates the FastAPI app with /copilotkit and other routes
adk_app = get_fast_api_app(
    agents_dir="sre_agent",
    web=False,  # We don't need the internal ADK React UI
)

# Mount the ADK app into our main app
app.mount("/", adk_app)

if __name__ == "__main__":
    # Run on 8000
    print("🚀 Starting SRE Agent + Tools API on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
