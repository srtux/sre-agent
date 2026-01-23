"""Agent chat endpoints."""

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

from sre_agent.agent import root_agent
from sre_agent.auth import get_current_project_id
from sre_agent.models.investigation import (
    PHASE_INSTRUCTIONS,
    InvestigationState,
)
from sre_agent.services import get_session_service
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


@router.post("/api/genui/chat")
@router.post("/agent")
async def chat_agent(request: AgentRequest, raw_request: Request) -> StreamingResponse:
    """Handle chat requests for the SRE Agent."""
    # Import tool event helpers from the helpers module
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

        # 1. Get or Create Session
        # Prioritize project ID from header/context
        effective_project_id = get_current_project_id() or request.project_id

        if request.session_id:
            # Pass user_id to ensure we find the correct session
            session = await session_manager.get_session(
                request.session_id, user_id=request.user_id
            )

        if not session:
            initial_state = {}
            if effective_project_id:
                initial_state["project_id"] = effective_project_id

            # Initialize investigation state
            initial_state["investigation_state"] = InvestigationState().to_dict()

            session = await session_manager.create_session(
                user_id=request.user_id, initial_state=initial_state
            )
            is_new_session = True

        # 2. Prepare State & Context
        state_dict = session.state.get("investigation_state", {})
        inv_state = InvestigationState.from_dict(state_dict)

        last_msg_text = request.messages[-1].text if request.messages else ""

        # Inject Phase Guidance to help agent focus on current stage
        phase_instruction = PHASE_INSTRUCTIONS.get(inv_state.phase, "")
        enhanced_text = (
            f"[INVESTIGATION PHASE: {inv_state.phase.value.upper()}]\n"
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

            # Refresh session to ensure we have the latest state
            active_session = session
            refreshed_session = await session_manager.get_session(
                session.id, user_id=request.user_id
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

            try:
                # Wrap the agent generator in a task-like structure for proactive cancellation
                # This is essential for detecting disconnection while the agent is busy/sleeping
                async def run_agent() -> AsyncGenerator[Any, None]:
                    async for event in root_agent.run_async(inv_ctx):
                        yield event

                agent_gen = run_agent()

                while True:
                    # Create tasks for the next event and the disconnect check
                    # Note: __anext__() returns a coroutine that we wrap in a task
                    next_event = asyncio.create_task(agent_gen.__anext__())
                    disconnect_check = asyncio.create_task(
                        raw_request.is_disconnected()
                    )

                    done, pending = await asyncio.wait(
                        [next_event, disconnect_check],
                        return_when=asyncio.FIRST_COMPLETED,
                    )

                    # Cancel whichever is still pending (important to drive CancelledError into the agent)
                    for task in pending:
                        task.cancel()

                    if disconnect_check in done and disconnect_check.result():
                        logger.info("❌ Client disconnected, cancelling agent run")
                        break

                    if next_event in done:
                        try:
                            event = next_event.result()
                            logger.debug(f"📥 Received event from agent: {event}")

                            # Persist generated event
                            await session_manager.session_service.append_event(
                                active_session, event
                            )

                            # Extract content and parts robustly
                            content = getattr(event, "content", None)
                            if not content:
                                continue

                            parts = []
                            if hasattr(content, "parts"):
                                parts = content.parts
                            elif isinstance(content, dict):
                                parts = content.get("parts", [])

                            if not parts:
                                continue

                            for part in parts:
                                # 1. Handle Text
                                text = None
                                if hasattr(part, "text"):
                                    text = part.text
                                elif isinstance(part, dict):
                                    text = part.get("text")

                                if text:
                                    logger.info(
                                        f"📤 Yielding text part: {text[:50]}..."
                                    )
                                    yield (
                                        json.dumps({"type": "text", "content": text})
                                        + "\n"
                                    )

                                # 2. Handle Tool Calls
                                fc = None
                                if hasattr(part, "function_call"):
                                    fc = part.function_call
                                elif isinstance(part, dict):
                                    fc = part.get("function_call")

                                if fc:
                                    tool_name = getattr(fc, "name", None) or (
                                        isinstance(fc, dict) and fc.get("name")
                                    )
                                    if not tool_name:
                                        continue

                                    tool_args_raw = getattr(fc, "args", None) or (
                                        isinstance(fc, dict) and fc.get("args")
                                    )
                                    tool_args = normalize_tool_args(tool_args_raw)

                                    logger.info(f"🛠️ Tool Call: {tool_name}")
                                    _, events = create_tool_call_events(
                                        tool_name, tool_args, pending_tool_calls
                                    )
                                    for evt_str in events:
                                        yield evt_str + "\n"

                                # 3. Handle Tool Responses
                                fr = None
                                if hasattr(part, "function_response"):
                                    fr = part.function_response
                                elif isinstance(part, dict):
                                    fr = part.get("function_response")

                                if fr:
                                    tool_name = getattr(fr, "name", None) or (
                                        isinstance(fr, dict) and fr.get("name")
                                    )
                                    if not tool_name:
                                        continue

                                    result = getattr(fr, "response", None) or (
                                        isinstance(fr, dict) and fr.get("response")
                                    )
                                    logger.info(f"✅ Tool Response: {tool_name}")

                                    # 1. Update tool log (generic)
                                    _, events = create_tool_response_events(
                                        tool_name, result, pending_tool_calls
                                    )
                                    for evt_str in events:
                                        yield evt_str + "\n"

                                    # 2. Widget visualization
                                    widget_events = create_widget_events(
                                        tool_name, result
                                    )
                                    for evt_str in widget_events:
                                        yield evt_str + "\n"

                        except StopAsyncIteration:
                            break
                        except Exception as e:
                            # Propagate other exceptions
                            raise e

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

        return StreamingResponse(event_generator(), media_type="application/x-ndjson")

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
