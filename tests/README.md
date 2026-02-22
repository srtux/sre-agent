# SRE Agent Test Suite

This directory contains the Python test suite for the SRE Agent. As of 2026-02-15, the suite includes **196 test files** containing approximately **2,300+ test functions** with an 80% minimum coverage gate.

For the full testing strategy and style guide, see [docs/testing/testing.md](../docs/testing/testing.md).
For Flutter frontend tests, see [docs/guides/frontend_testing.md](../docs/guides/frontend_testing.md).

## Directory Structure

```text
tests/
├── conftest.py                       # Global fixtures (environment sanitization, sample logs/traces, mock clients)
├── fixtures/                         # Dynamic synthetic data generators
│   └── synthetic_otel_data.py        #   OTel trace/span/log factories (7 generator classes)
│
├── unit/                             # FAST: Isolated logic tests (164 test files)
│   ├── sre_agent/                    #   Mirrors sre_agent/ source structure
│   │   ├── api/                      #     API layer tests
│   │   │   ├── helpers/              #       Dashboard events, tool events, trace links (6 files)
│   │   │   ├── routers/              #       Agent, sessions, tools, system, permissions, preferences routers (8 files)
│   │   │   └── test_app_factory.py   #       App factory tests
│   │   ├── core/                     #     Core engine (circuit breaker, model callbacks, runner, router, etc.)
│   │   ├── council/                  #     Council of Experts (orchestrator, panels, debate, critic, schemas, etc.)
│   │   ├── memory/                   #     Memory subsystem (manager, callbacks, learning, mistake store, etc.)
│   │   ├── models/                   #     Data model tests (investigation state)
│   │   ├── services/                 #     Service tests (agent engine client, session init)
│   │   ├── sub_agents/               #     Sub-agent tests (logs, metrics, prompt syntax)
│   │   └── tools/                    #     Tool ecosystem tests
│   │       ├── analysis/             #       Analysis modules (trace, logs, metrics, SLO, correlation, remediation, BigQuery, agent trace)
│   │       ├── bigquery/             #       BigQuery client, schemas, queries
│   │       ├── clients/              #       GCP API clients (16 files: trace, logging, monitoring, alerts, GKE, SLO, etc.)
│   │       ├── common/               #       Shared utilities (decorators, cache, telemetry, serialization, debug)
│   │       ├── discovery/            #       GCP resource discovery
│   │       ├── github/               #       GitHub client and tools
│   │       ├── mcp/                  #       MCP tools (mock MCP, fallback, GCP auth, orchestration)
│   │       ├── playbooks/            #       Runbook execution (registry, schemas, self-healing)
│   │       ├── proactive/            #       Proactive signal analysis
│   │       └── sandbox/              #       Sandboxed code execution (executor, processors, schemas)
│   ├── tools/                        #   Additional tool tests
│   │   ├── exploration/              #     Health check exploration
│   │   └── synthetic/                #     Synthetic data provider, guest mode
│   └── deploy/                       #   Deployment script tests
│
├── sre_agent/                        # COMPONENT: Core engine tests (9 test files)
│   ├── api/
│   │   └── test_e2e_integration.py   #   API end-to-end integration
│   └── core/
│       ├── test_adk_integration.py   #   ADK integration
│       ├── test_approval.py          #   Human approval workflow
│       ├── test_context_compactor.py #   Context window management
│       ├── test_graph_service.py     #   Service dependency graph (28 tests)
│       ├── test_policy_engine.py     #   Safety guardrails
│       ├── test_prompt_composer.py   #   Dynamic prompt composition
│       ├── test_runner.py            #   Agent execution logic
│       └── test_summarizer.py        #   Response summarization
│
├── server/                           # SERVER: Application layer tests (7 files)
│   ├── test_server.py                #   FastAPI endpoint basics
│   ├── test_genui_chat_events.py     #   GenUI event streaming and A2UI injection
│   ├── test_cancellation.py          #   Request cancellation logic
│   ├── test_debug_ui_alias.py        #   Debug UI alias routes
│   ├── test_metric_list_handling.py  #   Metric list response handling
│   ├── test_session_rename.py        #   Session rename endpoint
│   ├── test_widget_logic.py          #   Widget rendering logic
│   └── reproduce_session_access.py   #   Session access reproduction script (not a test)
│
├── integration/                      # INTEGRATION: Service interaction tests (6 files)
│   ├── test_api_pipeline.py          #   API-to-agent pipeline
│   ├── test_auth_integration.py      #   Authentication flow integration
│   ├── test_chat_persistence.py      #   Session history persistence
│   ├── test_council_pipeline.py      #   Council of Experts pipeline (largest integration test)
│   ├── test_middleware_integration.py #   Auth + tracing + CORS middleware
│   └── test_session.py               #   Session management (InMemorySessionService)
│
├── api/                              # API: HTTP endpoint tests (1 file)
│   └── test_help.py                  #   Help endpoint
│
└── e2e/                              # E2E: Full end-to-end flows (9 files)
    ├── test_agent_execution.py       #   Agent execution lifecycle
    ├── test_agent_integration.py     #   Agent integration scenarios
    ├── test_analysis_e2e.py          #   Analysis pipeline end-to-end
    ├── test_api_flow.py              #   API-to-agent flow
    ├── test_auth_flow.py             #   Authentication flow end-to-end
    ├── test_e2e_cujs.py              #   Critical User Journeys (largest E2E test)
    ├── test_investigation_pipeline.py #   Investigation pipeline end-to-end
    ├── test_mocks_e2e.py             #   Mock-based E2E scenarios
    └── test_trace_selection.py       #   Trace selection logic end-to-end
```

## Test Categories

### 1. Unit Tests (`tests/unit/`) -- 164 test files

Isolated logic tests. Fast and comprehensive. Organized to mirror the source directory structure.

Key areas:
- **Council of Experts** (`council/`): Orchestrator, panels, debate, critic, intent classifier, schemas, slim tools, tool registry (17 files)
- **Memory** (`memory/`): Manager, callbacks, learning, mistake store, mistake learner, sanitizer, security (10 files)
- **API Helpers** (`api/helpers/`): Dashboard events (council, exploration), tool events, memory events, trace links (6 files)
- **API Routers** (`api/routers/`): Agent router (dual mode, project), sessions, tools, system, permissions, preferences (8 files)
- **GCP Clients** (`tools/clients/`): Trace, logging, monitoring, alerts, GKE, SLO, factory, AppHub, asset inventory, dependency graph, MCP fallback (16 files)
- **Analysis** (`tools/analysis/`): Trace patterns/comparison/statistics, log extraction/patterns, metrics, SLO burn rate, correlation (cross-signal, critical path, dependencies, change), remediation, BigQuery OTel, agent trace, GenUI adapter (20+ files)
- **Core Engine** (`core/`): Circuit breaker, model callbacks, large payload handler, runner adapter, runner policy, router, context compaction (7 files)

### 2. Component Tests (`tests/sre_agent/`) -- 9 test files

Tests for core engine components that require more integration-level setup but are not full system tests. Covers the runner, policy engine, approval workflow, graph service, prompt composer, summarizer, context compactor, and ADK integration.

### 3. Server Tests (`tests/server/`) -- 7 test files

Tests the FastAPI application layer including endpoint handling, GenUI event streaming, request cancellation, debug UI, and session rename.

### 4. Integration Tests (`tests/integration/`) -- 6 test files

Tests focusing on service interactions: API pipeline, authentication, session persistence, council pipeline orchestration, and middleware behavior.

### 5. API Tests (`tests/api/`) -- 1 test file

HTTP API endpoint tests (help endpoint).

### 6. End-to-End Tests (`tests/e2e/`) -- 9 test files

Full user journeys and complex orchestration flows including Critical User Journeys (CUJs), investigation pipelines, agent execution, and trace selection.

## Global Fixtures (`conftest.py`)

The `conftest.py` file provides shared resources available to all tests:

### Environment Sanitization (session-scoped, autouse)
- Removes `GOOGLE_API_KEY` and `GEMINI_API_KEY` when Vertex AI is enabled (prevents "mutually exclusive" client errors)
- Removes `SRE_AGENT_ID` (prevents tests from accidentally using remote agent engine mode)
- Sets `USE_DATABASE_SESSIONS=false` (uses InMemorySessionService to prevent SQLite lock conflicts in parallel test execution)

### Sample Data Fixtures
- **Log entries**: `sample_text_payload_logs`, `sample_json_payload_logs`, `sample_proto_payload_logs`, `baseline_period_logs`, `incident_period_logs`, `mixed_payload_logs`
- **Trace spans**: `sample_trace_spans` (HTTP + DB span pair)

### Mock Client Fixtures
- `mock_logging_client` -- MagicMock for Cloud Logging
- `mock_trace_client` -- MagicMock for Cloud Trace
- `mock_bigquery_client` -- MagicMock for BigQuery
- `mock_tool_context` -- MagicMock for ADK ToolContext

### Helper Functions
- `generate_trace_id()` -- Random 128-bit trace ID as hex
- `generate_span_id()` -- Random 64-bit span ID as hex
- `generate_timestamp()` -- ISO format timestamp with optional base time and offset

## Synthetic Data Generators (`fixtures/synthetic_otel_data.py`)

Factory classes for generating realistic OpenTelemetry data:

| Class | What it generates |
|-------|------------------|
| `SpanEventGenerator` | Exception events (with stacktraces), log events |
| `SpanLinkGenerator` | Span links (follows_from, batch, async) |
| `OtelSpanGenerator` | Complete OTel spans (HTTP server, database client, linked spans) |
| `TraceGenerator` | Multi-span traces (simple HTTP, fanout, async, multi-service with latency strategies) |
| `BigQueryResultGenerator` | Mock BigQuery results (aggregate metrics, time-series, exemplar traces, exception events) |
| `CloudTraceAPIGenerator` | Mock Cloud Trace API responses |
| `CloudLoggingAPIGenerator` | Mock Cloud Logging API responses |

## Running the Tests

### Quick Commands

```bash
# Run backend tests with coverage gate (parallel via pytest-xdist)
uv run poe test

# Run backend tests without coverage (fastest)
uv run poe test-fast

# Run Flutter frontend tests
uv run poe test-flutter

# Run both backend and frontend tests
uv run poe test-all

# Run agent evaluations
uv run poe eval
```

### Manual Commands

```bash
# Run with detailed coverage report
uv run pytest tests --cov=sre_agent --cov-report=term-missing --cov-fail-under=80

# Run a single test file
uv run pytest tests/unit/sre_agent/tools/clients/test_trace.py -v

# Run tests matching a keyword
uv run pytest tests -k "test_fetch_trace" -v

# Run without parallelism (debugging)
uv run pytest tests -n 0 -v
```

### Environment Variables

The `test` poe task sets these automatically:

| Variable | Value | Purpose |
|----------|-------|---------|
| `GOOGLE_CLOUD_PROJECT` | `test-project` | Mock project ID |
| `STRICT_EUC_ENFORCEMENT` | `false` | Skip real credential checks |
| `DISABLE_TELEMETRY` | `true` | No OTel export |
| `GOOGLE_GENAI_USE_VERTEXAI` | `false` | No Vertex AI client |
| `SRE_AGENT_DEPLOYMENT_MODE` | `true` | Skip heavyweight imports |

Additionally, `conftest.py` sets `USE_DATABASE_SESSIONS=false` to prevent SQLite lock conflicts during parallel execution.

## MCP Mocking

Set `USE_MOCK_MCP=true` to use `MockMcpTool`/`MockMcpToolset` from `sre_agent/tools/mcp/mock_mcp.py` instead of real MCP server connections. The mock supports: `list_log_entries`, `list_timeseries`, `query_range`, `query_promql`, `list_dataset_ids`, `list_table_ids`, `execute_sql`, `get_table_info`.

See `tests/unit/sre_agent/tools/mcp/test_mock_mcp.py` for usage examples.

## Best Practices

- **Mocks vs. Real APIs**: Use the mocks provided in `conftest.py` and `unittest.mock` to avoid making actual GCP calls during tests.
- **Data Generation**: Use the factories in `tests/fixtures/synthetic_otel_data.py` for complex trace structures rather than hardcoding large dicts.
- **Naming**: Files: `test_<module>.py`. Functions: `test_<function>_<condition>_<expected>`.
- **Async**: Use `@pytest.mark.asyncio` for all async test functions.
- **Isolation**: Tests run in parallel via `pytest-xdist`. Avoid shared mutable state between test files.
- **Path Mirroring**: Test file path should mirror source file path (e.g., `sre_agent/tools/clients/trace.py` -> `tests/unit/sre_agent/tools/clients/test_trace.py`).

---
*Last verified: 2026-02-15 -- Auto SRE Team*
