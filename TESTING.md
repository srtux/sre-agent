# 🧪 SRE Agent: World-Class Testing Strategy & Style Guide

## 🎯 Global Goal: 100% Coverage, 0% Regressions

Testing is the bedrock of the SRE Agent. Because this agent performs autonomous operations on production infrastructure, its behavior must be **fully verifiable, correct, and predictable**.

Our philosophy is simple: **If it's not tested, it's broken.**

### 🏛️ Core Principles

1.  **Shift Left**: Bugs are cheapest when caught during development. Developers are responsible for their own tests.
2.  **Test-Driven Development (TDD)**: Specs must be translated into tests **before** the code is written. For coding agents, this is a strict rule.
3.  **100% Path Coverage**: We don't just test the "happy path." Every branch, every error condition, and every edge case must have a corresponding test.
4.  **Deterministic behavior**: Tests must be hermetic and repeatable. Use robust mocking for all external GCP APIs.
5.  **Verifiable Correctness**: Coverage is a metric, but correctness is the goal. Tests must assert on the *integrity* of the logic, not just that the lines were executed.

---

## 🏗️ Testing Levels

| Level | Path | Description |
|-------|------|-------------|
| **Unit** | `tests/unit/` | Isolated logic, pure functions, tool implementations with mocked clients. |
| **Integration** | `tests/integration/` | Interactions between services (e.g., Session Service + DB), State management. |
| **System** | `tests/server/` | API endpoints, Middleware, Authentication flow, and Routing. |
| **E2E** | `tests/e2e/` | Full agent loops, user query to final remediation plan. |

---

## 🎨 Style Guide & Patterns

### 1. File Structure
Test files must mirror the source directory structure exactly.
- Source: `sre_agent/tools/clients/trace.py`
- Test: `tests/unit/sre_agent/tools/clients/test_trace.py`

### 2. High-Level Goal Documentation
Each test file **MUST** begin with a docstring explaining its purpose and the specific behavior it verifies.

```python
"""
Goal: Verify the Cloud Trace client correctly handles EUC propagation and error states.
Patterns: Client Factory Mocking, Tool Context Simulation.
"""
```

### 3. Naming Conventions
- **Files**: `test_<module_name>.py`
- **Classes**: `Test<ClassName>`
- **Functions**: `test_<function_name>_<condition>_<expected_outcome>` (e.g., `test_fetch_trace_not_found_returns_error_json`)

### 4. Robust Mocking
Never use live tokens or real GCP projects in unit tests. Use `unittest.mock` (`patch`, `AsyncMock`, `MagicMock`).
- **Clients**: Mock the factory returned from `sre_agent.tools.clients.factory`.
- **Telemetry**: Ensure `adk_tool` spans are ignored or asserted on correctly.

### 5. Dependency Injection via Context
Since our tools rely on `ToolContext` for session and credentials, use specialized fixtures to create mock contexts.

---

## 📜 Policies

1.  **TDD Rule**: For all new features, you must produce a test file demonstrating the intended behavior before modifying `sre_agent/`.
2.  **Coverage Gate**: PRs that drop the project coverage level will be rejected.
3.  **Regression Zero**: Every bug fix must include a regression test that fails without the fix.
4.  **No Placeholders**: Do not use `TODO` in tests. Tests must be complete and assert on all relevant fields in responses.

## 🚀 Execution

Run the suite with:
```bash
uv run poe test
```

For detailed coverage reports:
```bash
uv run pytest --cov=sre_agent --cov-report=term-missing
```
