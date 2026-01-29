"""Test script for LangSmith integration."""

import os

from dotenv import load_dotenv


def test_langsmith_connection():
    """Verify LangSmith environment variables."""
    load_dotenv()

    tracing = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    api_key = os.getenv("LANGCHAIN_API_KEY")
    project = os.getenv("LANGCHAIN_PROJECT", "default")

    print(f"LangSmith Tracing: {'Enabled' if tracing else 'Disabled'}")
    print(f"Project: {project}")

    if tracing and not api_key:
        print(
            "⚠️ Warning: LANGCHAIN_TRACING_V2 is enabled but LANGCHAIN_API_KEY is missing."
        )
    elif tracing and api_key:
        print("✅ LangSmith configuration found.")
    else:
        print(
            "💡 To enable LangSmith, set LANGCHAIN_TRACING_V2=true and LANGCHAIN_API_KEY."
        )


if __name__ == "__main__":
    test_langsmith_connection()
