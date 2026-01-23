"""Model configuration for SRE Agent.

Handles dynamic model selection based on environment (Local vs Agent Engine).
"""

import logging
import os

logger = logging.getLogger(__name__)

# Environment variable to detect Agent Engine
AGENT_ENGINE_ENV_VAR = "RUNNING_IN_AGENT_ENGINE"


def get_model_name(capability: str = "fast") -> str:
    """Get the appropriate model name based on environment and capability.

    Args:
        capability: "fast" (for simple tasks) or "deep" (for reasoning/analysis).

    Returns:
        Model name string.
    """
    is_agent_engine = os.environ.get(AGENT_ENGINE_ENV_VAR, "false").lower() == "true"

    if is_agent_engine:
        # Agent Engine (Cloud) Configuration
        # User requested: gemini-2.5-flash and gemini-2.5-pro
        if capability == "fast":
            model = "gemini-2.5-flash"
        else:
            model = "gemini-2.5-pro"
        logger.info(f"Using Agent Engine model ({capability}): {model}")
        return model
    else:
        # Local Development Configuration
        # User requested: gemini-3-flash-preview and gemini-3-pro-preview
        if capability == "fast":
            model = "gemini-3-flash-preview"
        else:
            model = "gemini-3-pro-preview"
        logger.info(f"Using Local model ({capability}): {model}")
        return model
