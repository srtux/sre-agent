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
3. Proxy calls `stream_query` with session_id
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
    encrypt_token,
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
        from vertexai import agent_engines

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
            # Use GA agent_engines.get which ensures proper method registration
            self._adk_app = agent_engines.get(resource_name)
            self._initialized = True

            # Verify the agent has the expected methods
            methods = [m for m in dir(self._adk_app) if not m.startswith("_")]
            if not hasattr(self._adk_app, "query") and not hasattr(
                self._adk_app, "stream_query"
            ):
                logger.warning(
                    f"Agent Engine resource found but expected methods (.query/.stream_query) are missing. "
                    f"Available methods: {methods}"
                )
            else:
                logger.info(f"Agent Engine client initialized with methods: {methods}")
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
        # The ADK app's stream_query will read credentials from session state

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
        2. Calls the remote agent with the message using the required 'message'
           keyword-only argument and preferring 'async_stream_query'.
        3. Yields streaming events

        Args:
            user_id: User identifier
            message: The query message (propagated as 'message=' to SDK)
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
        session = await session_manager.get_or_create_session(
            session_id=session_id, user_id=user_id, project_id=project_id
        )
        effective_session_id = session.id

        # ALWAYS update session state with latest credentials to ensure EUC propagation
        state_delta = {}
        if (
            access_token
            and session.state.get(SESSION_STATE_ACCESS_TOKEN_KEY) != access_token
        ):
            state_delta[SESSION_STATE_ACCESS_TOKEN_KEY] = encrypt_token(access_token)
        if project_id and session.state.get(SESSION_STATE_PROJECT_ID_KEY) != project_id:
            state_delta[SESSION_STATE_PROJECT_ID_KEY] = project_id

        # PROPAGATION: Include current OTel Trace Context in session state for cross-service correlation!
        from opentelemetry import trace

        from sre_agent.auth import (
            SESSION_STATE_SPAN_ID_KEY,
            SESSION_STATE_TRACE_FLAGS_KEY,
            SESSION_STATE_TRACE_ID_KEY,
        )

        span_context = trace.get_current_span().get_span_context()
        if span_context.is_valid:
            trace_id = format(span_context.trace_id, "032x")
            span_id = format(span_context.span_id, "016x")
            trace_flags = format(span_context.trace_flags, "02x")

            if session.state.get(SESSION_STATE_TRACE_ID_KEY) != trace_id:
                state_delta[SESSION_STATE_TRACE_ID_KEY] = trace_id
                logger.debug(f"📍 Injecting Trace ID into session state: {trace_id}")

            if session.state.get(SESSION_STATE_SPAN_ID_KEY) != span_id:
                state_delta[SESSION_STATE_SPAN_ID_KEY] = span_id
                logger.debug(f"📍 Injecting Span ID into session state: {span_id}")

            if session.state.get(SESSION_STATE_TRACE_FLAGS_KEY) != trace_flags:
                state_delta[SESSION_STATE_TRACE_FLAGS_KEY] = trace_flags
                logger.debug(
                    f"📍 Injecting Trace Flags into session state: {trace_flags}"
                )

        if state_delta:
            logger.info(
                f"🔄 Updating session state with EUC: {list(state_delta.keys())}"
            )
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

        import asyncio

        def process_event(event: Any) -> dict[str, Any]:
            """Helper to convert ADK event to dict."""
            if hasattr(event, "model_dump"):
                return dict(event.model_dump())
            elif hasattr(event, "to_dict"):
                return dict(event.to_dict())
            elif isinstance(event, dict):
                return event
            else:
                return {
                    "type": "event",
                    "content": str(event),
                }

        # Stream query to Agent Engine
        try:
            # Vertex AI Reasoning Engine SDK prefers 'async_stream_query'.
            # It uses 'message' (keyword-only) as the query argument, not 'input'.
            if hasattr(self._adk_app, "async_stream_query"):
                stream = self._adk_app.async_stream_query(
                    message=message,
                    user_id=user_id,
                    session_id=effective_session_id,
                )

                try:
                    async for chunk in stream:
                        # Log raw chunk on debug for tracing specific protocol issues
                        # logger.debug(f"📥 Received chunk: {chunk}")
                        yield process_event(chunk)
                except ValueError as e:
                    # Google API REST streaming raises ValueError when parsing
                    # malformed responses (e.g., "Can only parse array of JSON objects")
                    error_msg = str(e)

                    # Log the actual failure to help developers identify the malformed response
                    logger.error(
                        f"❌ Agent Engine stream returned invalid JSON format: {error_msg}. "
                        "This usually happens when the backend returns a non-protocol error (e.g. 500 HTML or raw traceback)."
                    )

                    yield {
                        "type": "error",
                        "error": (
                            "Agent execution failed. This is typically caused by authentication issues "
                            "(e.g., expired/invalid token or encryption key mismatch) or a backend crash. "
                            "Please check the Agent Engine logs in GCP Console using the correlation Trace ID."
                        ),
                    }
                except AttributeError as e:
                    # Catch specific error where SDK expects dict but gets list
                    if "'list' object has no attribute 'get'" in str(e):
                        logger.error(
                            "Agent Engine backend returned an invalid response format (List instead of Dict). "
                            "This usually indicates an upstream error that the SDK cannot parse."
                        )
                        yield {
                            "type": "error",
                            "error": "Agent Engine returned an invalid response. Please check backend logs.",
                        }
                    else:
                        raise

            elif hasattr(self._adk_app, "stream_query"):
                # Fallback to sync stream_query (deprecated in SDK but still present)
                stream = self._adk_app.stream_query(
                    message=message,
                    user_id=user_id,
                    session_id=effective_session_id,
                )

                # The vertexai proxy might return either a sync or async iterator
                # depending on the internal client state and SDK version.
                if hasattr(stream, "__aiter__"):
                    try:
                        async for event in stream:
                            yield process_event(event)
                    except ValueError as e:
                        # Google API REST streaming raises ValueError when parsing
                        # malformed responses (e.g., "Can only parse array of JSON objects")
                        error_msg = str(e)
                        logger.error(
                            f"Agent Engine stream returned invalid JSON format: {error_msg}. "
                            "This usually indicates an authentication or execution error."
                        )
                        yield {
                            "type": "error",
                            "error": (
                                "Agent execution failed. This is typically caused by authentication issues "
                                "(e.g., expired/invalid token or encryption key mismatch). "
                                "Please try signing out and back in."
                            ),
                        }
                    except AttributeError as e:
                        # Catch specific error where SDK expects dict but gets list
                        if "'list' object has no attribute 'get'" in str(e):
                            logger.error(
                                "Agent Engine backend returned an invalid response format (List instead of Dict). "
                                "This usually indicates an upstream error that the SDK cannot parse."
                            )
                            yield {
                                "type": "error",
                                "error": "Agent Engine returned an invalid response. Please check backend logs.",
                            }
                        else:
                            raise
                else:
                    # Fallback for sync iterator. We iterate manually.
                    # Note: for-loop on a sync generator is fine here as it's
                    # what the SDK provides by default in most versions.
                    try:
                        for event in stream:
                            yield process_event(event)
                    except ValueError as e:
                        # Google API REST streaming raises ValueError when parsing
                        # malformed responses (e.g., "Can only parse array of JSON objects")
                        error_msg = str(e)
                        logger.error(
                            f"Agent Engine stream returned invalid JSON format: {error_msg}. "
                            "This usually indicates an authentication or execution error."
                        )
                        yield {
                            "type": "error",
                            "error": (
                                "Agent execution failed. This is typically caused by authentication issues "
                                "(e.g., expired/invalid token or encryption key mismatch). "
                                "Please try signing out and back in."
                            ),
                        }
                    except AttributeError as e:
                        if "'list' object has no attribute 'get'" in str(e):
                            logger.error(
                                "Agent Engine backend returned an invalid response format (List instead of Dict). "
                                "This usually indicates an upstream error that the SDK cannot parse."
                            )
                            yield {
                                "type": "error",
                                "error": "Agent Engine returned an invalid response. Please check backend logs.",
                            }
                        else:
                            raise

            # Fallback to sync query in thread if streaming methods are somehow missing
            elif hasattr(self._adk_app, "query"):
                logger.warning(
                    "AgentEngine missing streaming methods, falling back to sync 'query'"
                )

                def _query_agent() -> Any:
                    return self._adk_app.query(
                        message=message,
                        user_id=user_id,
                        session_id=effective_session_id,
                    )

                response = await asyncio.to_thread(_query_agent)
                if hasattr(response, "__iter__") and not isinstance(
                    response, str | dict
                ):
                    for event in response:
                        yield process_event(event)
                else:
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
            # Check for async_list_sessions or list_sessions
            if hasattr(self._adk_app, "async_list_sessions"):
                sessions = await self._adk_app.async_list_sessions(user_id=user_id)
            elif hasattr(self._adk_app, "list_sessions"):
                # Run sync method in thread
                import asyncio

                sessions = await asyncio.to_thread(
                    self._adk_app.list_sessions, user_id=user_id
                )
            else:
                logger.warning("Agent Engine does not support list_sessions")
                return []

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
            if hasattr(self._adk_app, "async_delete_session"):
                await self._adk_app.async_delete_session(
                    user_id=user_id,
                    session_id=session_id,
                )
            elif hasattr(self._adk_app, "delete_session"):
                import asyncio

                await asyncio.to_thread(
                    self._adk_app.delete_session,
                    user_id=user_id,
                    session_id=session_id,
                )
            else:
                logger.warning("Agent Engine does not support delete_session")
                return False

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
