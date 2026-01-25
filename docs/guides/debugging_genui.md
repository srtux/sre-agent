# Debugging the GenUI/A2UI Protocol

This guide documents known issues and debugging techniques for the GenUI (A2UI) protocol implementation in the Auto SRE Agent.

## ⚠️ Known Issues

### 1. The "Component Wrapper" Mismatch

**Problem**:
The GenUI frontend library and the `autosre` implementation have a subtle but critical expectation regarding the JSON structure of tool events.
- **Backend Tests (Historical)**: Often enforced a nested structure: `{"component": {"x-sre-tool-log": {...}}}`.
- **Frontend (`autosre`)**: Expects a flattened structure: `{"x-sre-tool-log": {...}}`.

**Symptoms**:
- Tool call widgets (e.g., "Thinking...", "Running tool...") do not appear in the chat stream.
- No client-side errors in the browser console (the event is simply ignored or parsed as empty).
- Backend logs show successful event yielding.

**Resolution**:
Ensure the backend sends the flattened structure.
```python
# Correct (sre_agent/api/helpers/__init__.py)
"components": [
    {
        "x-sre-tool-log": { ... }
    }
]

# Incorrect (Legacy/Broken)
"components": [
    {
        "component": {
            "x-sre-tool-log": { ... }
        }
    }
]
```

**Prevention**:
- Always verify `autosre/lib/catalog.dart`'s `widgetBuilder` logic if you suspect a protocol mismatch.
- The `autosre` catalog now has defensive code to handle both, but the backend *must* default to the flattened structure for compatibility with standard GenUI behaviors.

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
