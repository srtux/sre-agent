import logging
import os

from dotenv import load_dotenv

# Initialize telemetry and environment before anything else
load_dotenv()

from sre_agent.api import create_app  # noqa: E402

# Set log level
os.environ["LOG_LEVEL"] = os.getenv("LOG_LEVEL", "DEBUG")
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create the modular FastAPI application
# This includes all routers (health, agent, tools, sessions) refactored from the monolithic version
app = create_app(title="SRE Agent Toolbox API", include_adk_routes=True)

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"🚀 Starting SRE Agent API on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
