"""Integration tests for adaptive classifier wired into orchestrator and mode_router."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sre_agent.council.intent_classifier import SignalType
from sre_agent.council.mode_router import classify_investigation_mode
from sre_agent.council.orchestrator import (
    CouncilOrchestrator,
    _str_to_signal_type,
    create_council_orchestrator,
)
from sre_agent.council.schemas import (
    ClassificationContext,
    CouncilConfig,
    InvestigationMode,
)


class TestStrToSignalType:
    """Tests for the signal type string-to-enum helper."""

    def test_valid_types(self) -> None:
        assert _str_to_signal_type("trace") == SignalType.TRACE
        assert _str_to_signal_type("metrics") == SignalType.METRICS
        assert _str_to_signal_type("logs") == SignalType.LOGS
        assert _str_to_signal_type("alerts") == SignalType.ALERTS

    def test_case_insensitive(self) -> None:
        assert _str_to_signal_type("TRACE") == SignalType.TRACE
        assert _str_to_signal_type("Metrics") == SignalType.METRICS

    def test_unknown_defaults_to_trace(self) -> None:
        assert _str_to_signal_type("unknown") == SignalType.TRACE
        assert _str_to_signal_type("") == SignalType.TRACE


class TestBuildClassificationContext:
    """Tests for context extraction from session state."""

    def test_empty_session_state(self) -> None:
        orchestrator = create_council_orchestrator()
        ctx = MagicMock()
        ctx.session.state = {}

        result = orchestrator._build_classification_context(ctx)
        assert isinstance(result, ClassificationContext)
        assert result.session_history == []
        assert result.alert_severity is None
        assert result.remaining_token_budget is None
        assert result.previous_modes == []

    def test_with_full_session_state(self) -> None:
        orchestrator = create_council_orchestrator()
        ctx = MagicMock()
        ctx.session.state = {
            "investigation_queries": ["q1", "q2", "q3"],
            "current_alert_severity": "critical",
            "remaining_token_budget": 25000,
            "previous_investigation_modes": ["fast", "standard"],
        }

        result = orchestrator._build_classification_context(ctx)
        assert result.session_history == ["q1", "q2", "q3"]
        assert result.alert_severity == "critical"
        assert result.remaining_token_budget == 25000
        assert result.previous_modes == ["fast", "standard"]

    def test_history_limited_to_5(self) -> None:
        orchestrator = create_council_orchestrator()
        ctx = MagicMock()
        ctx.session.state = {
            "investigation_queries": [f"q{i}" for i in range(10)],
        }

        result = orchestrator._build_classification_context(ctx)
        assert len(result.session_history) == 5
        assert result.session_history[0] == "q5"

    def test_no_session(self) -> None:
        orchestrator = create_council_orchestrator()
        ctx = MagicMock()
        ctx.session = None

        result = orchestrator._build_classification_context(ctx)
        assert result.session_history == []


class TestModeRouterAdaptiveIntegration:
    """Tests for mode_router using adaptive classifier."""

    @pytest.mark.asyncio
    async def test_rule_based_when_disabled(self) -> None:
        # Explicitly disable the adaptive classifier to test rule-based path
        with patch.dict("os.environ", {"SRE_AGENT_ADAPTIVE_CLASSIFIER": "false"}):
            result = await classify_investigation_mode(
                query="check the status of my service"
            )
            # Should work and return a BaseToolResponse
            assert result.status.value == "success"
            assert result.metadata is not None
            assert result.metadata.get("classifier") == "rule_based"

    @pytest.mark.asyncio
    async def test_adaptive_when_enabled(self) -> None:
        mock_response = MagicMock()
        mock_response.text = '{"mode": "standard", "signal_type": "metrics", "confidence": 0.85, "reasoning": "multi-signal"}'

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with (
            patch.dict("os.environ", {"SRE_AGENT_ADAPTIVE_CLASSIFIER": "true"}),
            patch(
                "sre_agent.council.adaptive_classifier.genai.Client",
                return_value=mock_client,
            ),
        ):
            result = await classify_investigation_mode(query="analyze cpu and memory")
            assert result.status.value == "success"
            assert result.result is not None
            assert result.result["mode"] == "standard"
            assert result.result["confidence"] == 0.85
            assert result.result["reasoning"] == "multi-signal"
            assert result.metadata is not None
            assert result.metadata["classifier"] == "llm_augmented"

    @pytest.mark.asyncio
    async def test_adaptive_fallback_on_error(self) -> None:
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=RuntimeError("LLM down")
        )

        with (
            patch.dict("os.environ", {"SRE_AGENT_ADAPTIVE_CLASSIFIER": "true"}),
            patch(
                "sre_agent.council.adaptive_classifier.genai.Client",
                return_value=mock_client,
            ),
        ):
            result = await classify_investigation_mode(query="root cause of the outage")
            assert result.status.value == "success"
            assert result.metadata is not None
            assert result.metadata["classifier"] == "fallback"


class TestOrchestratorAdaptiveFactory:
    """Tests for orchestrator factory with adaptive configuration."""

    def test_create_default_orchestrator(self) -> None:
        orch = create_council_orchestrator()
        assert isinstance(orch, CouncilOrchestrator)
        assert orch.council_config.mode == InvestigationMode.STANDARD

    def test_create_with_config(self) -> None:
        config = CouncilConfig(
            mode=InvestigationMode.DEBATE,
            max_debate_rounds=5,
            confidence_threshold=0.9,
        )
        orch = create_council_orchestrator(config=config)
        assert orch.council_config.max_debate_rounds == 5
        assert orch.council_config.confidence_threshold == 0.9
