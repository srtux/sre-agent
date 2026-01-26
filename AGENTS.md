# AGENTS.md: Universal AI Agent Standard

**This is the Single Source of Truth for all AI Agents working on this project.**

## 🚨 Critical Entry Points
*   **[Project Plan](docs/PROJECT_PLAN.md)**: Roadmap. **Update after every major change.**
*   **[Rules & Vibe](docs/guides/development.md)**: Core rules.
*   **[System Architecture](docs/architecture/system_overview.md)**: Topology.
*   **[Testing Strategy](docs/guides/testing.md)**: Standards.
*   **[Reference](docs/reference/)**: Specs.

## ⚡ Quick Rules
1.  **Vibe First**: Read docs, load context, then plan.
2.  **Test First**: Create/update tests *before* implementing logic.
3.  **Lint Always**: `uv run poe lint-all` must be clean.
4.  **No Hallucinations**: Read `pydantic` schemas; use `extra="forbid"`.
5.  **Compaction**: Update `PROJECT_PLAN.md` and docs when task completes.

## 🛠️ Build, Lint, & Test Commands

**Dependency Management:**
- Sync dependencies: `uv run poe sync`

**Linting & Formatting (Run before commit):**
- Run all linters: `uv run poe lint-all`
- Fix formatting: `uv run ruff format .`
- Fix lint issues: `uv run ruff check --fix .`
- Type check: `uv run mypy .`

**Testing:**
- **Run all tests**: `uv run poe test-all`
- **Run backend tests**: `uv run poe test`
- **Run specific test file**: `uv run pytest tests/sre_agent/tools/clients/test_trace.py`
- **Run specific test case**: `uv run pytest tests/sre_agent/tools/clients/test_trace.py::test_fetch_trace`
- **With verbose output**: Add `-v -s` (e.g., `uv run pytest ... -v -s`)

**Running the App:**
- Backend only: `uv run poe web`
- Full stack (Backend + Flutter): `uv run poe dev`

## 🎨 Code Style & Guidelines

### Python (Backend)
- **Version**: Python 3.10+
- **Type Hints**: **MANDATORY** & Strict. No implicit `Any`.
  - Good: `def func(a: str | None = None) -> list[int]: ...`
  - Bad: `def func(a=None): ...`
- **Imports**: Absolute imports preferred (e.g., `from sre_agent.tools import ...`).
- **Async**: Always `await` coroutines. Use `asyncio.gather` for parallelism.
- **Error Handling**: Use `try/except` blocks. Log errors with `logger.error(..., exc_info=True)`. Return structured error responses in tools.

### Pydantic Models
- **Strict Config**: ALWAYS use `extra="forbid"` to prevent hallucinations.
  ```python
  class MyModel(BaseModel):
      model_config = ConfigDict(frozen=True, extra="forbid")
      field: str
  ```

### Tool Development Pattern
- **Decorator**: Use `@adk_tool` for all tools.
- **Return Structure**: Must follow `BaseToolResponse`.
  ```python
  @adk_tool
  async def my_tool(arg: str) -> str:
      try:
          # ... implementation ...
          return json.dumps({"status": "success", "result": {...}})
      except Exception as e:
          return json.dumps({"status": "error", "error": str(e)})
  ```
- **Clients**: Use factory pattern (`get_trace_client()`). Never instantiate directly.
- **Credentials**: Respect End-User Credentials (EUC). Pass `tool_context` where needed.

### Testing Standards
- **Mocking**: NEVER use real credentials or project IDs. Mock all GCP clients.
- **Structure**: Mirror source (e.g., `sre_agent/foo.py` -> `tests/sre_agent/test_foo.py`).
- **Coverage**: Aim for 100% path coverage.

### Flutter (Frontend)
- **Format**: `dart format .`
- **Lint**: `flutter analyze .`
- **Test**: `flutter test`
- **Style**: "Deep Space" theme (Glassmorphism). Use `UnifiedPromptInput`, `StatusToast`.

## 🏗️ Architecture Overview
- **Orchestrator**: `sre_agent/agent.py` delegates to sub-agents.
- **Sub-Agents**: Located in `sre_agent/sub_agents/` (Trace, Log, Metrics specialists).
- **Tools**: `sre_agent/tools/` (MCP for heavy SQL, Direct API for low latency).
- **Protocol**: GenUI over HTTP.

## ❌ Common Pitfalls
- **Missing @adk_tool**: Agent won't see the tool.
- **Hardcoded Secrets**: Use env vars (`GOOGLE_CLOUD_PROJECT`).
- **Implicit Any**: `mypy` will fail. Define types explicitly.
- **Relative Imports**: Use absolute paths to avoid circular deps.

## 📝 Development Workflow
1.  **Read**: Understand file context and related tests.
2.  **Plan**: Check `docs/PROJECT_PLAN.md` and define approach.
3.  **Test**: Write failing test first (TDD).
4.  **Implement**: Write code to pass test.
5.  **Verify**: Run `uv run poe lint-all` and `uv run poe test`.
6.  **Commit**: Use conventional commits (feat, fix, docs, refactor).
