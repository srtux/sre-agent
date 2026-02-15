# Development Guide

## Development Philosophy

Auto SRE prioritizes high-velocity development with AI assistance while maintaining strict quality gates. We move fast but never skip tests, linting, or documentation.

### The Development Lifecycle

1.  **Context Loading**: Read `AGENTS.md`, `docs/PROJECT_PLAN.md`, and relevant source code to understand the current state.
2.  **Explicit Planning**: Review and update `docs/PROJECT_PLAN.md`. Never start coding without a clear roadmap entry.
3.  **Spec-Driven TDD**: Write the test first. The test is the contract. Aim for **100% code coverage** on all new tools and core logic.
4.  **Micro-Iteration**: Make changes in small, testable chunks.
5.  **Green-to-Fix Loop**: Make tests pass, then run `uv run poe lint-all`.
6.  **Self-Critique**: Challenge your own design before asking for review.
7.  **Knowledge Compaction**: Update documentation and `docs/PROJECT_PLAN.md` to reflect final changes.

---

## Development Environment

### Prerequisites

*   **Python**: 3.10+ but less than 3.13 (as specified in `pyproject.toml`: `requires-python = ">=3.10,<3.13"`).
*   **uv**: Python package manager (replaces pip/poetry). Install from [astral.sh/uv](https://astral.sh/uv).
*   **Flutter SDK**: Dart SDK 3.10.7+ for frontend development.
*   **Google Cloud SDK**: For GCP authentication and local testing.
*   **poethepoet**: Task runner, installed automatically as a dev dependency.

### Initial Setup

```bash
# Install all dependencies (Python + Flutter)
uv run poe sync

# Set up environment
cp .env.example .env
# Edit .env with your settings (see Getting Started guide)

# Install pre-commit hooks
uv run pre-commit install
```

### Essential Commands

All tasks are managed via **poethepoet** (`poe`). Run any task with `uv run poe <task>`.

#### Development

| Command | Description |
|---------|-------------|
| `uv run poe dev` | Full stack: FastAPI backend (port 8001) + Flutter frontend (Chrome, port 8080) |
| `uv run poe web` | Backend server only (FastAPI on port 8001) |
| `uv run poe run` | Terminal agent via ADK (no UI) |
| `uv run poe sync` | Install/update all dependencies (runs `uv sync` + `flutter pub get`) |

#### Quality

| Command | Description |
|---------|-------------|
| `uv run poe lint` | Full Python lint pipeline: format, ruff check, mypy, codespell, deptry |
| `uv run poe lint-flutter` | Flutter analysis (`flutter analyze`) |
| `uv run poe lint-all` | Both Python and Flutter linters |
| `uv run poe format` | Auto-format Python code (Ruff) |
| `uv run poe typecheck` | MyPy strict type checking |
| `uv run poe spell` | Codespell spelling check |
| `uv run poe deptry` | Dependency analysis (unused/missing) |
| `uv run poe test` | pytest with coverage (80% minimum gate, parallel via pytest-xdist) |
| `uv run poe test-fast` | pytest without coverage (fastest iteration) |
| `uv run poe test-flutter` | Flutter tests (`flutter test`) |
| `uv run poe test-all` | Both Python and Flutter tests |
| `uv run poe eval` | Agent evaluations (trajectory + rubrics) |
| `uv run poe pre-commit` | Run all pre-commit hooks on all files |

#### Deployment

| Command | Description |
|---------|-------------|
| `uv run poe deploy` | Backend to Vertex AI Agent Engine |
| `uv run poe deploy-web` | Frontend to Cloud Run |
| `uv run poe deploy-all` | Full stack (backend + frontend) |
| `uv run poe deploy-gke` | Full stack to GKE |
| `uv run poe list` | List deployed agents |
| `uv run poe delete` | Delete a deployed agent (pass `--resource_id ID`) |

---

## Coding Standards

### 1. Python

*   **Dependency Management**: `uv` with `pyproject.toml`. Always commit `uv.lock`.
*   **Import Style**: Prefer absolute imports (`from sre_agent.tools.clients.factory import get_trace_client`). Relative imports are acceptable within the same package.
*   **Type Hints**: Mandatory on all functions. No implicit `Any`. Use explicit `Optional` style: `name: str | None = None`.
*   **Async**: All external I/O (GCP APIs, database, LLM calls) must use `async/await`.
*   **Pydantic Models**: All schemas use `model_config = ConfigDict(frozen=True, extra="forbid")`.
*   **Tools**: Must use the `@adk_tool` decorator and return `BaseToolResponse` JSON.
*   **Docstrings**: Google convention (enforced by Ruff rule `D` with `pydocstyle.convention = "google"`).

### 2. Frontend (Flutter)

*   **Framework**: Flutter Web with GenUI protocol.
*   **Theme**: "Deep Space" aesthetic (glassmorphism, dark mode, Material 3).
*   **Widgets**: Use `UnifiedPromptInput` and `StatusToast` for consistency.
*   **Service Access**: Use `context.read<T>()` or `context.watch<T>()` (Provider). Avoid direct singleton access (e.g., `T.instance`) to maintain testability.
*   **Lint Rules**: Defined in `autosre/analysis_options.yaml`. Key rules:
    *   `prefer_const_constructors`: Use `const` constructors for widget performance.
    *   `unawaited_futures`: Catch missing `await` on async calls.
    *   `always_declare_return_types`: Explicit return types everywhere.
*   **Commands**:
    ```bash
    # Format
    dart format autosre/

    # Analyze
    flutter analyze autosre/

    # Test
    flutter test  # (from autosre/ directory)
    ```

### 3. Git Standards

*   **Conventional Commits**:
    *   `feat`: New capability
    *   `fix`: Bug fix
    *   `docs`: Documentation only
    *   `refactor`: Code change without behavioral change
    *   `test`: Test updates
    *   `chore`: Build, CI, tooling changes

---

## Architecture Overview

### Council of Experts

The project uses a **Council of Experts** pattern (`sre_agent/council/`):

1.  **Orchestrator** (`agent.py`): Main entry point. Runs a 3-stage pipeline (Aggregate, Triage, Deep Dive) and delegates to specialists.
2.  **Council Modes** (enabled via `SRE_AGENT_COUNCIL_ORCHESTRATOR=true`):

| Mode | Trigger | Behavior |
|------|---------|----------|
| **Fast** | Narrow-scope queries | Single-panel dispatch |
| **Standard** | Normal investigations | 5 parallel panels -> Synthesizer merge |
| **Debate** | High-severity incidents | Panels -> Critic LoopAgent -> Confidence gating |

3.  **Specialist Sub-Agents** (`sre_agent/sub_agents/`):
    *   **Trace Analyst**: Latency, errors, distributed tracing.
    *   **Log Analyst**: Pattern clustering (Drain3), anomaly extraction.
    *   **Metrics Analyst**: Anomaly detection, statistical analysis.
    *   **Alert Analyst**: Triage and classification.
    *   **Root Cause Analyst**: Multi-signal synthesis, causality, dependency mapping.
    *   **Agent Debugger**: Agent execution debugging and inspection.

### Tool Ecosystem

Tools live in `sre_agent/tools/` (158+ files). Key conventions:
*   All tools use the `@adk_tool` decorator.
*   Registration requires updates in 4 places: `tools/__init__.py`, `agent.py` (base_tools + TOOL_NAME_MAP), `tools/config.py` (ToolConfig).
*   GCP clients use the singleton factory pattern (`tools/clients/factory.py`).

### Dual-Mode Execution

*   **Local** (`SRE_AGENT_ID` not set): Agent runs in-process in FastAPI.
*   **Remote** (`SRE_AGENT_ID` set): Forwards requests to Vertex AI Agent Engine.

---

## Testing

*   **Coverage gate**: 80% minimum (enforced by `pytest-cov`). Target 100% on new code.
*   **Parallel execution**: Tests run in parallel via `pytest-xdist` (`-n auto --dist worksteal`).
*   **Async tests**: Use `@pytest.mark.asyncio`.
*   **Mock external APIs**: Use `patch`, `AsyncMock`, `MagicMock`. Never call real GCP in tests.
*   **Path mirroring**: `sre_agent/tools/clients/trace.py` -> `tests/unit/sre_agent/tools/clients/test_trace.py`.
*   **Test environment variables** (set automatically by poe tasks):
    *   `GOOGLE_CLOUD_PROJECT=test-project`
    *   `DISABLE_TELEMETRY=true`
    *   `STRICT_EUC_ENFORCEMENT=false`
    *   `GOOGLE_GENAI_USE_VERTEXAI=false`
    *   `SRE_AGENT_DEPLOYMENT_MODE=true`
*   **Naming**: `test_<function>_<condition>_<expected>` (e.g., `test_fetch_trace_not_found_returns_error`).

See [Testing Guide](testing.md) for comprehensive details.

---

## PR Checklist

Before submitting a pull request:

1.  **Sync**: `uv run poe sync`
2.  **Pre-commit**: `uv run poe pre-commit`
3.  **Lint**: `uv run poe lint-all`
4.  **Test**: `uv run poe test-all`
5.  **Docs**: Update `docs/PROJECT_PLAN.md` and relevant architecture docs.
6.  **Commit messages**: Use conventional commit format.

---
*Last verified: 2026-02-15 -- Auto SRE Team*
