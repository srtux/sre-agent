"""Custom BaseAgent orchestrator for council-based investigation.

The CouncilOrchestrator replaces the root LlmAgent when the
SRE_AGENT_COUNCIL_ORCHESTRATOR feature flag is enabled. It:

1. Classifies user intent into an investigation mode
2. Routes to the appropriate pipeline (fast/standard/debate)
3. Streams events from sub-agents back to the caller
"""

import logging
from collections.abc import AsyncGenerator
from typing import Any

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types as genai_types

from .adaptive_classifier import adaptive_classify, is_adaptive_classifier_enabled
from .debate import create_debate_pipeline
from .intent_classifier import SignalType, classify_intent_with_signal
from .panels import (
    create_alerts_panel,
    create_logs_panel,
    create_metrics_panel,
    create_trace_panel,
)
from .parallel_council import create_council_pipeline
from .schemas import (
    ClassificationContext,
    CouncilConfig,
    InvestigationMode,
)

logger = logging.getLogger(__name__)


class CouncilOrchestrator(BaseAgent):
    """Custom orchestrator that routes investigations to council pipelines.

    Replaces the root LlmAgent when SRE_AGENT_COUNCIL_ORCHESTRATOR=true.
    Classifies user intent and delegates to the appropriate pipeline:
    - FAST: Single best-fit panel
    - STANDARD: Parallel council (5 panels + synthesizer)
    - DEBATE: Parallel council + critic loop with confidence gating
    """

    council_config: CouncilConfig = CouncilConfig()

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Core orchestration logic.

        Args:
            ctx: InvocationContext with session, user content, etc.

        Yields:
            Events from the selected pipeline sub-agents.
        """
        # Extract user query from the invocation context
        query = self._extract_query(ctx)
        if not query:
            yield self._make_text_event(
                ctx, "No query provided. Please describe the issue to investigate."
            )
            return

        # Classify intent — adaptive (LLM) or rule-based
        if is_adaptive_classifier_enabled():
            context = self._build_classification_context(ctx)
            adaptive_result = await adaptive_classify(query, context)
            mode = adaptive_result.mode
            signal_type_str = adaptive_result.signal_type
            # Map string back to SignalType enum for panel routing
            signal_type = _str_to_signal_type(signal_type_str)
            logger.info(
                f"🏛️ Adaptive classifier: mode={mode.value}, "
                f"signal={signal_type.value}, confidence={adaptive_result.confidence:.2f}, "
                f"classifier={adaptive_result.classifier_used}, query={query[:80]}..."
            )
        else:
            classification = classify_intent_with_signal(query)
            mode = classification.mode
            signal_type = classification.signal_type
            logger.info(
                f"🏛️ Council orchestrator: mode={mode.value}, "
                f"signal={signal_type.value}, query={query[:80]}..."
            )

        # Emit a status event
        yield self._make_text_event(
            ctx,
            f"Starting {mode.value} investigation...",
        )

        # Build the appropriate pipeline
        config = CouncilConfig(
            mode=mode,
            max_debate_rounds=self.council_config.max_debate_rounds,
            confidence_threshold=self.council_config.confidence_threshold,
            timeout_seconds=self.council_config.timeout_seconds,
        )

        if mode == InvestigationMode.FAST:
            pipeline = self._create_fast_pipeline(signal_type)
        elif mode == InvestigationMode.DEBATE:
            pipeline = create_debate_pipeline(config)
        else:
            pipeline = create_council_pipeline(config)

        # Register sub-agent for context propagation
        pipeline.parent_agent = self

        # Create a child context for the pipeline
        child_ctx = InvocationContext(
            invocation_id=ctx.invocation_id,
            agent=pipeline,
            session=ctx.session,
            session_service=ctx.session_service,
            artifact_service=ctx.artifact_service,
            memory_service=ctx.memory_service,
            credential_service=ctx.credential_service,
            user_content=ctx.user_content,
            run_config=ctx.run_config,
        )

        # Stream events from the pipeline with deadline enforcement (OPT-4)
        # Compatible with Python 3.10+ (asyncio.timeout requires 3.11+).
        import time

        deadline = time.monotonic() + config.timeout_seconds
        timed_out = False
        async for event in pipeline.run_async(child_ctx):
            yield event
            if time.monotonic() > deadline:
                timed_out = True
                break
        if timed_out:
            logger.warning(
                f"Council pipeline timed out after {config.timeout_seconds}s "
                f"(mode={mode.value})"
            )
            yield self._make_text_event(
                ctx,
                f"Investigation timed out after {config.timeout_seconds}s. "
                "Returning partial results collected so far.",
            )

    def _extract_query(self, ctx: InvocationContext) -> str:
        """Extract the user query text from the invocation context."""
        if ctx.user_content and ctx.user_content.parts:
            texts = [
                part.text
                for part in ctx.user_content.parts
                if hasattr(part, "text") and part.text
            ]
            return " ".join(texts)
        return ""

    def _make_text_event(self, ctx: InvocationContext, text: str) -> Event:
        """Create a simple text Event."""
        return Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            content=genai_types.Content(
                role="model",
                parts=[genai_types.Part(text=text)],
            ),
        )

    def _create_fast_pipeline(
        self, signal_type: SignalType = SignalType.TRACE
    ) -> BaseAgent:
        """Create a single-panel pipeline for fast mode.

        Routes to the best-fit panel based on the detected signal type
        from the user's query. Falls back to the trace panel if no
        specific signal type is detected.

        Args:
            signal_type: The detected signal type from intent classification.

        Returns:
            A single specialist panel agent.
        """
        panel_factories = {
            SignalType.TRACE: create_trace_panel,
            SignalType.METRICS: create_metrics_panel,
            SignalType.LOGS: create_logs_panel,
            SignalType.ALERTS: create_alerts_panel,
        }
        factory = panel_factories.get(signal_type, create_trace_panel)
        logger.info(f"🏛️ Fast mode: routing to {signal_type.value} panel")
        return factory()

    def _build_classification_context(
        self, ctx: InvocationContext
    ) -> ClassificationContext:
        """Build classification context from session state.

        Extracts investigation history, alert severity, and token budget
        from the session state for adaptive classification.
        """
        state = ctx.session.state if ctx.session else {}

        # Extract recent queries from session
        session_history: list[str] = list(state.get("investigation_queries", []))[-5:]

        # Extract alert severity if available
        alert_severity: str | None = state.get("current_alert_severity")

        # Extract remaining token budget
        remaining_budget: int | None = state.get("remaining_token_budget")

        # Extract previous investigation modes
        previous_modes: list[str] = list(state.get("previous_investigation_modes", []))

        return ClassificationContext(
            session_history=session_history,
            alert_severity=alert_severity,
            remaining_token_budget=remaining_budget,
            previous_modes=previous_modes,
        )


def _str_to_signal_type(signal_str: str) -> SignalType:
    """Convert a signal type string to the SignalType enum."""
    mapping = {
        "trace": SignalType.TRACE,
        "metrics": SignalType.METRICS,
        "logs": SignalType.LOGS,
        "alerts": SignalType.ALERTS,
    }
    return mapping.get(signal_str.lower(), SignalType.TRACE)


def create_council_orchestrator(
    config: CouncilConfig | None = None,
    sub_agents: list[Any] | None = None,
) -> CouncilOrchestrator:
    """Factory function for creating a CouncilOrchestrator.

    Args:
        config: Council configuration. Uses defaults if not provided.
        sub_agents: Additional sub-agents to include (e.g., existing specialists).

    Returns:
        Configured CouncilOrchestrator.
    """
    if config is None:
        config = CouncilConfig()

    return CouncilOrchestrator(
        name="sre_agent",
        description=(
            "SRE Agent with Council-based investigation. Routes queries to "
            "parallel specialist panels with optional debate-based consensus."
        ),
        council_config=config,
        sub_agents=sub_agents or [],
    )
