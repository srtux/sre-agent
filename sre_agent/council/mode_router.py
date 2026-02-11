"""Mode router tool for the SRE agent.

Provides an @adk_tool that classifies user intent and routes to the
appropriate council investigation mode (Fast, Standard, or Debate).
"""

import logging
from typing import Any

from sre_agent.schema import BaseToolResponse, ToolStatus
from sre_agent.tools.common import adk_tool

from .adaptive_classifier import adaptive_classify, is_adaptive_classifier_enabled
from .intent_classifier import classify_intent
from .schemas import InvestigationMode

logger = logging.getLogger(__name__)


@adk_tool
async def classify_investigation_mode(
    query: str,
    tool_context: Any | None = None,
) -> BaseToolResponse:
    """Classify a user query into an investigation mode.

    Analyzes the query to determine the appropriate depth of investigation:
    - fast: Quick status checks, single-service queries (~5s)
    - standard: Multi-signal parallel analysis (~30s)
    - debate: Deep dive with critic cross-examination (~60s+)

    Args:
        query: The user's investigation query to classify.
        tool_context: ADK tool context.
    """
    try:
        if is_adaptive_classifier_enabled():
            adaptive_result = await adaptive_classify(query)
            logger.info(
                f"🏛️ Adaptive classified: {adaptive_result.mode.value} "
                f"(classifier={adaptive_result.classifier_used}) "
                f"for query: {query[:50]}..."
            )

            return BaseToolResponse(
                status=ToolStatus.SUCCESS,
                result={
                    "mode": adaptive_result.mode.value,
                    "description": _MODE_DESCRIPTIONS[adaptive_result.mode],
                    "query": query,
                    "confidence": adaptive_result.confidence,
                    "reasoning": adaptive_result.reasoning,
                    "signal_type": adaptive_result.signal_type,
                },
                metadata={"classifier": adaptive_result.classifier_used},
            )

        mode = classify_intent(query)
        logger.info(
            f"🏛️ Classified investigation mode: {mode.value} for query: {query[:50]}..."
        )

        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={
                "mode": mode.value,
                "description": _MODE_DESCRIPTIONS[mode],
                "query": query,
            },
            metadata={"classifier": "rule_based"},
        )
    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error=str(e),
            metadata={"classifier": "rule_based"},
        )


_MODE_DESCRIPTIONS: dict[InvestigationMode, str] = {
    InvestigationMode.FAST: (
        "Quick check — single best-fit panel, no cross-examination."
    ),
    InvestigationMode.STANDARD: (
        "Standard investigation — 4 panels in parallel, synthesized result."
    ),
    InvestigationMode.DEBATE: (
        "Deep investigation — parallel panels with critic cross-examination "
        "and iterative debate until confidence threshold is met."
    ),
}
