"""Remote Agent Engine client for calling deployed ADK agents.

This module provides a client to call agents deployed to Vertex AI Agent Engine,
with support for End User Credentials (EUC) propagation via session state.

## Architecture

In production, the Flutter web app calls the FastAPI proxy in Cloud Run,
which then calls the remote Agent Engine:

```
Browser → Cloud Run (Proxy) → Agent Engine (Remote Agent)
                ↓                       ↓
          Extract token          Read from session state
          Pass to session        Use EUC for GCP API calls
```

## EUC Flow

1. Proxy extracts OAuth token from Authorization header
2. Proxy creates/updates session with token in state:
   - `_user_access_token`: The OAuth access token
   - `_user_project_id`: The selected GCP project
3. Proxy calls `async_stream_query` with session_id
4. Agent Engine loads session state
5. Tools read credentials via `get_credentials_from_tool_context()`
6. Tools use user's credentials for GCP API calls
"""

import logging
import os
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

from sre_agent.auth import (
    SESSION_STATE_ACCESS_TOKEN_KEY,
    SESSION_STATE_PROJECT_ID_KEY,
)

logger = logging.getLogger(__name__)


@dataclass
class AgentEngineConfig:
    """Configuration for connecting to Agent Engine."""

    project_id: str
    location: str
    agent_id: str  # The resource ID from deployment

    @classmethod
    def from_env(cls) -> "AgentEngineConfig | None":
        """Create config from environment variables.

        Returns None if not configured (local dev mode).
        """
        agent_id_raw = os.getenv("SRE_AGENT_ID")
        if not agent_id_raw:
            return None

        # Check if SRE_AGENT_ID is a full resource name
        # Format: projects/{project}/locations/{location}/reasoningEngines/{id}
        if agent_id_raw.startswith("projects/"):
            try:
                parts = agent_id_raw.split("/")
                # Expecting: projects, {project}, locations, {location}, reasoningEngines, {id}
                if (
                    len(parts) >= 6
                    and parts[0] == "projects"
                    and parts[2] == "locations"
                    and parts[4] == "reasoningEngines"
                ):
                    return cls(
                        project_id=parts[1], location=parts[3], agent_id=parts[5]
                    )
            except Exception:
                logger.warning(
                    f"Failed to parse SRE_AGENT_ID as resource name: {agent_id_raw}"
                )

        # Fallback to separate environment variables
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID")
        location = (
            os.getenv("AGENT_ENGINE_LOCATION")
            or os.getenv("GCP_LOCATION")
            or os.getenv("GOOGLE_CLOUD_LOCATION")
            or "us-central1"
        )

        if not project_id:
            logger.warning("SRE_AGENT_ID set but GOOGLE_CLOUD_PROJECT missing")
            return None

        return cls(project_id=project_id, location=location, agent_id=agent_id_raw)


class AgentEngineClient:
    """Client for calling remote Agent Engine with EUC support.

    This client handles:
    - Connecting to deployed Agent Engine
    - Session management with EUC in state
    - Streaming query responses

    Usage:
        config = AgentEngineConfig.from_env()
        if config:
            client = AgentEngineClient(config)
            async for event in client.stream_query(
                user_id="user-123",
                message="Hello",
                access_token="ya29...",
                project_id="my-project",
            ):
                print(event)
    """

    def __init__(self, config: AgentEngineConfig):
        """Initialize the Agent Engine client.

        Args:
            config: Agent Engine configuration
        """
        self.config = config
        self._adk_app: Any = None
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """Lazily initialize the Vertex AI client."""
        if self._initialized:
            return

        import vertexai
        from vertexai.preview import reasoning_engines

        # Initialize Vertex AI
        vertexai.init(
            project=self.config.project_id,
            location=self.config.location,
        )

        # Get the deployed agent
        resource_name = (
            f"projects/{self.config.project_id}/"
            f"locations/{self.config.location}/"
            f"reasoningEngines/{self.config.agent_id}"
        )

        logger.info(f"Connecting to Agent Engine: {resource_name}")
        try:
            self._adk_app = reasoning_engines.ReasoningEngine(resource_name)
            self._initialized = True
            logger.info("Agent Engine client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Agent Engine client: {e}")
            # Do not set _initialized to True, so next call retries (or fails again)
            raise e

    async def _update_session_state(
        self,
        user_id: str,
        session_id: str,
        access_token: str | None,
        project_id: str | None,
    ) -> None:
        """Update session state with user credentials.

        This is called before each query to ensure the session has
        the latest user credentials.

        Args:
            user_id: User identifier
            session_id: Session identifier
            access_token: User's OAuth access token
            project_id: Selected GCP project ID
        """
        if not access_token and not project_id:
            return

        state_delta: dict[str, Any] = {}
        if access_token:
            state_delta[SESSION_STATE_ACCESS_TOKEN_KEY] = access_token
        if project_id:
            state_delta[SESSION_STATE_PROJECT_ID_KEY] = project_id

        # Note: State updates are handled via initial session state in get_or_create_session
        # The ADK app's async_stream_query will read credentials from session state

    async def get_or_create_session(
        self,
        user_id: str,
        session_id: str | None = None,
        access_token: str | None = None,
        project_id: str | None = None,
    ) -> str:
        """Get existing session or create new one with EUC in state.

        Delegates to ADKSessionManager.
        """
        from sre_agent.services.session import get_session_service

        session_manager = get_session_service()

        initial_state = {}
        if access_token:
            initial_state[SESSION_STATE_ACCESS_TOKEN_KEY] = access_token
        if project_id:
            initial_state[SESSION_STATE_PROJECT_ID_KEY] = project_id

        session = await session_manager.get_or_create_session(
            session_id=session_id, user_id=user_id, project_id=project_id
        )
        return session.id

    async def stream_query(
        self,
        user_id: str,
        message: str,
        session_id: str | None = None,
        access_token: str | None = None,
        project_id: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream a query to the remote Agent Engine.

        This method:
        1. Ensures session exists with EUC in state
        2. Calls the remote agent with the message
        3. Yields streaming events

        Args:
            user_id: User identifier
            message: The query message
            session_id: Optional session ID (creates new if None)
            access_token: User's OAuth access token for EUC
            project_id: Selected GCP project ID

        Yields:
            Event dictionaries from the agent
        """
        await self._ensure_initialized()

        # Ensure session exists with EUC using the Session Manager
        from sre_agent.services.session import get_session_service

        session_manager = get_session_service()

        # Get session ID using the unified session manager
        # This handles the EUC state update properly via initial_state if creating new
        initial_state = {}
        if access_token:
            initial_state[SESSION_STATE_ACCESS_TOKEN_KEY] = access_token
        if project_id:
            initial_state[SESSION_STATE_PROJECT_ID_KEY] = project_id

        session = await session_manager.get_or_create_session(
            session_id=session_id, user_id=user_id, project_id=project_id
        )
        effective_session_id = session.id

        # Update state if existing session and creds changed
        if session_id and (access_token or project_id):
            state_delta = {}
            if access_token:
                state_delta[SESSION_STATE_ACCESS_TOKEN_KEY] = access_token
            if project_id:
                state_delta[SESSION_STATE_PROJECT_ID_KEY] = project_id
            if state_delta:
                await session_manager.update_session_state(session, state_delta)

        logger.info(
            f"Streaming query to Agent Engine: user={user_id}, "
            f"session={effective_session_id}, message={message[:50]}..."
        )

        # Yield session ID first
        yield {
            "type": "session",
            "session_id": effective_session_id,
        }

        # Stream query to Agent Engine
        # Warning: vertexai.preview.reasoning_engines.ReasoningEngine.query is synchronous
        # and doesn't natively support async streaming protocols yet.
        # We run it in a thread to avoid blocking the event loop.
        import asyncio

        def _query_agent() -> Any:
            # Pass user_id and session_id as kwargs which the remote agent should be configured to accept
            return self._adk_app.query(
                input=message, user_id=user_id, session_id=effective_session_id
            )

        try:
            # Note: This assumes the agent returns an iterable (generator) for streaming.
            # If the agent is non-streaming, this will return the full response at once.
            response = await asyncio.to_thread(_query_agent)

            # Handle both streaming (generator) and non-streaming (direct return) responses
            if hasattr(response, "__iter__") and not isinstance(response, str | dict):
                for event in response:
                    # Convert ADK event to dict if needed
                    if hasattr(event, "model_dump"):
                        event_dict = event.model_dump()
                    elif hasattr(event, "to_dict"):
                        event_dict = event.to_dict()
                    elif isinstance(event, dict):
                        event_dict = event
                    else:
                        event_dict = {
                            "type": "event",
                            "content": str(event),
                        }
                    yield event_dict
            else:
                # Non-streaming response
                yield {"type": "event", "content": str(response)}

        except Exception as e:
            logger.error(f"Error streaming from Agent Engine: {e}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e),
            }

    async def list_sessions(self, user_id: str) -> list[dict[str, Any]]:
        """List all sessions for a user.

        Args:
            user_id: User identifier

        Returns:
            List of session dictionaries
        """
        await self._ensure_initialized()

        try:
            sessions = await self._adk_app.async_list_sessions(user_id=user_id)
            return sessions if isinstance(sessions, list) else [sessions]
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            return []

    async def delete_session(self, user_id: str, session_id: str) -> bool:
        """Delete a session.

        Args:
            user_id: User identifier
            session_id: Session to delete

        Returns:
            True if deleted successfully
        """
        await self._ensure_initialized()

        try:
            await self._adk_app.async_delete_session(
                user_id=user_id,
                session_id=session_id,
            )
            logger.info(f"Deleted session: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False


# =============================================================================
# Singleton Access
# =============================================================================

_client: AgentEngineClient | None = None


def get_agent_engine_client() -> AgentEngineClient | None:
    """Get the Agent Engine client singleton, or None if not configured.

    Returns:
        AgentEngineClient if SRE_AGENT_ID is set, None otherwise.
    """
    global _client

    if _client is not None:
        return _client

    config = AgentEngineConfig.from_env()
    if config is None:
        logger.debug("Agent Engine not configured (SRE_AGENT_ID not set)")
        return None

    _client = AgentEngineClient(config)
    return _client


def is_remote_mode() -> bool:
    """Check if running in remote Agent Engine mode.

    Returns:
        True if SRE_AGENT_ID is set (production mode),
        False otherwise (local development mode).
    """
    return os.getenv("SRE_AGENT_ID") is not None
