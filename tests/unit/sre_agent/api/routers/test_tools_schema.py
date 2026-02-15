"""Tests for Pydantic schema compliance on router request models."""

import pytest
from pydantic import ValidationError

from sre_agent.api.routers.tools import (
    AlertsQueryRequest,
    BigQueryQueryRequest,
    LogAnalyzeRequest,
    LogsQueryRequest,
    MetricsQueryRequest,
    NLQueryRequest,
    PromQLQueryRequest,
    ToolConfigUpdate,
    ToolTestRequest,
    TracesQueryRequest,
)


class TestRouterModelSchemaCompliance:
    """Verify all router request models enforce extra='forbid'."""

    @pytest.mark.parametrize(
        "model_cls,valid_kwargs",
        [
            (ToolConfigUpdate, {"enabled": True}),
            (ToolTestRequest, {"tool_name": "fetch_trace"}),
            (LogAnalyzeRequest, {}),
            (TracesQueryRequest, {}),
            (MetricsQueryRequest, {}),
            (PromQLQueryRequest, {}),
            (AlertsQueryRequest, {}),
            (LogsQueryRequest, {}),
            (NLQueryRequest, {"query": "test", "domain": "traces"}),
            (BigQueryQueryRequest, {"sql": "SELECT 1"}),
        ],
    )
    def test_rejects_unknown_fields(self, model_cls, valid_kwargs):
        """Each model must reject unknown fields via extra='forbid'."""
        with pytest.raises(ValidationError, match="extra"):
            model_cls(**valid_kwargs, unknown_field="bad")

    @pytest.mark.parametrize(
        "model_cls,valid_kwargs",
        [
            (ToolConfigUpdate, {"enabled": True}),
            (ToolTestRequest, {"tool_name": "fetch_trace"}),
            (LogAnalyzeRequest, {}),
            (TracesQueryRequest, {}),
            (MetricsQueryRequest, {}),
            (PromQLQueryRequest, {}),
            (AlertsQueryRequest, {}),
            (LogsQueryRequest, {}),
            (NLQueryRequest, {"query": "test", "domain": "traces"}),
            (BigQueryQueryRequest, {"sql": "SELECT 1"}),
        ],
    )
    def test_valid_construction(self, model_cls, valid_kwargs):
        """Each model must accept valid fields."""
        instance = model_cls(**valid_kwargs)
        assert instance is not None

    @pytest.mark.parametrize(
        "model_cls,valid_kwargs",
        [
            (ToolConfigUpdate, {"enabled": True}),
            (ToolTestRequest, {"tool_name": "fetch_trace"}),
            (LogAnalyzeRequest, {}),
            (TracesQueryRequest, {}),
            (MetricsQueryRequest, {}),
            (PromQLQueryRequest, {}),
            (AlertsQueryRequest, {}),
            (LogsQueryRequest, {}),
            (NLQueryRequest, {"query": "test", "domain": "traces"}),
            (BigQueryQueryRequest, {"sql": "SELECT 1"}),
        ],
    )
    def test_frozen(self, model_cls, valid_kwargs):
        """Each model must be immutable (frozen=True)."""
        instance = model_cls(**valid_kwargs)
        with pytest.raises(ValidationError):
            # Try to mutate the first field
            first_field = next(iter(model_cls.model_fields))
            setattr(instance, first_field, "changed")
