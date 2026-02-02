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

| Level | Path | Tool | Description |
|-------|------|------|-------------|
| **Behavioral** | `openspec/specs/` | **OpenSpec** | "Source of Truth" specs defining behavior and acceptance criteria. |
| **Unit** | `tests/unit/` | `pytest` | Isolated logic, pure functions, tool implementations with mocked clients. |
| **Integration** | `tests/integration/` | `pytest` | Interactions between services (e.g., Session Service + DB), State management. |
| **Frontend** | `autosre/test/` | `flutter test` | Widget tests, Layout verification, Service injection testing. |
| **System** | `tests/server/` | `pytest` | API endpoints, Middleware, Authentication flow, and Routing. |
| **Agent Eval** | `eval/` | **ADK Eval** | "World-Class" reasoning validation. Uses LLM-as-a-judge and trajectory scoring. |
| **E2E** | `tests/e2e/` | `pytest` | Full agent loops, user query to final remediation plan. |

---

## 🏆 Agent Evaluation (The Quality Gate)

While unit tests verify the code, **Agent Evaluations** verify the **Reasoning**. We use the Vertex AI GenAI Evaluation Service to ensure the agent's logic remains "Award-Winning."

### 1. Trajectory Scoring
We measure the accuracy of the agent's tool-selection path.
*   **Goal**: 100% Match with the "Golden Trajectory" (Aggregate → Triage → Deep Dive).

### 2. LLM-as-a-Judge (Rubrics)
We use `gemini-1.5-pro` to grade responses on:
*   **Technical Precision**: Specificity of GCP signal evidence.
*   **Root Cause Causality**: "Why" it happened vs just "What" happened.
*   **Actionability**: Clear, recommended shell commands or fixes.

For implementation details, see **[docs/guides/evaluation.md](evaluation.md)**.

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

## 🛰️ OpenSpec-Driven Development (BDD)

Every major feature or fix should be anchored in an OpenSpec change located in `openspec/changes/`.

### 1. The BDD Lifecycle (TDD Schema)
When building a new capability, use the `tdd` schema:
1. **`spec`**: Define the behavior, input/output contracts, and success criteria.
2. **`tests`**: Draft the test cases (Gherkin/Functional).
3. **`implementation`**: Write code to pass the tests.
4. **`archive`**: Permanently move verified specs to `openspec/specs/`.

### 2. Retroactive Specification
For critical existing modules (like the `chat_agent`), we maintain "Base Specs" in `openspec/specs/` to serve as the definitive source of truth for behavior.

---

## 📜 Policies

1.  **OpenSpec First**: No PR should be submitted for a new feature without a corresponding OpenSpec artifact.
2.  **TDD Rule**: For all new features, you must produce a test file demonstrating the intended behavior before modifying `sre_agent/`.
3.  **Coverage Gate**: PRs that drop the project coverage level will be rejected.
4.  **Regression Zero**: Every bug fix must include a regression test that fails without the fix.
5.  **Documentation Rule**: Every new feature MUST include updates to internal architecture docs and the public Help Center (`docs/help`).
6.  **No Placeholders**: Do not use `TODO` in tests. Tests must be complete and assert on all relevant fields in responses.

## 🚀 Execution

Run the suite with:
```bash
uv run poe test
```

For detailed coverage reports:
```bash
uv run pytest --cov=sre_agent --cov-report=term-missing
```

---

## 📱 Frontend Testing
For details on how to test the Flutter dashboard and use the `test_helper.dart` utility, see **[docs/guides/frontend_testing.md](frontend_testing.md)**.
