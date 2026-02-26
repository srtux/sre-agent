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
import os
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
from pydantic import BaseModel, ConfigDict

from sre_agent.api.helpers.memory_events import get_memory_event_bus
from sre_agent.auth import (
    encrypt_token,
    get_current_credentials_or_none,
    get_current_project_id,
    is_guest_mode,
    set_current_credentials,
    set_current_project_id,
    set_current_user_id,
)
from sre_agent.core.prompt_composer import DomainContext
from sre_agent.core.runner import Runner, create_runner
from sre_agent.models.investigation import (
    PHASE_INSTRUCTIONS,
    InvestigationState,
)
from sre_agent.services.agent_engine_client import (
    get_agent_engine_client,
    is_remote_mode,
)
from sre_agent.services.session import get_session_service
from sre_agent.suggestions import generate_contextual_suggestions
from sre_agent.tools.synthetic.demo_chat_responses import (
    get_demo_suggestions,
    get_demo_turns,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["agent"])

# Enable verbose A2UI debugging with environment variable
A2UI_DEBUG = os.environ.get("A2UI_DEBUG", "").lower() in ("true", "1", "yes")


def _a2ui_debug(message: str, data: Any = None) -> None:
    """Log A2UI debug messages when A2UI_DEBUG is enabled."""
    if A2UI_DEBUG:
        if data is not None:
            if isinstance(data, (dict, list)):
                formatted = json.dumps(data, indent=2, default=str)[:1000]
                logger.info(f"🔍 A2UI_ROUTER: {message}\n{formatted}")
            else:
                logger.info(f"🔍 A2UI_ROUTER: {message} -> {str(data)[:500]}")
        else:
            logger.info(f"🔍 A2UI_ROUTER: {message}")


class AgentMessage(BaseModel):
    """A chat message from the agent."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    role: str
    text: str


class AgentRequest(BaseModel):
    """Request model for the chat agent endpoint."""

    model_config = ConfigDict(frozen=True, extra="forbid")

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
    # Optimized regex to avoid polynomial backtracking (ReDoS)
    # Using a more restrictive pattern and limiting input length for safety
    if len(text) < 1000:
        text = re.sub(r"\[Context:[^\[\]]*\]", "", text).strip()

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
    from sre_agent.api.helpers import get_current_trace_info
    from sre_agent.api.helpers.tool_events import (
        create_dashboard_event,
        create_exploration_dashboard_events,
        create_tool_call_events,
        create_tool_response_events,
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

        # Emit trace_info so the frontend can deep-link to Cloud Trace
        trace_info = get_current_trace_info(project_id=project_id)
        if trace_info:
            yield json.dumps(trace_info) + "\n"

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
                    # Robust extraction: part can be a dict or a structured object (ADK Part)
                    text = getattr(part, "text", None)
                    if text is None and isinstance(part, dict):
                        text = part.get("text")

                    if text:
                        yield json.dumps({"type": "text", "content": text}) + "\n"

                    # Handle thought
                    thought = getattr(part, "thought", None)
                    if thought is None and isinstance(part, dict):
                        thought = part.get("thought")

                    if thought:
                        formatted_thought = f"\n\n**Thought**: {thought}\n\n"
                        yield (
                            json.dumps({"type": "text", "content": formatted_thought})
                            + "\n"
                        )

                    # Handle function calls
                    fc = getattr(part, "function_call", None)
                    if fc is None and isinstance(part, dict):
                        fc = part.get("function_call")

                    if fc:
                        tool_name = (
                            getattr(fc, "name", None)
                            if not isinstance(fc, dict)
                            else fc.get("name", "")
                        )
                        if tool_name and isinstance(tool_name, str):
                            tool_args_raw = (
                                getattr(fc, "args", None)
                                if not isinstance(fc, dict)
                                else fc.get("args", {})
                            )
                            tool_args = normalize_tool_args(tool_args_raw)
                            remote_fc_id = (
                                getattr(fc, "id", None)
                                if not isinstance(fc, dict)
                                else fc.get("id")
                            )
                            _call_id, events = create_tool_call_events(
                                tool_name,
                                tool_args,
                                pending_tool_calls,
                                fc_id=remote_fc_id,
                            )
                            for evt_str in events:
                                yield evt_str + "\n"

                    # Handle function responses
                    fr = getattr(part, "function_response", None)
                    if fr is None and isinstance(part, dict):
                        fr = part.get("function_response")

                    if fr:
                        tool_name = (
                            getattr(fr, "name", None)
                            if not isinstance(fr, dict)
                            else fr.get("name", "")
                        )
                        if tool_name and isinstance(tool_name, str):
                            result = (
                                getattr(fr, "response", None)
                                or getattr(fr, "result", None)
                                if not isinstance(fr, dict)
                                else (fr.get("response") or fr.get("result"))
                            )
                            remote_fr_id = (
                                getattr(fr, "id", None)
                                if not isinstance(fr, dict)
                                else fr.get("id")
                            )
                            _resp_id, events = create_tool_response_events(
                                tool_name,
                                result,
                                pending_tool_calls,
                                fr_id=remote_fr_id,
                            )
                            for evt_str in events:
                                yield evt_str + "\n"

                            # Dashboard data event (separate channel for right panel)
                            if tool_name == "explore_project_health":
                                for evt in create_exploration_dashboard_events(result):
                                    yield evt + "\n"
                            else:
                                dash_evt = create_dashboard_event(tool_name, result)
                                if dash_evt:
                                    yield dash_evt + "\n"

                        # Memory events for UI visibility (toasts)
                        event_bus = get_memory_event_bus()
                        async for mem_event in event_bus.drain_events(
                            request.session_id or "global"
                        ):
                            yield mem_event.to_json() + "\n"

        except Exception as e:
            logger.error(f"Error streaming from Agent Engine: {e}", exc_info=True)
            yield (
                json.dumps(
                    {
                        "type": "text",
                        "content": "\n\n**Error:** An internal error occurred while streaming from Agent Engine.",
                    }
                )
                + "\n"
            )

    return StreamingResponse(
        remote_event_generator(),
        media_type="application/x-ndjson",
    )


async def _guest_event_generator(turn_index: int = 0) -> AsyncGenerator[str, None]:
    """Stream pre-recorded demo events for guest mode."""
    turns = get_demo_turns()
    suggestions = get_demo_suggestions()

    # Emit session event first
    session_event = json.dumps(
        {
            "type": "session",
            "session_id": "demo-session-001",
            "title": "Demo: Cymbal Shops Incident Investigation",
        }
    )
    yield session_event + "\n"

    # Clamp turn index to available turns
    idx = min(turn_index, len(turns) - 1)

    # Stream all events for this turn with small delays
    for event_line in turns[idx]:
        yield event_line + "\n"
        await asyncio.sleep(0.05)  # Small delay for realistic streaming

    # Emit suggestions at the end
    suggestion_event = json.dumps(
        {
            "type": "suggestions",
            "suggestions": suggestions,
        }
    )
    yield suggestion_event + "\n"


@router.post("/api/genui/chat")
@router.post("/agent")
async def chat_agent(request: AgentRequest, raw_request: Request) -> StreamingResponse:
    """Handle chat requests for the SRE Agent.

    This endpoint supports two modes:
    - **Remote Mode** (production): Forwards to Vertex AI Agent Engine
    - **Local Mode** (development): Runs agent directly in this process

    The mode is determined by the SRE_AGENT_ID environment variable.
    """
    # Guest mode: stream pre-recorded demo responses
    if is_guest_mode():
        # Use message count to determine which turn to show
        turn_index = len(request.messages) - 1 if request.messages else 0
        return StreamingResponse(
            _guest_event_generator(turn_index=turn_index),
            media_type="application/x-ndjson",
        )

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

    # Log auth context
    logger.info(
        f"🔐 Chat Auth Context: user={effective_user_id}, "
        f"project={effective_project_id}, has_token={access_token is not None}"
    )

    # Check if we should use remote Agent Engine
    if is_remote_mode():
        logger.info("Using remote Agent Engine mode")

        # We must override the user_id in the request passed to remote agent
        # to ensure it uses the trusted ID.
        request = request.model_copy(update={"user_id": effective_user_id})

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
    from sre_agent.api.helpers import get_current_trace_info
    from sre_agent.api.helpers.dashboard_queue import (
        drain_dashboard_queue,
        init_dashboard_queue,
    )
    from sre_agent.api.helpers.tool_events import (
        create_dashboard_event,
        create_exploration_dashboard_events,
        create_tool_call_events,
        create_tool_response_events,
        normalize_tool_args,
    )

    # Lazy init runner
    if not hasattr(root_agent, "_runner"):
        setattr(root_agent, "_runner", create_runner(root_agent))  # noqa: B010
    runner: Runner = getattr(root_agent, "_runner")  # noqa: B009

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
                    and (session.state or {}).get(SESSION_STATE_PROJECT_ID_KEY)
                    != effective_project_id
                ):
                    state_updates[SESSION_STATE_PROJECT_ID_KEY] = effective_project_id

                if (
                    access_token
                    and (session.state or {}).get(SESSION_STATE_ACCESS_TOKEN_KEY)
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
                initial_state[SESSION_STATE_ACCESS_TOKEN_KEY] = encrypt_token(
                    access_token
                )

            # Initialize investigation state
            initial_state["investigation_state"] = InvestigationState().to_dict()

            session = await session_manager.create_session(
                user_id=effective_user_id, initial_state=initial_state
            )
            is_new_session = True

        # 2. Prepare State & Context
        state_dict = (session.state or {}).get("investigation_state", {})
        inv_state = InvestigationState.from_dict(state_dict)
        current_project_id = (session.state or {}).get(
            SESSION_STATE_PROJECT_ID_KEY
        ) or effective_project_id

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

        # Create InvocationContext with memory service for PreloadMemoryTool
        from sre_agent.memory.factory import get_adk_memory_service

        inv_ctx = InvocationContext(
            session=session,
            agent=root_agent,
            invocation_id=uuid.uuid4().hex,
            session_service=session_manager.session_service,
            run_config=RunConfig(),
            memory_service=get_adk_memory_service(),
        )
        inv_ctx.user_content = user_content

        # Persist User Message (Original Text for history)
        user_event = Event(
            invocation_id=inv_ctx.invocation_id,
            author="user",
            content=Content(parts=[Part(text=last_msg_text)], role="user"),
            timestamp=time.time(),
        )
        await session_manager.append_event(session, user_event)

        # 3. Stream Response
        async def event_generator() -> AsyncGenerator[str, None]:
            # Propagate authentication context into the generator.
            # This is CRITICAL for StreamingResponse because the middleware's finally block
            # clears the ContextVars before the generator starts yielding.
            if access_token:
                from google.oauth2.credentials import Credentials

                set_current_credentials(Credentials(token=access_token))  # type: ignore[no-untyped-call]
            if effective_project_id:
                set_current_project_id(effective_project_id)
            if effective_user_id:
                set_current_user_id(effective_user_id)

            # Initialise the dashboard event queue for this request.
            # Tools decorated with @adk_tool enqueue their results here so
            # that sub-agent tool calls (hidden inside AgentTool) also
            # produce dashboard events.
            init_dashboard_queue()

            # Track pending tool calls for FIFO matching
            pending_tool_calls: list[dict[str, Any]] = []

            # Track inline-emitted dashboard events to avoid duplicates
            # when the same tool result appears in both the event stream
            # (inline) and the dashboard queue (from @adk_tool decorator).
            inline_emitted_counts: dict[str, int] = {}

            # --- DEBUG UI TEST PATTERN ---
            if "DEBUG_UI_TEST" in last_msg_text:
                logger.info("🧪 Triggering DEBUG_UI_TEST mock sequence")
                yield json.dumps({"type": "session", "session_id": session.id}) + "\n"

                # Test: Simple 'tool-log' Alias + Waterfall Control
                yield (
                    json.dumps(
                        {
                            "type": "text",
                            "content": "### Test: Simple 'tool-log' Alias + BUTTON Control\nExpecting: GREEN/CYAN BOX or BUTTON",
                        }
                    )
                    + "\n"
                )

                sid = uuid.uuid4().hex
                cid = f"tool-log-{sid[:8]}"

                # Atomic Init with Alias & Redundant Types & Button
                yield (
                    json.dumps(
                        {
                            "type": "a2ui",
                            "message": {
                                "beginRendering": {
                                    "surfaceId": sid,
                                    "root": cid,
                                    "components": [
                                        {
                                            "id": cid,
                                            "type": "tool-log",  # Root Level Type
                                            "component": {
                                                "type": "tool-log",
                                                "componentType": "tool-log",
                                                "tool-log": {
                                                    "type": "tool-log",
                                                    "tool_name": "alias_test",
                                                    "status": "running",
                                                },
                                            },
                                        }
                                    ],
                                }
                            },
                        }
                    )
                    + "\n"
                )

                # Sequenced: Marker AFTER data
                yield json.dumps({"type": "ui", "surface_id": sid}) + "\n"
                yield (
                    json.dumps(
                        {
                            "type": "a2ui",
                            "message": {
                                "surfaceUpdate": {
                                    "surfaceId": sid,
                                    "components": [
                                        {
                                            "id": cid,
                                            "type": "tool-log",
                                            "component": {
                                                "type": "tool-log",
                                                "componentType": "tool-log",
                                                "tool-log": {
                                                    "type": "tool-log",
                                                    "tool_name": "alias_test",
                                                    "status": "completed",  # Update to completed
                                                    "result": "Local UI test successful",
                                                },
                                            },
                                        }
                                    ],
                                }
                            },
                        }
                    )
                    + "\n"
                )

                # Test Button (Core Catalog)
                sid_btn = uuid.uuid4().hex
                cid_btn = f"btn-{sid_btn[:8]}"

                # Sequencing: DATA FIRST
                yield (
                    json.dumps(
                        {
                            "type": "a2ui",
                            "message": {
                                "beginRendering": {
                                    "surfaceId": sid_btn,
                                    "root": cid_btn,
                                    "components": [
                                        {
                                            "id": cid_btn,
                                            "type": "button",
                                            "component": {
                                                "type": "button",
                                                "label": "CORE BUTTON TEST",
                                                "actionId": "test_action",
                                            },
                                        }
                                    ],
                                }
                            },
                        }
                    )
                    + "\n"
                )

                # Sequencing: MARKER SECOND
                yield json.dumps({"type": "ui", "surface_id": sid_btn}) + "\n"

                return
            # -----------------------------

            # Send session ID first
            session_init_evt = (
                json.dumps({"type": "session", "session_id": session.id}) + "\n"
            )
            logger.info(f"📤 Initializing session stream: {session.id}")
            yield session_init_evt

            # Emit trace_info so the frontend can deep-link to Cloud Trace
            trace_info = get_current_trace_info(project_id=effective_project_id)
            if trace_info:
                yield json.dumps(trace_info) + "\n"

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
                # Iterate through agent events from the Runner
                # create domain context for the run
                domain_ctx = DomainContext(
                    project_id=effective_project_id,
                    investigation_phase=inv_state.phase.value if inv_state else None,
                )
                async for event in runner.run_turn(
                    session=active_session,
                    user_message=last_msg_text,
                    user_id=effective_user_id,
                    project_id=effective_project_id,
                    domain_context=domain_ctx,
                ):
                    logger.debug(
                        f"📥 Received event from runner: {str(event)[:500]}..."
                    )

                    # Persist generated event
                    await session_manager.append_event(active_session, event)

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
                        logger.debug(f"🔍 Processing part: {str(part)[:500]}...")

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
                            # logger.info(f"🧠 Yielding reasoning thought: {str(thought)[:50]}...")
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
                            tool_name = (
                                getattr(fc, "name", None)
                                if not isinstance(fc, dict)
                                else fc.get("name")
                            )
                            if tool_name and isinstance(tool_name, str):
                                tool_args_raw = (
                                    getattr(fc, "args", None)
                                    if not isinstance(fc, dict)
                                    else fc.get("args")
                                )
                                tool_args = normalize_tool_args(tool_args_raw)
                                # Extract function call id for robust matching
                                fc_id = (
                                    getattr(fc, "id", None)
                                    if not isinstance(fc, dict)
                                    else fc.get("id")
                                )

                                logger.info(
                                    f"🛠️ Tool Call: {tool_name} args={str(tool_args)[:100]}..."
                                )
                                _call_id, events = create_tool_call_events(
                                    tool_name,
                                    tool_args,
                                    pending_tool_calls,
                                    fc_id=fc_id,
                                )

                                for evt_str in events:
                                    yield evt_str + "\n"

                        # D. Handle Tool Responses
                        fr = getattr(part, "function_response", None)
                        if fr is None and isinstance(part, dict):
                            fr = part.get("function_response")

                        if fr:
                            tool_name = (
                                getattr(fr, "name", None)
                                if not isinstance(fr, dict)
                                else fr.get("name")
                            )
                            if tool_name and isinstance(tool_name, str):
                                result = (
                                    getattr(fr, "response", None)
                                    or getattr(fr, "result", None)
                                    if not isinstance(fr, dict)
                                    else (fr.get("response") or fr.get("result"))
                                )
                                # Extract function response id for robust matching
                                fr_id = (
                                    getattr(fr, "id", None)
                                    if not isinstance(fr, dict)
                                    else fr.get("id")
                                )

                                logger.info(f"✅ Tool Response: {tool_name}")
                                _resp_id, events = create_tool_response_events(
                                    tool_name, result, pending_tool_calls, fr_id=fr_id
                                )
                                for evt_str in events:
                                    yield evt_str + "\n"

                                # Separate dashboard data event
                                if tool_name == "explore_project_health":
                                    for evt in create_exploration_dashboard_events(
                                        result
                                    ):
                                        logger.info(
                                            f"📊 Dashboard event (inline) for {tool_name}"
                                        )
                                        yield evt + "\n"
                                    inline_emitted_counts[tool_name] = (
                                        inline_emitted_counts.get(tool_name, 0) + 1
                                    )
                                else:
                                    dash_evt = create_dashboard_event(tool_name, result)
                                    if dash_evt:
                                        logger.info(
                                            f"📊 Dashboard event (inline) for {tool_name}"
                                        )
                                        yield dash_evt + "\n"
                                        inline_emitted_counts[tool_name] = (
                                            inline_emitted_counts.get(tool_name, 0) + 1
                                        )

                                # Memory events for UI visibility (toasts)
                                event_bus = get_memory_event_bus()
                                async for mem_event in event_bus.drain_events(
                                    session.id or "global"
                                ):
                                    logger.info(
                                        f"🧠 Memory event: {mem_event.action.value}"
                                    )
                                    yield mem_event.to_json() + "\n"

                    # ── Drain dashboard event queue ──────────────────────
                    # The @adk_tool decorator queues dashboard-relevant
                    # results (including from sub-agent tool calls hidden
                    # inside AgentTool).  Drain them after each runner event
                    # so the frontend receives dashboard updates promptly.
                    # Skip entries already emitted inline to avoid duplicates.
                    for queued_name, queued_result in drain_dashboard_queue():
                        if inline_emitted_counts.get(queued_name, 0) > 0:
                            inline_emitted_counts[queued_name] -= 1
                            continue
                        if queued_name == "explore_project_health":
                            for evt in create_exploration_dashboard_events(
                                queued_result
                            ):
                                logger.info(
                                    f"📊 Dashboard event (queued) for {queued_name}"
                                )
                                yield evt + "\n"
                        else:
                            dash_evt = create_dashboard_event(
                                queued_name, queued_result
                            )
                            if dash_evt:
                                logger.info(
                                    f"📊 Dashboard event (queued) for {queued_name}"
                                )
                                yield dash_evt + "\n"

                # 4. Post-run Cleanup & Memory Sync
                try:
                    # Sync findings and observations to Long-term Memory Bank
                    # This makes the investigation searchable in future sessions
                    await session_manager.sync_to_memory(active_session)
                except Exception:
                    logger.warning(f"⚠️ Memory sync skipped or failed for {session.id}")

            except Exception as e:
                logger.error(f"🔥 Error in agent run: {e}", exc_info=True)
                yield (
                    json.dumps(
                        {
                            "type": "text",
                            "content": "\n\n**Error executing agent:** An internal error occurred.",
                        }
                    )
                    + "\n"
                )
            finally:
                if "checker_task" in locals() and not checker_task.done():
                    checker_task.cancel()

        return StreamingResponse(event_generator(), media_type="application/x-ndjson")

    except Exception:
        logger.error("Error in chat endpoint", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from None
