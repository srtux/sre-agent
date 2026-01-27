"""GCP Observability Library - SRE Agent & Tools.

This library provides the SRE Agent and a suite of observability tools
for Google Cloud (Traces, Logs, Metrics).
"""

import os

# EARLY SANITIZATION: Fix duplicated project IDs (e.g. "proj,proj") before any other libs load
_p = os.environ.get("GOOGLE_CLOUD_PROJECT")
if _p and "," in _p:
    os.environ["GOOGLE_CLOUD_PROJECT"] = _p.split(",")[0].strip()


# =============================================================================
# CRITICAL: Pydantic TypeAdapter Patch for google-adk Compatibility
# =============================================================================
# This MUST run BEFORE any ADK imports. When deployed to Vertex AI Agent Engine,
# the reasoning-engine-assembly-service imports this package directly.
# Without this patch, Pydantic 2.10+ raises:
#   PydanticUserError: Cannot use `config` when the type is a BaseModel...
#
# The ADK library passes `config=ConfigDict(arbitrary_types_allowed=True)` to
# TypeAdapter, but Pydantic forbids this when the type already has its own config.
# =============================================================================
def _patch_pydantic_typeadapter() -> None:
    """Patch Pydantic TypeAdapter to ignore config for BaseModel types."""
    try:
        import inspect
        from typing import Any

        import pydantic
        from pydantic import TypeAdapter

        # Guard against double-patching
        if getattr(TypeAdapter, "_adk_patched", False):
            return

        original_init = TypeAdapter.__init__

        def patched_init(
            self: Any,
            type_: Any,
            *,
            config: Any = None,
            _parent_depth: int = 2,
            module: str | None = None,
        ) -> None:
            # If config is provided and type is a BaseModel, drop the config
            # to avoid PydanticUserError. The BaseModel's own config is used.
            if config is not None:
                if inspect.isclass(type_) and issubclass(type_, pydantic.BaseModel):
                    config = None
            return original_init(
                self, type_, config=config, _parent_depth=_parent_depth, module=module
            )

        TypeAdapter.__init__ = patched_init  # type: ignore[assignment]
        TypeAdapter._adk_patched = True  # type: ignore[attr-defined]
    except (ImportError, AttributeError):
        # Pydantic not installed or incompatible version - skip patching
        pass


# Apply the patch immediately at module load time
_patch_pydantic_typeadapter()


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

# Avoid top-level imports of heavy agent modules to prevent early
# initialization of OTel or ADK before telemetry.setup_telemetry() runs.
# Modules should import from .agent directly.
# However, for ADK CLI compatibility (e.g. adk eval), we need to expose
# the agent module and root_agent at the package level.
from . import agent  # noqa: E402
from .agent import root_agent  # noqa: E402

__all__ = ["agent", "auth", "prompt", "root_agent", "schema", "suggestions", "tools"]
