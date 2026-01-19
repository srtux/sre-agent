# SRE Agent Test Suite

This directory contains the test suite for the SRE Agent (GCP Observability Analysis Toolkit). The tests have been refactored to mirror the source code structure, ensuring better organization and maintainability.

## 📂 Directory Structure

```text
tests/
├── conftest.py                   # Global fixtures (Mocks, Sample Logs, Synthetic Traces)
├── fixtures/                     # Dynamic synthetic data generators
│   └── synthetic_otel_data.py    # OTel trace data generation utilities
├── unit/                         # FAST: Isolated logic tests (Mirrors source code)
│   └── sre_agent/                # Unit tests for tools, sub-agents, and schemas
│       ├── sub_agents/           # Tests for specialized analysts
│       ├── tools/                # Unit tests for core tools
│       └── ...
├── server/                       # API: Application layer tests
│   ├── test_server.py            # FastAPI endpoint tests
│   ├── test_genui_chat_events.py  # GenUI event streaming tests
│   └── test_cancellation.py      # Request cancellation logic
├── integration/                  # STATE: Database and side-effect tests
│   ├── test_chat_persistence.py  # Session history persistence
│   └── test_session.py           # Session management tests
└── e2e/                          # SLOW: Full end-to-end flows
    ├── test_e2e_cujs.py          # Critical User Journeys
    ├── test_api_flow.py          # API-to-Agent flow tests
    └── ...
```

## 🧪 Test Categories

### 1. Unit Tests (`tests/unit/`)
Isolated logic tests. Fast and comprehensive.
*   **Analysis Logic** (`tools/analysis/`): Tests for statistical analysis, comparison logic, and log pattern extraction.
*   **Infrastructure** (`test_schema.py`, etc.): Tests for schemas, telemetry, and caching.

### 2. Server & API Tests (`tests/server/`)
Tests the application layer and `server.py` integration.
*   **`test_genui_chat_events.py`**: Verifies streaming output and A2UI event injection.

### 3. Integration Tests (`tests/integration/`)
Tests focusing on side effects like session persistence and database state.

### 4. End-to-End Tests (`tests/e2e/`)
Full user journeys and complex orchestration flows.
*   **Clients** (`tools/clients/`): Tests for API interaction, ensuring mocks are used correctly to avoid real network calls.
*   **Infrastructure** (`tools/common/`, `test_schema.py`): Tests for schemas, telemetry, and caching.

## 🛠️ Global Fixtures (`conftest.py`)

The `conftest.py` file provides shared resources available to all tests:
*   **Synthetic Traces/Logs**: Helpers to generate random trace IDs, span IDs, and timestamps.
*   **Sample Data**: Pre-defined log entry payloads (Text, JSON, Proto).
*   **Mock Clients**: Shared mock objects for Cloud Logging, Trace, and BigQuery APIs.

## 🚀 Running the Tests

To run the full test suite (81% Coverage):

```bash
# Run backend tests
uv run pytest

# Run Flutter frontend tests
cd autosre
flutter test

# Run with coverage report
cd ..
uv run pytest --cov=sre_agent --cov-report=term-missing
```

## 📝 Best Practices
*   **Mocks vs. Real APIs**: Use the mocks provided in `conftest.py` to avoid making actual GCP calls during unit tests.
*   **Data Generation**: Use the utilities in `tests/fixtures/synthetic_otel_data.py` for complex trace structures rather than hardcoding large dicts.
*   **Naming**: Prefix test files with `test_` and test functions with `test_` for automatic discovery by `pytest`.
