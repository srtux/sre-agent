"""Tests for the adaptive LLM-augmented intent classifier."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from sre_agent.council.adaptive_classifier import (
    _build_context_block,
    _parse_llm_response,
    _rule_based_result,
    _validate_mode,
    _validate_signal_type,
    adaptive_classify,
    is_adaptive_classifier_enabled,
)
from sre_agent.council.schemas import (
    AdaptiveClassificationResult,
    ClassificationContext,
    InvestigationMode,
)


class TestIsAdaptiveClassifierEnabled:
    """Tests for the feature flag check."""

    def test_enabled_by_default(self) -> None:
        """Adaptive classifier is ON when env var is absent (new default)."""
        with patch.dict("os.environ", {}, clear=True):
            assert is_adaptive_classifier_enabled() is True

    def test_enabled_when_true(self) -> None:
        with patch.dict("os.environ", {"SRE_AGENT_ADAPTIVE_CLASSIFIER": "true"}):
            assert is_adaptive_classifier_enabled() is True

    def test_enabled_case_insensitive(self) -> None:
        with patch.dict("os.environ", {"SRE_AGENT_ADAPTIVE_CLASSIFIER": "True"}):
            assert is_adaptive_classifier_enabled() is True

    def test_disabled_when_false(self) -> None:
        with patch.dict("os.environ", {"SRE_AGENT_ADAPTIVE_CLASSIFIER": "false"}):
            assert is_adaptive_classifier_enabled() is False

    def test_disabled_when_no(self) -> None:
        """'no' is an explicit opt-out value."""
        with patch.dict("os.environ", {"SRE_AGENT_ADAPTIVE_CLASSIFIER": "no"}):
            assert is_adaptive_classifier_enabled() is False

    def test_enabled_when_unrecognised_value(self) -> None:
        """Unrecognised values (e.g. 'yes') are treated as enabled."""
        with patch.dict("os.environ", {"SRE_AGENT_ADAPTIVE_CLASSIFIER": "yes"}):
            assert is_adaptive_classifier_enabled() is True


class TestBuildContextBlock:
    """Tests for context block generation."""

    def test_none_context(self) -> None:
        result = _build_context_block(None)
        assert result == "No additional context available."

    def test_empty_context(self) -> None:
        ctx = ClassificationContext()
        result = _build_context_block(ctx)
        assert result == "No additional context available."

    def test_with_session_history(self) -> None:
        ctx = ClassificationContext(session_history=["check logs", "analyze traces"])
        result = _build_context_block(ctx)
        assert "Recent queries" in result
        assert "check logs" in result

    def test_history_limited_to_last_5(self) -> None:
        ctx = ClassificationContext(session_history=[f"query {i}" for i in range(10)])
        result = _build_context_block(ctx)
        assert "query 5" in result
        assert "query 0" not in result

    def test_with_alert_severity(self) -> None:
        ctx = ClassificationContext(alert_severity="critical")
        result = _build_context_block(ctx)
        assert "Alert severity: critical" in result

    def test_with_token_budget(self) -> None:
        ctx = ClassificationContext(remaining_token_budget=50000)
        result = _build_context_block(ctx)
        assert "Remaining token budget: 50000" in result

    def test_low_token_budget_warning(self) -> None:
        ctx = ClassificationContext(remaining_token_budget=5000)
        result = _build_context_block(ctx)
        assert "WARNING" in result
        assert "Low token budget" in result

    def test_with_previous_modes(self) -> None:
        ctx = ClassificationContext(previous_modes=["fast", "standard"])
        result = _build_context_block(ctx)
        assert "Modes used previously" in result

    def test_full_context(self) -> None:
        ctx = ClassificationContext(
            session_history=["query1"],
            alert_severity="warning",
            remaining_token_budget=20000,
            previous_modes=["fast"],
        )
        result = _build_context_block(ctx)
        assert "Recent queries" in result
        assert "Alert severity" in result
        assert "token budget" in result
        assert "Modes used" in result


class TestParseLlmResponse:
    """Tests for LLM response parsing."""

    def test_valid_json(self) -> None:
        response = json.dumps(
            {
                "mode": "standard",
                "signal_type": "metrics",
                "confidence": 0.85,
                "reasoning": "multi-signal needed",
            }
        )
        result = _parse_llm_response(response)
        assert result["mode"] == "standard"
        assert result["confidence"] == 0.85

    def test_json_with_markdown_fences(self) -> None:
        response = '```json\n{"mode": "fast", "signal_type": "logs", "confidence": 0.9, "reasoning": "simple"}\n```'
        result = _parse_llm_response(response)
        assert result["mode"] == "fast"

    def test_json_with_plain_fences(self) -> None:
        response = '```\n{"mode": "debate", "signal_type": "trace", "confidence": 0.7, "reasoning": "complex"}\n```'
        result = _parse_llm_response(response)
        assert result["mode"] == "debate"

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(json.JSONDecodeError):
            _parse_llm_response("not json at all")

    def test_whitespace_handling(self) -> None:
        response = '  \n  {"mode": "fast", "signal_type": "trace", "confidence": 0.5, "reasoning": ""}  \n  '
        result = _parse_llm_response(response)
        assert result["mode"] == "fast"


class TestValidateMode:
    """Tests for mode validation."""

    def test_valid_modes(self) -> None:
        assert _validate_mode("fast") == InvestigationMode.FAST
        assert _validate_mode("standard") == InvestigationMode.STANDARD
        assert _validate_mode("debate") == InvestigationMode.DEBATE

    def test_case_insensitive(self) -> None:
        assert _validate_mode("FAST") == InvestigationMode.FAST
        assert _validate_mode("Standard") == InvestigationMode.STANDARD

    def test_invalid_mode_defaults_to_standard(self) -> None:
        assert _validate_mode("unknown") == InvestigationMode.STANDARD
        assert _validate_mode("") == InvestigationMode.STANDARD


class TestValidateSignalType:
    """Tests for signal type validation."""

    def test_valid_signal_types(self) -> None:
        assert _validate_signal_type("trace") == "trace"
        assert _validate_signal_type("metrics") == "metrics"
        assert _validate_signal_type("logs") == "logs"
        assert _validate_signal_type("alerts") == "alerts"

    def test_case_insensitive(self) -> None:
        assert _validate_signal_type("TRACE") == "trace"
        assert _validate_signal_type("Metrics") == "metrics"

    def test_invalid_defaults_to_trace(self) -> None:
        assert _validate_signal_type("unknown") == "trace"
        assert _validate_signal_type("") == "trace"


class TestRuleBasedResult:
    """Tests for rule-based fallback classification."""

    def test_returns_adaptive_result(self) -> None:
        result = _rule_based_result("check the status")
        assert isinstance(result, AdaptiveClassificationResult)
        assert result.classifier_used == "rule_based"

    def test_fast_mode_detection(self) -> None:
        result = _rule_based_result("quick health check")
        assert result.mode == InvestigationMode.FAST

    def test_debate_mode_detection(self) -> None:
        result = _rule_based_result("root cause of the outage")
        assert result.mode == InvestigationMode.DEBATE
        # Confidence is now computed from signal strength, not hardcoded
        assert 0.0 < result.confidence <= 1.0

    def test_standard_mode_detection(self) -> None:
        result = _rule_based_result("analyze the error rates")
        assert result.mode == InvestigationMode.STANDARD
        # Confidence is now computed from signal strength, not hardcoded
        assert 0.0 < result.confidence <= 1.0

    def test_reasoning_included(self) -> None:
        result = _rule_based_result("quick check")
        assert "Rule-based" in result.reasoning


class TestAdaptiveClassify:
    """Tests for the main adaptive_classify function."""

    @pytest.mark.asyncio
    async def test_uses_rule_based_when_disabled(self) -> None:
        # Explicitly disable the adaptive classifier via env var
        with patch.dict("os.environ", {"SRE_AGENT_ADAPTIVE_CLASSIFIER": "false"}):
            result = await adaptive_classify("check the status")
            assert result.classifier_used == "rule_based"
            assert isinstance(result, AdaptiveClassificationResult)

    @pytest.mark.asyncio
    async def test_uses_llm_when_enabled(self) -> None:
        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {
                "mode": "standard",
                "signal_type": "metrics",
                "confidence": 0.9,
                "reasoning": "multi-signal analysis needed",
            }
        )

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with (
            patch.dict("os.environ", {"SRE_AGENT_ADAPTIVE_CLASSIFIER": "true"}),
            patch(
                "sre_agent.council.adaptive_classifier.genai.Client",
                return_value=mock_client,
            ),
        ):
            result = await adaptive_classify("check cpu and memory usage")
            assert result.classifier_used == "llm_augmented"
            assert result.mode == InvestigationMode.STANDARD
            assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_falls_back_on_llm_failure(self) -> None:
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=RuntimeError("LLM unavailable")
        )

        with (
            patch.dict("os.environ", {"SRE_AGENT_ADAPTIVE_CLASSIFIER": "true"}),
            patch(
                "sre_agent.council.adaptive_classifier.genai.Client",
                return_value=mock_client,
            ),
        ):
            result = await adaptive_classify("root cause of the incident")
            assert result.classifier_used == "fallback"
            assert "fallback" in result.reasoning

    @pytest.mark.asyncio
    async def test_falls_back_on_empty_llm_response(self) -> None:
        mock_response = MagicMock()
        mock_response.text = ""

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with (
            patch.dict("os.environ", {"SRE_AGENT_ADAPTIVE_CLASSIFIER": "true"}),
            patch(
                "sre_agent.council.adaptive_classifier.genai.Client",
                return_value=mock_client,
            ),
        ):
            result = await adaptive_classify("analyze the system")
            assert result.classifier_used == "fallback"

    @pytest.mark.asyncio
    async def test_falls_back_on_invalid_json(self) -> None:
        mock_response = MagicMock()
        mock_response.text = "I think you should use standard mode"

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with (
            patch.dict("os.environ", {"SRE_AGENT_ADAPTIVE_CLASSIFIER": "true"}),
            patch(
                "sre_agent.council.adaptive_classifier.genai.Client",
                return_value=mock_client,
            ),
        ):
            result = await adaptive_classify("what is happening")
            assert result.classifier_used == "fallback"

    @pytest.mark.asyncio
    async def test_context_passed_to_llm(self) -> None:
        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {
                "mode": "debate",
                "signal_type": "trace",
                "confidence": 0.95,
                "reasoning": "critical alert severity warrants deep investigation",
            }
        )

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        context = ClassificationContext(
            session_history=["check logs", "analyze metrics"],
            alert_severity="critical",
            remaining_token_budget=50000,
            previous_modes=["fast", "standard"],
        )

        with (
            patch.dict("os.environ", {"SRE_AGENT_ADAPTIVE_CLASSIFIER": "true"}),
            patch(
                "sre_agent.council.adaptive_classifier.genai.Client",
                return_value=mock_client,
            ),
        ):
            result = await adaptive_classify(
                "investigate the payment failure", context=context
            )
            assert result.mode == InvestigationMode.DEBATE
            assert result.confidence == 0.95

            # Verify LLM was called with context
            assert mock_client.aio.models.generate_content.called

    @pytest.mark.asyncio
    async def test_low_budget_downgrades_debate(self) -> None:
        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {
                "mode": "debate",
                "signal_type": "trace",
                "confidence": 0.8,
                "reasoning": "complex issue",
            }
        )

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        context = ClassificationContext(remaining_token_budget=5000)

        with (
            patch.dict("os.environ", {"SRE_AGENT_ADAPTIVE_CLASSIFIER": "true"}),
            patch(
                "sre_agent.council.adaptive_classifier.genai.Client",
                return_value=mock_client,
            ),
        ):
            result = await adaptive_classify("root cause analysis", context=context)
            assert result.mode == InvestigationMode.STANDARD
            assert "low token budget" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_confidence_clamped(self) -> None:
        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {
                "mode": "fast",
                "signal_type": "trace",
                "confidence": 1.5,
                "reasoning": "obvious",
            }
        )

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with (
            patch.dict("os.environ", {"SRE_AGENT_ADAPTIVE_CLASSIFIER": "true"}),
            patch(
                "sre_agent.council.adaptive_classifier.genai.Client",
                return_value=mock_client,
            ),
        ):
            result = await adaptive_classify("check status")
            assert result.confidence <= 1.0


class TestSchemaModels:
    """Tests for the new schema models."""

    def test_classification_context_frozen(self) -> None:
        ctx = ClassificationContext(alert_severity="critical")
        with pytest.raises(ValidationError):
            ctx.alert_severity = "warning"  # type: ignore[misc]

    def test_classification_context_extra_forbid(self) -> None:
        with pytest.raises(ValidationError):
            ClassificationContext(unknown_field="value")  # type: ignore[call-arg]

    def test_classification_context_defaults(self) -> None:
        ctx = ClassificationContext()
        assert ctx.session_history == []
        assert ctx.alert_severity is None
        assert ctx.remaining_token_budget is None
        assert ctx.previous_modes == []

    def test_adaptive_result_frozen(self) -> None:
        result = AdaptiveClassificationResult(mode=InvestigationMode.FAST)
        with pytest.raises(ValidationError):
            result.mode = InvestigationMode.DEBATE  # type: ignore[misc]

    def test_adaptive_result_extra_forbid(self) -> None:
        with pytest.raises(ValidationError):
            AdaptiveClassificationResult(
                mode=InvestigationMode.FAST,
                unknown="value",  # type: ignore[call-arg]
            )

    def test_adaptive_result_defaults(self) -> None:
        result = AdaptiveClassificationResult(mode=InvestigationMode.STANDARD)
        assert result.signal_type == "trace"
        assert result.confidence == 0.0
        assert result.reasoning == ""
        assert result.classifier_used == "rule_based"

    def test_adaptive_result_confidence_bounds(self) -> None:
        with pytest.raises(ValidationError):
            AdaptiveClassificationResult(mode=InvestigationMode.FAST, confidence=-0.1)
        with pytest.raises(ValidationError):
            AdaptiveClassificationResult(mode=InvestigationMode.FAST, confidence=1.1)


class TestComputeRuleBasedConfidence:
    """Tests for the signal-derived confidence scorer."""

    def test_imports(self) -> None:
        from sre_agent.council.adaptive_classifier import (
            _compute_rule_based_confidence,  # noqa: F401
        )

    def test_complex_query_higher_confidence_than_simple(self) -> None:
        from sre_agent.council.adaptive_classifier import _compute_rule_based_confidence

        ctx = ClassificationContext()
        simple = _compute_rule_based_confidence(
            "show logs", ctx, InvestigationMode.STANDARD
        )
        complex_ = _compute_rule_based_confidence(
            "investigate the latency anomaly and analyze trace errors for incident",
            ctx,
            InvestigationMode.STANDARD,
        )
        assert complex_ > simple

    def test_debate_penalized_on_low_budget(self) -> None:
        from sre_agent.council.adaptive_classifier import _compute_rule_based_confidence

        ctx_low = ClassificationContext(remaining_token_budget=5_000)
        ctx_high = ClassificationContext(remaining_token_budget=500_000)
        low = _compute_rule_based_confidence(
            "investigate", ctx_low, InvestigationMode.DEBATE
        )
        high = _compute_rule_based_confidence(
            "investigate", ctx_high, InvestigationMode.DEBATE
        )
        assert low < high

    def test_critical_alert_boosts_debate_confidence(self) -> None:
        from sre_agent.council.adaptive_classifier import _compute_rule_based_confidence

        ctx_no_alert = ClassificationContext()
        ctx_critical = ClassificationContext(alert_severity="critical")
        no_alert = _compute_rule_based_confidence(
            "investigate", ctx_no_alert, InvestigationMode.DEBATE
        )
        critical = _compute_rule_based_confidence(
            "investigate", ctx_critical, InvestigationMode.DEBATE
        )
        assert critical > no_alert

    def test_confidence_clipped_to_unit_interval(self) -> None:
        from sre_agent.council.adaptive_classifier import _compute_rule_based_confidence

        ctx = ClassificationContext()
        for mode in InvestigationMode:
            conf = _compute_rule_based_confidence("x" * 1000, ctx, mode)
            assert 0.0 <= conf <= 1.0

    def test_rule_based_result_uses_computed_confidence(self) -> None:
        """_rule_based_result must not return the old hardcoded 0.8/0.6 values."""
        ctx = ClassificationContext(remaining_token_budget=5_000)
        result = _rule_based_result("investigate incident", ctx)
        # With a low budget penalty applied, DEBATE confidence must be < 0.8
        assert result.confidence != 0.8
        assert result.confidence != 0.6


class TestRuleBasedResultAcceptsContext:
    """Tests that _rule_based_result passes context to confidence calculation."""

    def test_accepts_none_context(self) -> None:
        result = _rule_based_result("analyze logs", None)
        assert isinstance(result, AdaptiveClassificationResult)
        assert 0.0 <= result.confidence <= 1.0

    def test_accepts_rich_context(self) -> None:
        ctx = ClassificationContext(
            session_history=["previous query"],
            alert_severity="warning",
            remaining_token_budget=100_000,
            previous_modes=["standard"],
        )
        result = _rule_based_result("investigate the service", ctx)
        assert isinstance(result, AdaptiveClassificationResult)
