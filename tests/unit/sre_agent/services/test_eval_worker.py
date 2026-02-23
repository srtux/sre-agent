"""Tests for the batch evaluation worker (sre_agent/services/eval_worker.py).

Tests the scheduled evaluation worker functions including:
- _fetch_eval_configs: loading enabled configs from storage
- _fetch_unevaluated_spans: BigQuery query construction
- _run_vertex_eval: Vertex AI evaluation and result parsing
- _update_last_eval_timestamp: timestamp persistence
- run_scheduled_evaluations: full orchestration flow
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sre_agent.services.eval_worker import (
    _fetch_eval_configs,
    _fetch_unevaluated_spans,
    _update_last_eval_timestamp,
    run_scheduled_evaluations,
)

# ========== _fetch_eval_configs ==========


def _make_mock_storage(backend_get_return=None):
    """Create a mock storage service with an AsyncMock _backend."""
    mock_storage = MagicMock()
    mock_storage._backend = AsyncMock()
    mock_storage._backend.get.return_value = backend_get_return
    return mock_storage


@pytest.mark.asyncio
async def test_fetch_eval_configs_empty_storage():
    """Empty storage returns empty list."""
    mock_storage = _make_mock_storage(backend_get_return=None)

    with patch(
        "sre_agent.services.storage.get_storage_service",
        return_value=mock_storage,
    ):
        result = await _fetch_eval_configs()

    assert result == []
    mock_storage._backend.get.assert_called_once_with("eval_configs")


@pytest.mark.asyncio
async def test_fetch_eval_configs_empty_dict():
    """Empty dict in storage returns empty list."""
    mock_storage = _make_mock_storage(backend_get_return={})

    with patch(
        "sre_agent.services.storage.get_storage_service",
        return_value=mock_storage,
    ):
        result = await _fetch_eval_configs()

    assert result == []


@pytest.mark.asyncio
async def test_fetch_eval_configs_mixed_enabled_disabled():
    """Only enabled configs are returned."""
    mock_storage = _make_mock_storage(
        backend_get_return={
            "agent-a": {
                "is_enabled": True,
                "sampling_rate": 1.0,
                "metrics": ["coherence"],
            },
            "agent-b": {
                "is_enabled": False,
                "sampling_rate": 1.0,
                "metrics": ["fluency"],
            },
            "agent-c": {
                "is_enabled": True,
                "sampling_rate": 0.5,
                "metrics": ["safety"],
            },
        }
    )

    with patch(
        "sre_agent.services.storage.get_storage_service",
        return_value=mock_storage,
    ):
        result = await _fetch_eval_configs()

    assert len(result) == 2
    agent_names = {c["agent_name"] for c in result}
    assert agent_names == {"agent-a", "agent-c"}


@pytest.mark.asyncio
async def test_fetch_eval_configs_missing_is_enabled_field():
    """Config without is_enabled field defaults to not enabled."""
    mock_storage = _make_mock_storage(
        backend_get_return={
            "agent-x": {"sampling_rate": 1.0, "metrics": ["coherence"]},
        }
    )

    with patch(
        "sre_agent.services.storage.get_storage_service",
        return_value=mock_storage,
    ):
        result = await _fetch_eval_configs()

    assert result == []


# ========== _fetch_unevaluated_spans ==========


@pytest.mark.asyncio
async def test_fetch_unevaluated_spans_correct_params():
    """BigQuery client is called with correct SQL and parameters."""
    mock_row1 = {
        "trace_id": "abc123",
        "span_id": "span1",
        "input_text": "hello",
        "output_text": "world",
        "gen_ai_system": "gemini",
        "start_time": "2026-02-20T12:00:00Z",
    }

    mock_query_job = MagicMock()
    mock_query_job.result.return_value = [mock_row1]

    mock_bq_client = MagicMock()
    mock_bq_client.query.return_value = mock_query_job

    mock_bq_module = MagicMock()
    mock_bq_module.Client.return_value = mock_bq_client

    with patch("google.cloud.bigquery", mock_bq_module):
        result = await _fetch_unevaluated_spans(
            project_id="test-project",
            agent_name="my-agent",
            last_eval_timestamp="2026-01-01T00:00:00Z",
            dataset="otel_export",
            max_spans=50,
        )

    mock_bq_module.Client.assert_called_once_with(project="test-project")
    mock_bq_client.query.assert_called_once()
    # Verify the query was formatted with project and dataset
    query_arg = mock_bq_client.query.call_args[0][0]
    assert "test-project" in query_arg
    assert "otel_export" in query_arg
    assert len(result) == 1


@pytest.mark.asyncio
async def test_fetch_unevaluated_spans_empty_result():
    """No matching spans returns empty list."""
    mock_query_job = MagicMock()
    mock_query_job.result.return_value = []

    mock_bq_client = MagicMock()
    mock_bq_client.query.return_value = mock_query_job

    mock_bq_module = MagicMock()
    mock_bq_module.Client.return_value = mock_bq_client

    with patch("google.cloud.bigquery", mock_bq_module):
        result = await _fetch_unevaluated_spans(
            project_id="test-project",
            agent_name="my-agent",
            last_eval_timestamp="2026-01-01T00:00:00Z",
        )

    assert result == []


# ========== _run_vertex_eval ==========


@pytest.mark.asyncio
async def test_run_vertex_eval_empty_spans():
    """Empty spans list returns empty dict."""
    from sre_agent.services.eval_worker import _run_vertex_eval

    result = await _run_vertex_eval(spans=[], metrics=["coherence"])
    assert result == {}


@pytest.mark.asyncio
async def test_run_vertex_eval_import_error():
    """ImportError when vertexai not installed returns empty dict."""
    original_import = __import__

    def _import_raiser(name, *args, **kwargs):
        if name == "vertexai.evaluation" or name.startswith("vertexai.evaluation."):
            raise ImportError("No module named 'vertexai.evaluation'")
        return original_import(name, *args, **kwargs)

    from sre_agent.services.eval_worker import _run_vertex_eval

    with patch("builtins.__import__", side_effect=_import_raiser):
        result = await _run_vertex_eval(
            spans=[{"span_id": "s1", "input_text": "hi", "output_text": "hello"}],
            metrics=["coherence"],
        )

    assert result == {}


@pytest.mark.asyncio
async def test_run_vertex_eval_successful():
    """Successful evaluation returns parsed per-span, per-metric results."""
    import pandas as pd

    mock_metrics_table = pd.DataFrame(
        {
            "coherence/score": [0.85],
            "coherence/explanation": ["Well structured response"],
        }
    )
    mock_result = MagicMock()
    mock_result.metrics_table = mock_metrics_table

    mock_eval_task_instance = MagicMock()
    mock_eval_task_instance.evaluate.return_value = mock_result

    mock_eval_task_cls = MagicMock(return_value=mock_eval_task_instance)

    mock_metric_templates = MagicMock()
    mock_metric_templates.COHERENCE = "coherence_template"

    with patch("vertexai.evaluation.EvalTask", mock_eval_task_cls):
        with patch("vertexai.evaluation.MetricPromptTemplateExamples") as mock_mpt:
            mock_mpt.Pointwise = mock_metric_templates

            from sre_agent.services.eval_worker import _run_vertex_eval

            result = await _run_vertex_eval(
                spans=[
                    {"span_id": "span-1", "input_text": "hi", "output_text": "hello"}
                ],
                metrics=["coherence"],
            )

    assert "span-1" in result
    assert "coherence" in result["span-1"]
    assert result["span-1"]["coherence"]["score"] == 0.85
    assert "Well structured" in result["span-1"]["coherence"]["explanation"]


@pytest.mark.asyncio
async def test_run_vertex_eval_no_valid_metrics():
    """No valid metrics resolved returns empty dict."""
    # Create a mock Pointwise object where getattr returns None for any metric
    mock_metric_templates = MagicMock()
    mock_metric_templates.NONEXISTENT_METRIC = None

    with patch("vertexai.evaluation.EvalTask", MagicMock()):
        with patch("vertexai.evaluation.MetricPromptTemplateExamples") as mock_mpt:
            mock_mpt.Pointwise = mock_metric_templates
            # getattr(MagicMock(), "NONEXISTENT_METRIC") returns a new MagicMock
            # which is truthy. We need to make it return None.
            mock_metric_templates.configure_mock(**{"NONEXISTENT_METRIC": None})

            from sre_agent.services.eval_worker import _run_vertex_eval

            result = await _run_vertex_eval(
                spans=[{"span_id": "s1", "input_text": "a", "output_text": "b"}],
                metrics=["nonexistent_metric"],
            )

    assert result == {}


@pytest.mark.asyncio
async def test_run_vertex_eval_evaluation_exception():
    """EvalTask.evaluate() failure returns empty dict."""
    mock_eval_task_instance = MagicMock()
    mock_eval_task_instance.evaluate.side_effect = RuntimeError("Vertex AI error")
    mock_eval_task_cls = MagicMock(return_value=mock_eval_task_instance)

    mock_metric_templates = MagicMock()
    mock_metric_templates.COHERENCE = "coherence_template"

    with patch("vertexai.evaluation.EvalTask", mock_eval_task_cls):
        with patch("vertexai.evaluation.MetricPromptTemplateExamples") as mock_mpt:
            mock_mpt.Pointwise = mock_metric_templates

            from sre_agent.services.eval_worker import _run_vertex_eval

            result = await _run_vertex_eval(
                spans=[{"span_id": "s1", "input_text": "a", "output_text": "b"}],
                metrics=["coherence"],
            )

    assert result == {}


# ========== _update_last_eval_timestamp ==========


@pytest.mark.asyncio
async def test_update_last_eval_timestamp_updates_correct_config():
    """Updates last_eval_timestamp for the correct agent in storage."""
    mock_storage = _make_mock_storage(
        backend_get_return={
            "agent-a": {
                "is_enabled": True,
                "last_eval_timestamp": None,
            },
            "agent-b": {
                "is_enabled": True,
                "last_eval_timestamp": None,
            },
        }
    )

    ts = datetime(2026, 2, 20, 12, 0, 0, tzinfo=timezone.utc)

    with patch(
        "sre_agent.services.storage.get_storage_service",
        return_value=mock_storage,
    ):
        await _update_last_eval_timestamp("agent-a", ts)

    mock_storage._backend.set.assert_called_once()
    saved_configs = mock_storage._backend.set.call_args[0][1]
    assert saved_configs["agent-a"]["last_eval_timestamp"] == ts.isoformat()
    # agent-b should remain unchanged
    assert saved_configs["agent-b"]["last_eval_timestamp"] is None


@pytest.mark.asyncio
async def test_update_last_eval_timestamp_missing_agent():
    """If agent doesn't exist in storage, no update is performed."""
    mock_storage = _make_mock_storage(
        backend_get_return={
            "other-agent": {"is_enabled": True, "last_eval_timestamp": None},
        }
    )

    ts = datetime(2026, 2, 20, 12, 0, 0, tzinfo=timezone.utc)

    with patch(
        "sre_agent.services.storage.get_storage_service",
        return_value=mock_storage,
    ):
        await _update_last_eval_timestamp("nonexistent-agent", ts)

    mock_storage._backend.set.assert_not_called()


@pytest.mark.asyncio
async def test_update_last_eval_timestamp_empty_storage():
    """If storage is empty/None, no update is performed."""
    mock_storage = _make_mock_storage(backend_get_return=None)

    ts = datetime(2026, 2, 20, 12, 0, 0, tzinfo=timezone.utc)

    with patch(
        "sre_agent.services.storage.get_storage_service",
        return_value=mock_storage,
    ):
        await _update_last_eval_timestamp("any-agent", ts)

    mock_storage._backend.set.assert_not_called()


# ========== run_scheduled_evaluations ==========


@pytest.mark.asyncio
async def test_run_scheduled_evaluations_no_project_id():
    """Missing GOOGLE_CLOUD_PROJECT returns error."""
    with patch.dict("os.environ", {"GOOGLE_CLOUD_PROJECT": ""}, clear=False):
        result = await run_scheduled_evaluations()

    assert "error" in result
    assert "GOOGLE_CLOUD_PROJECT" in result["error"]


@pytest.mark.asyncio
async def test_run_scheduled_evaluations_no_configs():
    """No active configs returns empty summary."""
    with patch.dict(
        "os.environ", {"GOOGLE_CLOUD_PROJECT": "test-project"}, clear=False
    ):
        with patch(
            "sre_agent.services.eval_worker._fetch_eval_configs",
            return_value=[],
        ):
            result = await run_scheduled_evaluations()

    assert result["agents_processed"] == 0
    assert result["total_spans_evaluated"] == 0


@pytest.mark.asyncio
async def test_run_scheduled_evaluations_config_with_no_metrics():
    """Config with empty metrics list is skipped."""
    config = {
        "agent_name": "agent-a",
        "is_enabled": True,
        "sampling_rate": 1.0,
        "metrics": [],
        "last_eval_timestamp": None,
    }

    with patch.dict(
        "os.environ", {"GOOGLE_CLOUD_PROJECT": "test-project"}, clear=False
    ):
        with patch(
            "sre_agent.services.eval_worker._fetch_eval_configs",
            return_value=[config],
        ):
            result = await run_scheduled_evaluations()

    assert result["agents_processed"] == 0
    assert result["total_spans_evaluated"] == 0


@pytest.mark.asyncio
async def test_run_scheduled_evaluations_no_spans():
    """No un-evaluated spans results in no evaluation."""
    config = {
        "agent_name": "agent-a",
        "is_enabled": True,
        "sampling_rate": 1.0,
        "metrics": ["coherence"],
        "last_eval_timestamp": "1970-01-01T00:00:00Z",
    }

    with patch.dict(
        "os.environ", {"GOOGLE_CLOUD_PROJECT": "test-project"}, clear=False
    ):
        with patch(
            "sre_agent.services.eval_worker._fetch_eval_configs",
            return_value=[config],
        ):
            with patch(
                "sre_agent.services.eval_worker._fetch_unevaluated_spans",
                return_value=[],
            ):
                result = await run_scheduled_evaluations()

    assert result["agents_processed"] == 0
    assert result["total_spans_evaluated"] == 0


@pytest.mark.asyncio
async def test_run_scheduled_evaluations_full_flow():
    """Full orchestration flow with mocked BQ and Vertex."""
    config = {
        "agent_name": "agent-a",
        "is_enabled": True,
        "sampling_rate": 1.0,
        "metrics": ["coherence"],
        "last_eval_timestamp": "2026-01-01T00:00:00Z",
    }
    spans = [
        {
            "trace_id": "trace1",
            "span_id": "span1",
            "input_text": "hello",
            "output_text": "world",
            "start_time": datetime(2026, 2, 20, 12, 0, 0, tzinfo=timezone.utc),
        },
    ]
    eval_results = {
        "span1": {
            "coherence": {"score": 0.9, "explanation": "Good"},
        },
    }

    with patch.dict(
        "os.environ", {"GOOGLE_CLOUD_PROJECT": "test-project"}, clear=False
    ):
        with patch(
            "sre_agent.services.eval_worker._fetch_eval_configs",
            return_value=[config],
        ):
            with patch(
                "sre_agent.services.eval_worker._fetch_unevaluated_spans",
                return_value=spans,
            ):
                with patch(
                    "sre_agent.services.eval_worker._run_vertex_eval",
                    return_value=eval_results,
                ):
                    with patch(
                        "sre_agent.tools.common.telemetry.log_evaluation_result",
                        return_value=True,
                    ) as mock_log:
                        with patch(
                            "sre_agent.services.eval_worker._update_last_eval_timestamp",
                        ) as mock_update_ts:
                            result = await run_scheduled_evaluations()

    assert result["agents_processed"] == 1
    assert result["total_spans_evaluated"] == 1
    assert result["details"]["agent-a"]["spans_fetched"] == 1
    assert result["details"]["agent-a"]["spans_evaluated"] == 1

    mock_log.assert_called_once_with(
        original_trace_id="trace1",
        original_span_id="span1",
        eval_results={"coherence": {"score": 0.9, "explanation": "Good"}},
    )
    mock_update_ts.assert_called_once()


@pytest.mark.asyncio
async def test_run_scheduled_evaluations_sampling_filters_spans():
    """Sampling rate < 1.0 can filter out all spans."""
    config = {
        "agent_name": "agent-a",
        "is_enabled": True,
        "sampling_rate": 0.0,  # 0% sampling - all spans filtered
        "metrics": ["coherence"],
        "last_eval_timestamp": "2026-01-01T00:00:00Z",
    }
    spans = [
        {
            "trace_id": "t1",
            "span_id": "s1",
            "input_text": "hi",
            "output_text": "hello",
            "start_time": datetime(2026, 2, 20, tzinfo=timezone.utc),
        },
    ]

    with patch.dict(
        "os.environ", {"GOOGLE_CLOUD_PROJECT": "test-project"}, clear=False
    ):
        with patch(
            "sre_agent.services.eval_worker._fetch_eval_configs",
            return_value=[config],
        ):
            with patch(
                "sre_agent.services.eval_worker._fetch_unevaluated_spans",
                return_value=spans,
            ):
                # With sampling_rate=0.0, random.random() always >= 0.0
                # so all spans are filtered out
                with patch("random.random", return_value=0.5):
                    result = await run_scheduled_evaluations()

    assert result["agents_processed"] == 0


@pytest.mark.asyncio
async def test_run_scheduled_evaluations_exception_in_agent_processing():
    """Exception processing one agent is caught and recorded in details."""
    config = {
        "agent_name": "agent-a",
        "is_enabled": True,
        "sampling_rate": 1.0,
        "metrics": ["coherence"],
        "last_eval_timestamp": "2026-01-01T00:00:00Z",
    }

    with patch.dict(
        "os.environ", {"GOOGLE_CLOUD_PROJECT": "test-project"}, clear=False
    ):
        with patch(
            "sre_agent.services.eval_worker._fetch_eval_configs",
            return_value=[config],
        ):
            with patch(
                "sre_agent.services.eval_worker._fetch_unevaluated_spans",
                side_effect=RuntimeError("BQ connection failed"),
            ):
                result = await run_scheduled_evaluations()

    assert "error" in result["details"]["agent-a"]


@pytest.mark.asyncio
async def test_run_scheduled_evaluations_log_eval_failure():
    """When log_evaluation_result returns False, spans_evaluated count is 0."""
    config = {
        "agent_name": "agent-a",
        "is_enabled": True,
        "sampling_rate": 1.0,
        "metrics": ["coherence"],
        "last_eval_timestamp": "2026-01-01T00:00:00Z",
    }
    spans = [
        {
            "trace_id": "t1",
            "span_id": "s1",
            "input_text": "hi",
            "output_text": "hello",
            "start_time": datetime(2026, 2, 20, tzinfo=timezone.utc),
        },
    ]
    eval_results = {
        "s1": {"coherence": {"score": 0.8, "explanation": "OK"}},
    }

    with patch.dict(
        "os.environ", {"GOOGLE_CLOUD_PROJECT": "test-project"}, clear=False
    ):
        with patch(
            "sre_agent.services.eval_worker._fetch_eval_configs",
            return_value=[config],
        ):
            with patch(
                "sre_agent.services.eval_worker._fetch_unevaluated_spans",
                return_value=spans,
            ):
                with patch(
                    "sre_agent.services.eval_worker._run_vertex_eval",
                    return_value=eval_results,
                ):
                    with patch(
                        "sre_agent.tools.common.telemetry.log_evaluation_result",
                        return_value=False,
                    ):
                        with patch(
                            "sre_agent.services.eval_worker._update_last_eval_timestamp",
                        ):
                            result = await run_scheduled_evaluations()

    assert result["agents_processed"] == 1
    assert result["total_spans_evaluated"] == 0
    assert result["details"]["agent-a"]["spans_evaluated"] == 0


@pytest.mark.asyncio
async def test_run_scheduled_evaluations_multiple_agents():
    """Multiple agents are processed independently."""
    configs = [
        {
            "agent_name": "agent-a",
            "is_enabled": True,
            "sampling_rate": 1.0,
            "metrics": ["coherence"],
            "last_eval_timestamp": "2026-01-01T00:00:00Z",
        },
        {
            "agent_name": "agent-b",
            "is_enabled": True,
            "sampling_rate": 1.0,
            "metrics": ["fluency"],
            "last_eval_timestamp": "2026-01-01T00:00:00Z",
        },
    ]

    def _make_spans(agent_name):
        return [
            {
                "trace_id": f"trace-{agent_name}",
                "span_id": f"span-{agent_name}",
                "input_text": "hi",
                "output_text": "hello",
                "start_time": datetime(2026, 2, 20, tzinfo=timezone.utc),
            }
        ]

    def _mock_fetch_spans(project_id, agent_name, last_eval_timestamp, dataset):
        return _make_spans(agent_name)

    eval_results_a = {
        "span-agent-a": {"coherence": {"score": 0.9, "explanation": "Good"}},
    }
    eval_results_b = {
        "span-agent-b": {"fluency": {"score": 0.7, "explanation": "OK"}},
    }

    async def _mock_run_eval(spans, metrics):
        span_id = spans[0]["span_id"]
        if "agent-a" in span_id:
            return eval_results_a
        return eval_results_b

    with patch.dict(
        "os.environ", {"GOOGLE_CLOUD_PROJECT": "test-project"}, clear=False
    ):
        with patch(
            "sre_agent.services.eval_worker._fetch_eval_configs",
            return_value=configs,
        ):
            with patch(
                "sre_agent.services.eval_worker._fetch_unevaluated_spans",
                side_effect=_mock_fetch_spans,
            ):
                with patch(
                    "sre_agent.services.eval_worker._run_vertex_eval",
                    side_effect=_mock_run_eval,
                ):
                    with patch(
                        "sre_agent.tools.common.telemetry.log_evaluation_result",
                        return_value=True,
                    ):
                        with patch(
                            "sre_agent.services.eval_worker._update_last_eval_timestamp",
                        ):
                            result = await run_scheduled_evaluations()

    assert result["agents_processed"] == 2
    assert result["total_spans_evaluated"] == 2
    assert "agent-a" in result["details"]
    assert "agent-b" in result["details"]
