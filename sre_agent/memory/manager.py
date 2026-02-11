"""Memory Manager for SRE Agent.

This module provides the central interface for storing and retrieving investigation context
using Vertex AI Memory Bank (or fallback persistence).

Includes a learning pattern system that tracks successful investigation strategies
and tool sequences to improve future investigations.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from google.adk.memory import VertexAiMemoryBankService

from sre_agent.schema import Confidence, InvestigationPhase, MemoryItem

logger = logging.getLogger(__name__)


class InvestigationPattern:
    """A reusable pattern learned from a successful investigation.

    Captures the symptom type, tool sequence that led to resolution,
    and the root cause category for future matching.
    """

    def __init__(
        self,
        symptom_type: str,
        root_cause_category: str,
        tool_sequence: list[str],
        resolution_summary: str,
        confidence: float = 0.5,
        occurrence_count: int = 1,
    ):
        """Initialize an investigation pattern.

        Args:
            symptom_type: Category of the initial symptom.
            root_cause_category: Category of the root cause found.
            tool_sequence: Ordered list of tools used in the investigation.
            resolution_summary: Brief description of the resolution.
            confidence: Confidence score from 0.0 to 1.0.
            occurrence_count: Number of times this pattern has been observed.
        """
        self.symptom_type = symptom_type
        self.root_cause_category = root_cause_category
        self.tool_sequence = tool_sequence
        self.resolution_summary = resolution_summary
        self.confidence = confidence
        self.occurrence_count = occurrence_count

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for storage."""
        return {
            "symptom_type": self.symptom_type,
            "root_cause_category": self.root_cause_category,
            "tool_sequence": self.tool_sequence,
            "resolution_summary": self.resolution_summary,
            "confidence": self.confidence,
            "occurrence_count": self.occurrence_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InvestigationPattern":
        """Deserialize from dictionary."""
        return cls(
            symptom_type=data.get("symptom_type", "unknown"),
            root_cause_category=data.get("root_cause_category", "unknown"),
            tool_sequence=data.get("tool_sequence", []),
            resolution_summary=data.get("resolution_summary", ""),
            confidence=data.get("confidence", 0.5),
            occurrence_count=data.get("occurrence_count", 1),
        )


class MemoryManager:
    """Manages investigation state, findings, and learned patterns.

    Uses Vertex AI Memory Bank for persistence with SQLite fallback.
    Includes a learning system that captures successful investigation
    patterns for future reuse.
    """

    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        agent_engine_id: str | None = None,
    ):
        """Initialize the Memory Manager.

        Args:
            project_id: GCP Project ID.
            location: GCP Location (default: us-central1).
            agent_engine_id: Agent Engine ID (required for Vertex AI Memory Bank).
        """
        self.project_id = project_id
        self.location = location
        self.agent_engine_id = agent_engine_id
        self.memory_service: Any | None = None
        self._check_init_memory_service()

        # Local state cache (for current execution)
        self._current_state = InvestigationPhase.INITIATED
        self._findings_cache: list[MemoryItem] = []

        # Learning pattern cache: tracks tool calls in current session
        self._current_tool_sequence: list[str] = []
        self._learned_patterns: list[InvestigationPattern] = []

    def _check_init_memory_service(self) -> None:
        """Initialize the Vertex AI Memory Service if credentials allow."""
        try:
            # Vertex AI Memory Bank requires SRE_AGENT_ID to be set (effectively running in Agent Engine)
            # If not set, we skip and fallback to local memory immediately to avoid "Agent Engine ID missing" errors.
            import os

            agent_engine_id = self.agent_engine_id or os.environ.get("SRE_AGENT_ID")
            if not agent_engine_id:
                raise ValueError(
                    "SRE_AGENT_ID not set. Skipping Vertex AI Memory Bank setup in local mode."
                )

            self.memory_service = VertexAiMemoryBankService(
                project=self.project_id,
                location=self.location,
                agent_engine_id=agent_engine_id,
            )
            logger.info(
                f"✅ Memory Manager initialized for project {self.project_id} "
                f"(agent_engine_id={agent_engine_id})"
            )
        except Exception as e:
            logger.warning(
                f"⚠️ Failed to initialize Vertex AI Memory Service: {e}. "
                "Falling back to Local SQLite Memory."
            )
            try:
                from sre_agent.memory.local import LocalMemoryService

                self.memory_service = LocalMemoryService()
                logger.info("✅ Local Memory Service initialized")
            except Exception as local_e:
                logger.error(
                    f"❌ Failed to initialize Local Memory fallback: {local_e}"
                )
                self.memory_service = None

    async def add_finding(
        self,
        description: str,
        source_tool: str,
        confidence: Confidence = Confidence.MEDIUM,
        structured_data: dict[str, Any] | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> None:
        """Add a finding to memory.

        Args:
            description: Human-readable description.
            source_tool: Tool that produced the finding.
            confidence: Confidence level.
            structured_data: Optional raw data.
            session_id: Current session ID (required for persistence).
            user_id: The authenticated user ID (email) for isolation.
        """
        item = MemoryItem(
            source_tool=source_tool,
            confidence=confidence,
            timestamp=datetime.now(timezone.utc).isoformat(),
            description=description,
            structured_data=structured_data,
        )
        self._findings_cache.append(item)

        if self.memory_service and session_id:
            try:
                # Store as unstructured text for semantic search
                if hasattr(self.memory_service, "save_memory"):
                    # Using local memory or compatible service
                    await self.memory_service.save_memory(
                        session_id=session_id,
                        memory_content=f"[{source_tool}] {description}",
                        metadata={
                            "confidence": confidence.value,
                            "timestamp": item.timestamp,
                            "tool": source_tool,
                            "type": "finding",
                            "user_id": user_id or "anonymous",
                        },
                    )
                elif hasattr(self.memory_service, "add_session_to_memory"):
                    # explicitly add finding if VertexAiMemoryBankService provides client/engine id
                    if hasattr(self.memory_service, "_get_api_client") and getattr(
                        self.memory_service, "_agent_engine_id", None
                    ):
                        from sre_agent.services.session import ADKSessionManager

                        client = self.memory_service._get_api_client()
                        app_name = ADKSessionManager.APP_NAME
                        safe_user_id = user_id or "anonymous"

                        client.agent_engines.memories.create(
                            name=f"reasoningEngines/{self.memory_service._agent_engine_id}",
                            fact=f"[{source_tool}] {description}",
                            scope={"app_name": app_name, "user_id": safe_user_id},
                        )
                        logger.info(
                            f"Explicitly added finding to Vertex AI Memory Bank for {safe_user_id}"
                        )
                    else:
                        logger.debug(
                            "VertexAiMemoryBankService detected but unable to write directly. Relying on session sync."
                        )
                else:
                    logger.warning(
                        f"Memory service {type(self.memory_service).__name__} does not support save_memory"
                    )
            except Exception as e:
                logger.error(f"Failed to save finding to Memory Bank: {e}")

    async def get_relevant_findings(
        self,
        query: str,
        session_id: str | None = None,
        limit: int = 5,
        user_id: str | None = None,
    ) -> list[MemoryItem]:
        """Retrieve relevant findings from memory.

        Args:
            query: Semantic query string.
            session_id: Session ID to scope search.
            limit: Max results.
            user_id: The authenticated user ID (email) for isolation.

        Returns:
            List of MemoryItems (reconstructed from storage).
        """
        results: list[MemoryItem] = []

        # 1. Search persistence if available
        if self.memory_service:
            try:
                # ADK search_memory signature: (app_name, user_id, query)
                # or (session_id, query, limit) for local
                if hasattr(self.memory_service, "save_memory"):
                    # LocalMemoryService / legacy
                    memories = await self.memory_service.search_memory(
                        session_id=session_id,
                        query=query,
                        limit=limit * 2,  # Fetch extra for client-side filtering
                    )
                else:
                    # VertexAiMemoryBankService
                    search_user = user_id or "anonymous"
                    # We use a placeholder app_name if not provided, though tools should pass it
                    # But tool_context often has session with app_name
                    from sre_agent.services.session import ADKSessionManager

                    app_name = ADKSessionManager.APP_NAME

                    response = await self.memory_service.search_memory(
                        app_name=app_name, user_id=search_user, query=query
                    )
                    memories = getattr(response, "memories", [])

                for mem in memories:
                    # STRICT SECURITY: Filter by user_id
                    # We default to "anonymous" to prevent None matching everything
                    meta = getattr(mem, "metadata", {}) or {}
                    mem_user_id = meta.get("user_id", "anonymous")
                    search_user_id = user_id or "anonymous"

                    if (
                        hasattr(self.memory_service, "save_memory")
                        and mem_user_id != search_user_id
                    ):
                        continue

                    # simplistic reconstruction
                    content = getattr(mem, "content", "")
                    if hasattr(content, "parts"):
                        # Handle ADK Content object
                        content = content.parts[0].text if content.parts else ""

                    results.append(
                        MemoryItem(
                            source_tool=meta.get("tool", "unknown"),
                            confidence=Confidence(
                                meta.get("confidence", Confidence.MEDIUM.value)
                            ),
                            timestamp=meta.get(
                                "timestamp", datetime.now(timezone.utc).isoformat()
                            ),
                            description=content or str(mem),
                            structured_data=None,  # Not persisted in simple text memory
                        )
                    )
            except Exception as e:
                logger.error(f"Failed to search Memory Bank: {e}")

        # Limit results after filtering
        results = results[:limit]

        # 2. Add local cache if not present (simple dedup)
        # In a real impl, we might merge/rank, but here we just ensure we have *something*
        if not results:
            return self._findings_cache[-limit:]  # Return most recent if offline

        return results

    async def update_state(
        self, state: InvestigationPhase, session_id: str | None = None
    ) -> None:
        """Update the investigation state."""
        self._current_state = state
        logger.info(f"🔄 Investigation State transitioned to: {state.value}")

        if self.memory_service and session_id:
            try:
                if hasattr(self.memory_service, "save_memory"):
                    # We store state transition as a memory events too
                    # This requires user_id in metadata for LocalMemoryService
                    await self.memory_service.save_memory(
                        session_id=session_id,
                        memory_content=f"Investigation state changed to {state.value}",
                        metadata={
                            "type": "state_change",
                            "new_state": state.value,
                            "user_id": "system",
                        },
                    )
                else:
                    logger.debug(
                        "VertexAiMemoryBankService detected: state change persistence relies on session sync."
                    )
            except Exception as e:
                logger.error(f"Failed to persist state change: {e}")

    @property
    def is_enabled(self) -> bool:
        """Check if memory service is available."""
        return self.memory_service is not None

    async def add_session_to_memory(self, session: Any) -> bool:
        """Store session events in long-term memory for search.

        Args:
            session: The ADK Session object containing history/findings

        Returns:
            True if successfully stored
        """
        if not self.memory_service:
            return False

        try:
            if hasattr(self.memory_service, "add_session_to_memory"):
                await self.memory_service.add_session_to_memory(session)
                logger.debug(f"Session {session.id} added to Memory Bank")
                return True
            else:
                logger.warning(
                    f"Memory service {type(self.memory_service).__name__} does not support add_session_to_memory"
                )
                return False
        except Exception as e:
            logger.error(f"Error adding session to memory: {e}")
            return False

    def get_state(self) -> InvestigationPhase:
        """Get the current investigation state."""
        return self._current_state

    # ── Learning Pattern System ──────────────────────────────────────

    def record_tool_call(self, tool_name: str) -> None:
        """Record a tool call in the current session sequence.

        Args:
            tool_name: Name of the tool that was called.
        """
        self._current_tool_sequence.append(tool_name)

    async def learn_from_investigation(
        self,
        symptom_type: str,
        root_cause_category: str,
        resolution_summary: str,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> None:
        """Extract a reusable pattern from a completed investigation.

        Called when an investigation reaches a successful conclusion.
        Stores the symptom-to-resolution mapping along with the tool
        sequence that was used, so future investigations can start
        with a better strategy.

        Args:
            symptom_type: Category of the initial symptom (e.g. "high_latency",
                "error_rate_spike", "oom_killed").
            root_cause_category: Category of the root cause found (e.g.
                "connection_pool_exhaustion", "memory_leak", "config_change").
            resolution_summary: Brief description of how it was resolved.
            session_id: Current session ID for persistence.
            user_id: User ID for isolation.
        """
        pattern = InvestigationPattern(
            symptom_type=symptom_type,
            root_cause_category=root_cause_category,
            tool_sequence=list(self._current_tool_sequence),
            resolution_summary=resolution_summary,
        )

        # Check if we've seen a similar pattern before and boost confidence
        for existing in self._learned_patterns:
            if (
                existing.symptom_type == symptom_type
                and existing.root_cause_category == root_cause_category
            ):
                existing.occurrence_count += 1
                existing.confidence = min(1.0, existing.confidence + 0.1)
                logger.info(
                    f"📚 Reinforced existing pattern: {symptom_type} -> {root_cause_category} "
                    f"(occurrences: {existing.occurrence_count}, confidence: {existing.confidence:.1f})"
                )
                return

        self._learned_patterns.append(pattern)
        logger.info(
            f"📚 Learned new investigation pattern: {symptom_type} -> {root_cause_category}"
        )

        # Persist the pattern to memory service
        if self.memory_service and session_id:
            try:
                pattern_content = (
                    f"[PATTERN] Symptom: {symptom_type} | "
                    f"Root Cause: {root_cause_category} | "
                    f"Resolution: {resolution_summary} | "
                    f"Tools: {' -> '.join(self._current_tool_sequence)}"
                )
                if hasattr(self.memory_service, "save_memory"):
                    await self.memory_service.save_memory(
                        session_id=session_id,
                        memory_content=pattern_content,
                        metadata={
                            "type": "investigation_pattern",
                            "symptom_type": symptom_type,
                            "root_cause_category": root_cause_category,
                            "tool_sequence": json.dumps(self._current_tool_sequence),
                            "confidence": str(pattern.confidence),
                            "user_id": user_id or "anonymous",
                        },
                    )
                elif hasattr(self.memory_service, "add_session_to_memory"):
                    if hasattr(self.memory_service, "_get_api_client") and getattr(
                        self.memory_service, "_agent_engine_id", None
                    ):
                        from sre_agent.services.session import ADKSessionManager

                        client = self.memory_service._get_api_client()
                        app_name = ADKSessionManager.APP_NAME
                        safe_user_id = user_id or "anonymous"

                        client.agent_engines.memories.create(
                            name=f"reasoningEngines/{self.memory_service._agent_engine_id}",
                            fact=pattern_content,
                            scope={"app_name": app_name, "user_id": safe_user_id},
                        )
                        logger.info(
                            f"Explicitly added pattern to Vertex AI Memory Bank for {safe_user_id}"
                        )
            except Exception as e:
                logger.error(f"Failed to persist learned pattern: {e}")

    async def get_recommended_strategy(
        self,
        symptom_description: str,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> list[InvestigationPattern]:
        """Find investigation patterns that match the given symptom.

        Searches both in-memory patterns and persisted memory for
        relevant past investigation strategies.

        Args:
            symptom_description: Description of the current symptom.
            session_id: Current session ID.
            user_id: User ID for isolation.

        Returns:
            List of matching patterns sorted by confidence.
        """
        results: list[InvestigationPattern] = []

        # 1. Check local pattern cache
        symptom_lower = symptom_description.lower()
        for pattern in self._learned_patterns:
            if (
                pattern.symptom_type.lower() in symptom_lower
                or symptom_lower in pattern.symptom_type.lower()
            ):
                results.append(pattern)

        # 2. Search persisted memory for past patterns
        if self.memory_service:
            try:
                findings = await self.get_relevant_findings(
                    query=f"investigation pattern for {symptom_description}",
                    session_id=session_id,
                    limit=5,
                    user_id=user_id,
                )
                for finding in findings:
                    if finding.description.startswith("[PATTERN]"):
                        # Parse pattern from description
                        try:
                            parts = finding.description.split("|")
                            symptom = parts[0].replace("[PATTERN] Symptom:", "").strip()
                            root_cause = (
                                parts[1].replace("Root Cause:", "").strip()
                                if len(parts) > 1
                                else "unknown"
                            )
                            resolution = (
                                parts[2].replace("Resolution:", "").strip()
                                if len(parts) > 2
                                else ""
                            )
                            tools_str = (
                                parts[3].replace("Tools:", "").strip()
                                if len(parts) > 3
                                else ""
                            )
                            tool_seq = [
                                t.strip() for t in tools_str.split("->") if t.strip()
                            ]

                            results.append(
                                InvestigationPattern(
                                    symptom_type=symptom,
                                    root_cause_category=root_cause,
                                    tool_sequence=tool_seq,
                                    resolution_summary=resolution,
                                )
                            )
                        except (IndexError, ValueError):
                            continue
            except Exception as e:
                logger.error(f"Failed to search patterns from memory: {e}")

        # Sort by confidence (highest first), then by occurrence count
        results.sort(key=lambda p: (p.confidence, p.occurrence_count), reverse=True)
        return results

    def reset_session_tracking(self) -> None:
        """Reset the tool call sequence for a new session/investigation."""
        self._current_tool_sequence = []
        self._current_state = InvestigationPhase.INITIATED
