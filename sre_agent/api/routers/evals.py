"""Online GenAI evaluation configuration and metrics endpoints."""

import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import anyio
from fastapi import APIRouter, HTTPException, Query, Response
from google.cloud import bigquery
from pydantic import BaseModel, ConfigDict, Field

from sre_agent.auth import is_guest_mode
from sre_agent.exceptions import UserFacingError
from sre_agent.services import get_storage_service
from sre_agent.tools.bigquery.queries import get_aggregate_eval_metrics_query

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


# ---------------------------------------------------------------------------
# Aggregate metrics endpoint
# ---------------------------------------------------------------------------

_DEFAULT_BQ_DATASET = os.environ.get("SRE_AGENT_EVAL_BQ_DATASET", "otel_export")

_IDENTIFIER_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$")


def _validate_identifier(value: str, name: str) -> None:
    """Validate that *value* looks like a safe BQ identifier."""
    if not _IDENTIFIER_RE.match(value):
        raise HTTPException(status_code=400, detail=f"Invalid {name}.")


@router.get("/metrics/aggregate")
async def get_eval_metrics_aggregate(
    project_id: str = Query(..., description="GCP project ID"),
    hours: int = Query(default=24, ge=1, le=720, description="Lookback window"),
    service_name: str = Query(default="", description="Agent/service name filter"),
    trace_dataset: str = Query(
        default=_DEFAULT_BQ_DATASET, description="BQ dataset name"
    ),
) -> dict[str, Any]:
    """Return aggregate evaluation metrics grouped by hour and metric name.

    Returns:
        A JSON object with a ``metrics`` key containing a list of
        ``{timeBucket, metricName, avgScore, sampleCount}`` dicts.
    """
    if is_guest_mode():
        return {"metrics": _demo_eval_metrics(hours)}

    _validate_identifier(project_id, "project_id")
    _validate_identifier(trace_dataset, "trace_dataset")
    if service_name:
        _validate_identifier(service_name, "service_name")

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours)

    table_name = f"{project_id}.{trace_dataset}._AllSpans"
    query = get_aggregate_eval_metrics_query(
        table_name=table_name,
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat(),
        service_name=service_name or None,
    )

    try:
        client = bigquery.Client(project=project_id)
        rows = await anyio.to_thread.run_sync(
            lambda: list(client.query_and_wait(query))
        )

        metrics = []
        for row in rows:
            metrics.append(
                {
                    "timeBucket": row.time_bucket.isoformat()
                    if row.time_bucket
                    else None,
                    "metricName": row.metric_name,
                    "avgScore": float(row.avg_score) if row.avg_score else 0.0,
                    "sampleCount": int(row.sample_count) if row.sample_count else 0,
                }
            )

        return {"metrics": metrics}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to fetch aggregate eval metrics")
        raise HTTPException(
            status_code=500, detail="Failed to fetch aggregate eval metrics."
        ) from exc


def _demo_eval_metrics(hours: int) -> list[dict[str, Any]]:
    """Generate synthetic eval metrics for demo/guest mode."""
    import random

    now = datetime.now(timezone.utc)
    metric_names = ["coherence", "groundedness", "fluency", "safety"]
    results: list[dict[str, Any]] = []
    random.seed(42)

    for h in range(min(hours, 48)):
        bucket = (now - timedelta(hours=hours - h)).replace(
            minute=0, second=0, microsecond=0
        )
        for metric in metric_names:
            base = {
                "coherence": 0.85,
                "groundedness": 0.78,
                "fluency": 0.90,
                "safety": 0.95,
            }
            score = max(0.0, min(1.0, base[metric] + random.uniform(-0.1, 0.1)))
            results.append(
                {
                    "timeBucket": bucket.isoformat(),
                    "metricName": metric,
                    "avgScore": round(score, 3),
                    "sampleCount": random.randint(5, 50),
                }
            )
    return results
