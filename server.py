import logging
import os

from dotenv import load_dotenv

# Initialize environment before anything else
load_dotenv()

# Telemetry is initialized inside create_app() — no need to duplicate here.
# Previously, setup_telemetry() was called both here and in create_app(),
# doubling the initialization overhead per worker process.

from sre_agent.api import create_app  # noqa: E402

# 0. SET LOG LEVEL EARLY
os.environ["LOG_LEVEL"] = os.getenv("LOG_LEVEL", "DEBUG")
logger = logging.getLogger(__name__)

# Create the modular FastAPI application
# This includes all routers (health, agent, tools, sessions) refactored from the monolithic version
# Telemetry, MCP patches, and Vertex AI initialization are handled inside create_app
app = create_app(title="SRE Agent Toolbox API", include_adk_routes=True)

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8001"))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"🚀 Starting SRE Agent API on {host}:{port}")

    # Identify and silence the Uvicorn access logger for health checks
    # This filter sits "above" the handler and drops records before they are emitted
    class HealthCheckFilter(logging.Filter):
        """Filter out health check requests from access logs."""

        def filter(self, record: logging.LogRecord) -> bool:
            """Filter record."""
            return record.getMessage().find("GET /health") == -1

    # Get the uvicorn access logger (it's created by uvicorn.run, but we can pre-configure it)
    logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())

    # We rely on our own setup_telemetry() for formatting, so we pass log_config=None
    # However, Uvicorn will still create 'uvicorn' and 'uvicorn.access' loggers.
    # By passing log_config=None, Uvicorn won't overwrite our root logger configuration.
    # Each worker forks a full copy of the Python process (~250-350 MB with
    # GCP SDKs, ADK, OTel, etc.).  Match workers to allocated CPUs.
    # Cloud Run deploy allocates 4 CPUs / 16Gi — 4 workers fits comfortably.
    workers = int(os.getenv("WEB_CONCURRENCY", "4"))
    uvicorn.run("server:app", host=host, port=port, log_config=None, workers=workers)
