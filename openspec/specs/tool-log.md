# Component: Tool Logging (x-sre-tool-log)

## Overview
The Tool Logging component provides real-time feedback to the user while the agent is executing tools. It supports "Running", "Success", and "Error" states.

## Data Schema (A2UI v0.8)
```yaml
id: str                   # Unique component ID
component:
  x-sre-tool-log:
    tool_name: str        # Name of the tool being called
    args: dict            # Input arguments
    status: str           # "running", "success", "error"
    result: Any | None    # Result data if successful
    error: str | None     # Error message if failed
```

## Behavior
- **Init**: Displays a "Thinking..." or "Running [tool_name]" indicator.
- **Update**: Transitions from "running" to "success" or "error" as events arrive.
- **Redundancy**: Frontend must support both `x-sre-tool-log` and the `tool-log` alias for backward compatibility.

## Acceptance Criteria
- [ ] Must render correctly in the Flutter `ConversationPage`.
- [ ] Must handle "promoted" root-level data keys for GenUI compatibility.
- [ ] Must not show double-borders when nested in a tool surface.

## Test Scenarios

### Scenario: Tool Execution Lifecycle
- **Given** an active chat session
- **When** the agent calls `fetch_trace`
- **Then** a `beginRendering` event with `status: running` should be emitted
- **And** a subsequent `surfaceUpdate` with `status: success` should update the widget
