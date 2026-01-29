"""Test script for LangSmith integration."""

import os

from dotenv import load_dotenv


def test_langsmith_connection():
    """Verify LangSmith environment variables."""
    load_dotenv()

    # Support both LANGCHAIN and LANGSMITH prefixes
    tracing_v2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    tracing_smith = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
    tracing = tracing_v2 or tracing_smith

    api_key = os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")
    project = (
        os.getenv("LANGCHAIN_PROJECT") or os.getenv("LANGSMITH_PROJECT") or "default"
    )

    print(f"LangSmith Tracing: {'Enabled' if tracing else 'Disabled'}")
    print(f"Project: {project}")

    if tracing and not api_key:
        print("⚠️ Warning: Tracing is enabled but API KEY is missing.")
    elif tracing and api_key:
        print("✅ LangSmith configuration found.")
    else:
        print(
            "💡 To enable LangSmith, set LANGSMITH_TRACING=true and LANGSMITH_API_KEY."
        )


if __name__ == "__main__":
    test_langsmith_connection()
