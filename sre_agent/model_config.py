"""Model configuration for SRE Agent.

Handles dynamic model selection based on environment (Local vs Agent Engine).
Includes OPT-10: Vertex AI context caching configuration.
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Environment variable to detect Agent Engine
AGENT_ENGINE_ENV_VAR = "RUNNING_IN_AGENT_ENGINE"

# OPT-10: Context caching configuration
# When enabled, static system prompt prefixes are cached at 75% cost reduction.
# Set SRE_AGENT_CONTEXT_CACHING=true to enable.
CONTEXT_CACHING_ENV_VAR = "SRE_AGENT_CONTEXT_CACHING"

# Default TTL for cached context (in seconds). 1 hour covers most investigations.
_DEFAULT_CACHE_TTL_SECONDS = 3600


def get_model_name(capability: str = "fast") -> str:
    """Get the appropriate model name based on environment and capability.

    Args:
        capability: "fast" (for simple tasks) or "deep" (for reasoning/analysis).

    Returns:
        Model name string.
    """
    is_agent_engine = os.environ.get(AGENT_ENGINE_ENV_VAR, "false").lower() == "true"

    if is_agent_engine:
        # Agent Engine (Cloud) Configuration - Using stable 2.5 models
        if capability == "fast":
            model = "gemini-2.5-flash"
        else:
            model = "gemini-2.5-pro"
        logger.info(f"Using Agent Engine model ({capability}): {model}")
        return model
    else:
        # Local Development Configuration - Consistent with cloud 2.5 models
        if capability == "fast":
            model = "gemini-2.5-flash"
        else:
            model = "gemini-2.5-pro"
        logger.info(f"Using Local model ({capability}): {model}")
        return model


def is_context_caching_enabled() -> bool:
    """Check if Vertex AI context caching is enabled.

    Context caching stores static system prompt prefixes on the server,
    reducing input token costs by up to 75% for repeated calls.

    Enable via: SRE_AGENT_CONTEXT_CACHING=true

    Returns:
        True if context caching is enabled.
    """
    return os.environ.get(CONTEXT_CACHING_ENV_VAR, "false").lower() == "true"


def get_context_cache_config() -> dict[str, Any] | None:
    """Get context caching configuration for Vertex AI.

    Returns configuration suitable for passing to the Vertex AI
    GenerativeModel or ADK model configuration. When caching is disabled,
    returns None.

    The cached content should include the static portions of the system
    prompt (everything except dynamic elements like timestamps). This
    avoids re-processing ~1,000+ tokens of system instructions on every turn.

    Usage with Vertex AI SDK::

        config = get_context_cache_config()
        if config:
            from vertexai.caching import CachedContent
            cached = CachedContent.create(
                model_name=get_model_name("fast"),
                system_instruction=config["system_instruction"],
                ttl=config["ttl_seconds"],
            )
            # Use cached.resource_name in subsequent model calls

    Returns:
        Dict with caching configuration, or None if disabled.
    """
    if not is_context_caching_enabled():
        return None

    ttl = int(
        os.environ.get("SRE_AGENT_CONTEXT_CACHE_TTL", str(_DEFAULT_CACHE_TTL_SECONDS))
    )

    return {
        "enabled": True,
        "ttl_seconds": ttl,
        # The caller should set system_instruction to the static prompt prefix.
        # Dynamic elements (timestamps, session-specific context) must be excluded.
        "system_instruction": None,  # Set by caller
    }
