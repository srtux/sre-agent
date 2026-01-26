# Tech Stack

The project uses a modern, high-performance stack for both AI orchestration and user interaction.

## Backend (Python)
- **Framework**: FastAPI for the web server.
- **Agent Framework**: Google **Agent Development Kit (ADK)**.
- **Data Validation**: **Pydantic 2.x** (with strict settings).
- **LLM**: Gemini 2x Models.
- **Infrastructure**: SQLite (Local), Firestore (Cloud), GCP SDKs.
- **Testing**: Pytest with 80%+ coverage requirements.
- **Linting/Formatting**: Ruff (replaces Black/Isort/Flake8), MyPy (Strict).

## Frontend (Flutter)
- **Framework**: Flutter Web.
- **Protocol**: GenUI (Generative UI) / A2UI.
- **State Management**: Provider.
- **Visuals**: Deep space theme, glassmorphism, modern typography.

## Deployment & Ops
- **Containerization**: Docker.
- **Orchestration**: Managed via `poe` (task runner) and `uv` (dependency management).
- **Environment**: Supports Local and Remote execution modes.
