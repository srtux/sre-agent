"""Test script for Langfuse tracing with Google ADK.

This script demonstrates:
1. Session grouping (multiple traces in one conversation)
2. User tracking
3. Custom metadata and tags
4. User feedback / scores

Usage:
    LANGFUSE_TRACING=true uv run python scripts/test_langfuse.py
"""

import asyncio
import os
import sys
import uuid

# Add project root to path for direct python execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv


def validate_config() -> bool:
    """Verify Langfuse environment variables are set correctly."""
    load_dotenv()

    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
    tracing = os.getenv("LANGFUSE_TRACING", "false").lower() == "true"

    print("=" * 60)
    print("Langfuse Configuration Check")
    print("=" * 60)
    print(f"  LANGFUSE_TRACING:      {'✅ Enabled' if tracing else '❌ Disabled'}")
    print(f"  LANGFUSE_PUBLIC_KEY:   {'✅ Set' if public_key else '❌ Missing'}")
    print(f"  LANGFUSE_SECRET_KEY:   {'✅ Set' if secret_key else '❌ Missing'}")
    print(f"  LANGFUSE_HOST:         {host}")
    print("=" * 60)

    if not tracing:
        print("\n💡 To enable tracing, set: LANGFUSE_TRACING=true")
        return False

    if not public_key or not secret_key:
        print("\n❌ Error: LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are required.")
        return False

    print("\n✅ Configuration looks good!")
    return True


async def test_session_grouping() -> None:
    """Demonstrate session grouping - multiple traces in one conversation."""
    print("\n" + "=" * 60)
    print("🧵 Testing Session Grouping (Conversation Sessions)")
    print("=" * 60)

    # Import our utilities
    from google.adk import Runner
    from google.adk.agents import LlmAgent
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    from sre_agent.tools.common.telemetry import (
        add_langfuse_tags,
        set_langfuse_metadata,
        set_langfuse_session,
        set_langfuse_user,
    )

    agent = LlmAgent(
        name="langfuse_session_test",
        model="gemini-2.5-flash",
        instruction="You are a helpful SRE assistant. Keep responses brief (1-2 sentences max).",
    )

    session_service = InMemorySessionService()  # type: ignore[no-untyped-call]
    runner = Runner(
        app_name="langfuse_test",
        agent=agent,
        session_service=session_service,
    )

    # Create a unique session ID for this conversation
    thread_id = f"session_{uuid.uuid4().hex[:8]}"
    user_id = "test_user"
    session_id = "test_session"

    await session_service.create_session(
        app_name="langfuse_test",
        user_id=user_id,
        session_id=session_id,
    )

    print(f"\n📌 Session ID: {thread_id}")
    print("   All messages in this test will be grouped under this session.\n")

    # Set Langfuse context for session grouping
    set_langfuse_session(thread_id)
    set_langfuse_user("demo@example.com")
    set_langfuse_metadata(
        {
            "environment": "development",
            "test_type": "session_demo",
        }
    )
    add_langfuse_tags(["demo", "session-test"])

    # Simulate a multi-turn conversation
    messages = [
        "Hi! I'm investigating a latency issue.",
        "It started 2 hours ago.",
        "Thanks for the help!",
    ]

    for i, msg in enumerate(messages, 1):
        print(f"   Turn {i}: {msg}")

        content = types.Content(
            parts=[types.Part(text=msg)],
            role="user",
        )

        events = runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        )

        response = ""
        for event in events:
            if hasattr(event, "content") and event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        response = part.text
                        break

        print(
            f"   Agent: {response[:80]}..."
            if len(response) > 80
            else f"   Agent: {response}"
        )
        print()

    print("✅ Session demo complete!")
    print("   View at Langfuse → Sessions tab")
    print(f"   Filter by: session_id = {thread_id}")


def show_evaluation_guide() -> None:
    """Show how to set up evaluations in Langfuse."""
    print("\n" + "=" * 60)
    print("📊 Langfuse Evaluation Setup Guide")
    print("=" * 60)

    print("""
Langfuse supports these evaluation types:

1. **LLM-as-Judge**
   - Automatically evaluate production traces with an LLM
   - Custom prompts for domain-specific evaluation

2. **Manual Scores**
   - Send scores programmatically from your app
   - Track user feedback (thumbs up/down, ratings)

3. **Custom Evaluators**
   - Run custom Python code on traces via the SDK
   - Check for regex patterns, length limits, format validation

🔧 To set up Evaluations:

1. Go to your Langfuse dashboard
2. Navigate to Scores / Evaluations
3. Configure evaluators for your traces
4. Monitor results in the dashboard
""")

    # Show how to send scores programmatically
    print("💬 Sending Scores Programmatically:")
    print("-" * 40)

    print("""
# Example: After user clicks thumbs up/down
from sre_agent.tools.common.telemetry import send_langfuse_score

send_langfuse_score(
    trace_id="<trace-id>",  # From trace
    name="user_rating",
    value=1.0,  # or 0.0 for thumbs_down
    comment="Very helpful analysis!",
)
""")


def main() -> None:
    """Run all Langfuse feature demos."""
    if not validate_config():
        print("\n⚠️  Fix configuration issues above and try again.")
        return

    print("\n" + "=" * 60)
    print("🚀 Langfuse Tracing Demo")
    print("=" * 60)

    # Run session grouping demo
    asyncio.run(test_session_grouping())

    # Show evaluation setup
    show_evaluation_guide()

    print("\n" + "=" * 60)
    print("✨ Demo Complete!")
    print("=" * 60)
    print("""
📚 Next Steps:

1. **View Sessions**: Go to Langfuse → Sessions tab
   - See all conversation turns grouped together

2. **Set Up Evaluations**:
   - Go to Langfuse → Scores / Evaluations
   - Configure LLM-as-Judge or custom evaluators

3. **Explore Dashboard**:
   - View traces, latency, cost, and quality metrics

🔗 Dashboard: http://localhost:3000/ (self-hosted)
📖 Docs: https://langfuse.com/docs
""")


if __name__ == "__main__":
    main()
