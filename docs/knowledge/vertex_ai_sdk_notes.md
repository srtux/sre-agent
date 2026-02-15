# Vertex AI Agent Engine SDK Findings

## `AgentEngine` Method Availability (GA)

**Date**: 2026-01-25 (updated 2026-02-15)
**SDK Version**: `google-cloud-aiplatform[adk,agent-engines]>=1.93.0` (pinned to `1.134.0` for deployment)
**ADK Version**: `google-adk>=1.23.0` (pinned to `1.23.0` for deployment)
**Pydantic Version**: `pydantic>=2.10.6` (pinned to `2.12.5` for deployment)

### Issue
When interacting with a deployed Agent Engine resource using `vertexai.agent_engines.get(...)`, the returned `AgentEngine` object may interact differently than previous Preview versions. Specifically, code expecting a synchronous `.query()` method may fail with an `AttributeError`.

### Findings
Introspection of the `AgentEngine` object returned by the GA SDK reveals:

1.  **Missing `query`**: The synchronous `.query()` method is NOT present on the `AgentEngine` object by default in some contexts.
2.  **Available Methods**: The object explicitly exposes:
    *   `async_stream_query(**kwargs) -> AsyncIterable`
    *   `stream_query(**kwargs) -> Iterable`
    *   `list_sessions`, `delete_session`, etc.

### Proper Usage
The correct way to stream responses from a deployed agent is to use `async_stream_query` (for async applications) or `stream_query` (for sync applications).

> [!IMPORTANT]
> The query argument must be named `message` (not `input`), and it must be passed as a **keyword-only** argument.

**Incorrect (Legacy/Preview):**
```python
# Fails because 'input' is not an expected keyword
response = agent.async_stream_query(input="Hello", ...)
```

**Correct (GA):**
```python
# Async Streaming
stream = agent.async_stream_query(
    message="Hello",  # MUST use 'message='
    user_id="user-123",
    session_id="session-456"
)
async for event in stream:
    print(event)
```

> [!NOTE]
> `stream_query` is currently deprecated in the `vertexai` template in favor of `async_stream_query`. It is recommended to use the `async` version whenever possible.

### Reference Implementation
See `sre_agent/services/agent_engine_client.py` for a production-grade implementation that handles:
*   Dynamic method checking (using `hasattr`).
*   Precedence of `async_stream_query` over `stream_query`, with fallback to sync `query`.
*   Correct `message` keyword-only argument propagation.
*   Event dictionary processing support for JSON serialization (via `model_dump`, `to_dict`, or raw dict).
*   Graceful error handling for malformed JSON streaming responses (`ValueError`).
*   Handling of invalid response formats where SDK expects dict but receives list (`AttributeError`).
*   Singleton pattern via `get_agent_engine_client()` for reuse across requests.

---

## Deployment Architecture

**Date**: 2026-02-15
**Reference**: `deploy/deploy.py`

### Agent Wrapping for Deployment

The agent is **not** deployed directly. Instead, it is wrapped in a `RunnerAgentAdapter` before being passed to `AdkApp`:

```python
from sre_agent.agent import root_agent
from sre_agent.core.runner import create_runner
from sre_agent.core.runner_adapter import RunnerAgentAdapter
from vertexai.agent_engines import AdkApp

runner = create_runner(root_agent)
adapter = RunnerAgentAdapter(runner, name=root_agent.name)
adk_app = AdkApp(agent=adapter)
```

This wrapping ensures stateless execution, policy enforcement, and context compaction in the remote Agent Engine environment.

### JSON Schema Feature Flag

Before importing the agent module, the deployment script enables a critical feature flag:

```python
from google.adk.features import FeatureName, override_feature_enabled
override_feature_enabled(FeatureName.JSON_SCHEMA_FOR_FUNC_DECL, True)
```

This ensures tool schemas use camelCase (`additionalProperties`) instead of snake_case, which is required for Vertex AI API compatibility. The same flag is also set in `sre_agent/api/app.py` for the local FastAPI server.

### Deployment Modes

The deployment script supports two SDK paths:

| Mode | API Version | Use Case |
|------|-------------|----------|
| **Standard** (`--use_agent_identity=false`) | GA `vertexai.agent_engines` | Default deployment, uses service account |
| **Agent Identity** (`--use_agent_identity=true`) | `v1beta1` via `vertexai.Client()` | Enables per-user identity (EUC), no service account |

When Agent Identity is enabled, a `vertexai.Client` is created with `http_options=dict(api_version="v1beta1")` and the `identity_type` is set to `types.IdentityType.AGENT_IDENTITY`.

### Pinned Deployment Dependencies

The deployment script pins exact versions of critical packages to avoid compatibility issues. These pins override the ranges in `pyproject.toml`:

| Package | Pinned Version | `pyproject.toml` Range |
|---------|---------------|----------------------|
| `google-adk` | `1.23.0` | `>=1.23.0` |
| `google-cloud-aiplatform` | `1.134.0` | `>=1.93.0` |
| `google-genai` | `1.59.0` | `>=1.9.0` |
| `pydantic` | `2.12.5` | `>=2.10.6` |
| `mcp` | `1.25.0` | `>=0.1.0` |
| `opentelemetry-instrumentation-google-genai` | `0.6b0` | `>=0.5.0` |

FastAPI, uvicorn, and other server-only dependencies are **excluded** from Agent Engine deployment since the Agent Engine provides its own serving infrastructure.

### Environment Variables Propagated to Agent Engine

The deployment script propagates both required and optional environment variables. Key propagated variables include:

*   `RUNNING_IN_AGENT_ENGINE=true` -- Signals to `model_config.py` that the agent is running in the cloud.
*   `GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY=true` -- Enables native telemetry.
*   `ADK_OTEL_TO_CLOUD=true` -- Routes OpenTelemetry data to Cloud Trace/Logging.
*   `STRICT_EUC_ENFORCEMENT` -- Controls whether ADC fallback is blocked.
*   `SRE_AGENT_ENFORCE_POLICY` -- Enables safety guardrails.
*   `SRE_AGENT_COUNCIL_ORCHESTRATOR` -- Enables the Council of Experts architecture.
*   `SRE_AGENT_SLIM_TOOLS` -- Reduces root agent tools to ~20.
*   `SRE_AGENT_ID` -- Set to the existing resource name when updating (not creating) an agent.

### Concurrent Update Handling

The deployment script retries on `InvalidArgument` errors (HTTP 400) which Vertex AI returns when an update is already in progress. It retries up to 12 times with 60-second intervals (12 minutes total). Permanent build failures (containing `"Build failed"`) are not retried.

---

## Model Configuration

**Date**: 2026-02-15
**Reference**: `sre_agent/model_config.py`

### Model Selection

The `get_model_name(capability)` function returns the model name based on the requested capability:

| Capability | Model | Use Case |
|-----------|-------|----------|
| `"fast"` | `gemini-2.5-flash` | Simple tasks, sub-agent panels, low-latency queries |
| `"deep"` | `gemini-2.5-pro` | Reasoning, root cause analysis, complex synthesis |

Both local development and Agent Engine environments use the same model names. The environment is detected via the `RUNNING_IN_AGENT_ENGINE` environment variable.

---

## Context Caching (OPT-10)

**Date**: 2026-02-15
**Reference**: `sre_agent/model_config.py`

### Overview

Vertex AI context caching stores static system prompt prefixes on the server, reducing input token costs by up to **75%** for repeated calls. This is particularly valuable for the SRE Agent, which has a large system prompt (~1,000+ tokens) that is sent on every turn.

### Configuration

| Environment Variable | Purpose | Default |
|---------------------|---------|---------|
| `SRE_AGENT_CONTEXT_CACHING` | Enable/disable context caching | `false` |
| `SRE_AGENT_CONTEXT_CACHE_TTL` | TTL for cached context in seconds | `3600` (1 hour) |

### How It Works

1.  Enable via `SRE_AGENT_CONTEXT_CACHING=true`.
2.  Call `get_context_cache_config()` to obtain the caching configuration dict.
3.  The caller creates a `CachedContent` object using the Vertex AI SDK:

```python
from sre_agent.model_config import get_context_cache_config, get_model_name

config = get_context_cache_config()
if config:
    from vertexai.caching import CachedContent
    cached = CachedContent.create(
        model_name=get_model_name("fast"),
        system_instruction=config["system_instruction"],
        ttl=config["ttl_seconds"],
    )
    # Use cached.resource_name in subsequent model calls
```

### Important Constraints

*   Only **static** portions of the system prompt should be cached. Dynamic elements (timestamps, session-specific context, user project IDs) must be excluded.
*   The default TTL of 1 hour covers most investigation sessions.
*   Context caching is propagated to Agent Engine via the `SRE_AGENT_CONTEXT_CACHE_TTL` environment variable in `deploy/deploy.py`.

---

## ADK 1.23.0 + Pydantic 2.12+ Compatibility Monkeypatch

**Date**: 2026-02-15
**Reference**: `sre_agent/api/app.py` (`_patch_pydantic` function)

### Problem

ADK 1.23.0 passes `config=pydantic.ConfigDict(arbitrary_types_allowed=True)` to `pydantic.TypeAdapter.__init__()`. Starting with Pydantic 2.12, this raises a `PydanticUserError` if the type being adapted is already a `BaseModel` subclass (since BaseModel subclasses carry their own `model_config`).

### Workaround

A monkeypatch in `sre_agent/api/app.py` intercepts `TypeAdapter.__init__()` and strips the `config` argument when the type is a `BaseModel` subclass:

```python
def _patch_pydantic() -> None:
    original_init = TypeAdapter.__init__

    def new_init(self, type, *, config=None, _parent_depth=2, module=None):
        if config is not None:
            if inspect.isclass(type) and issubclass(type, pydantic.BaseModel):
                config = None  # Let BaseModel's own config take precedence
        return original_init(self, type, config=config, ...)

    TypeAdapter.__init__ = new_init
```

> [!WARNING]
> Do **not** remove this patch until ADK is updated to handle Pydantic 2.12+ natively. The patch is applied in both `sre_agent/api/app.py` (FastAPI server) and is needed wherever ADK introspects tool schemas.

### Additional Patches

Two other patches are applied alongside the Pydantic patch:

1.  **MCP Pydantic bridge** (`_apply_mcp_patch`): Adds `__get_pydantic_core_schema__` to `mcp.client.session.ClientSession` so it can be used in Pydantic models.
2.  **JSON Schema feature flag** (`_enable_json_schema_feature`): Enables `FeatureName.JSON_SCHEMA_FOR_FUNC_DECL` to ensure camelCase schema keys for Vertex AI compatibility.

---

## Dual-Mode Execution (Local vs Remote)

**Date**: 2026-02-15
**Reference**: `sre_agent/services/agent_engine_client.py`

### Detection

The execution mode is determined by the `SRE_AGENT_ID` environment variable:

| `SRE_AGENT_ID` | Mode | Behavior |
|----------------|------|----------|
| Not set | **Local** | Agent runs in-process within FastAPI |
| Set (resource name or ID) | **Remote** | Requests forwarded to Vertex AI Agent Engine |

The `is_remote_mode()` function provides a simple boolean check.

### Resource Name Parsing

`SRE_AGENT_ID` accepts two formats:

1.  **Full resource name**: `projects/{project}/locations/{location}/reasoningEngines/{id}` -- project and location are extracted automatically.
2.  **Bare ID**: Combined with `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` (or `AGENT_ENGINE_LOCATION`, or fallback `us-central1`).

### API Key Conflict Resolution

The `google-genai` SDK fails if both project/location AND an API key (`GOOGLE_API_KEY` or `GEMINI_API_KEY`) are present. Both the `AgentEngineClient` and the FastAPI app's `_initialize_vertex_ai()` function unset these API keys to favor project-based (ADC/EUC) authentication when Agent Engine mode is active.

### EUC Credential Propagation (Remote Mode)

In remote mode, user credentials are propagated via session state:

1.  Proxy extracts OAuth token from `Authorization` header.
2.  Session state is updated with `_user_access_token` (encrypted via `encrypt_token`) and `_user_project_id`.
3.  Agent Engine loads session state on each query.
4.  Tools read credentials via `get_credentials_from_tool_context()`.
