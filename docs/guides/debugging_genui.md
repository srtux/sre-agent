# Debugging the GenUI/A2UI Protocol

This guide documents known issues and debugging techniques for the GenUI (A2UI) protocol implementation in the Auto SRE Agent.

## 📋 A2UI v0.8 Protocol Compliance

The Auto SRE Agent now follows the **A2UI v0.8 specification** for proper compatibility with the genui package.

### Required Component Format

Each component in a `surfaceUpdate` message MUST have:
- `id`: A unique identifier string
- `component`: An object wrapping the actual component type

```json
{
  "surfaceUpdate": {
    "surfaceId": "unique-surface-id",
    "components": [
      {
        "id": "component-unique-id",
        "component": {
          "x-sre-tool-log": {
            "tool_name": "fetch_trace",
            "args": {"trace_id": "abc123"},
            "status": "running"
          }
        }
      }
    ]
  }
}
```

### Required beginRendering Format

The `beginRendering` message MUST include a `root` field pointing to the root component ID:

```json
{
  "beginRendering": {
    "surfaceId": "unique-surface-id",
    "root": "component-unique-id"
  }
}
```

## ⚠️ Known Issues

### 1. Component Format Mismatch (RESOLVED)

**Previous Problem**:
The backend was sending components without the required `id` and `component` wrapper fields.

**Previous Incorrect Format**:
```python
# Old (incorrect) - Missing id and component wrapper
"components": [
    {
        "x-sre-tool-log": { ... }
    }
]
```

**Current Correct Format (A2UI v0.8)**:
```python
# New (correct) - Has id and component wrapper
"components": [
    {
        "id": "tool-log-abc12345",
        "component": {
            "x-sre-tool-log": { ... }
        }
    }
]
```

**Symptoms (if regression occurs)**:
- Tool call widgets (e.g., "Thinking...", "Running tool...") do not appear in the chat stream.
- No client-side errors in the browser console (the event is simply ignored or parsed as empty).
- Backend logs show successful event yielding.

**Prevention**:
- The `autosre/lib/catalog.dart` has defensive code (`_unwrapComponentData()`) to handle multiple formats.
- Tests in `tests/sre_agent/api/test_tool_events.py` verify A2UI v0.8 compliance.

### 2. "Ghost Bubbles" & Race Conditions (RESOLVED)

**Problem**:
Surface bubbles would sometimes appear empty ("Ghost Bubbles") or duplicated. This was caused by the UI marker (`{"type": "ui", "surface_id": "..."}`) arriving at the frontend before the actual component data (`beginRendering`). The frontend would create a bubble for the ID, but since the data hadn't arrived, it rendered nothing.

**Current Solution (Sequencing)**:
The backend MUST yield the A2UI data events **BEFORE** yielding the UI marker. This ensures that when the frontend creates the `GenUiSurface` bubble, the data is already registered in the `A2uiMessageProcessor`.

```python
# Optimal Yield Sequence (sre_agent/api/routers/agent.py)
# 1. Yield A2UI metadata/data first
for evt_str in events:
    yield evt_str + "\n"

# 2. Yield UI marker second (this triggers the visual bubble)
yield json.dumps({"type": "ui", "surface_id": surface_id}) + "\n"
```

### 3. Root-Level type Promotion (A2UI v0.8+)

For specialized widgets (charts, traces), we now promote the `type` field to the root level of the component object. This helps the `CatalogRegistry` match the widget correctly without deep-diving into nested keys.

```json
{
  "id": "chart-123",
  "type": "x-sre-metric-chart",  // Root-level promotion
  "component": {
    "type": "x-sre-metric-chart",
    "x-sre-metric-chart": { ... data ... }
  }
}
```

### 4. Sub-Agent Delegation & Policy Rejections

When a tool call is rejected by the `PolicyEngine` (e.g., restricted access or disabled tool), the `Runner` MUST still yield a `function_response` event to the ADK loop.

**Why**: If a `function_call` is emitted but no `function_response` follows, the ADK event history becomes inconsistent, leading to a `ValueError: No function call event found for function responses`.

**Guideline**: Always catch rejections and yield a dummy "error" response to satisfy the framework's state machine.

---

## 🏗️ World-Class Platform Patterns

### 1. "Verify-then-Query" Anti-Hallucination
Before the agent queries a specific metric, it should use `list_metric_descriptors` to verify the exact string name (e.g., `kubernetes.io/container/cpu/core_usage_time` vs `usage_time`). This prevents 404s and hallucinated metric names.

### 2. Reactive Errors & Hints
Monitoring tools now include **Smart Error Hints**. If a query fails with a 400 (Bad Request), the tool adds a context-aware HINT (e.g., "Your query looks like MQL but this tool requires PromQL") to help the agent self-correct.

---

## 🔍 Debugging Techniques

### 1. Debugging Backend Events (Event Loop)

If events are missing from the stream, add print debugging to the main event loop in `sre_agent/api/routers/agent.py`.
**Note**: Use `print()` instead of `logger.debug()` if looking for immediate terminal output in `uv run poe dev`, as logging might be buffered or filtered.

```python
# sre_agent/api/routers/agent.py

async for event in root_agent.run_async(inv_ctx):
    print(f"DEBUG: 📥 Event: type={type(event)}")

    # ... inside the parts processing loop ...
    for part in parts:
        print(f"DEBUG: 🔍 Processing part: type={type(part)}")
        if hasattr(part, "function_call"):
             print(f"DEBUG: Part has function_call: {part.function_call}")
```

### 2. Debugging Frontend Rendering (Catalog)

If the backend claims to send an event but it doesn't render, inspect the `CatalogItem` builder in `autosre/lib/catalog.dart`.

```dart
// autosre/lib/catalog.dart

CatalogItem(
  name: "x-sre-tool-log",
  widgetBuilder: (context) {
    print("DEBUG: x-sre-tool-log builder called");
    print("DEBUG: Data received: ${context.data}");
    // ...
  }
)
```

**Viewing Logs**:
- When running `uv run poe dev`, Flutter logs (stdout) should appear in the terminal console alongside backend logs.
- If running in Chrome context, use `F12` DevTools Console.

### 3. Restarting the Environment

The `uv run poe dev` command orchestrates both backend (Python) and frontend (Flutter).
- **Backend Changes**: Usually require a restart if `uvicorn` reload is not active or if `agent.py` logic (which is often cached) is modified.
- **Frontend Changes**: Dart code changes require a full rebuild/restart of the Flutter process (`kill` port 8080 and restart `poe dev`) to be absolutely sure. 'Hot Restart' (r) is available if you run `flutter run` manually, but `poe dev` wraps it.
