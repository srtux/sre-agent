"""SRE Agent API routers module."""

from .agent import router as agent_router
from .health import router as health_router
from .permissions import router as permissions_router
from .preferences import router as preferences_router
from .sessions import router as sessions_router
from .tools import router as tools_router

__all__ = [
    "agent_router",
    "health_router",
    "permissions_router",
    "preferences_router",
    "sessions_router",
    "tools_router",
]
