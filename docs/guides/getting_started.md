# Getting Started with Auto SRE

This guide covers the prerequisites, installation, and configuration required to run the Auto SRE Agent.

## Prerequisites

### Required

*   **Python**: 3.10 or higher, but less than 3.13 (i.e., 3.10, 3.11, or 3.12).
*   **uv**: Python package manager. Install from [astral.sh/uv](https://astral.sh/uv).
*   **Google Cloud SDK**: Installed and configured (`gcloud auth login`, `gcloud auth application-default login`).
*   **GCP Project**: Access to a project with Cloud Trace, Cloud Logging, and Cloud Monitoring enabled.

### Required for Frontend

*   **Flutter SDK**: Dart SDK 3.10.7 or higher. Install from [flutter.dev](https://flutter.dev/docs/get-started/install).
*   **Chrome**: Required for Flutter Web development (`flutter run -d chrome`).

### Optional

*   **Docker**: For containerized deployments (GKE, Cloud Run).
*   **pre-commit**: Installed automatically as a dev dependency, but the hooks need to be set up (see [Development Guide](development.md)).

## Installation

We use `uv` for Python dependency management and Flutter `pub` for Dart dependencies.

```bash
# 1. Clone the repository
git clone <repo-url> && cd sre-agent

# 2. Install all dependencies (Python + Flutter)
uv run poe sync

# 3. Configure environment
cp .env.example .env
```

> [!NOTE]
> `uv run poe sync` runs two steps internally: `uv sync` (Python dependencies) and `flutter pub get` in the `autosre/` directory (Dart dependencies). If you only need the backend, you can run `uv sync` directly.

## Configuration

Edit your `.env` file with the following required variables. See `.env.example` for the full template with comments, or `docs/reference/configuration.md` for detailed documentation.

### Required Settings

```bash
# Google Cloud Vertex AI
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=your-gcp-project
GOOGLE_CLOUD_LOCATION=us-central1

# Google OAuth Client ID (for Frontend sign-in)
# Create at: GCP Console > APIs & Services > Credentials > OAuth 2.0 Client IDs
GOOGLE_CLIENT_ID=your-oauth-client-id.apps.googleusercontent.com

# AES-256 Fernet key for encrypting session tokens
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
SRE_AGENT_ENCRYPTION_KEY=your-secure-encryption-key

# Gemini API key (required if not using ADC/Service Account)
GEMINI_API_KEY=your-gemini-api-key
```

### Alternative: Google AI Studio (Non-Vertex)

If you prefer a simpler setup without Vertex AI, use Google AI Studio instead:

```bash
GOOGLE_GENAI_USE_VERTEXAI=0
GOOGLE_API_KEY=your-google-gemini-api-key
```

### Optional Settings

```bash
# Enable Remote Agent Engine (Production Mode)
# SRE_AGENT_ID=projects/xxx/locations/xxx/reasoningEngines/xxx

# Strict End-User Credential Enforcement (blocks ADC fallback)
STRICT_EUC_ENFORCEMENT=false

# Policy enforcement for tool calls
SRE_AGENT_ENFORCE_POLICY=true

# Disable auth for local development (injects dummy credentials)
# ENABLE_AUTH=false

# Allow all CORS origins (development only)
# CORS_ALLOW_ALL=true

# Council of Experts architecture (parallel specialist panels)
# SRE_AGENT_COUNCIL_ORCHESTRATOR=true

# Reduce root agent to ~20 tools (default: true)
# SRE_AGENT_SLIM_TOOLS=true

# Max token budget per session (0 = unlimited)
# SRE_AGENT_TOKEN_BUDGET=0

# Enable Vertex AI context caching
# SRE_AGENT_CONTEXT_CACHING=false

# Sandbox local execution mode
# SRE_AGENT_LOCAL_EXECUTION=false

# Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Server host and port
PORT=8001
HOST=0.0.0.0
```

### Telemetry Settings

```bash
# Export spans to Google Cloud Trace
# OTEL_TO_CLOUD=true

# Capture full prompt/response content in traces (verbose, development only)
# OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true

# Disable all telemetry (useful in tests)
# DISABLE_TELEMETRY=true
```

### External Integrations

```bash
# Langfuse tracing (local agentic debugging)
# LANGFUSE_TRACING=false
# LANGFUSE_PUBLIC_KEY=your-key
# LANGFUSE_SECRET_KEY=your-key
# LANGFUSE_HOST=http://localhost:3000

# Google Custom Search (for online research tool)
# GOOGLE_CUSTOM_SEARCH_API_KEY=your-key
# GOOGLE_CUSTOM_SEARCH_ENGINE_ID=your-engine-id

# GitHub integration (source code access and PR creation)
# GITHUB_TOKEN=your-github-pat
# GITHUB_REPO=owner/repo
```

## Running the Application

### Full Stack (Backend + Frontend)

Run the entire stack locally with a single command:

```bash
uv run poe dev
```

This starts:
*   **Backend** (FastAPI): `http://localhost:8001`
*   **Frontend** (Flutter Web in Chrome): `http://localhost:8080`

> [!TIP]
> To see agent logic traces in Google Cloud Trace while developing locally, set `OTEL_TO_CLOUD=true` and `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true` in your `.env`.

### Backend Only

```bash
uv run poe web
```

Starts the FastAPI server on `http://localhost:8001` (configurable via `PORT` and `HOST` env vars).

### Frontend Only

```bash
cd autosre && flutter run -d chrome --web-hostname localhost --web-port 8080
```

> [!NOTE]
> Pass `--dart-define=GOOGLE_CLIENT_ID=your-client-id` to enable Google sign-in during local development.

### Terminal Agent (No UI)

Run the agent directly in the terminal via ADK:

```bash
uv run poe run
```

### Production Mode (Remote)

Deploy to Vertex AI Agent Engine and Cloud Run:

```bash
# Deploy full stack (backend + frontend)
uv run poe deploy-all

# Or deploy individually
uv run poe deploy       # Backend to Vertex AI Agent Engine
uv run poe deploy-web   # Frontend to Cloud Run
uv run poe deploy-gke   # Full stack to GKE
```

See [Deployment Guide](deployment.md) for detailed production instructions.

## Verification

1. Open the frontend URL in Chrome.
2. Sign in with Google.
3. Type "Hello" to verify the agent responds.
4. Try "Analyze traces for service X" to verify GCP connectivity.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `uv: command not found` | Install uv: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `flutter: command not found` | Install Flutter SDK from [flutter.dev](https://flutter.dev/docs/get-started/install) |
| `ModuleNotFoundError` | Run `uv run poe sync` to install all dependencies |
| Backend fails to start | Check `.env` has valid `GOOGLE_CLOUD_PROJECT` and `GOOGLE_GENAI_USE_VERTEXAI` |
| Frontend sign-in fails | Verify `GOOGLE_CLIENT_ID` is set and the OAuth client is configured for `http://localhost:8080` |
| Import errors after pulling | Run `uv run poe sync` to sync dependencies with the lockfile |

## Next Steps

*   [Development Guide](development.md) -- Development workflow, coding standards, and PR checklist.
*   [Linting Guide](linting.md) -- Linting tools, configuration, and enforcement rules.
*   [Testing Guide](testing.md) -- Test conventions, coverage requirements, and how to run tests.
*   [Deployment Guide](deployment.md) -- Production deployment instructions.

---
*Last verified: 2026-02-21
