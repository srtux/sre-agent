# CLAUDE.md: Auto SRE Project Guide

## 🚀 Core Mission
Auto SRE is an AI-powered reliability engine inspired by Google SRE practices. It uses a **Council of Experts** (specialized sub-agents) to automate incident investigation.

## 🛠 Tech Stack
-   **Backend**: Python 3.10+, FastAPI, Google ADK 1.23.0
-   **Frontend**: Flutter Web (Material 3 + Deep Space Aesthetic)
-   **LLM**: Gemini 2.5 Flash (via Vertex AI ADK)
-   **Storage**: SQLite (Dev) / Cloud SQL (Prod), Firestore (Configs)
-   **Telemetry**: Cloud Trace, Cloud Logging, Cloud Monitoring (Native OTel)

## 📋 Development Standards

### 1. Vibe Coding Cycle
1. **Read Docs** & Context
2. **Plan** (with logic verification)
3. **Test First** (Unit/Integration)
4. **Implement** (Strict types, Lint clean)
5. **Verify** & Self-Critique
6. **Compact Knowledge** (Update `AGENTS.md`, `PROJECT_PLAN.md`)

### 2. Strict Coding Rules
-   **Typing**: Mandatory explicit type hints for all functions. No implicit `Any`.
-   **Schemas**: Use Pydantic `frozen=True, extra="forbid"` to catch hallucinations.
-   **Tools**: Every tool MUST use `@adk_tool` and return `BaseToolResponse`.
-   **Async**: All external I/O (GCP, DB, LLM) must be `async/await`.
-   **Imports**: Prefer absolute imports (`from sre_agent.X import Y`).

### 3. Tool Implementation Checklist
- [ ] Add `@adk_tool` decorator.
- [ ] Implement `async` logic with robust error handling.
- [ ] Register in `sre_agent/tools/__init__.py`.
- [ ] Register in `sre_agent/agent.py` (`base_tools` & `TOOL_NAME_MAP`).
- [ ] Define in `sre_agent/tools/config.py`.
- [ ] 100% test coverage in `tests/unit/sre_agent/tools/`.

## 🧪 Testing & Linting
-   **Run All**: `uv run poe lint-all && uv run poe test`
-   **Linting**: Ruff (Format/Lint), MyPy (Types), Codespell, Deptry
-   **Testing**: Pytest for backend, Flutter test for frontend

## 🏗 Key Architectures
-   **Dashboard Data Channel**: Decoupled from A2UI. Backend emits `{"type": "dashboard", ...}` events. Frontend uses `dashboardStream`.
-   **Dual-Mode Agent**: Switch between Local Subprocess and Remote Agent Engine via `SRE_AGENT_ID`.
-   **EUC Pattern**: End-User Credentials propagated from Frontend headers to Tool Context for multi-tenant isolation.
-   **Telemetry**: Google GenAI SDK instrumentation + `OTEL_TO_CLOUD` multi-exporter pattern.

> [!IMPORTANT]
> **Always refer to `AGENTS.md` for the single source of truth on coding patterns.**
