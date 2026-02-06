"""Tests for _parse_panel_finding and _extract_council_result in agent.py.

These pure functions normalise session state values into structured dicts
consumed by the frontend's CouncilSynthesisData.fromJson.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from pydantic import BaseModel, ConfigDict

from sre_agent.agent import _extract_council_result, _parse_panel_finding
from sre_agent.council.schemas import InvestigationMode


# ---------------------------------------------------------------------------
# Helper: a minimal Pydantic model to exercise the model_dump branch
# ---------------------------------------------------------------------------
class _FakePanelModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    panel: str
    summary: str
    severity: str
    confidence: float


# ---------------------------------------------------------------------------
# _parse_panel_finding tests
# ---------------------------------------------------------------------------


class TestParsePanelFinding:
    """Tests for _parse_panel_finding."""

    def test_parse_panel_finding_none_returns_none(self) -> None:
        """None input yields None."""
        assert _parse_panel_finding(None) is None

    def test_parse_panel_finding_dict_returns_dict(self) -> None:
        """A plain dict is returned unchanged."""
        d = {"panel": "trace", "severity": "warning", "confidence": 0.8}
        result = _parse_panel_finding(d)
        assert result is d  # identity, not just equality

    def test_parse_panel_finding_json_string_returns_dict(self) -> None:
        """A valid JSON string is parsed into a dict."""
        payload = {"panel": "logs", "severity": "info", "confidence": 0.5}
        raw = json.dumps(payload)
        result = _parse_panel_finding(raw)
        assert result == payload

    def test_parse_panel_finding_invalid_json_returns_none(self) -> None:
        """A non-JSON string returns None."""
        assert _parse_panel_finding("not valid json {{{") is None

    def test_parse_panel_finding_json_non_dict_returns_none(self) -> None:
        """A JSON string that decodes to a list (not dict) returns None."""
        assert _parse_panel_finding(json.dumps([1, 2, 3])) is None

    def test_parse_panel_finding_pydantic_model_returns_dict(self) -> None:
        """An object with model_dump is converted via model_dump(mode='json')."""
        model = _FakePanelModel(
            panel="metrics",
            summary="high CPU",
            severity="warning",
            confidence=0.9,
        )
        result = _parse_panel_finding(model)
        assert isinstance(result, dict)
        assert result["panel"] == "metrics"
        assert result["summary"] == "high CPU"
        assert result["severity"] == "warning"
        assert result["confidence"] == 0.9

    def test_parse_panel_finding_arbitrary_object_returns_none(self) -> None:
        """An arbitrary object without model_dump returns None."""
        assert _parse_panel_finding(12345) is None
        assert _parse_panel_finding(object()) is None


# ---------------------------------------------------------------------------
# Helpers for _extract_council_result tests
# ---------------------------------------------------------------------------


def _make_tool_context(state: dict | None = None) -> MagicMock:
    """Build a mock tool_context with optional session state."""
    ctx = MagicMock()
    if state is not None:
        ctx.invocation_context.session.state = state
    else:
        # Make attribute access raise so the try/except path is exercised
        ctx.invocation_context.session.state = {}
    return ctx


def _panel_finding(
    panel: str,
    severity: str = "info",
    confidence: float = 0.5,
    summary: str = "test",
) -> dict:
    """Convenience builder for a panel finding dict."""
    return {
        "panel": panel,
        "severity": severity,
        "confidence": confidence,
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# _extract_council_result tests
# ---------------------------------------------------------------------------


class TestExtractCouncilResult:
    """Tests for _extract_council_result."""

    def test_extract_full_session_state_all_panels(self) -> None:
        """All 4 panel findings are collected from session state."""
        state = {
            "trace_finding": _panel_finding("trace", "warning", 0.8),
            "metrics_finding": _panel_finding("metrics", "info", 0.6),
            "logs_finding": _panel_finding("logs", "critical", 0.9),
            "alerts_finding": _panel_finding("alerts", "healthy", 0.4),
            "council_synthesis": "Root cause is a memory leak.",
        }
        ctx = _make_tool_context(state)
        result = _extract_council_result(ctx, None, InvestigationMode.STANDARD)

        assert len(result["panels"]) == 4
        assert result["synthesis"] == "Root cause is a memory leak."
        assert result["mode"] == "standard"
        assert result["rounds"] == 1
        assert result["critic_report"] is None

    def test_extract_empty_session_state_falls_back_to_raw_result(self) -> None:
        """When session state has no findings, synthesis falls back to raw_result."""
        ctx = _make_tool_context({})
        result = _extract_council_result(
            ctx, "fallback text", InvestigationMode.STANDARD
        )

        assert result["synthesis"] == "fallback text"
        assert result["panels"] == []
        assert result["overall_severity"] == "info"
        assert result["overall_confidence"] == 0.0

    def test_extract_raw_result_non_string_is_stringified(self) -> None:
        """Non-string raw_result is converted to str for synthesis fallback."""
        ctx = _make_tool_context({})
        result = _extract_council_result(ctx, {"key": "val"}, InvestigationMode.FAST)

        assert result["synthesis"] == str({"key": "val"})

    def test_extract_debate_mode_with_critic_report(self) -> None:
        """Debate mode extracts critic_report and convergence_history rounds."""
        state = {
            "trace_finding": _panel_finding("trace", "warning", 0.7),
            "metrics_finding": _panel_finding("metrics", "info", 0.5),
            "council_synthesis": "Debate conclusion.",
            "critic_report": {
                "agreements": ["both see high latency"],
                "contradictions": [],
                "gaps": ["no log analysis"],
                "revised_confidence": 0.75,
            },
            "debate_convergence_history": [0.5, 0.65, 0.75],
        }
        ctx = _make_tool_context(state)
        result = _extract_council_result(ctx, None, InvestigationMode.DEBATE)

        assert result["mode"] == "debate"
        assert result["rounds"] == 3
        assert result["critic_report"] is not None
        assert result["critic_report"]["revised_confidence"] == 0.75
        assert "both see high latency" in result["critic_report"]["agreements"]

    def test_extract_severity_calculation_max_of_panels(self) -> None:
        """Overall severity is the maximum across all panels."""
        state = {
            "trace_finding": _panel_finding("trace", "info", 0.5),
            "metrics_finding": _panel_finding("metrics", "critical", 0.9),
            "logs_finding": _panel_finding("logs", "warning", 0.7),
        }
        ctx = _make_tool_context(state)
        result = _extract_council_result(ctx, None, InvestigationMode.STANDARD)

        assert result["overall_severity"] == "critical"

    def test_extract_severity_healthy_is_lowest(self) -> None:
        """When all panels report healthy, overall severity is healthy."""
        state = {
            "trace_finding": _panel_finding("trace", "healthy", 0.9),
            "metrics_finding": _panel_finding("metrics", "healthy", 0.8),
        }
        ctx = _make_tool_context(state)
        result = _extract_council_result(ctx, None, InvestigationMode.FAST)

        assert result["overall_severity"] == "healthy"

    def test_extract_confidence_calculation_average(self) -> None:
        """Overall confidence is the average of all panel confidences."""
        state = {
            "trace_finding": _panel_finding("trace", "info", 0.6),
            "metrics_finding": _panel_finding("metrics", "info", 0.8),
            "logs_finding": _panel_finding("logs", "info", 1.0),
        }
        ctx = _make_tool_context(state)
        result = _extract_council_result(ctx, None, InvestigationMode.STANDARD)

        expected = round((0.6 + 0.8 + 1.0) / 3, 3)
        assert result["overall_confidence"] == expected

    def test_extract_confidence_no_panels_is_zero(self) -> None:
        """With no panels, overall confidence is 0.0."""
        ctx = _make_tool_context({})
        result = _extract_council_result(ctx, "fallback", InvestigationMode.STANDARD)

        assert result["overall_confidence"] == 0.0

    def test_extract_no_tool_context_access(self) -> None:
        """When tool_context raises on attribute access, falls back gracefully."""

        class _BrokenContext:
            """A tool_context that raises on any attribute access."""

            @property
            def invocation_context(self) -> None:
                raise RuntimeError("context unavailable")

        result = _extract_council_result(
            _BrokenContext(), "raw fallback", InvestigationMode.FAST
        )

        assert result["synthesis"] == "raw fallback"
        assert result["panels"] == []
        assert result["mode"] == "fast"

    def test_extract_synthesis_from_dict(self) -> None:
        """When council_synthesis is a dict, its 'synthesis' key is used."""
        state = {
            "council_synthesis": {
                "synthesis": "Dict-based synthesis.",
                "extra": "ignored",
            },
        }
        ctx = _make_tool_context(state)
        result = _extract_council_result(ctx, None, InvestigationMode.STANDARD)

        assert result["synthesis"] == "Dict-based synthesis."

    def test_extract_synthesis_from_pydantic_model(self) -> None:
        """When council_synthesis has model_dump, it is stringified."""
        model = _FakePanelModel(
            panel="synthesizer",
            summary="conclusion",
            severity="info",
            confidence=0.5,
        )
        state = {"council_synthesis": model}
        ctx = _make_tool_context(state)
        result = _extract_council_result(ctx, None, InvestigationMode.STANDARD)

        # The function converts model_dump(mode="json") to str
        assert "synthesizer" in result["synthesis"]
        assert "conclusion" in result["synthesis"]

    def test_extract_panel_finding_as_json_string(self) -> None:
        """Panel findings stored as JSON strings are parsed correctly."""
        finding = _panel_finding("trace", "warning", 0.75)
        state = {
            "trace_finding": json.dumps(finding),
            "council_synthesis": "synthesised text",
        }
        ctx = _make_tool_context(state)
        result = _extract_council_result(ctx, None, InvestigationMode.STANDARD)

        assert len(result["panels"]) == 1
        assert result["panels"][0]["panel"] == "trace"
        assert result["panels"][0]["confidence"] == 0.75

    def test_extract_convergence_history_empty_list(self) -> None:
        """An empty convergence_history results in rounds=1 (max(0,1))."""
        state = {
            "debate_convergence_history": [],
            "council_synthesis": "text",
        }
        ctx = _make_tool_context(state)
        result = _extract_council_result(ctx, None, InvestigationMode.DEBATE)

        assert result["rounds"] == 1

    def test_extract_mode_without_value_attribute(self) -> None:
        """If investigation_mode lacks .value, str() is used."""
        ctx = _make_tool_context({})
        result = _extract_council_result(ctx, "fallback", "custom_mode")

        assert result["mode"] == "custom_mode"

    def test_extract_skips_none_panel_findings(self) -> None:
        """Panel keys with None values are omitted from the panels list."""
        state = {
            "trace_finding": _panel_finding("trace", "info", 0.5),
            "metrics_finding": None,
            "logs_finding": None,
            "alerts_finding": _panel_finding("alerts", "warning", 0.6),
            "council_synthesis": "partial",
        }
        ctx = _make_tool_context(state)
        result = _extract_council_result(ctx, None, InvestigationMode.STANDARD)

        assert len(result["panels"]) == 2
        panel_names = [p["panel"] for p in result["panels"]]
        assert "trace" in panel_names
        assert "alerts" in panel_names
