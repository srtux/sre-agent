"""Adaptive intent classifier with LLM augmentation.

Augments the rule-based IntentClassifier with an LLM-based classifier
that considers investigation history, alert severity, and token budget.
Falls back to rule-based classification on any LLM failure.

Feature flag: SRE_AGENT_ADAPTIVE_CLASSIFIER=true to enable LLM augmentation.
"""

import json
import logging
import os

from google import genai

from sre_agent.model_config import get_model_name

from .intent_classifier import (
    classify_intent_with_signal,
)
from .schemas import (
    AdaptiveClassificationResult,
    ClassificationContext,
    InvestigationMode,
)

logger = logging.getLogger(__name__)

# Environment variable to enable LLM-augmented classification
_ADAPTIVE_CLASSIFIER_ENV_VAR = "SRE_AGENT_ADAPTIVE_CLASSIFIER"

# LLM classification prompt template
_CLASSIFICATION_PROMPT = """You are an SRE investigation router. Given a user query and optional context, classify the investigation mode.

## Modes
- **fast**: Quick status checks, single-service lookups, simple data retrieval. Use when the query is narrow and requires only one signal type (traces, metrics, logs, or alerts).
- **standard**: Multi-signal parallel investigation. Use for general diagnostic queries that benefit from examining multiple telemetry signals simultaneously.
- **debate**: Deep investigation with adversarial review. Use for production incidents, root cause analysis, high-severity alerts, or when conflicting signals are expected.

## Signal Types (for fast mode)
- **trace**: Distributed tracing, latency, spans, request flow
- **metrics**: Time-series data, CPU, memory, SLOs, error rates
- **logs**: Log entries, exceptions, patterns, stack traces
- **alerts**: Alert policies, firing alerts, notifications

## Context
{context_block}

## Query
{query}

## Response Format
Respond with ONLY a JSON object (no markdown, no explanation):
{{"mode": "fast|standard|debate", "signal_type": "trace|metrics|logs|alerts", "confidence": 0.0-1.0, "reasoning": "brief explanation"}}
"""


def is_adaptive_classifier_enabled() -> bool:
    """Check if the LLM-augmented adaptive classifier is enabled."""
    return os.environ.get(_ADAPTIVE_CLASSIFIER_ENV_VAR, "false").lower() == "true"


def _build_context_block(context: ClassificationContext | None) -> str:
    """Build the context section of the classification prompt."""
    if context is None:
        return "No additional context available."

    parts: list[str] = []

    if context.session_history:
        recent = context.session_history[-5:]  # Last 5 queries
        parts.append(f"Recent queries in this session: {recent}")

    if context.alert_severity:
        parts.append(f"Alert severity: {context.alert_severity}")

    if context.remaining_token_budget is not None:
        parts.append(f"Remaining token budget: {context.remaining_token_budget}")
        if context.remaining_token_budget < 10000:
            parts.append(
                "WARNING: Low token budget — prefer fast or standard over debate."
            )

    if context.previous_modes:
        parts.append(f"Modes used previously: {context.previous_modes}")

    return "\n".join(parts) if parts else "No additional context available."


def _parse_llm_response(response_text: str) -> dict[str, str | float]:
    """Parse the LLM JSON response, handling common formatting issues."""
    text = response_text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (fences)
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()

    return json.loads(text)  # type: ignore[no-any-return]


def _validate_mode(mode_str: str) -> InvestigationMode:
    """Validate and convert a mode string to InvestigationMode enum."""
    mode_map = {
        "fast": InvestigationMode.FAST,
        "standard": InvestigationMode.STANDARD,
        "debate": InvestigationMode.DEBATE,
    }
    return mode_map.get(mode_str.lower(), InvestigationMode.STANDARD)


def _validate_signal_type(signal_str: str) -> str:
    """Validate a signal type string."""
    valid_signals = {"trace", "metrics", "logs", "alerts"}
    return signal_str.lower() if signal_str.lower() in valid_signals else "trace"


async def _classify_with_llm(
    query: str, context: ClassificationContext | None = None
) -> AdaptiveClassificationResult:
    """Classify using LLM augmentation.

    Makes a single LLM call with the classification prompt and context.
    Raises on any failure so the caller can fall back to rule-based.

    Args:
        query: The user's investigation query.
        context: Optional classification context.

    Returns:
        AdaptiveClassificationResult from LLM classification.

    Raises:
        Exception: On any LLM call or parsing failure.
    """
    context_block = _build_context_block(context)
    prompt = _CLASSIFICATION_PROMPT.format(
        context_block=context_block,
        query=query,
    )

    model_name = get_model_name("fast")
    client = genai.Client()
    response = await client.aio.models.generate_content(
        model=model_name,
        contents=prompt,
    )

    if not response.text:
        msg = "LLM returned empty response for classification"
        raise ValueError(msg)

    parsed = _parse_llm_response(response.text)
    mode = _validate_mode(str(parsed.get("mode", "standard")))
    signal_type = _validate_signal_type(str(parsed.get("signal_type", "trace")))
    confidence = float(parsed.get("confidence", 0.5))
    reasoning = str(parsed.get("reasoning", ""))

    # Clamp confidence
    confidence = max(0.0, min(1.0, confidence))

    # Apply budget-aware override: if budget is low, downgrade debate to standard
    if (
        context
        and context.remaining_token_budget is not None
        and context.remaining_token_budget < 10000
        and mode == InvestigationMode.DEBATE
    ):
        logger.info(
            "Downgrading from DEBATE to STANDARD due to low token budget "
            f"({context.remaining_token_budget} remaining)"
        )
        mode = InvestigationMode.STANDARD
        reasoning += " [Downgraded from debate due to low token budget]"

    return AdaptiveClassificationResult(
        mode=mode,
        signal_type=signal_type,
        confidence=confidence,
        reasoning=reasoning,
        classifier_used="llm_augmented",
    )


def _rule_based_result(query: str) -> AdaptiveClassificationResult:
    """Produce an AdaptiveClassificationResult from the rule-based classifier."""
    result = classify_intent_with_signal(query)
    return AdaptiveClassificationResult(
        mode=result.mode,
        signal_type=result.signal_type.value,
        confidence=0.8 if result.mode == InvestigationMode.DEBATE else 0.6,
        reasoning=f"Rule-based classification: matched {result.mode.value} keywords",
        classifier_used="rule_based",
    )


async def adaptive_classify(
    query: str,
    context: ClassificationContext | None = None,
) -> AdaptiveClassificationResult:
    """Classify a user query with adaptive LLM augmentation.

    When SRE_AGENT_ADAPTIVE_CLASSIFIER=true, attempts LLM-based classification
    first. On any failure, falls back to the deterministic rule-based classifier.

    When the feature flag is disabled, always uses rule-based classification.

    Args:
        query: The user's investigation query.
        context: Optional context (history, severity, budget).

    Returns:
        AdaptiveClassificationResult with mode, signal type, and reasoning.
    """
    if not is_adaptive_classifier_enabled():
        return _rule_based_result(query)

    try:
        return await _classify_with_llm(query, context)
    except Exception:
        logger.warning(
            "LLM adaptive classification failed, falling back to rule-based",
            exc_info=True,
        )
        result = _rule_based_result(query)
        return AdaptiveClassificationResult(
            mode=result.mode,
            signal_type=result.signal_type,
            confidence=result.confidence,
            reasoning=result.reasoning + " [LLM classification failed, used fallback]",
            classifier_used="fallback",
        )
