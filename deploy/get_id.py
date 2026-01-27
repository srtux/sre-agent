import logging
import os
import sys

import vertexai
from dotenv import load_dotenv
from vertexai import agent_engines

# Suppress logging
logging.getLogger().setLevel(logging.ERROR)


def main():
    load_dotenv()
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.environ.get("PROJECT_ID")
    location = (
        os.getenv("AGENT_ENGINE_LOCATION")
        or os.getenv("GOOGLE_CLOUD_LOCATION")
        or "us-central1"
    )

    if not project_id:
        sys.stderr.write("Missing GOOGLE_CLOUD_PROJECT\n")
        sys.exit(1)

    # Initialize Vertex AI
    vertexai.init(project=project_id, location=location)

    display_name = "sre_agent"  # Default name

    try:
        # List all agents
        agents = agent_engines.list()
        for agent in agents:
            if agent.display_name == display_name:
                print(agent.resource_name)
                sys.exit(0)

        sys.stderr.write(f"Agent '{display_name}' not found.\n")
        sys.exit(1)

    except Exception as e:
        sys.stderr.write(f"Error listing agents: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
