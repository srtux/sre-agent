"""Batch evaluation worker for Online GenAI Evaluation Service.

This worker is designed to be triggered periodically (via Cloud Scheduler
or the ``POST /api/v1/evals/run`` endpoint).  It reads evaluation
configurations, fetches un-evaluated production traces from BigQuery,
runs them through the Vertex AI Gen AI Evaluation Service, and logs
results as OpenTelemetry events so they appear in the AgentOps dashboard.
"""

from __future__ import annotations

import asyncio
import json as _json
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Default BigQuery dataset for OTel spans
_DEFAULT_BQ_DATASET = "otel_export"

# ---------------------------------------------------------------------------
# SQL template for fetching un-evaluated GenAI spans.
#
# The OpenTelemetry GenAI semantic conventions store prompt/completion data
# in *span events* (``gen_ai.user.message``, ``gen_ai.choice``, etc.) or as
# JSON-encoded span attributes (``gen_ai.input.messages``,
# ``gen_ai.output.messages``).  We try both paths and COALESCE so the query
# works regardless of which instrumentation library wrote the data.
#
# The LEFT JOIN excludes spans that already have a sibling
# ``gen_ai.evaluation`` span in the same trace.
# ---------------------------------------------------------------------------
_UNEVALUATED_SPANS_SQL = """\
SELECT
    t.trace_id,
    t.span_id,
    COALESCE(
        -- Modern OTel GenAI conventions: structured messages attribute
        JSON_VALUE(t.attributes, '$.gen_ai.input.messages'),
        -- Legacy attribute name
        JSON_VALUE(t.attributes, '$.gen_ai.prompt'),
        -- Fallback: first user message from span events
        (
            SELECT JSON_VALUE(evt.attributes, '$.gen_ai.user.message.content')
            FROM UNNEST(t.events) AS evt
            WHERE evt.name IN ('gen_ai.user.message', 'gen_ai.content.prompt')
            LIMIT 1
        )
    ) AS input_text,
    COALESCE(
        -- Modern OTel GenAI conventions: structured messages attribute
        JSON_VALUE(t.attributes, '$.gen_ai.output.messages'),
        -- Legacy attribute name
        JSON_VALUE(t.attributes, '$.gen_ai.completion'),
        -- Fallback: first choice from span events
        (
            SELECT JSON_VALUE(evt.attributes, '$.gen_ai.choice.message.content')
            FROM UNNEST(t.events) AS evt
            WHERE evt.name IN ('gen_ai.choice', 'gen_ai.content.completion')
            LIMIT 1
        )
    ) AS output_text,
    JSON_VALUE(t.attributes, '$.gen_ai.system') AS gen_ai_system,
    t.start_time
FROM `{project}.{dataset}._AllSpans` AS t
LEFT JOIN `{project}.{dataset}._AllSpans` AS e
    ON t.trace_id = e.trace_id
    AND e.name = 'gen_ai.evaluation'
WHERE
    JSON_VALUE(t.resource.attributes, '$."service.name"') = @agent_name
    AND t.start_time > @last_eval_timestamp
    AND JSON_VALUE(t.attributes, '$.gen_ai.system') IS NOT NULL
    AND e.trace_id IS NULL
ORDER BY t.start_time ASC
LIMIT @max_spans
"""


async def _fetch_eval_configs() -> list[dict[str, Any]]:
    """Fetch all enabled evaluation configurations from storage.

    Returns:
        List of eval config dicts where is_enabled is True.
    """
    from sre_agent.services.storage import get_storage_service

    storage = get_storage_service()
    all_configs: dict[str, Any] | None = await storage._backend.get("eval_configs")
    if not all_configs:
        return []
    return [
        {**cfg, "agent_name": name}
        for name, cfg in all_configs.items()
        if cfg.get("is_enabled", False)
    ]


async def _fetch_unevaluated_spans(
    project_id: str,
    agent_name: str,
    last_eval_timestamp: str,
    dataset: str = _DEFAULT_BQ_DATASET,
    max_spans: int = 100,
) -> list[dict[str, Any]]:
    """Query BigQuery for GenAI spans that have not been evaluated yet.

    Args:
        project_id: GCP project ID.
        agent_name: The service name / agent name to filter on.
        last_eval_timestamp: ISO timestamp -- only fetch spans after this.
        dataset: BigQuery dataset containing OTel exports.
        max_spans: Maximum number of spans to fetch per run.

    Returns:
        List of span dicts with trace_id, span_id, input_text, output_text.
    """
    import anyio
    from google.cloud import bigquery

    client = bigquery.Client(project=project_id)
    # NOTE: project and dataset are interpolated via .format() because BQ
    # parameterized queries do not support table-name parameters.  Both
    # values come from trusted environment variables only.
    query = _UNEVALUATED_SPANS_SQL.format(
        project=project_id,
        dataset=dataset,
    )
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("agent_name", "STRING", agent_name),
            bigquery.ScalarQueryParameter(
                "last_eval_timestamp", "TIMESTAMP", last_eval_timestamp
            ),
            bigquery.ScalarQueryParameter("max_spans", "INT64", max_spans),
        ]
    )

    def _execute() -> list[dict[str, Any]]:
        query_job = client.query(query, job_config=job_config)
        return [dict(row) for row in query_job.result()]

    return await anyio.to_thread.run_sync(_execute)


def _extract_text_from_messages(raw: str | None) -> str:
    """Extract plain text from a GenAI messages JSON attribute.

    The ``gen_ai.input.messages`` / ``gen_ai.output.messages`` attributes are
    JSON arrays of message objects such as::

        [{"role": "user", "content": [{"type": "text", "text": "Hello"}]}]

    This helper extracts the concatenated text content.  If the value is
    already plain text (legacy ``gen_ai.prompt`` attribute), it is returned
    as-is.
    """
    if not raw:
        return ""
    # Fast path: not JSON
    if not raw.startswith("[") and not raw.startswith("{"):
        return raw
    try:
        data = _json.loads(raw)
    except (ValueError, TypeError):
        return raw

    parts: list[str] = []
    messages = data if isinstance(data, list) else [data]
    for msg in messages:
        if isinstance(msg, str):
            parts.append(msg)
            continue
        if not isinstance(msg, dict):
            continue
        # Handle {"content": "text"} or {"content": [{"text": "..."}]}
        content = msg.get("content", msg.get("parts", ""))
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(item.get("text", ""))
    return "\n".join(p for p in parts if p)


async def _run_vertex_eval(
    spans: list[dict[str, Any]],
    metrics: list[str],
) -> dict[str, dict[str, dict[str, Any]]]:
    """Run Vertex AI batch evaluation on a list of production trace spans.

    Uses the GA ``vertexai.evaluation.EvalTask`` API with
    ``MetricPromptTemplateExamples.Pointwise`` metrics (coherence,
    groundedness, fluency, safety).

    Args:
        spans: List of span dicts containing input_text and output_text.
        metrics: List of metric names to evaluate (e.g. ["coherence", "fluency"]).

    Returns:
        Nested dict: {span_id: {metric_name: {"score": float, "explanation": str}}}.
    """
    try:
        from vertexai.evaluation import EvalTask, MetricPromptTemplateExamples
    except ImportError:
        logger.warning(
            "vertexai.evaluation not available. "
            "Install google-cloud-aiplatform[evaluation]."
        )
        return {}

    if not spans:
        return {}

    # Build evaluation dataset — extract plain text from structured messages
    eval_dataset = []
    span_index: dict[int, str] = {}  # row index -> span_id
    for span in spans:
        prompt = _extract_text_from_messages(span.get("input_text"))
        response = _extract_text_from_messages(span.get("output_text"))
        if not prompt and not response:
            continue
        eval_dataset.append({"prompt": prompt, "response": response})
        span_index[len(eval_dataset) - 1] = span["span_id"]

    if not eval_dataset:
        logger.info("No spans with extractable text content. Skipping evaluation.")
        return {}

    # Resolve metric objects from Pointwise templates
    resolved_metrics: list[Any] = []
    for m in metrics:
        template = getattr(MetricPromptTemplateExamples.Pointwise, m.upper(), None)
        if template is not None:
            resolved_metrics.append(template)
        else:
            logger.warning(f"Unknown metric '{m}', skipping.")

    if not resolved_metrics:
        logger.warning("No valid metrics resolved. Skipping evaluation.")
        return {}

    # Run evaluation (blocking call — offload to thread)
    try:
        import anyio
        import pandas as pd

        eval_task = EvalTask(
            dataset=pd.DataFrame(eval_dataset),
            metrics=resolved_metrics,
        )
        result = await anyio.to_thread.run_sync(eval_task.evaluate)
    except Exception:
        logger.exception("Vertex AI evaluation failed")
        return {}

    # Parse results into per-span, per-metric format
    results_by_span: dict[str, dict[str, dict[str, Any]]] = {}
    metrics_table = result.metrics_table
    if metrics_table is not None:
        for idx, row in metrics_table.iterrows():
            span_id = span_index.get(int(idx), "")
            if not span_id:
                continue
            span_results: dict[str, dict[str, Any]] = {}
            for metric_name in metrics:
                score_col = f"{metric_name}/score"
                explanation_col = f"{metric_name}/explanation"
                if score_col in row:
                    span_results[metric_name] = {
                        "score": (
                            float(row[score_col]) if row[score_col] is not None else 0.0
                        ),
                        "explanation": str(row.get(explanation_col, "")),
                    }
            if span_results:
                results_by_span[span_id] = span_results

    return results_by_span


async def _update_last_eval_timestamp(
    agent_name: str,
    timestamp: datetime,
) -> None:
    """Update the last_eval_timestamp for an agent config in storage.

    Args:
        agent_name: The agent whose config to update.
        timestamp: The new last evaluation timestamp.
    """
    from sre_agent.services.storage import get_storage_service

    storage = get_storage_service()
    all_configs: dict[str, Any] | None = await storage._backend.get("eval_configs")
    if all_configs and agent_name in all_configs:
        all_configs[agent_name]["last_eval_timestamp"] = timestamp.isoformat()
        await storage._backend.set("eval_configs", all_configs)


async def run_scheduled_evaluations() -> dict[str, Any]:
    """Main entry point for the scheduled evaluation worker.

    Fetches active configs, queries BigQuery for un-evaluated spans,
    runs Vertex AI evaluations, and logs results as OTel events.

    Returns:
        Summary dict with counts of evaluated spans per agent.
    """
    from sre_agent.tools.common.telemetry import log_evaluation_result

    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    if not project_id:
        logger.error("GOOGLE_CLOUD_PROJECT not set. Cannot run evaluations.")
        return {"error": "GOOGLE_CLOUD_PROJECT not set"}

    bq_dataset = os.environ.get("SRE_AGENT_EVAL_BQ_DATASET")
    if not bq_dataset:
        # Try to discover the linked dataset for the project
        from sre_agent.api.helpers.bq_discovery import get_linked_trace_dataset

        discovered = await get_linked_trace_dataset(project_id)
        bq_dataset = discovered or _DEFAULT_BQ_DATASET

    summary: dict[str, Any] = {
        "agents_processed": 0,
        "total_spans_evaluated": 0,
        "details": {},
    }

    configs = await _fetch_eval_configs()
    if not configs:
        logger.info("No active eval configs found. Nothing to do.")
        return summary

    for config in configs:
        agent_name = config["agent_name"]
        metrics = config.get("metrics", [])
        sampling_rate = config.get("sampling_rate", 1.0)
        last_ts = config.get("last_eval_timestamp", "1970-01-01T00:00:00Z")

        if not metrics:
            logger.warning(f"Agent '{agent_name}' has no metrics configured. Skipping.")
            continue

        logger.info(f"Processing evaluations for agent '{agent_name}'")

        try:
            # Fetch un-evaluated spans
            spans = await _fetch_unevaluated_spans(
                project_id=project_id,
                agent_name=agent_name,
                last_eval_timestamp=last_ts,
                dataset=bq_dataset,
            )

            if not spans:
                logger.info(f"No new spans to evaluate for agent '{agent_name}'.")
                continue

            # Apply sampling
            if sampling_rate < 1.0:
                import random

                spans = [s for s in spans if random.random() < sampling_rate]
                if not spans:
                    logger.info(f"All spans filtered by sampling for '{agent_name}'.")
                    continue

            logger.info(f"Evaluating {len(spans)} spans for agent '{agent_name}'")

            # Run Vertex AI evaluation
            eval_results = await _run_vertex_eval(spans, metrics)

            # Log results as OTel events
            logged_count = 0
            for span in spans:
                span_id = span["span_id"]
                trace_id = span["trace_id"]
                if span_id in eval_results:
                    success = log_evaluation_result(
                        original_trace_id=trace_id,
                        original_span_id=span_id,
                        eval_results=eval_results[span_id],
                    )
                    if success:
                        logged_count += 1

            # Update last eval timestamp
            latest_ts = max(
                (
                    s.get("start_time", datetime.min.replace(tzinfo=timezone.utc))
                    for s in spans
                ),
                default=datetime.now(timezone.utc),
            )
            if isinstance(latest_ts, str):
                latest_ts = datetime.fromisoformat(latest_ts)
            if latest_ts.tzinfo is None:
                latest_ts = latest_ts.replace(tzinfo=timezone.utc)
            await _update_last_eval_timestamp(agent_name, latest_ts)

            summary["agents_processed"] += 1
            summary["total_spans_evaluated"] += logged_count
            summary["details"][agent_name] = {
                "spans_fetched": len(spans),
                "spans_evaluated": logged_count,
            }

        except Exception as e:
            logger.exception(f"Error processing evaluations for agent '{agent_name}'")
            summary["details"][agent_name] = {"error": str(e)}

    logger.info(f"Evaluation run complete: {summary}")
    return summary


def main() -> None:
    """CLI entry point for running the eval worker directly."""
    from sre_agent.tools.common.telemetry import setup_telemetry

    setup_telemetry()
    logger.info("Starting scheduled evaluation worker...")
    result = asyncio.run(run_scheduled_evaluations())
    logger.info(f"Worker finished: {result}")


if __name__ == "__main__":
    main()
