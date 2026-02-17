from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools import google_search_tool
from google.adk.tools.google_search_agent_tool import GoogleSearchAgentTool

from sre_agent.model_config import get_model_name


def get_research_agent() -> LlmAgent:
    """Returns an LlmAgent that only uses the google_search tool.

    This agent is designed to be wrapped by GoogleSearchAgentTool to bypass the
    ADK limitation of google_search needing to be the sole tool in an agent.
    """
    # Use gemini-2.0-flash by default as recommended for best grounding speed/quality
    model_name = get_model_name("fast")

    return LlmAgent(
        name="research",
        model=model_name,
        description="A specialized sub-agent for conducting internet research using Google Search.",
        instruction=(
            "You are a specialized research agent. Use the `google_search` tool "
            "to find up-to-date and relevant information to answer the user's queries. "
            "Always cite your sources and provide a concise, grounded answer."
        ),
        tools=[google_search_tool.google_search],
    )


def get_research_agent_tool() -> GoogleSearchAgentTool:
    """Returns a tool that wraps the research LlmAgent.

    This allows the main SRE Agent to perform Google Searches.
    """
    agent = get_research_agent()
    return GoogleSearchAgentTool(agent=agent)
