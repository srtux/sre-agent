import asyncio
import os
import time
import uuid
from dataclasses import dataclass

from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.run_config import RunConfig
from google.adk.events import Event
from google.genai.types import Content, Part

from sre_agent.agent import root_agent
from sre_agent.services import get_session_service


@dataclass
class SessionInfo:
    """Dataclass to store session information."""

    id: str


class AgentMessage:
    """Class representing a message in the agent conversation."""

    def __init__(self, role, text):
        """Initialize the agent message."""
        self.role = role
        self.text = text


class AgentRequest:
    """Class representing a request to the agent."""

    def __init__(self, messages, session_id=None, project_id=None):
        """Initialize the agent request."""
        self.messages = messages
        self.session_id = session_id
        self.project_id = project_id


async def run_chat_turn(session_id, text):
    """Run a single chat turn with the agent."""
    session_manager = get_session_service()
    session = await session_manager.get_session(session_id)
    if not session:
        print(f"Session {session_id} not found")
        return None

    user_content = Content(parts=[Part(text=text)], role="user")

    inv_ctx = InvocationContext(
        session=session,
        agent=root_agent,
        invocation_id=uuid.uuid4().hex,
        session_service=session_manager.session_service,
        run_config=RunConfig(),
    )
    inv_ctx.user_content = user_content

    # Persist User Message
    user_event = Event(
        invocation_id=inv_ctx.invocation_id,
        author="default",
        content=user_content,
        timestamp=time.time(),
    )
    await session_manager.session_service.append_event(session, user_event)

    response_text = ""
    print(f"Server processing user input: '{text}'")

    # Simulate server.py loop
    event_count_before = len(session.events) if session.events else 0
    print(f"Events before: {event_count_before}")
    if session.events:
        for i, e in enumerate(session.events):
            print(f"  Event {i}: author={e.author}, content={e.content}")

    async for event in root_agent.run_async(inv_ctx):
        # Persist generated event
        await session_manager.session_service.append_event(session, event)

        if hasattr(event, "content") and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    response_text += part.text

    # Reload session from DB to check persistence
    reloaded_session = await session_manager.get_session(session_id)
    event_count_after = len(reloaded_session.events) if reloaded_session.events else 0
    print(f"Events after from DB: {event_count_after}")

    return response_text


async def main():
    """Run the main reproduction script."""
    # Setup environment
    os.environ["USE_DATABASE_SESSIONS"] = "true"
    os.environ["SESSION_DB_PATH"] = "repro_test.db"

    # Ensure fresh DB
    if os.path.exists("repro_test.db"):
        os.remove("repro_test.db")

    # 1. Create Session
    session_manager = get_session_service()

    session = await session_manager.create_session(user_id="default")
    session_id = session.id
    print(f"Created session: {session_id}")

    # TEST MANUAL PERSISTENCE
    test_event = Event(
        invocation_id="test-inv",
        author="user",
        content=Content(parts=[Part(text="Manual Persistence Test")], role="user"),
        timestamp=time.time(),
    )
    await session_manager.session_service.append_event(session, test_event)
    print("Appended manual event.")

    # Check immediate persistence
    s2 = await session_manager.get_session(session_id)
    print(f"Events after manual append: {len(s2.events) if s2.events else 0}")

    # 2. Turn 1
    response1 = await run_chat_turn(session_id, "Hello, my name is James Bond.")
    print(f"Response 1: {response1[:50]}...")

    # 3. Turn 2
    response2 = await run_chat_turn(session_id, "What is my name?")
    print(f"Response 2: {response2}")

    # Check if context was preserved
    if "Bond" in response2 or "James" in response2:
        print("✅ SUCCESS: Context preserved.")
    else:
        print("❌ FAILURE: Context lost.")


if __name__ == "__main__":
    asyncio.run(main())
