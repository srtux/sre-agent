"""Online GenAI evaluation configuration endpoints."""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from sre_agent.auth import is_guest_mode
from sre_agent.exceptions import UserFacingError
from sre_agent.services import get_storage_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/evals", tags=["evals"])

KEY_EVAL_CONFIGS = "eval_configs"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class EvalConfig(BaseModel):
    """Persisted evaluation configuration for a single agent."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    agent_name: str
    is_enabled: bool = False
    sampling_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    metrics: list[str] = Field(default_factory=list)
    last_eval_timestamp: datetime | None = None


class UpsertEvalConfigRequest(BaseModel):
    """Request body for creating or updating an eval config."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    is_enabled: bool
    sampling_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    metrics: list[str] = Field(default_factory=list)


class EvalConfigResponse(BaseModel):
    """Response wrapper for a single eval config."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    config: EvalConfig


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _load_configs() -> dict[str, Any]:
    """Load all eval configs from the storage backend.

    Returns:
        A dict keyed by agent_name with config dicts as values.
    """
    storage = get_storage_service()
    data = await storage._backend.get(KEY_EVAL_CONFIGS)
    if isinstance(data, dict):
        return data
    return {}


async def _save_configs(configs: dict[str, Any]) -> None:
    """Persist eval configs to the storage backend."""
    storage = get_storage_service()
    await storage._backend.set(KEY_EVAL_CONFIGS, configs)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/config")
async def list_eval_configs() -> dict[str, Any]:
    """List all eval configurations.

    Returns:
        A JSON object with a ``configs`` key containing a list of
        :class:`EvalConfig` dicts.
    """
    if is_guest_mode():
        return {"configs": []}
    try:
        configs = await _load_configs()
        return {"configs": list(configs.values())}
    except (HTTPException, UserFacingError):
        raise
    except Exception as e:
        logger.exception("Error listing eval configs")
        raise UserFacingError(f"Internal server error: {e}") from e


@router.post("/config/{agent_name}", response_model=EvalConfigResponse)
async def upsert_eval_config(
    agent_name: str,
    request: UpsertEvalConfigRequest,
) -> dict[str, Any]:
    """Create or update an eval configuration for the given agent.

    Args:
        agent_name: The agent identifier (path parameter).
        request: The eval config fields to set.

    Returns:
        An :class:`EvalConfigResponse` wrapping the persisted config.
    """
    if is_guest_mode():
        # Return a synthetic response so the frontend does not break.
        config = EvalConfig(
            agent_name=agent_name,
            is_enabled=request.is_enabled,
            sampling_rate=request.sampling_rate,
            metrics=request.metrics,
        )
        return {"config": config.model_dump(mode="json")}
    try:
        configs = await _load_configs()

        # Preserve last_eval_timestamp if the config already exists.
        existing_timestamp: str | None = None
        if agent_name in configs:
            existing_timestamp = configs[agent_name].get("last_eval_timestamp")

        config = EvalConfig(
            agent_name=agent_name,
            is_enabled=request.is_enabled,
            sampling_rate=request.sampling_rate,
            metrics=request.metrics,
            last_eval_timestamp=existing_timestamp,  # type: ignore[arg-type]
        )

        configs[agent_name] = config.model_dump(mode="json")
        await _save_configs(configs)

        return {"config": configs[agent_name]}
    except (HTTPException, UserFacingError):
        raise
    except Exception as e:
        logger.exception("Error upserting eval config for %s", agent_name)
        raise UserFacingError(f"Internal server error: {e}") from e


@router.get("/config/{agent_name}", response_model=EvalConfigResponse)
async def get_eval_config(agent_name: str) -> dict[str, Any]:
    """Get the eval configuration for a single agent.

    Args:
        agent_name: The agent identifier (path parameter).

    Returns:
        An :class:`EvalConfigResponse` wrapping the config.

    Raises:
        HTTPException: 404 if no config exists for the given agent.
    """
    if is_guest_mode():
        return {"config": EvalConfig(agent_name=agent_name).model_dump(mode="json")}
    try:
        configs = await _load_configs()
        if agent_name not in configs:
            raise HTTPException(
                status_code=404,
                detail=f"Eval config not found for agent: {agent_name}",
            )
        return {"config": configs[agent_name]}
    except (HTTPException, UserFacingError):
        raise
    except Exception as e:
        logger.exception("Error getting eval config for %s", agent_name)
        raise UserFacingError(f"Internal server error: {e}") from e


@router.delete("/config/{agent_name}", status_code=204)
async def delete_eval_config(agent_name: str) -> Response:
    """Delete the eval configuration for the given agent.

    Args:
        agent_name: The agent identifier (path parameter).

    Returns:
        204 No Content on success.
    """
    if is_guest_mode():
        return Response(status_code=204)
    try:
        configs = await _load_configs()
        configs.pop(agent_name, None)
        await _save_configs(configs)
        return Response(status_code=204)
    except (HTTPException, UserFacingError):
        raise
    except Exception as e:
        logger.exception("Error deleting eval config for %s", agent_name)
        raise UserFacingError(f"Internal server error: {e}") from e
