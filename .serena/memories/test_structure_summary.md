# SRE Agent Test Structure and Patterns Summary

## Overview
- **Total Test Files**: 145
- **Test Classes**: 195
- **Async Tests**: 296 tests marked with `@pytest.mark.asyncio`
- **Fixtures Defined**: 102 pytest fixtures
- **Mocking Approaches**: Heavy use of `MagicMock`, `AsyncMock`, and `@patch` decorators

## Directory Structure

```
tests/
├── conftest.py                 # Global fixtures for all tests
├── fixtures/                   # Synthetic data generators
│   └── synthetic_otel_data.py # OTel trace/span generation factories
├── unit/                       # Fast isolated logic tests (mirrors source structure)
│   └── sre_agent/
│       ├── tools/              # 38 test files for tool analysis logic
│       │   ├── analysis/       # Trace, logs, metrics, correlation, remediation analysis
│       │   ├── clients/        # Client mocking tests (trace, logging, monitoring, SLO, etc.)
│       │   ├── mcp/            # MCP orchestration and GCP auth
│       │   ├── common/         # Cache, decorators, telemetry, serialization
│       │   ├── discovery/      # Telemetry source discovery
│       │   ├── bigquery/       # BigQuery schema and query tests
│       │   └── test_investigation.py  # Investigation state tracking
│       ├── api/                # API layer tests
│       │   ├── routers/        # Router endpoint tests
│       │   └── helpers/        # Tool events, trace links
│       ├── memory/             # Memory service tests
│       ├── services/           # Service layer tests
│       ├── sub_agents/         # Specialized analyst sub-agent tests
│       ├── core/               # Core runner, policy, circuit breaker tests
│       └── models/             # Schema validation tests
├── integration/                # Stateful tests (sessions, persistence)
├── e2e/                        # Full end-to-end workflow tests
├── server/                     # FastAPI server and event streaming tests
└── README.md                   # Test organization documentation
```

## Test Categories

### 1. Unit Tests (Fast, Isolated Logic)
Located in `tests/unit/sre_agent/tools/`

**Analysis Tools (38 test files)**:
- **Trace Analysis**: Pattern matching, statistical analysis, comparison logic, edge cases
  - `test_trace_analysis.py` - Call graphs, span durations, error extraction
  - `test_patterns.py` - Latency patterns, error patterns
  - `test_statistical_analysis.py` - Percentile calculations, outlier detection
  - `test_comparison_logic.py` - Baseline vs incident comparison
  
- **Log Analysis**: Message extraction, pattern detection
  - `test_extraction.py` - TextPayload, JsonPayload, ProtoPayload extraction
  - `test_patterns.py` - Log pattern detection and anomaly identification
  
- **Correlation & Correlation**: Cross-signal analysis
  - `test_cross_signal.py` - Metric + log + trace correlation
  - `test_dependencies.py` - Service dependency analysis
  - `test_critical_path.py` - Critical path identification
  
- **Remediation**: Suggestion generation, postmortem analysis
  - `test_suggestions.py` - Remedy suggestion logic
  - `test_postmortem.py` - Post-incident analysis
  
- **BigQuery**: Schema-aware queries
  - `test_bigquery_otel.py` - OTel trace schema querying
  - `test_logs.py` - Log querying
  
- **SLO & Metrics**: Burn rate, metric analysis
  - `test_burn_rate.py` - SLO burn rate calculations
  - `test_metrics_analysis.py` - Metric time-series analysis

**Client Tests**:
- `test_trace.py` - Trace client (Cloud Trace API)
- `test_logging.py` - Logging client (Cloud Logging API)
- `test_monitoring.py` - Monitoring client (Cloud Monitoring API)
- `test_alerts.py` - Alert client
- `test_slo.py` - SLO client
- `test_trace_selection_logic.py` - Trace sampling/selection logic
- `test_gcp_projects.py` - GCP project enumeration
- `test_gke.py` - GKE cluster querying

**Tool Connectivity**:
- `test_test_functions.py` - Health checks for tool availability

**Infrastructure**:
- `test_schema.py` - Pydantic model validation
- `test_auth.py` - Authentication and credentials
- `test_memory_integration.py` - Memory service integration
- `test_investigation.py` - Investigation state tracking

### 2. Integration Tests (Stateful, Side Effects)
Located in `tests/integration/`
- `test_session.py` - Session initialization and management
- `test_chat_persistence.py` - Chat history persistence
- `test_auth_integration.py` - Auth flow integration
- `test_api_pipeline.py` - Full API request/response pipeline
- `test_middleware_integration.py` - Middleware stacking

### 3. E2E Tests (Slow, Full Workflows)
Located in `tests/e2e/`
- `test_agent_integration.py` - Agent initialization and tool availability
- `test_api_flow.py` - End-to-end API flow
- `test_analysis_e2e.py` - Full analysis pipeline
- `test_auth_flow.py` - Complete authentication flow
- `test_e2e_cujs.py` - Critical User Journeys
- `test_investigation_pipeline.py` - Investigation state transitions
- `test_trace_selection.py` - Trace selection and filtering

### 4. Server Tests (API Layer)
Located in `tests/server/`
- `test_server.py` - FastAPI endpoint tests
- `test_genui_chat_events.py` - GenUI event streaming
- `test_cancellation.py` - Request cancellation handling
- `test_widget_logic.py` - UI widget logic
- `test_session_rename.py` - Session operations

## Test Patterns

### Global Fixtures (conftest.py)

**Helper Functions**:
```python
@pytest.fixture(scope="session", autouse=True)
def sanitize_environment():
    """Sanitize env vars to avoid client conflicts"""

def generate_trace_id() -> str
def generate_span_id() -> str
def generate_timestamp(base_time=None, offset_seconds=0) -> str
```

**Data Fixtures**:
- `sample_text_payload_logs()` - Text log entries
- `sample_json_payload_logs()` - JSON log entries
- `sample_proto_payload_logs()` - Audit logs (protoPayload)
- `mixed_payload_logs()` - Multiple payload types
- `baseline_period_logs()` - Normal operation logs
- `incident_period_logs()` - Error pattern logs
- `sample_trace_spans()` - Trace span objects

**Mock Fixtures**:
- `mock_logging_client()` - Cloud Logging mock
- `mock_trace_client()` - Cloud Trace mock
- `mock_bigquery_client()` - BigQuery mock
- `mock_tool_context()` - ADK ToolContext mock

### Mocking Patterns

**Standard Approach**:
```python
from unittest.mock import MagicMock, AsyncMock, patch

@pytest.mark.asyncio
@patch("module.function")
async def test_something(mock_function):
    mock_function.return_value = {"status": "success"}
    result = await target_function()
    assert result.status == ToolStatus.SUCCESS
```

**Async Mocking**:
```python
@pytest.mark.asyncio
async def test_async_tool(mock_tool_context):
    mock_service = AsyncMock()
    mock_service.run_async.return_value = {"data": "value"}
    
    with patch("module.ServiceClass", return_value=mock_service):
        result = await async_function()
```

**Context Manager Mocking**:
```python
with patch("module.func1") as mock1, \
     patch("module.func2") as mock2:
    mock1.return_value = data
    mock2.side_effect = [value1, value2, value3]
    result = function_under_test()
```

**Time Mocking** (for cache/TTL testing):
```python
@pytest.fixture()
def fixed_time(monkeypatch):
    ft = FixedTime()
    # Patch datetime.now(timezone.utc)
    return ft

def test_cache_expiry(fixed_time):
    cache.put("key", "value")
    fixed_time.advance(11)  # Advance 11 seconds
    assert cache.get("key") is None  # Expired
```

### Test Classes

**Class-based Tests** (195 test classes):
```python
class TestComponentName:
    @pytest.mark.asyncio
    async def test_success_case(self, fixture1):
        """Test description"""
        
    @pytest.mark.asyncio
    async def test_error_case(self):
        """Test description"""
```

- Organized by component/module
- Clear method naming: `test_<scenario>` or `test_<method>_<case>`
- Each test verifies a single behavior

### Synthetic Data Generators (fixtures/synthetic_otel_data.py)

**Trace/Span Builders**:
- `SpanEventGenerator` - Exception and log events
- `SpanLinkGenerator` - Span links and relationships
- `TraceFactory` - Complete trace generation with configurable structure

**Data Generation**:
```python
def generate_trace_id() -> str  # 128-bit hex
def generate_span_id() -> str   # 64-bit hex
def generate_timestamp(base_time=None, offset_seconds=0) -> str  # ISO format
def generate_random_string(length=10) -> str  # Random alphanumeric
```

## Test Coverage Statistics

### By Category:
- **Analysis Tools**: 38 test files covering trace, log, metric, correlation analysis
- **Clients**: ~10 test files for API client mocking
- **Infrastructure**: Core schema, auth, memory, investigation state
- **Integration**: ~5 test files for database/persistence
- **E2E**: ~9 test files for full workflows
- **Server**: ~6 test files for API layer

### Key Patterns:
- **Async/Await**: 296 async tests with `@pytest.mark.asyncio`
- **Mocking**: Heavy `patch()`, `MagicMock`, `AsyncMock` usage
- **Response Validation**: `assert result.status == ToolStatus.SUCCESS/ERROR`
- **Error Cases**: Edge cases and error scenarios in dedicated test methods
- **Fixtures**: Both global (conftest.py) and local file-level fixtures

## Tool/Agent Test Coverage

### Covered Tools:
1. **Trace Analysis** - Complete coverage of analysis logic
2. **Log Analysis** - Extraction and pattern detection
3. **Metric Analysis** - Time-series and correlation
4. **Discovery** - Telemetry source detection
5. **Investigation State** - State tracking and transitions
6. **Client Operations** - API client mocking
7. **BigQuery** - Schema and query validation
8. **SLO Analysis** - Burn rate calculations

### Exploration/Query Functionality:
- **Trace Selection** (`test_trace_selection_logic.py`):
  - Finding example traces (baseline + anomaly)
  - Trace URL parsing and fetching
  - Error trace vs normal trace classification
  
- **Discovery** (`test_discovery_tool.py`):
  - Dataset enumeration
  - Table discovery (_AllSpans, _AllLogs)
  - Fallback mode handling
  
- **Investigation** (`test_investigation.py`):
  - State phase tracking (triage → deep_dive → remediation)
  - Finding persistence
  - Hypothesis tracking

## Key Testing Principles (from CLAUDE.md)

1. **Read before modifying** - Tests serve as documentation
2. **Test first** - Create tests before implementing features
3. **Explicit types** - No implicit `Any`; Pydantic `frozen=True, extra="forbid"`
4. **Coverage gate** - 80% minimum; 100% on new tools and core logic
5. **Async I/O** - All external API calls use `async/await`
6. **Imports** - Prefer absolute imports (`from sre_agent.X import Y`)

## Best Practices Observed

1. **Fixtures**: Reusable across test files via conftest.py
2. **Mocking**: Isolate external dependencies (GCP APIs, databases)
3. **Parameterization**: Edge cases in separate test methods
4. **Naming**: Clear `test_<scenario>_<outcome>` convention
5. **Response Validation**: Always check `status`, `result`, and `error` fields
6. **Time Control**: Use `monkeypatch` for deterministic time-based tests
7. **Synthetic Data**: Factory functions for complex OTel structures
