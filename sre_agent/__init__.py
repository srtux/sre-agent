"""GCP Observability Library - SRE Agent & Tools.

This library provides the SRE Agent and a suite of observability tools
for Google Cloud (Traces, Logs, Metrics).
"""

import os

# EARLY SANITIZATION: Fix duplicated project IDs (e.g. "proj,proj") before any other libs load
_p = os.environ.get("GOOGLE_CLOUD_PROJECT")
if _p and "," in _p:
    os.environ["GOOGLE_CLOUD_PROJECT"] = _p.split(",")[0].strip()

# Fix for MCP ClientSession Pydantic compatibility
try:
    from typing import Any

    from mcp.client.session import ClientSession
    from pydantic_core import core_schema

    def _get_pydantic_core_schema(
        cls: type, source_type: Any, handler: Any
    ) -> core_schema.CoreSchema:
        return core_schema.is_instance_schema(cls)

    ClientSession.__get_pydantic_core_schema__ = classmethod(_get_pydantic_core_schema)  # type: ignore[attr-defined]
except ImportError:
    pass

from .agent import (  # noqa: E402
    create_configured_agent,
    get_agent_with_mcp_tools,
    get_enabled_base_tools,
    get_enabled_tools,
    is_tool_enabled,
    root_agent,
    sre_agent,
)

__all__ = [
    "create_configured_agent",
    "get_agent_with_mcp_tools",
    "get_enabled_base_tools",
    "get_enabled_tools",
    "is_tool_enabled",
    "root_agent",
    "sre_agent",
]
