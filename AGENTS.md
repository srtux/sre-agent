# AGENTS.md: Universal AI Agent Standard
**High-density summary available in [llm.txt](./llm.txt).**

## 🚀 Core Workflows

We use **`uv`** for dependency management and **`poethepoet`** for task automation defined in `pyproject.toml`.

| **Sync** | `uv run poe sync` | Install dependencies and update `.venv` |
| **Run** | `uv run poe run` | Launch interactive terminal agent |
| **Lint** | `uv run poe lint-all` | Run **Ruff**, **MyPy**, **Codespell**, **Deptry**, and **Flutter Analyze** |
| **Test** | `uv run poe test-all` | Run **Pytest** and **Flutter Test** with coverage guards |
| **Deploy** | `uv run poe deploy` | Validate & Deploy to Agent Engine |
| **Pre-commit** | `uv run poe pre-commit` | Run quality guards (formatting, trailing whitespace) |

**See [TESTING.md](./TESTING.md) for our world-class testing strategy and [LINTING.md](./LINTING.md) for linting rules.**

4.  **Zero-Warning Policy**: Treat linter warnings and "info" messages as hard failures.

### 🌊 The Vibe Coding Lifecycle
We embrace a "Vibe Coding" workflow—moving at high speed with AI while maintaining rigid quality via this 7-step cycle:
1.  **Context Loading**: Read the full documentation set (`*.md`) and relevant source code to load the project's "vibe" (architecture, style, patterns) before starting.
2.  **Explicit Planning**: Create a concrete plan in `task.md` or `implementation_plan.md`. Never start coding without a stated path.
3.  **Spec-Driven TDD**: Write the test **first**. The test is the "contract" that protects against AI drift.
4.  **Micro-Iteration**: Make changes in small, testable chunks. One function, one component, or one rule change at a time.
5.  **Green-to-Fix Loop**: Make the tests pass, then run `uv run poe lint-all`.
6.  **Agentic Self-Critique**: Critically review your own code. Challenge your design decisions before asking the user for review.
7.  **Knowledge Compaction**: Update documentation (`AGENTS.md`, `README.md`, etc.) to reflect the change. This "compacts" the new knowledge into the project's source of truth for the next iteration.

## 🛠️ Development Rules

### 1. Modern Python Stack - Testing First
- **Test-Driven Development**: specs **MUST** be translated to tests first before writing code. This is mandatory for all coding agents.
- **Coverage**: Project target is **100% coverage**. Every branch and every error condition must be tested.
- **Dependencies**: Managed via `pyproject.toml` (NOT `requirements.txt`).
- **Lockfile**: Always commit `uv.lock`.
- **Python Version**: 3.10+ (Testing uses 3.10 & 3.11).
- **Import Style**: Use absolute imports (e.g., `sre_agent.tools...`) except for relative sibling/parent imports within modules.

### 2. Code Quality & Linting
- **Linter**: **Ruff** replaces Flake8/Black/Isort. Configuration is in `pyproject.toml`.
- **Type Checking**: **MyPy** is strict.
  - **Explicit Optional**: Use `name: str | None = None` instead of `name: str = None`.
  - **No Implicit Any**: Annotate empty containers: `items: list[dict[str, Any]] = []`.
  - **Float Initialization**: Use `val: float = 0.0` (not `0`) to satisfy strict typing.
- **Pydantic Schemas**: Use `model_config = ConfigDict(frozen=True, extra="forbid")` for all structured outputs.
  - **Schema-Driven Coding**: Always read the model definition (source of truth) before writing code that instantiates it. This prevents "imaginary" fields.
- **Dependency Freshness**: **Deptry** ensures no unused or missing dependencies are in `pyproject.toml`.
- **Error Envelopes**: All tools should follow the `BaseToolResponse` structure (status, result, error, metadata) to ensure the Orchestrator can handle failures gracefully.
- **Structured Logging**: Use `configure_logging()` from `sre_agent.tools.common.telemetry`. Set `LOG_FORMAT=JSON` in production for Cloud Logging compatibility.
- **Secret Scanning**: **detect-secrets** scans for leaked keys.
  - If you encounter a false positive, update the baseline: `uv run detect-secrets scan --baseline .secrets.baseline`.
- **Pre-commit**: You **MUST** run `uv run poe pre-commit` before pushing. It fixes formatting and spacing issues automatically.
- **Session Stability**: When working with long-running async tasks (like the Agent event loop), **ALWAYS** refresh the `Session` object from the database to avoid Optimistic Locking errors (`StaleSessionError`).
- **Project Context Enforcement**:
  - **Interceptor**: Never manually pass `project_id` in API calls if the `ProjectContextInterceptor` can handle it.
  - **Global Context**: Use `get_current_project_id()` to retrieve the context-aware project ID.
  - **No Hardcoding**: Hardcoded project IDs are strictly prohibited.

### 4. Frontend Development (Flutter)
- **Framework**: Flutter Web (GenUI).
- **Formatting**: Run `dart format .` before every commit.
- **Analysis**: Run `flutter analyze .` to catch type errors and lints.
- **Widgets**:
  - Use `UnifiedPromptInput` for all chat inputs.
  - Use `StatusToast` for notifications.
  - Adhere to the "Deep Space" theme (Glassmorphism, Dark Mode).
- **Testing**: `flutter test` for unit and widget tests.

### 5. Deployment Protocol
- **Command**: Always use `uv run poe deploy`.
- **Validation-First**: The deploy script (`deploy/deploy.py`) verifies:
  1. Local imports work.
  2. `pyproject.toml` dependencies are extracted accurately.
  3. `uv` sync is fresh.
- **Agent Engine**: Used for hosting. `deploy.py` handles the creation and update of the Reasoning Engine resource.

### 6. Git Standards
- **Conventional Commits**: Use semantic prefixes to help agents and automation understand changes:
  - `feat`: New capability
  - `fix`: Bug fix
  - `docs`: Documentation only
  - `style`: Formatting, missing semi colons, etc; no code change
  - `refactor`: Refactoring production code
  - `perf`: Code change that improves performance
  - `test`: Adding missing tests, refactoring tests; no production code change
  - `chore`: Updating build tasks, package manager configs, etc; no production code change

## 📝 Documentation Rules

- **Readme Updates**: If you add a feature, update:
  - `README.md`: Architecture diagrams and Tool tables.
  - `AGENTS.md`: If workflows change.
- **Architecture Diagrams**: Maintain Mermaid charts in `README.md`:
  - **System Architecture**: Sub-agents, tools, and GCP services.
  - **Interaction Workflow**: Sequence of analysis phases.

## 📦 Sub-Agent Architecture

The project follows the "Core Squad" pattern:

1.  **Orchestrator** (`sre_agent/agent.py`):
    - Receives user query.
    - Delegated to specialized sub-agents (`sre_agent/sub_agents/`).
2.  **Specialists**:
    - **Aggregate Analyzer**: "Big Picture" view, statistical baselines, and cross-service correlation.
    - **Alert Analyst**: Triage and classification of incoming alerts and incident scope.
    - **Trace Analyst**: Deep-dive latency, error structure, and distributed tracing analysis.
    - **Metrics Analyzer**: Time-series anomaly detection and Golden Signal analysis.
    - **Log Analyst**: SQL-based pattern clustering and anomaly extraction.
    - **Root Cause Analyst**: Causality, dependency mapping, and final diagnosis.
3.  **Tools**:
    - Located in `sre_agent/tools/`.
    - Divided into `mcp/` (Model Context Protocol) and `clients/` (Direct API).

## ✅ PR Checklist

1.  Sync dependencies: `uv run poe sync`
2.  Run pre-commit: `uv run poe pre-commit`
3.  Run lint checks: `uv run poe lint-all` (Must pass clean, see [LINTING.md](./LINTING.md))
4.  Run tests: `uv run poe test-all` (Must pass all tests, see [TESTING.md](./TESTING.md))
5.  Update docs: `README.md` if visible behavior changed.
