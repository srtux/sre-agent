from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from google.adk.events import Event
from google.genai.types import Content, Part

from server import app

# We import root_agent to patch it
from sre_agent.agent import root_agent


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.asyncio
async def test_chat_endpoint_persists_user_role(client):
    """Test that the /agent endpoint handles user messages with the correct role."""

    # 1. Define Mock for root_agent.run_async
    async def mock_run_async(*args, **kwargs):
        # Yield a dummy response event
        yield Event(
            author="sre_agent",
            content=Content(parts=[Part(text="Hello from mock agent")]),
            role="model",
        )

    # 2. Patch root_agent.run_async using object.__setattr__ to bypass Pydantic validation
    original_run_async = root_agent.run_async
    object.__setattr__(root_agent, "run_async", mock_run_async)

    try:
        # 3. Environment patch for session service
        with patch.dict(
            "os.environ", {"USE_DATABASE_SESSIONS": "false", "SRE_AGENT_ID": ""}
        ):
            # Reset singleton to ensure we use InMemorySessionService
            from sre_agent.services import session as session_module

            session_module._session_manager = None

            # Send a request
            response = client.post(
                "/api/genui/chat",
                json={
                    "messages": [{"role": "user", "text": "Hello persistence"}],
                    "session_id": None,
                },
            )

            assert response.status_code == 200

            # Parse response to get session_id
            # The response is NDJSON
            lines = response.text.strip().split("\n")
            first_line = next(filter(None, lines))
            import json

            session_data = json.loads(first_line)
            assert session_data["type"] == "session"
            session_id = session_data["session_id"]

            # 4. Verify Persistence
            # Get the session service singleton
            session_manager = session_module.get_session_service()
            session = await session_manager.get_session(session_id, user_id="default")

            assert session is not None
            # Check user role persistence
            user_events = [e for e in session.events if e.author == "user"]
            assert len(user_events) > 0, "No user events found in session"

            user_event = user_events[0]
            # This is the critical check
            assert user_event.content.role == "user", (
                "User role was not persisted correctly"
            )
            assert user_event.content.parts[0].text == "Hello persistence"

    finally:
        # Restore original method
        object.__setattr__(root_agent, "run_async", original_run_async)
