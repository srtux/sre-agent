"""Shared dependencies for API endpoints."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from google.adk.tools.tool_context import ToolContext

from sre_agent.agent import root_agent
from sre_agent.services import get_session_service
from sre_agent.services.session import ADKSessionManager

logger = logging.getLogger(__name__)


def get_session_manager() -> ADKSessionManager:
    """Get the session service singleton."""
    return get_session_service()


async def get_tool_context() -> "ToolContext":
    """Create a ToolContext with a dummy session/invocation.

    Used for API endpoints that need to call tools directly.
    """
    from google.adk.agents.invocation_context import InvocationContext
    from google.adk.agents.run_config import RunConfig
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.adk.sessions.session import Session
    from google.adk.tools.tool_context import ToolContext

    # Create a minimal session
    session = Session(app_name="sre_agent", user_id="system", id="api-session")

    # Create session service
    session_service = InMemorySessionService()  # type: ignore

    # Create invocation context
    inv_ctx = InvocationContext(
        session=session,
        agent=root_agent,
        invocation_id="api-inv",
        session_service=session_service,
        run_config=RunConfig(),
    )

    return ToolContext(invocation_context=inv_ctx)
