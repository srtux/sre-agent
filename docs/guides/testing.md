# SRE Agent: Testing Strategy and Style Guide

## Goal: 80% Gate, 100% Target, 0% Regressions

Testing is the bedrock of the SRE Agent. Because this agent performs autonomous operations on production infrastructure, its behavior must be **fully verifiable, correct, and predictable**.

Our philosophy is simple: **If it is not tested, it is broken.**

> **Coverage policy**: 80% minimum gate enforced in CI. 100% target on all new tools and core logic. PRs that drop project coverage below 80% will be rejected.

### Core Principles

1. **Shift Left**: Bugs are cheapest when caught during development. Developers are responsible for their own tests.
2. **Test-Driven Development (TDD)**: Specs must be translated into tests **before** the code is written. For coding agents, this is a strict rule.
3. **100% Path Coverage**: We do not just test the "happy path." Every branch, every error condition, and every edge case must have a corresponding test.
4. **Deterministic behavior**: Tests must be hermetic and repeatable. Use robust mocking for all external GCP APIs.
5. **Verifiable Correctness**: Coverage is a metric, but correctness is the goal. Tests must assert on the *integrity* of the logic, not just that the lines were executed.

---

## Test Suite Overview

As of 2026-02-15, the project has **196 Python test files** containing approximately **2,300+ test functions** and **21 Flutter test files** containing approximately **112 test functions**.

---

## Testing Levels

| Level | Path | Tool | Description |
|-------|------|------|-------------|
| **Behavioral** | `openspec/specs/` | **OpenSpec** | "Source of Truth" specs defining behavior and acceptance criteria. |
| **Unit** | `tests/unit/` | `pytest` | Isolated logic, pure functions, tool implementations with mocked clients. |
| **Integration** | `tests/integration/` | `pytest` | Interactions between services (e.g., Session Service + DB), state management, council pipeline, auth, middleware. |
| **Component** | `tests/sre_agent/` | `pytest` | Core engine tests (runner, policy engine, approval, graph service, prompt composer, summarizer, context compactor). |
| **Server** | `tests/server/` | `pytest` | FastAPI endpoint tests, GenUI event streaming, cancellation, widget logic, session rename, debug UI. |
| **API** | `tests/api/` | `pytest` | HTTP API endpoint tests (help endpoint). |
| **Frontend** | `autosre/test/` | `flutter test` | Widget tests, layout verification, service injection testing. |
| **Agent Eval** | `eval/` | **ADK Eval** | Reasoning validation. Uses LLM-as-a-judge and trajectory scoring. |
| **E2E** | `tests/e2e/` | `pytest` | Full agent loops, user query to final remediation plan, investigation pipelines. |

---

## Agent Evaluation (The Quality Gate)

While unit tests verify the code, **Agent Evaluations** verify the **Reasoning**. We use the Vertex AI GenAI Evaluation Service to ensure the agent's logic remains correct.

### 1. Trajectory Scoring
We measure the accuracy of the agent's tool-selection path.
* **Goal**: 100% Match with the "Golden Trajectory" (Aggregate > Triage > Deep Dive).

### 2. LLM-as-a-Judge (Rubrics)
We use `gemini-1.5-pro` to grade responses on:
* **Technical Precision**: Specificity of GCP signal evidence.
* **Root Cause Causality**: "Why" it happened vs just "What" happened.
* **Actionability**: Clear, recommended shell commands or fixes.

For implementation details, see **[docs/guides/evaluation.md](evaluation.md)**.

---

## Style Guide and Patterns

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
- **MCP**: Use `USE_MOCK_MCP=true` environment variable to substitute real MCP toolsets with `MockMcpTool`/`MockMcpToolset` from `sre_agent.tools.mcp.mock_mcp`. See the [MCP Mocking](#mcp-mocking-use_mock_mcp) section below.

### 5. Dependency Injection via Context
Since our tools rely on `ToolContext` for session and credentials, use specialized fixtures to create mock contexts. The shared `conftest.py` provides a `mock_tool_context` fixture for this purpose.

### 6. Async Test Pattern
All async tests must use the `@pytest.mark.asyncio` decorator:

```python
@pytest.mark.asyncio
async def test_my_async_tool_returns_success():
    """Test that the tool returns expected data."""
    result = await my_async_tool(arg="value", tool_context=mock_ctx)
    assert result["status"] == "success"
```

---

## Parallel Test Execution

Tests run in parallel using `pytest-xdist` with automatic worker detection:

```
addopts = "--import-mode=importlib -n auto --dist worksteal"
```

This means all workers share the same test session but execute different test files concurrently using the `worksteal` distribution strategy. Tests must be **isolated** and **hermetic** to avoid interference between workers.

### SQLite Lock Conflict Resolution

Running parallel tests with SQLite-backed session storage causes `database is locked` errors. The project resolves this by forcing `InMemorySessionService` during testing:

```python
# In tests/conftest.py (session-scoped, autouse)
os.environ["USE_DATABASE_SESSIONS"] = "false"
```

This session-scoped fixture runs once at the start of the entire test session and sets the environment variable so that all session management code uses `InMemorySessionService` instead of `DatabaseSessionService`. Individual integration tests that need to test database behavior explicitly set this variable themselves.

---

## MCP Mocking (USE_MOCK_MCP)

The Model Context Protocol (MCP) tools connect to real BigQuery, Cloud Logging, and Cloud Monitoring backends. For testing, the project provides a complete mock layer:

- **Environment variable**: Set `USE_MOCK_MCP=true` to activate mock MCP toolsets.
- **Mock classes**: `MockMcpTool` and `MockMcpToolset` in `sre_agent/tools/mcp/mock_mcp.py`.
- **Supported mock tools**: `list_log_entries`, `list_timeseries`, `query_range`/`query_promql`, `list_dataset_ids`, `list_table_ids`, `execute_sql`, `get_table_info`.
- **Fallback behavior**: When `USE_MOCK_MCP=true`, the MCP GCP module (`sre_agent/tools/mcp/gcp.py`) returns mock toolsets instead of connecting to real MCP servers.
- **MCP fallback tests**: `tests/unit/sre_agent/tools/clients/test_mcp_fallback.py` verifies that when MCP calls fail, the system falls back to direct API calls.

```python
# Example: Testing with mock MCP
@pytest.mark.asyncio
async def test_mcp_tool_returns_mock_data():
    tool = MockMcpTool("list_log_entries")
    result = await tool.run_async({}, None)
    assert "entries" in result
```

---

## Synthetic Test Data (tests/fixtures/)

### synthetic_otel_data.py

The `tests/fixtures/synthetic_otel_data.py` module provides factory classes for generating realistic OpenTelemetry data following the Google Cloud Observability schema:

| Generator Class | Purpose |
|----------------|---------|
| `SpanEventGenerator` | Creates span events (exceptions with stacktraces, log events) |
| `SpanLinkGenerator` | Creates span links (follows_from, batch, async) |
| `OtelSpanGenerator` | Creates complete OTel spans with configurable attributes (HTTP server, database, linked spans) |
| `TraceGenerator` | Creates complete multi-span traces (simple HTTP, fanout, async, multi-service with latency strategies) |
| `BigQueryResultGenerator` | Creates mock BigQuery response data (aggregate metrics, time-series, exemplar traces, exception events) |
| `CloudTraceAPIGenerator` | Creates mock Cloud Trace API responses (single trace, list traces) |
| `CloudLoggingAPIGenerator` | Creates mock Cloud Logging API responses (structured log entries, log entry lists) |

Helper functions: `generate_trace_id()`, `generate_span_id()`, `generate_timestamp()`, `generate_random_string()`.

The `TraceGenerator` supports multiple trace topologies:
- **Simple HTTP trace**: Single request with optional database call and error injection
- **Fanout trace**: One root service calling multiple child services in parallel
- **Async trace**: Producer/consumer pattern with span links between disjoint traces
- **Multi-service trace**: Chain of services with configurable latency strategies (`normal`, `creep`, `spike`)

### Global Fixtures (conftest.py)

The `tests/conftest.py` file provides shared resources available to all tests:

| Fixture | Description |
|---------|-------------|
| `sanitize_environment` | Session-scoped autouse fixture that cleans env vars (removes `GOOGLE_API_KEY`, `GEMINI_API_KEY`, `SRE_AGENT_ID`; sets `USE_DATABASE_SESSIONS=false`) |
| `sample_text_payload_logs` | 5 log entries with textPayload (INFO, ERROR, WARNING) |
| `sample_json_payload_logs` | 4 log entries with jsonPayload (various field names: `message`, `msg`, `log`) |
| `sample_proto_payload_logs` | 1 audit log entry with protoPayload |
| `baseline_period_logs` | 23 log entries simulating a healthy period (20 INFO + 3 WARNING) |
| `incident_period_logs` | 43 log entries simulating an incident (connection refused, lock timeouts, retries) |
| `mixed_payload_logs` | 7 log entries mixing all payload types for extraction testing |
| `sample_trace_spans` | 2 spans forming a simple HTTP+DB trace |
| `mock_logging_client` | MagicMock for Cloud Logging client |
| `mock_trace_client` | MagicMock for Cloud Trace client |
| `mock_bigquery_client` | MagicMock for BigQuery client |
| `mock_tool_context` | MagicMock for ADK ToolContext |

Helper functions defined in conftest: `generate_trace_id()`, `generate_span_id()`, `generate_timestamp()`.

---

## Environment Variables for Testing

The following environment variables are set by the `test` poe task:

| Variable | Value | Purpose |
|----------|-------|---------|
| `GOOGLE_CLOUD_PROJECT` | `test-project` | Provides a project ID without requiring real GCP access |
| `STRICT_EUC_ENFORCEMENT` | `false` | Allows tests to run without real user credentials |
| `DISABLE_TELEMETRY` | `true` | Prevents OTel span export during tests |
| `GOOGLE_GENAI_USE_VERTEXAI` | `false` | Disables Vertex AI client to avoid credential requirements |
| `SRE_AGENT_DEPLOYMENT_MODE` | `true` | Skips heavyweight module imports (e.g., ADK agent loading) at module level |
| `USE_DATABASE_SESSIONS` | `false` | Set by conftest.py to use InMemorySessionService (prevents SQLite lock conflicts) |
| `USE_MOCK_MCP` | `true` | (Optional) Enables mock MCP toolsets instead of real MCP connections |

---

## OpenSpec-Driven Development (BDD)

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

## Policies

1. **OpenSpec First**: No PR should be submitted for a new feature without a corresponding OpenSpec artifact.
2. **TDD Rule**: For all new features, you must produce a test file demonstrating the intended behavior before modifying `sre_agent/`.
3. **Coverage Gate**: PRs that drop the project coverage level below 80% will be rejected.
4. **Regression Zero**: Every bug fix must include a regression test that fails without the fix.
5. **Documentation Rule**: Every new feature MUST include updates to internal architecture docs and the public Help Center (`docs/help`).
6. **No Placeholders**: Do not use `TODO` in tests. Tests must be complete and assert on all relevant fields in responses.

---

## Execution

### Backend Tests

```bash
# Run full test suite with coverage gate (parallel via pytest-xdist)
uv run poe test

# Run tests without coverage (fastest iteration)
uv run poe test-fast

# Run with detailed coverage report (manual)
uv run pytest tests --cov=sre_agent --cov-report=term-missing --cov-fail-under=80

# Run a single test file
uv run pytest tests/unit/sre_agent/tools/clients/test_trace.py -v

# Run tests matching a keyword
uv run pytest tests -k "test_fetch_trace" -v
```

### Frontend Tests

```bash
# Run Flutter tests via poe
uv run poe test-flutter

# Run from the autosre/ directory
cd autosre && flutter test

# Run a specific test file
cd autosre && flutter test test/council_panel_test.dart
```

### Full Suite

```bash
# Run both backend and frontend tests
uv run poe test-all
```

### Agent Evaluations

```bash
# Run agent quality evaluations (trajectory + rubric scoring)
uv run poe eval
```

---

## Frontend Testing
For details on how to test the Flutter dashboard and use the `test_helper.dart` utility, see **[docs/guides/frontend_testing.md](frontend_testing.md)**.

---
*Last verified: 2026-02-15 -- Auto SRE Team*
