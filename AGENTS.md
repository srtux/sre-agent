# AGENTS.md: Universal AI Agent Standard

**This is the Single Source of Truth for all AI Agents working on this project.**

## 🚨 Critical Entry Points
*   **[Project Plan](docs/PROJECT_PLAN.md)**: The living roadmap of completed work and future tasks. **Update this after every major change.**
*   **[Rules & Vibe](docs/guides/development.md)**: The core "Vibe Coding" lifecycle, patterns, and strict rules.
*   **[System Architecture](docs/architecture/system_overview.md)**: Understanding the topology before making changes.
*   **[Testing Strategy](docs/guides/testing.md)**: The world-class testing standards you must follow.
*   **[Reference](docs/reference/)**: API and Configuration specs.

## ⚡ Quick Rules
1.  **Vibe First**: Read the docs, load the context, then plan.
2.  **Test First**: Create a test case before implementing logic.
3.  **Lint Always**: `uv run poe lint-all` must be clean.
4.  **No Hallucinations**: Read `pydantic` schemas before using them.
5.  **Compaction**: Update documentation and `PROJECT_PLAN.md` when you learn something new or complete a task.

**For deep details, go to [docs/guides/development.md](docs/guides/development.md).**
