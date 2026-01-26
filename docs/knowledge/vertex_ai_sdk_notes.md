# Vertex AI Agent Engine SDK Findings

## `AgentEngine` Method Availability (GA)

**Date**: 2026-01-25
**SDK Version**: `vertexai` (Generic Availability release)

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
*   Precedence of `async_stream_query` over `stream_query`.
*   Correct `message` keyword-only argument propagation.
*   Event dictionary processing support for JSON serialization.
