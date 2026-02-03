# CLAUDE.md: Auto SRE — Claude Code Quick Reference

> **Canonical reference**: [`AGENTS.md`](AGENTS.md) is the Single Source of Truth for all coding patterns.
> This file provides Claude-specific shortcuts. For full details, always consult AGENTS.md.

## Reading Order
1. **[llm.txt](llm.txt)** — High-density context (read first)
2. **[AGENTS.md](AGENTS.md)** — Patterns, checklists, pitfalls
3. **[docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md)** — Roadmap and status
4. Task-specific docs in [`docs/`](docs/README.md)

## Quick Rules
1. **Read before modifying** — Never propose changes to unread code.
2. **Test first** — Create/update tests *before* implementing logic.
3. **Lint always** — `uv run poe lint-all` must be clean.
4. **Explicit types** — Mandatory type hints, no implicit `Any`.
5. **Coverage** — 80% minimum gate; 100% target on new tools and core logic.
6. **Schemas** — Pydantic `frozen=True, extra="forbid"` on all models.
7. **Async** — All external I/O (GCP, DB, LLM) must be `async/await`.
8. **Imports** — Prefer absolute (`from sre_agent.X import Y`); relative OK within same package.
9. **Tools** — Must use `@adk_tool` decorator and return `BaseToolResponse` JSON.
10. **Compaction** — Update `PROJECT_PLAN.md` and docs after completing major changes.

## Essential Commands
```bash
uv run poe dev          # Full stack (backend + frontend)
uv run poe test         # pytest + 80% coverage gate
uv run poe lint-all     # Ruff + MyPy + codespell + deptry
uv run poe deploy-all   # Full stack deployment
```

## Tech Stack
- **Backend**: Python 3.10+, FastAPI, Google ADK
- **Frontend**: Flutter Web (Material 3, Deep Space aesthetic)
- **LLM**: Gemini 2.5 Flash/Pro (via `get_model_name("fast"|"deep")`)
- **Testing**: pytest (backend), flutter test (frontend), ADK eval (agent quality)

## Key Architecture Pointers
| Pattern | Details in AGENTS.md |
|---------|---------------------|
| Tool decorator (`@adk_tool`) | Section 2 |
| Pydantic schemas (`extra="forbid"`) | Section 1 |
| Client factory (singletons) | Section 4 |
| EUC credential propagation | Section 11 |
| Dual-mode execution | Section 10 |
| Dashboard data channel | Section 12 |
| MCP vs Direct API | Section 9 |

> [!IMPORTANT]
> **Always refer to [`AGENTS.md`](AGENTS.md) for the single source of truth on coding patterns.**

---
*Last verified: 2026-02-02 — Auto SRE Team*
