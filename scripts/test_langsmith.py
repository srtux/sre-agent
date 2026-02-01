"""Test script for LangSmith advanced features with Google ADK.

This script demonstrates:
1. Thread grouping (multiple traces in one conversation)
2. User tracking
3. Custom metadata and tags
4. User feedback

Usage:
    LANGSMITH_TRACING=true uv run python scripts/test_langsmith.py
"""

import asyncio
import os
import sys
import uuid

# Add project root to path for direct python execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv


def validate_config() -> bool:
    """Verify LangSmith environment variables are set correctly."""
    load_dotenv()

    api_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
    project = os.getenv("LANGSMITH_PROJECT", "sre-agent")
    tracing = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"

    print("=" * 60)
    print("LangSmith Configuration Check")
    print("=" * 60)
    print(f"  LANGSMITH_TRACING:    {'✅ Enabled' if tracing else '❌ Disabled'}")
    print(f"  LANGSMITH_API_KEY:    {'✅ Set' if api_key else '❌ Missing'}")
    print(f"  LANGSMITH_PROJECT:    {project}")
    print("=" * 60)

    if not tracing:
        print("\n💡 To enable tracing, set: LANGSMITH_TRACING=true")
        return False

    if not api_key:
        print("\n❌ Error: LANGSMITH_API_KEY is required when tracing is enabled.")
        return False

    print("\n✅ Configuration looks good!")
    return True


async def test_thread_grouping() -> None:
    """Demonstrate thread grouping - multiple traces in one conversation."""
    print("\n" + "=" * 60)
    print("🧵 Testing Thread Grouping (Conversation Threads)")
    print("=" * 60)

    # Setup LangSmith tracing
    from langsmith.integrations.otel import configure
    from openinference.instrumentation.google_adk import GoogleADKInstrumentor

    project = os.getenv("LANGSMITH_PROJECT", "sre-agent")
    configure(project_name=project)
    GoogleADKInstrumentor().instrument()

    # Import our utilities
    # Create ADK agent and runner
    from google.adk import Runner
    from google.adk.agents import LlmAgent
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    from sre_agent.tools.common.telemetry import (
        add_langsmith_tags,
        set_langsmith_metadata,
        set_langsmith_session,
        set_langsmith_user,
    )

    agent = LlmAgent(
        name="langsmith_thread_test",
        model="gemini-2.5-flash",
        instruction="You are a helpful SRE assistant. Keep responses brief (1-2 sentences max).",
    )

    session_service = InMemorySessionService()  # type: ignore[no-untyped-call]
    runner = Runner(
        app_name="langsmith_test",
        agent=agent,
        session_service=session_service,
    )

    # Create a unique session ID for this conversation thread
    thread_id = f"thread_{uuid.uuid4().hex[:8]}"
    user_id = "test_user"
    session_id = "test_session"

    await session_service.create_session(
        app_name="langsmith_test",
        user_id=user_id,
        session_id=session_id,
    )

    print(f"\n📌 Thread ID: {thread_id}")
    print("   All messages in this test will be grouped under this thread.\n")

    # Set LangSmith context for thread grouping
    set_langsmith_session(thread_id)
    set_langsmith_user("demo@example.com")
    set_langsmith_metadata(
        {
            "environment": "development",
            "test_type": "thread_demo",
        }
    )
    add_langsmith_tags(["demo", "thread-test"])

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

    print("✅ Thread demo complete!")
    print("   View at LangSmith → Threads tab")
    print(f"   Filter by: session_id = {thread_id}")


def show_online_evaluation_guide() -> None:
    """Show how to set up for online evaluations."""
    print("\n" + "=" * 60)
    print("📊 Online Evaluation Setup Guide")
    print("=" * 60)

    print("""
LangSmith supports these ONLINE evaluation types:

1. **LLM-as-Judge**
   - Automatically evaluate production traces with an LLM
   - Pre-built evaluators: Correctness, Helpfulness, Harmfulness
   - Custom prompts for domain-specific evaluation

2. **Code Evaluators**
   - Run custom Python code on each trace
   - Check for regex patterns, length limits, format validation

3. **Composite Evaluators**
   - Combine multiple evaluators into one score
   - Weighted averages or custom aggregation

🔧 To set up Online Evaluations:

1. Go to your LangSmith project
2. Click "Rules" → "Add Rule"
3. Choose "Online Evaluator"
4. Configure:
   - Filter: Which traces to evaluate (e.g., by tag, metadata)
   - Sampling: % of traces to evaluate (start with 10%)
   - Evaluator: LLM-as-Judge or Code
5. Save and monitor results in the dashboard

📝 Example filter (to only evaluate SRE-related traces):
   has(tags, "production") AND metadata.agent_name = "sre_agent"
""")

    # Show how to send feedback programmatically
    print("💬 Sending User Feedback Programmatically:")
    print("-" * 40)

    print("""
# Example: After user clicks thumbs up/down
from sre_agent.tools.common.telemetry import send_langsmith_feedback

send_langsmith_feedback(
    run_id="<langsmith-run-id>",  # From trace
    key="user_rating",
    value="thumbs_up",  # or "thumbs_down"
    comment="Very helpful analysis!",
)
""")


def main() -> None:
    """Run all LangSmith feature demos."""
    if not validate_config():
        print("\n⚠️  Fix configuration issues above and try again.")
        return

    print("\n" + "=" * 60)
    print("🚀 LangSmith Advanced Features Demo")
    print("=" * 60)

    # Run thread grouping demo
    asyncio.run(test_thread_grouping())

    # Show online evaluation setup
    show_online_evaluation_guide()

    print("\n" + "=" * 60)
    print("✨ Demo Complete!")
    print("=" * 60)
    print("""
📚 Next Steps:

1. **View Threads**: Go to LangSmith → Threads tab
   - See all conversation turns grouped together

2. **Set Up Online Evaluations**:
   - Go to LangSmith → Rules → Add Rule
   - Configure LLM-as-Judge or Code evaluators

3. **Explore Polly (AI Assistant)**:
   - Ask "Why did this trace fail?"

🔗 Dashboard: https://smith.langchain.com/
📖 Docs: https://docs.langchain.com/langsmith/
""")


if __name__ == "__main__":
    main()
