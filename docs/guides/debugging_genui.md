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
