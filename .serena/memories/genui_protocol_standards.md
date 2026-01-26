# GenUI & A2UI Protocol Standards

The SRE Agent uses the GenUI (Generative UI) protocol to deliver rich, interactive diagnostic widgets.

## Protocol Compliance (A2UI v0.8)
Backend messages must follow structural rules for the `genui` package to render them correctly in Flutter:
- **`surfaceUpdate` & `beginRendering`**: MUST include component wrappers with `id` and `component` keys.
- **`root` Field**: `beginRendering` must specify the `root` component ID.

### Correct Json Structure Example:
```json
{
  "id": "unique-id",
  "component": {
    "x-sre-tool-log": {
      "tool_name": "...",
      "status": "running"
    }
  }
}
```

## Known Issues & Debugging
- **Wrapper Issue**: If tool widgets (like "Thinking...") are invisible, check if the `component` wrapper is missing.
- **`CatalogItem`**: Flutter components are defined in `autosre/lib/catalog.dart`. Each name (e.g., `x-sre-tool-log`) must match the backend `type`.
- **Debugging**: Add print statements in `sre_agent/api/routers/agent.py` to inspect event types as they are yielded.
