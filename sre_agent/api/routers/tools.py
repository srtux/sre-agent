"""Tool configuration and testing endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from sre_agent.tools import (
    extract_log_patterns,
    fetch_trace,
    list_gcp_projects,
    list_log_entries,
)
from sre_agent.tools.config import (
    ToolCategory,
    get_tool_config_manager,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tools", tags=["tools"])


class ToolConfigUpdate(BaseModel):
    """Request model for updating tool configuration."""

    enabled: bool


class ToolTestRequest(BaseModel):
    """Request model for testing a tool."""

    tool_name: str


# =============================================================================
# TOOL EXECUTION ENDPOINTS
# =============================================================================


@router.get("/trace/{trace_id}")
async def get_trace(trace_id: str, project_id: Any | None = None) -> Response:
    """Fetch and summarize a trace."""
    try:
        result = await fetch_trace(
            trace_id=trace_id,
            project_id=project_id,
        )
        # Optimized: return pre-serialized JSON to avoid double serialization
        return Response(content=result, media_type="application/json")
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/projects/list")
async def list_projects(query: str | None = None) -> Any:
    """List accessible GCP projects."""
    try:
        result = await list_gcp_projects(query=query)
        return result
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/logs/analyze")
async def analyze_logs(payload: dict[str, Any]) -> Any:
    """Fetch logs and extract patterns."""
    import json as json_lib

    try:
        # 1. Fetch logs from Cloud Logging
        entries_json = await list_log_entries(
            filter_str=payload.get("filter"),
            project_id=payload.get("project_id"),
        )

        # Parse JSON result from list_log_entries since it returns a string
        entries_data = json_lib.loads(entries_json)

        # Handle potential error response
        if "error" in entries_data:
            raise HTTPException(status_code=500, detail=entries_data["error"])

        log_entries = entries_data.get("entries", [])

        # 2. Extract patterns from the fetched entries
        result = await extract_log_patterns(
            log_entries=log_entries,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e)) from e


# =============================================================================
# TOOL CONFIGURATION ENDPOINTS
# =============================================================================


@router.get("/config")
async def get_tool_configs(
    category: str | None = None,
    enabled_only: bool = False,
) -> Any:
    """Get all tool configurations.

    Args:
        category: Optional filter by category (api_client, mcp, analysis, etc.)
        enabled_only: If True, only return enabled tools

    Returns:
        List of tool configurations grouped by category.
    """
    try:
        manager = get_tool_config_manager()
        configs = manager.get_all_configs()

        # Filter by category if specified
        if category:
            try:
                cat = ToolCategory(category)
                configs = [c for c in configs if c.category == cat]
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid category: {category}. "
                    f"Valid categories: {[c.value for c in ToolCategory]}",
                ) from None

        # Filter by enabled status if specified
        if enabled_only:
            configs = [c for c in configs if c.enabled]

        # Group by category for better UI organization
        grouped: dict[str, list[dict[str, Any]]] = {}
        for config in configs:
            cat_name = config.category.value
            if cat_name not in grouped:
                grouped[cat_name] = []
            grouped[cat_name].append(config.to_dict())

        # Calculate summary stats
        total = len(configs)
        enabled = len([c for c in configs if c.enabled])
        testable = len([c for c in configs if c.testable])

        return {
            "tools": grouped,
            "summary": {
                "total": total,
                "enabled": enabled,
                "disabled": total - enabled,
                "testable": testable,
            },
            "categories": [c.value for c in ToolCategory],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tool configs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/config/{tool_name}")
async def get_tool_config(tool_name: str) -> Any:
    """Get configuration for a specific tool."""
    try:
        manager = get_tool_config_manager()
        config = manager.get_config(tool_name)

        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{tool_name}' not found",
            )

        return config.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tool config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/config/{tool_name}")
async def update_tool_config(tool_name: str, update: ToolConfigUpdate) -> Any:
    """Update configuration for a specific tool (enable/disable)."""
    try:
        manager = get_tool_config_manager()
        config = manager.get_config(tool_name)

        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{tool_name}' not found",
            )

        success = manager.set_enabled(tool_name, update.enabled)

        if not success:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update tool '{tool_name}'",
            )

        # Return updated config
        updated_config = manager.get_config(tool_name)
        return {
            "message": f"Tool '{tool_name}' "
            f"{'enabled' if update.enabled else 'disabled'} successfully",
            "tool": updated_config.to_dict() if updated_config else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tool config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/config/bulk")
async def bulk_update_tool_configs(updates: dict[str, bool]) -> Any:
    """Bulk update tool configurations.

    Args:
        updates: Dictionary of tool_name -> enabled (bool)

    Returns:
        Summary of updates performed.
    """
    try:
        manager = get_tool_config_manager()
        results: dict[str, Any] = {
            "updated": {},
            "failed": {},
            "not_found": [],
        }

        for tool_name, enabled in updates.items():
            config = manager.get_config(tool_name)
            if not config:
                results["not_found"].append(tool_name)
                continue

            success = manager.set_enabled(tool_name, enabled)
            if success:
                results["updated"][tool_name] = enabled
            else:
                results["failed"][tool_name] = "Update failed"

        return {
            "message": f"Bulk update completed: {len(results['updated'])} updated, "
            f"{len(results['failed'])} failed, {len(results['not_found'])} not found",
            "results": results,
        }
    except Exception as e:
        logger.error(f"Error in bulk update: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


# =============================================================================
# TOOL TESTING ENDPOINTS
# =============================================================================


@router.post("/test/{tool_name}")
async def test_tool(tool_name: str) -> Any:
    """Test a specific tool's connectivity/functionality.

    This performs a lightweight connectivity test to verify the tool is working.
    """
    try:
        manager = get_tool_config_manager()
        config = manager.get_config(tool_name)

        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{tool_name}' not found",
            )

        if not config.testable:
            return {
                "tool_name": tool_name,
                "testable": False,
                "message": f"Tool '{tool_name}' is not testable",
            }

        result = await manager.test_tool(tool_name)

        return {
            "tool_name": tool_name,
            "testable": True,
            "result": {
                "status": result.status.value,
                "message": result.message,
                "latency_ms": result.latency_ms,
                "timestamp": result.timestamp,
                "details": result.details,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing tool: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/test-all")
async def test_all_tools(category: str | None = None) -> Any:
    """Test all testable tools and return results.

    Args:
        category: Optional filter to test only tools in a specific category
    """
    try:
        manager = get_tool_config_manager()
        configs = manager.get_all_configs()

        # Filter by category if specified
        if category:
            try:
                cat = ToolCategory(category)
                configs = [c for c in configs if c.category == cat]
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid category: {category}",
                ) from None

        # Filter to testable tools only
        testable_configs = [c for c in configs if c.testable]

        results = []
        for config in testable_configs:
            try:
                result = await manager.test_tool(config.name)
                results.append(
                    {
                        "tool_name": config.name,
                        "category": config.category.value,
                        "status": result.status.value,
                        "message": result.message,
                        "latency_ms": result.latency_ms,
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "tool_name": config.name,
                        "category": config.category.value,
                        "status": "error",
                        "message": str(e),
                        "latency_ms": None,
                    }
                )

        # Calculate summary
        passed = len([r for r in results if r["status"] == "success"])
        failed = len([r for r in results if r["status"] != "success"])

        return {
            "summary": {
                "total": len(results),
                "passed": passed,
                "failed": failed,
            },
            "results": results,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing all tools: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
