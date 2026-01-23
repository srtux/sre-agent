# API Module

This directory contains the modular FastAPI routers refactored from the monolithic `server.py`.

## Structure

- `app.py` - Main FastAPI application factory
- `middleware.py` - Auth and CORS middleware
- `dependencies.py` - Shared dependencies
- `routers/` - Route modules
  - `health.py` - Health and debug endpoints
  - `agent.py` - Chat agent endpoint
  - `tools.py` - Tool configuration and testing endpoints
  - `sessions.py` - Session management endpoints
  - `preferences.py` - User preferences endpoints
  - `permissions.py` - Project permission endpoints
  - `genui.py` - GenUI/A2UI protocol endpoints
