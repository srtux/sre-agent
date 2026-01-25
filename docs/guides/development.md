# Development & Vibe Coding Guide

## 🌊 The Vibe Coding Philosophy
Auto SRE embraces **"Vibe Coding"**—moving at high speed with AI while maintaining rigid quality. We prioritize high-level intent ("the vibe") over manual boilerplate, using agents to generate implementation details.

### The 7-Step Lifecycle
1.  **Context Loading**: Read `docs/architecture/system_overview.md` and source code to load the "vibe".
2.  **Explicit Planning**: Review and update **`docs/PROJECT_PLAN.md`**. Never start coding without a clear roadmap entry.
3.  **Spec-Driven TDD**: Write the test **first**. The test is the contract.
4.  **Micro-Iteration**: Make changes in small, testable chunks.
5.  **Green-to-Fix Loop**: Make tests pass, then run `uv run poe lint-all`.
6.  **Agentic Self-Critique**: Challenge your own design before asking for review.
7.  **Knowledge Compaction**: Update documentation and **`docs/PROJECT_PLAN.md`** to reflect final changes.

---

## 🛠️ Development Rules

### 1. Modern Python Stack
*   **Dependency Management**: `uv` is the standard. Managed via `pyproject.toml`.
*   **Lockfile**: Always commit `uv.lock`.
*   **Python Version**: 3.10+ (Testing uses 3.10 & 3.11).
*   **Import Style**: Use absolute imports (e.g., `sre_agent.tools...`).

### 2. Code Quality & Linting
*   **Linter**: **Ruff** (configured in `pyproject.toml`).
*   **Type Checking**: **MyPy** (Strict Mode).
    *   Explicit Optional: `name: str | None = None`
    *   No Implicit Any: `items: list[dict[str, Any]] = []`
*   **Pydantic**: Use `model_config = ConfigDict(frozen=True, extra="forbid")`.
*   **Pre-commit**: **MUST** run `uv run poe pre-commit` before pushing.

### 3. Frontend Development (Flutter)
*   **Framework**: Flutter Web (GenUI).
*   **Theme**: "Deep Space" (Glassmorphism, Dark Mode).
*   **Widgets**: Use `UnifiedPromptInput` and `StatusToast`.
*   **Commands**:
    *   `dart format .`
    *   `flutter analyze .`
    *   `flutter test`

### 4. Git Standards
*   **Conventional Commits**:
    *   `feat`: New capability
    *   `fix`: Bug fix
    *   `docs`: Documentation only
    *   `refactor`: Code change without behavioral change
    *   `test`: Test updates

---

## 📦 Core Squad Architecture

The project uses the **Core Squad** pattern (`sre_agent/sub_agents/`):

1.  **Orchestrator** (`agent.py`): Delegates to specialists.
2.  **Specialists**:
    *   **Trace Analyst**: Latency, errors, distributed tracing.
    *   **Log Analyst**: Pattern clustering, anomaly extraction.
    *   **Root Cause Analyst**: Causality, dependency mapping.
    *   **Alert Analyst**: Triage and classification.
    *   **Aggregate Analyzer**: BigQuery statistical baselines.

---

## ✅ PR Checklist

1.  Sync: `uv run poe sync`
2.  Pre-commit: `uv run poe pre-commit`
3.  Lint: `uv run poe lint-all`
4.  Test: `uv run poe test-all`
5.  Docs: Update **`docs/PROJECT_PLAN.md`** and relevant architecture docs.
