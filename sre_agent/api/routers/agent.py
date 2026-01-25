"""Agent chat endpoints.

This module provides the main chat endpoint for the SRE Agent, supporting both:

1. **Local Mode (Development)**: Agent runs directly in the FastAPI process.
   - Faster iteration during development
   - Credentials passed via ContextVars
   - Uses local session storage (SQLite or in-memory)

2. **Remote Mode (Production)**: Agent runs in Vertex AI Agent Engine.
   - Scalable, managed infrastructure
   - Credentials passed via session state
   - Uses VertexAiSessionService for persistence

The mode is determined by the `SRE_AGENT_ID` environment variable:
- If set: Remote mode (call Agent Engine)
- If not set: Local mode (run agent locally)
"""

import asyncio
import json
import logging
import re
import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.run_config import RunConfig
from google.adk.events import Event
from google.adk.sessions.session import Session as AdkSession
from google.genai.types import Content, Part
from pydantic import BaseModel

from sre_agent.auth import (
    get_current_credentials_or_none,
    get_current_project_id,
)
from sre_agent.models.investigation import (
    PHASE_INSTRUCTIONS,
    InvestigationState,
)
from sre_agent.services import get_session_service
from sre_agent.services.agent_engine_client import (
    get_agent_engine_client,
    is_remote_mode,
)
from sre_agent.suggestions import generate_contextual_suggestions

logger = logging.getLogger(__name__)
router = APIRouter(tags=["agent"])


class AgentMessage(BaseModel):
    """A chat message from the agent."""

    role: str
    text: str


class AgentRequest(BaseModel):
    """Request model for the chat agent endpoint."""

    messages: list[AgentMessage]
    session_id: str | None = None
    project_id: str | None = None
    user_id: str = "default"


def _generate_session_title(user_message: str) -> str:
    """Generate a concise session title from the first user message.

    Creates a 3-5 word title suitable for the sidebar display.

    Args:
        user_message: The first user message in the session

    Returns:
        A concise title string
    """
    # Clean up the message
    text = user_message.strip()

    # Remove common prefixes
    prefixes = ["can you", "please", "help me", "i want to", "i need to", "could you"]
    lower_text = text.lower()
    for prefix in prefixes:
        if lower_text.startswith(prefix):
            text = text[len(prefix) :].strip()
            break

    # Remove context tags like [Context: ...]
    text = re.sub(r"\[Context:.*?\]", "", text).strip()

    # Take first sentence or first N words
    sentences = re.split(r"[.?!\n]", text)
    first_sentence = sentences[0].strip() if sentences else text

    # Split into words and take first 5 meaningful words
    words = first_sentence.split()
    title_words: list[str] = []
    for word in words:
        # Skip very short words at the start
        if len(title_words) == 0 and len(word) <= 2:
            continue
        title_words.append(word)
        if len(title_words) >= 5:
            break

    if not title_words:
        return "New Investigation"

    title = " ".join(title_words)

    # Capitalize first letter
    if title:
        title = title[0].upper() + title[1:]

    # Truncate if still too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title


@router.get("/api/suggestions")
async def get_suggestions(
    project_id: str | None = None,
    session_id: str | None = None,
    user_id: str = "default",
) -> Any:
    """Get contextual suggestions for the user."""
    try:
        suggestions = await generate_contextual_suggestions(
            project_id=project_id,
            session_id=session_id,
            user_id=user_id,
        )
        return {"suggestions": suggestions}
    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        return {
            "suggestions": [
                "Analyze last hour's logs",
                "List active incidents",
                "Check for high latency",
            ]
        }


async def _handle_remote_agent(
    request: AgentRequest,
    raw_request: Request,
    access_token: str | None,
    project_id: str | None,
) -> StreamingResponse:
    """Handle chat request by calling remote Agent Engine.

    This function is used in production when SRE_AGENT_ID is set.
    It forwards the request to the deployed Agent Engine and streams
    the response back to the client.

    Args:
        request: The chat request
        raw_request: The raw FastAPI request
        access_token: User's OAuth access token for EUC
        project_id: Selected GCP project ID

    Returns:
        StreamingResponse with agent events
    """
    from sre_agent.api.helpers.tool_events import (
        create_tool_call_events,
        create_tool_response_events,
        create_widget_events,
        normalize_tool_args,
    )

    client = get_agent_engine_client()
    if client is None:
        raise HTTPException(
            status_code=500,
            detail="Agent Engine client not configured (SRE_AGENT_ID missing)",
        )

    last_msg_text = request.messages[-1].text if request.messages else ""

    async def remote_event_generator() -> AsyncGenerator[str, None]:
        """Stream events from remote Agent Engine."""
        pending_tool_calls: list[dict[str, Any]] = []

        try:
            async for event in client.stream_query(
                user_id=request.user_id,
                message=last_msg_text,
                session_id=request.session_id,
                access_token=access_token,
                project_id=project_id,
            ):
                event_type = event.get("type", "unknown")

                # Handle session event
                if event_type == "session":
                    yield json.dumps(event) + "\n"
                    yield (
                        json.dumps({"type": "text", "content": "*(Thinking...)* "})
                        + "\n"
                    )
                    continue

                # Handle error event
                if event_type == "error":
                    yield (
                        json.dumps(
                            {
                                "type": "text",
                                "content": f"\n\n**Error:** {event.get('error', 'Unknown error')}",
                            }
                        )
                        + "\n"
                    )
                    continue

                # Process content parts from the event
                content = event.get("content", {})
                parts = content.get("parts", []) if isinstance(content, dict) else []

                for part in parts:
                    # Handle text
                    text = part.get("text") if isinstance(part, dict) else None
                    if text:
                        yield json.dumps({"type": "text", "content": text}) + "\n"

                    # Handle function calls
                    fc = part.get("function_call") if isinstance(part, dict) else None
                    if fc:
                        tool_name = fc.get("name", "")
                        tool_args = normalize_tool_args(fc.get("args", {}))
                        _, events = create_tool_call_events(
                            tool_name, tool_args, pending_tool_calls
                        )
                        for evt_str in events:
                            yield evt_str + "\n"

                    # Handle function responses
                    fr = (
                        part.get("function_response")
                        if isinstance(part, dict)
                        else None
                    )
                    if fr:
                        tool_name = fr.get("name", "")
                        result = fr.get("response") or fr.get("result")
                        _, events = create_tool_response_events(
                            tool_name, result, pending_tool_calls
                        )
                        for evt_str in events:
                            yield evt_str + "\n"

                        # Widget events
                        widget_events = create_widget_events(tool_name, result)
                        for evt_str in widget_events:
                            yield evt_str + "\n"

        except Exception as e:
            logger.error(f"Error streaming from Agent Engine: {e}", exc_info=True)
            yield (
                json.dumps(
                    {
                        "type": "text",
                        "content": f"\n\n**Error:** {e!s}",
                    }
                )
                + "\n"
            )

    return StreamingResponse(
        remote_event_generator(),
        media_type="application/x-ndjson",
    )


@router.post("/api/genui/chat")
@router.post("/agent")
async def chat_agent(request: AgentRequest, raw_request: Request) -> StreamingResponse:
    """Handle chat requests for the SRE Agent.

    This endpoint supports two modes:
    - **Remote Mode** (production): Forwards to Vertex AI Agent Engine
    - **Local Mode** (development): Runs agent directly in this process

    The mode is determined by the SRE_AGENT_ID environment variable.
    """
    # Get credentials from middleware (set by auth_middleware)
    creds = get_current_credentials_or_none()

    # STRICT SECURITY: Use trusted user ID from token if available
    from sre_agent.auth import get_current_user_id

    trusted_user_id = get_current_user_id()
    effective_user_id = trusted_user_id or request.user_id

    # If strict enforcement is on, we might reject mismatch, but for now we
    # just prioritize the trusted one if running in the same process.
    if trusted_user_id and trusted_user_id != request.user_id:
        logger.warning(
            f"User ID mismatch: Request={request.user_id}, Token={trusted_user_id}. Using Token ID."
        )

    access_token = creds.token if creds and hasattr(creds, "token") else None
    effective_project_id = get_current_project_id() or request.project_id

    # Check if we should use remote Agent Engine
    if is_remote_mode():
        logger.info("Using remote Agent Engine mode")

        # We must override the user_id in the request passed to remote agent
        # to ensure it uses the trusted ID.
        request.user_id = effective_user_id

        return await _handle_remote_agent(
            request=request,
            raw_request=raw_request,
            access_token=access_token,
            project_id=effective_project_id,
        )

    # Local mode: Run agent directly
    logger.info("Using local agent execution mode")

    # Import root_agent only in local mode to avoid loading model in proxy-only mode
    from sre_agent.agent import root_agent
    from sre_agent.api.helpers.tool_events import (
        create_tool_call_events,
        create_tool_response_events,
        create_widget_events,
        normalize_tool_args,
    )

    try:
        session_manager = get_session_service()
        session: AdkSession | None = None
        is_new_session = False

        from sre_agent.auth import (
            SESSION_STATE_ACCESS_TOKEN_KEY,
            SESSION_STATE_PROJECT_ID_KEY,
        )

        # access_token and effective_project_id already extracted at function start

        if request.session_id:
            # Pass user_id to ensure we find the correct session
            session = await session_manager.get_session(
                request.session_id, user_id=effective_user_id
            )
            # Update project ID if it changed in the UI project selector
            # Update project ID or Access Token if changed
            if session:
                state_updates = {}
                if (
                    effective_project_id
                    and session.state.get(SESSION_STATE_PROJECT_ID_KEY)
                    != effective_project_id
                ):
                    state_updates[SESSION_STATE_PROJECT_ID_KEY] = effective_project_id

                if (
                    access_token
                    and session.state.get(SESSION_STATE_ACCESS_TOKEN_KEY)
                    != access_token
                ):
                    state_updates[SESSION_STATE_ACCESS_TOKEN_KEY] = access_token

                if state_updates:
                    logger.info(f"🔄 Updating session state: {state_updates.keys()}")
                    await session_manager.update_session_state(session, state_updates)

        if not session:
            initial_state: dict[str, Any] = {}
            if effective_project_id:
                initial_state[SESSION_STATE_PROJECT_ID_KEY] = effective_project_id
            if access_token:
                initial_state[SESSION_STATE_ACCESS_TOKEN_KEY] = access_token

            # Initialize investigation state
            initial_state["investigation_state"] = InvestigationState().to_dict()

            session = await session_manager.create_session(
                user_id=effective_user_id, initial_state=initial_state
            )
            is_new_session = True

        # 2. Prepare State & Context
        state_dict = session.state.get("investigation_state", {})
        inv_state = InvestigationState.from_dict(state_dict)
        current_project_id = (
            session.state.get(SESSION_STATE_PROJECT_ID_KEY) or effective_project_id
        )

        last_msg_text = request.messages[-1].text if request.messages else ""

        # Inject Phase Guidance and Project Context to help agent focus on current stage and project
        phase_instruction = PHASE_INSTRUCTIONS.get(inv_state.phase, "")
        enhanced_text = (
            f"[INVESTIGATION PHASE: {inv_state.phase.value.upper()}]\n"
            f"[CURRENT PROJECT: {current_project_id}]\n"
            f"Guidance: {phase_instruction}\n\n"
            f"User Message: {last_msg_text}"
        )
        user_content = Content(parts=[Part(text=enhanced_text)], role="user")

        # Create InvocationContext
        inv_ctx = InvocationContext(
            session=session,
            agent=root_agent,
            invocation_id=uuid.uuid4().hex,
            session_service=session_manager.session_service,
            run_config=RunConfig(),
        )
        inv_ctx.user_content = user_content

        # Persist User Message (Original Text for history)
        user_event = Event(
            invocation_id=inv_ctx.invocation_id,
            author="user",
            content=Content(parts=[Part(text=last_msg_text)], role="user"),
            timestamp=time.time(),
        )
        await session_manager.session_service.append_event(session, user_event)

        # 3. Stream Response
        async def event_generator() -> AsyncGenerator[str, None]:
            # Track pending tool calls for FIFO matching
            pending_tool_calls: list[dict[str, Any]] = []

            # Send session ID first
            session_init_evt = (
                json.dumps({"type": "session", "session_id": session.id}) + "\n"
            )
            logger.info(f"📤 Initializing session stream: {session.id}")
            yield session_init_evt

            # Yield an initial indicator to open the chat bubble
            yield json.dumps({"type": "text", "content": "*(Thinking...)* "}) + "\n"

            # Refresh session to ensure we have the latest state
            active_session = session
            refreshed_session = await session_manager.get_session(
                session.id, user_id=effective_user_id
            )
            if refreshed_session:
                active_session = refreshed_session
                # Update invocation context with fresh session reference
                inv_ctx.session = active_session

            # Auto-generate title for new sessions
            if is_new_session and last_msg_text:
                title = _generate_session_title(last_msg_text)
                try:
                    await session_manager.update_session_state(
                        active_session, {"title": title}
                    )
                    logger.info(f"🏷️ Auto-named session {session.id}: {title}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to auto-name session: {e}")

            # Start a background task to monitor client disconnection.
            # This ensures the agent run is cancelled immediately (with CancelledError)
            # when the client disconnects, even if the StreamResponse hasn't yet
            # polled the generator. The 0.1s interval matches test expectations.
            current_task = asyncio.current_task()

            async def disconnect_checker() -> None:
                try:
                    while not await raw_request.is_disconnected():
                        await asyncio.sleep(0.1)
                    if current_task:
                        logger.warning(
                            f"🔌 Client disconnected for session {session.id}. Cancelling agent task."
                        )
                        current_task.cancel()
                except asyncio.CancelledError:
                    pass

            checker_task = asyncio.create_task(disconnect_checker())

            try:
                # Iterate through agent events and yield to the stream
                # FastAPI StreamingResponse natively handles client disconnection via CancelledError
                async for event in root_agent.run_async(inv_ctx):
                    logger.debug(f"📥 Received event from agent: {event}")

                    # Persist generated event
                    await session_manager.session_service.append_event(
                        active_session, event
                    )

                    # 1. Extract parts from content if available
                    parts = []
                    content = getattr(event, "content", None) or (
                        isinstance(event, dict) and event.get("content")
                    )

                    if content:
                        raw_parts = getattr(content, "parts", []) or (
                            isinstance(content, dict) and content.get("parts", [])
                        )
                        # Normalize to a list of parts
                        if isinstance(raw_parts, list):
                            parts = raw_parts
                        else:
                            parts = [raw_parts]

                    # 2. If no content parts, check if the event itself is a direct tool response or call
                    # Some ADK event types might have these as direct attributes
                    if not parts:
                        fc = getattr(event, "function_call", None)
                        fr = getattr(event, "function_response", None)
                        if fc or fr:
                            parts = [
                                {"function_call": fc}
                                if fc
                                else {"function_response": fr}
                            ]

                    if not parts:
                        logger.debug(
                            f"[INFO] Skipping event with no parts: {type(event).__name__}"
                        )
                        continue

                    for part in parts:
                        logger.debug(f"🔍 Processing part: {part}")

                        # A. Handle Text
                        text = getattr(part, "text", None)
                        if text is None and isinstance(part, dict):
                            text = part.get("text")
                        if text and isinstance(text, str):
                            logger.info(f"📤 Yielding text: {str(text)[:50]}...")
                            yield json.dumps({"type": "text", "content": text}) + "\n"

                        # B. Handle Thought (Reasoning)
                        thought = getattr(part, "thought", None)
                        if thought is None and isinstance(part, dict):
                            thought = part.get("thought")
                        if thought and isinstance(thought, str):
                            logger.info(
                                f"🧠 Yielding reasoning thought: {str(thought)[:50]}..."
                            )
                            formatted_thought = f"\n\n**Thought**: {thought}\n\n"
                            yield (
                                json.dumps(
                                    {"type": "text", "content": formatted_thought}
                                )
                                + "\n"
                            )

                        # C. Handle Tool Calls
                        fc = getattr(part, "function_call", None)
                        if fc is None and isinstance(part, dict):
                            fc = part.get("function_call")

                        if fc:
                            tool_name = getattr(fc, "name", None)
                            if tool_name is None and isinstance(fc, dict):
                                tool_name = fc.get("name")

                            if tool_name and isinstance(tool_name, str):
                                tool_args_raw = getattr(fc, "args", None)
                                if tool_args_raw is None and isinstance(fc, dict):
                                    tool_args_raw = fc.get("args")
                                tool_args = normalize_tool_args(tool_args_raw)
                                logger.info(f"🛠️ Tool Call Request: {tool_name}")
                                _, events = create_tool_call_events(
                                    tool_name, tool_args, pending_tool_calls
                                )
                                for evt_str in events:
                                    logger.info(
                                        f"📤 Yielding tool call event: {evt_str}"
                                    )
                                    yield evt_str + "\n"

                        # D. Handle Tool Responses
                        fr = getattr(part, "function_response", None)
                        if fr is None and isinstance(part, dict):
                            fr = part.get("function_response")

                        if fr:
                            tool_name = getattr(fr, "name", None)
                            if tool_name is None and isinstance(fr, dict):
                                tool_name = fr.get("name")

                            if tool_name and isinstance(tool_name, str):
                                result = getattr(fr, "response", None)
                                if result is None and isinstance(fr, dict):
                                    result = fr.get("response")
                                # Fallback to 'result' or 'output' if 'response' is missing
                                if result is None:
                                    result = getattr(fr, "result", None)
                                    if result is None and isinstance(fr, dict):
                                        result = fr.get("result")

                                logger.info(f"✅ Tool Response Received: {tool_name}")
                                _, events = create_tool_response_events(
                                    tool_name, result, pending_tool_calls
                                )
                                for evt_str in events:
                                    logger.info(
                                        f"📤 Yielding tool response event: {evt_str}"
                                    )
                                    yield evt_str + "\n"

                                # Yield specialized widget
                                widget_events = create_widget_events(tool_name, result)
                                for evt_str in widget_events:
                                    logger.info(f"📤 Yielding widget event: {evt_str}")
                                    yield evt_str + "\n"

                # 4. Post-run Cleanup & Memory Sync
                try:
                    # Sync findings and observations to Long-term Memory Bank
                    # This makes the investigation searchable in future sessions
                    await session_manager.sync_to_memory(active_session)
                except Exception as e:
                    logger.warning(
                        f"⚠️ Memory sync skipped or failed for {session.id}: {e}"
                    )

            except Exception as e:
                logger.error(f"🔥 Error in agent run: {e}", exc_info=True)
                yield (
                    json.dumps(
                        {
                            "type": "text",
                            "content": f"\n\n**Error executing agent:** {e!s}",
                        }
                    )
                    + "\n"
                )
            finally:
                if "checker_task" in locals() and not checker_task.done():
                    checker_task.cancel()

        return StreamingResponse(event_generator(), media_type="application/x-ndjson")

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
