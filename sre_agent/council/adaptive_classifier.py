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

from sre_agent.auth import get_current_credentials_or_none
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
    """Check if the LLM-augmented adaptive classifier is enabled.

    Defaults to True — the adaptive classifier provides better routing than
    the rule-based fallback for novel or ambiguous queries.  Set
    ``SRE_AGENT_ADAPTIVE_CLASSIFIER=false`` (or ``0`` / ``no`` / ``off``) to
    disable and fall back to deterministic rule-based classification only.
    """
    val = os.environ.get(_ADAPTIVE_CLASSIFIER_ENV_VAR, "true").lower()
    return val not in ("false", "0", "no", "off")


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
    # Use EUC credentials from ContextVar (set by middleware / emojify_agent).
    # Falls back to Application Default Credentials when ContextVar is unset
    # (e.g. in unit tests or local runs without a signed-in user).
    creds = get_current_credentials_or_none()
    client = genai.Client(credentials=creds) if creds is not None else genai.Client()
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


def _compute_rule_based_confidence(
    query: str,
    context: ClassificationContext | None,
    mode: InvestigationMode,
) -> float:
    """Compute a signal-derived confidence score for rule-based classification.

    Factors considered:
    - **Keyword density**: more investigation-relevant terms -> higher confidence.
    - **Query length**: longer queries tend to be more complex and unambiguous.
    - **Mode consistency**: same mode used in previous turns -> higher confidence.
    - **Alert severity**: critical alert + DEBATE mode -> bonus.
    - **Budget penalty**: very low token budget + DEBATE mode -> penalty (may need
      to downgrade, so confidence in DEBATE is lower).

    Args:
        query: The raw user query string.
        context: Optional classification context.
        mode: The InvestigationMode selected by the rule-based classifier.

    Returns:
        Confidence in [0.0, 1.0], rounded to 3 decimal places.
    """
    base = 0.65

    # Keyword density: count SRE-relevant terms present in the query
    sre_keywords = {
        "investigate",
        "analyze",
        "analyse",
        "trace",
        "metric",
        "log",
        "alert",
        "error",
        "latency",
        "incident",
        "cause",
        "why",
        "debug",
        "root",
        "spike",
        "anomaly",
        "anomalies",
        "slow",
        "outage",
        "failure",
        "crash",
        "timeout",
    }
    query_lower = query.lower()
    keyword_hits = sum(1 for kw in sre_keywords if kw in query_lower)
    keyword_bonus = min(keyword_hits * 0.04, 0.20)

    # Query length: more characters -> harder query -> classifier more decisive
    length_bonus = min(len(query) / 600.0, 0.10)

    # Mode consistency across turns
    mode_history_bonus = 0.0
    if context and mode.value in context.previous_modes:
        mode_history_bonus = 0.05

    # Alert severity: critical alert strongly suggests DEBATE
    severity_bonus = 0.0
    if (
        mode == InvestigationMode.DEBATE
        and context
        and context.alert_severity
        in (
            "critical",
            "page",
            "p0",
            "p1",
            "sev0",
            "sev1",
        )
    ):
        severity_bonus = 0.10

    # Budget penalty: tight budget makes DEBATE risky -> lower confidence
    budget_penalty = 0.0
    if (
        mode == InvestigationMode.DEBATE
        and context
        and context.remaining_token_budget is not None
    ):
        if context.remaining_token_budget < 10_000:
            budget_penalty = 0.20
        elif context.remaining_token_budget < 50_000:
            budget_penalty = 0.10

    raw = (
        base
        + keyword_bonus
        + length_bonus
        + mode_history_bonus
        + severity_bonus
        - budget_penalty
    )
    return round(max(0.0, min(1.0, raw)), 3)


def _rule_based_result(
    query: str,
    context: ClassificationContext | None = None,
) -> AdaptiveClassificationResult:
    """Produce an AdaptiveClassificationResult from the rule-based classifier."""
    result = classify_intent_with_signal(query)
    confidence = _compute_rule_based_confidence(query, context, result.mode)
    return AdaptiveClassificationResult(
        mode=result.mode,
        signal_type=result.signal_type.value,
        confidence=confidence,
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
        return _rule_based_result(query, context)

    try:
        return await _classify_with_llm(query, context)
    except Exception:
        logger.warning(
            "LLM adaptive classification failed, falling back to rule-based",
            exc_info=True,
        )
        result = _rule_based_result(query, context)
        return AdaptiveClassificationResult(
            mode=result.mode,
            signal_type=result.signal_type,
            confidence=result.confidence,
            reasoning=result.reasoning + " [LLM classification failed, used fallback]",
            classifier_used="fallback",
        )
