# Debugging the GenUI/A2UI Protocol

This guide documents known issues and debugging techniques for the GenUI (A2UI) protocol implementation in the Auto SRE Agent. For a comprehensive overview of the architecture and component schemas, see **[Rendering Telemetry](rendering_telemetry.md)**.

## A2UI v0.8 Protocol Compliance

The Auto SRE Agent follows the **A2UI v0.8 specification** for proper compatibility with the genui package.

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

---

## Known Issues

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
- Tests in `tests/server/test_genui_chat_events.py` and `tests/server/test_widget_logic.py` verify A2UI v0.8 compliance.

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
  "type": "x-sre-metric-chart",
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

### 5. Dashboard Event Duplication

**Problem**: When tool results are emitted both inline (from the event stream in `agent.py`) and via the dashboard queue (from `@adk_tool` decorator), the same dashboard event can appear twice on the frontend.

**Current Solution**: The `event_generator()` in `sre_agent/api/routers/agent.py` tracks `inline_emitted_counts` per tool name. When draining the dashboard queue, it skips entries already emitted inline. See the `drain_dashboard_queue()` loop in the agent router.

**Symptoms (if regression occurs)**:
- Duplicate panels in the dashboard (e.g., two identical trace panels).
- Check backend logs for `Dashboard event (inline)` and `Dashboard event (queued)` -- if both appear for the same tool call, deduplication may have failed.

### 6. Dashboard Query Language Confusion (MQL vs PromQL)

**Problem**: The agent LLM sometimes generates MQL (Monitoring Query Language) syntax when the `query_promql` tool expects PromQL, or vice versa.

**Symptoms**:
- 400 Bad Request errors from the Cloud Monitoring API.
- Error messages containing `HINT: Your query looks like MQL. This tool ONLY supports PromQL.`
- Queries containing `fetch_gcp_metric` or `::` (MQL indicators) sent to the PromQL endpoint.

**Current Mitigation** (in `sre_agent/tools/clients/monitoring.py`):
- Smart error hints detect MQL-in-PromQL and PromQL-in-MQL confusion.
- The tool appends context-aware HINT messages to error responses, helping the agent self-correct on retry.
- Additional hints for common mistakes like `instance_name` vs `instance_id` in GCE metrics.

**Debugging**:
```bash
# Check for query language errors in logs
LOG_LEVEL=DEBUG uv run poe web
# Look for lines containing "HINT:" or "400" in the monitoring tool output
```

---

## World-Class Platform Patterns

### 1. "Verify-then-Query" Anti-Hallucination
Before the agent queries a specific metric, it should use `list_metric_descriptors` to verify the exact string name (e.g., `kubernetes.io/container/cpu/core_usage_time` vs `usage_time`). This prevents 404s and hallucinated metric names.

### 2. Reactive Errors & Hints
Monitoring tools include **Smart Error Hints**. If a query fails with a 400 (Bad Request), the tool adds a context-aware HINT to help the agent self-correct:
- MQL syntax detected in PromQL tool: `"Your query looks like MQL. This tool ONLY supports PromQL."`
- Invalid OR between metric types: `"'list_time_series' does not support OR between metric types."`
- GCE label confusion: `"For GCE instance metrics, use 'instance_id' instead of 'instance_name'."`
- Histogram quantile issues: `"histogram_quantile requires sum by (le, ...)."`

---

## Debugging Techniques

### 1. Comprehensive A2UI Debug Mode (RECOMMENDED)

The codebase includes a comprehensive A2UI debugging system that can be enabled via environment variable. This provides detailed logging across the entire A2UI pipeline:

**Enable Debug Mode:**

```bash
# Linux/Mac
export A2UI_DEBUG=true
uv run poe dev

# Or inline
A2UI_DEBUG=true uv run poe dev
```

**What gets logged when A2UI_DEBUG=true:**

| Location | Log Prefix | What it shows |
|----------|-----------|---------------|
| Backend: Tool Event Helpers | `A2UI_DEBUG:` | Event creation, component structure, surface IDs |
| Backend: Agent Router | `A2UI_ROUTER:` | Event yielding, NDJSON stream output |
| Frontend: ContentGenerator | `[A2UI #N]` | A2UI message parsing, beginRendering/surfaceUpdate details |
| Frontend: ContentGenerator | `[UI #N]` | UI marker reception, surface ID association |
| Frontend: Catalog | `[UNWRAP #N]` | Component data unwrapping strategy used |
| Frontend: ConversationPage | `[CONV]` / `[CONV_A2UI]` | Message processing callbacks |

**Example Debug Output (Backend):**

```
A2UI_DEBUG: [TOOL_CALL_START] Creating tool call event
{
  "tool_name": "fetch_trace",
  "surface_id": "abc123-...",
  "component_id": "tool-log-abc12345",
  "args_preview": "{\"trace_id\": \"123\"}"
}
A2UI_DEBUG: [TOOL_CALL_EVENT] Created beginRendering event
{
  "surface_id": "abc123-...",
  "event_type": "beginRendering",
  "component_type": "x-sre-tool-log",
  "event_size_bytes": 456
}
A2UI_ROUTER: [ROUTER_FC_YIELD_A2UI] Yielding A2UI event 1/1
A2UI_ROUTER: [ROUTER_FC_YIELD_UI] Yielding UI marker
```

**Example Debug Output (Frontend - Browser Console/F12):**

```
[LINE 5] Received: {"type":"a2ui","message":{"beginRendering":{...}}}
[LINE 5] Parsed type: a2ui
[A2UI #1] ===== A2UI MESSAGE RECEIVED =====
[A2UI #1] Type: beginRendering
[A2UI #1] surfaceId: abc123-...
[A2UI #1] Component[0] id: tool-log-abc12345
[A2UI #1] Component[0] type: x-sre-tool-log
[A2UI #1] Emitted to stream
[UI #1] ===== UI MARKER RECEIVED =====
[UI #1] surface_id: abc123-...
[UNWRAP #1] ===== _unwrapComponentData START =====
[UNWRAP #1] componentName: x-sre-tool-log
[UNWRAP #1] Strategy 2: Component wrapper type matches
```

**Debug Log Tags Reference:**

| Tag | Meaning |
|-----|---------|
| `[TOOL_CALL_*]` | Tool call event creation |
| `[TOOL_RESPONSE_*]` | Tool response event creation |
| `[WIDGET_*]` | Visualization widget creation |
| `[ROUTER_FC_*]` | Router function call handling |
| `[ROUTER_FR_*]` | Router function response handling |
| `[A2UI #N]` | Frontend A2UI message N |
| `[UI #N]` | Frontend UI marker N |
| `[UNWRAP #N]` | Catalog unwrap operation N |
| `[CONV_*]` | Conversation page processing |

### 2. DEBUG_UI_TEST Mode

The agent router includes a built-in test mode for verifying the full A2UI pipeline end-to-end. Send a message containing `DEBUG_UI_TEST` to trigger a mock sequence:

```
# In the chat UI, type:
DEBUG_UI_TEST
```

This produces:
1. A tool-log component (alias test) with beginRendering + surfaceUpdate flow.
2. A core button component test.
3. Proper sequencing verification (DATA before MARKER).

Check the backend logs for `Triggering DEBUG_UI_TEST mock sequence` to confirm activation.

### 3. Manual Backend Event Debugging

If you need more granular control, add print debugging to the main event loop in `sre_agent/api/routers/agent.py`.
**Note**: Use `print()` instead of `logger.debug()` if looking for immediate terminal output in `uv run poe dev`, as logging might be buffered or filtered.

```python
# sre_agent/api/routers/agent.py

async for event in runner.run_turn(session=active_session, ...):
    print(f"DEBUG: Event: type={type(event)}")

    # ... inside the parts processing loop ...
    for part in parts:
        print(f"DEBUG: Processing part: type={type(part)}")
        if hasattr(part, "function_call"):
             print(f"DEBUG: Part has function_call: {part.function_call}")
```

### 4. Manual Frontend Rendering Debugging (Catalog)

The catalog includes debugging in `_unwrapComponentData()`. Check the browser console (F12) for logs related to `UNWRAP`.

The `_unwrapComponentData()` function in `autosre/lib/catalog.dart` tries four strategies in order:
1. **Direct key match**: Data contains the component name as a key (e.g., `{"x-sre-tool-log": {...}}`)
2. **Component wrapper**: Data has a `component` key wrapping the component name (e.g., `{"component": {"x-sre-tool-log": {...}}}`)
3. **Root type match**: Data has `type` equal to the component name (e.g., `{"type": "x-sre-tool-log", ...}`)
4. **Fallback**: Returns the raw data as-is

If you need additional debugging, modify the `CatalogItem` builder in `autosre/lib/catalog.dart`:

```dart
// autosre/lib/catalog.dart

CatalogItem(
  name: 'x-sre-tool-log',
  widgetBuilder: (context) {
    print('DEBUG: x-sre-tool-log builder called');
    print('DEBUG: Data received: ${context.data}');
    // ...
  }
)
```

**Viewing Logs**:
- When running `uv run poe dev`, Flutter logs (stdout) should appear in the terminal console alongside backend logs.
- If running in Chrome context, use `F12` DevTools Console.

### 5. Debugging Data Flow Step-by-Step

When widgets are not rendering, follow this debugging checklist:

1. **Check Backend Event Creation** (A2UI_DEBUG log):
   - Look for `[TOOL_CALL_EVENT]` or `[WIDGET_EVENTS]` logs
   - Verify `event_size_bytes` > 0
   - Check that `surface_id` and `component_id` are generated

2. **Check Backend Event Yielding** (A2UI_DEBUG log):
   - Look for `[ROUTER_FC_YIELD_A2UI]` and `[ROUTER_FC_YIELD_UI]`
   - Verify A2UI events are yielded BEFORE UI marker
   - Confirm no exceptions during yield

3. **Check Frontend Stream Reception** (Browser Console):
   - Look for `[LINE N]` logs
   - Verify the line contains `"type":"a2ui"`
   - Check that JSON parsing succeeds

4. **Check Frontend A2UI Processing** (Browser Console):
   - Look for `[A2UI #N]` logs
   - Verify `surfaceId` and `components` are present
   - Check for `Emitted to stream` confirmation

5. **Check Frontend UI Marker Reception** (Browser Console):
   - Look for `[UI #N]` logs
   - Verify `surface_id` matches the A2UI surfaceId
   - Check `a2ui messages received so far` count > 0

6. **Check Frontend Catalog Unwrapping** (Browser Console):
   - Look for `[UNWRAP #N]` logs
   - Check which strategy matched (1-4)
   - Verify final data contains expected keys (e.g., `tool_name`, `status`)

### 6. Debugging Dashboard Data Channel

Dashboard events are emitted on a separate channel from the main chat stream. If dashboard panels are not updating:

1. **Check inline emission** -- look for `Dashboard event (inline) for <tool_name>` in backend logs.
2. **Check queued emission** -- look for `Dashboard event (queued) for <tool_name>` in backend logs.
3. **Verify the dashboard queue is initialized** -- `init_dashboard_queue()` is called at the start of each `event_generator()` in `sre_agent/api/routers/agent.py`.
4. **Check deduplication** -- if both inline and queued events appear for the same tool, the `inline_emitted_counts` tracking may have a bug.

### 7. Restarting the Environment

The `uv run poe dev` command orchestrates both backend (Python) and frontend (Flutter).
- **Backend Changes**: Usually require a restart if `uvicorn` reload is not active or if `agent.py` logic (which is often cached) is modified.
- **Frontend Changes**: Dart code changes require a full rebuild/restart of the Flutter process (`kill` port 8080 and restart `poe dev`) to be absolutely sure. 'Hot Restart' (r) is available if you run `flutter run` manually, but `poe dev` wraps it.

### 8. Common Failure Points

| Symptom | Likely Cause | Debug Focus |
|---------|-------------|-------------|
| No A2UI logs in backend | Tool call not detected | Check `[ROUTER_FC_DETECTED]` |
| A2UI logs but no UI marker | Exception during yield | Check for errors after `[ROUTER_FC_YIELD_A2UI]` |
| Frontend receives nothing | NDJSON stream issue | Check `[LINE N]` count |
| Frontend receives but no widget | Catalog unwrap failure | Check `[UNWRAP]` strategy |
| Widget builds but empty | Data format mismatch | Check `x-sre-tool-log unwrapped data` |
| Ghost bubble (empty) | Race condition | Verify A2UI before UI in logs |
| Duplicate dashboard panels | Dedup tracking failure | Check `inline_emitted_counts` |
| 400 on metric queries | MQL/PromQL confusion | Check for HINT in tool response |
| Agent retries same query | Self-correction loop | Verify HINT messages are propagated |

---

## Key Source Files

| File | Purpose |
|------|---------|
| `sre_agent/api/routers/agent.py` | Main chat endpoint, event generator, A2UI yielding |
| `sre_agent/api/helpers/tool_events.py` | A2UI event creation (`create_tool_call_events`, `create_tool_response_events`) |
| `sre_agent/api/helpers/dashboard_queue.py` | Dashboard event queue (`init_dashboard_queue`, `drain_dashboard_queue`) |
| `autosre/lib/catalog.dart` | CatalogRegistry, `_unwrapComponentData()` |
| `sre_agent/tools/clients/monitoring.py` | Smart Error Hints for query language issues |
| `tests/server/test_genui_chat_events.py` | A2UI protocol compliance tests |
| `tests/server/test_widget_logic.py` | Widget rendering logic tests |
