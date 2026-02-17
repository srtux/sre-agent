# Default Dashboard Experience

After sign-in, the Auto SRE application provides an immediate, data-rich experience rather than presenting users with an empty screen. The system automatically selects the user's last-used GCP project (or prompts for one), opens the Logs dashboard in a 70/30 split layout, displays a personalized greeting in the chat pane, and begins loading telemetry data -- all without requiring any user interaction.

---

## Overview

The default experience is designed around three principles:

1. **Immediate context**: The user sees live telemetry data within seconds of sign-in.
2. **Minimal friction**: Project selection is remembered across sessions; returning users skip the picker entirely.
3. **Progressive disclosure**: Logs load by default on the active tab. Traces and alerts load on-demand when the user switches tabs, avoiding unnecessary API calls.

The flow proceeds as follows:

```
Sign-in complete
       |
       v
ProjectService.fetchProjects()
       |
       +-- loadSavedProject() finds saved project? ---YES---> _onProjectChanged()
       |                                                           |
       NO                                                          v
       |                                                   DashboardState.clear()
       v                                                   DashboardState.setTimeRange(15m)
_onNeedsProjectSelection()                                 DashboardState.openDashboard()
       |                                                   DashboardState.setActiveTab(logs)
       v                                                          |
ProjectSelectionDialog                                            v
       |                                                   ExplorerQueryService.loadDefaultLogs()
       +-- user selects project --> _onProjectChanged()
```

---

## Project Selection Flow

Project selection is the entry point for the default experience. The logic lives in `ConversationPage.initState()` and its listeners.

### Step 1: Load Saved Project

On initialization, `ProjectService.fetchProjects()` is called. Internally this method:

1. Fetches the project list from `GET /api/tools/projects/list` using the caller's EUC.
2. Calls `loadSavedProject()`, which checks `SharedPreferences` for a locally cached `selected_project_id`.
3. If no local preference exists, falls back to the backend preference via `GET /api/preferences/project` (Firestore-backed, per-user).
4. If a saved project is found, sets `_selectedProject` -- which triggers the `_onProjectChanged` listener in `ConversationPage`.

### Step 2: No Saved Project -- Show Selector Dialog

If no saved project is found after the fetch completes, `ProjectService` sets `_needsProjectSelection.value = true`. The `ConversationPage` listener (`_onNeedsProjectSelection`) responds by displaying a `ProjectSelectionDialog`:

- The dialog is **non-dismissible** (`barrierDismissible: false`), requiring the user to select a project before proceeding.
- It presents a searchable list of accessible GCP projects with filtering support.
- On selection, `selectProjectInstance()` persists the choice to both `SharedPreferences` (local) and `POST /api/preferences/project` (backend), then triggers `_onProjectChanged`.

### Step 3: Project Set -- Auto-open Dashboard

Once a project is selected (either from saved state or the dialog), `_onProjectChanged()` executes:

```dart
void _onProjectChanged() {
  final projectId = _projectService.selectedProjectId;
  _controller.contentGenerator?.projectId = projectId;
  _controller.contentGenerator?.fetchSuggestions();

  if (projectId != null) {
    _dashboardState.clear();
    _dashboardState.setTimeRange(
      TimeRange.fromPreset(TimeRangePreset.fifteenMinutes),
    );
    _dashboardState.openDashboard();
    _dashboardState.setActiveTab(DashboardDataType.logs);

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        final explorer = context.read<ExplorerQueryService>();
        explorer.loadDefaultLogs(projectId: projectId);
      }
    });
  }
}
```

This clears any stale dashboard data, sets the time range to 15 minutes, opens the dashboard to the Logs tab, and triggers an auto-load of log data via `ExplorerQueryService.loadDefaultLogs()`.

---

## Default Dashboard Behavior

Each telemetry tab has its own auto-load behavior. Logs load immediately on project selection. Traces and alerts load lazily when the user navigates to their respective tabs.

### Logs (Default Tab)

**Trigger**: Automatic on project selection via `_onProjectChanged()` and `LiveLogsExplorer.initState()`.

| Parameter | Value |
|-----------|-------|
| Time range | 15 minutes (`TimeRangePreset.fifteenMinutes`) |
| Filter | Empty (all logs) |
| Limit | 100 entries |
| Source | `DataSource.manual` with tool name `auto_load` |

**Implementation**: `ExplorerQueryService.loadDefaultLogs()` sends a `POST /api/tools/logs/query` request with `minutes_ago: 15` and an empty filter. The returned `LogEntriesData` is added to `DashboardState` and rendered in `LiveLogsExplorer`.

**User experience**:
- The timeline histogram displays severity-bucketed log counts.
- Severity filter chips (CRITICAL, ERROR, WARNING, INFO, DEBUG) provide faceted navigation.
- Full-text search across log payloads is available immediately.
- Pagination via `nextPageToken` enables loading additional entries.

### Traces (On Tab Switch)

**Trigger**: `LiveTracePanel.initState()` calls `_loadSlowTraces()` when the panel has no existing trace data.

| Parameter | Value |
|-----------|-------|
| Time range | 1 hour (60 minutes) |
| Filter | `MinDuration:3s` |
| Limit | 20 traces |
| Source | `DataSource.manual` with tool name `auto_load` |

**Implementation**: `ExplorerQueryService.loadSlowTraces()` sends a `POST /api/tools/traces/query` request. The backend calls `list_traces()` to find matching traces, then `fetch_trace()` in parallel for full span trees. Each trace is transformed via `genui_adapter.transform_trace()` and rendered as a waterfall chart.

**User experience**:
- Shows up to 20 traces with latency exceeding 3 seconds, providing an immediate view of performance bottlenecks.
- The first trace in the list is expanded by default for quick inspection.
- Each trace includes a "Open in Cloud Trace" deep link.

### Alerts (On Tab Switch)

**Trigger**: `LiveAlertsPanel.initState()` calls `_loadRecentAlerts()` when the panel has no existing alert data.

| Parameter | Value |
|-----------|-------|
| Time range | 7 days (10080 minutes) |
| Filter | None (all severities) |
| Source | `DataSource.manual` with tool name `auto_load` |

**Implementation**: `ExplorerQueryService.loadRecentAlerts()` sends a `POST /api/tools/alerts/query` request. The backend calls `list_alerts()` and transforms the result via `genui_adapter.transform_alerts_to_timeline()` into an `IncidentTimelineData` structure.

**User experience**:
- Displays a chronological timeline of alert events from the past week.
- Severity indicators (CRITICAL, ERROR, WARNING) provide visual prioritization.
- Alerts can be investigated further via the chat pane using `onPromptRequest`.

---

## Layout

The default layout uses a three-column structure:

```
+--+---------------------------+-----------+
|  |                           |           |
|R |     Dashboard (70%)       | Chat (30%)|
|A |                           |           |
|I |  +---------------------+ | Greeting  |
|L |  | SreToolbar          | | + Input   |
|  |  +---------------------+ | + Actions |
|  |  | ManualQueryBar      | |           |
|56|  +---------------------+ |           |
|px|  | Log Entries / Traces | |           |
|  |  | / Alerts / etc.     | |           |
|  |  |                     | |           |
+--+---------------------------+-----------+
```

### Investigation Rail (56px)

The `InvestigationRail` is a fixed-width vertical navigation bar on the far left. It provides:

- **Dashboard toggle**: Opens or closes the main dashboard panel.
- **Tab switching**: Icons for each `DashboardDataType` (Logs, Traces, Metrics, Alerts, Remediation, Council, Analytics).
- **Badge indicators**: Small colored dots indicate tabs with data; count badges show item counts on the active tab.
- **Tab auto-load**: Clicking a tab opens the dashboard and switches to that panel, which triggers the panel's `initState()` auto-load logic if no data exists.

### Dashboard Panel (70%)

The `DashboardPanelWrapper` controls the dashboard width:

- Default width factor: `0.7` (70% of available space after the rail).
- Resizable via a drag handle between the dashboard and chat panels.
- Maximizable to 95% width via the toolbar maximize button.
- Minimum chat panel width of 350px is enforced to prevent the chat from collapsing entirely.

### Chat Panel (30%)

The remaining space is used by the chat pane. When no messages exist, `HeroEmptyState` renders:

- A personalized greeting: "Hi, {first name}" (extracted from the authenticated user's display name).
- A prompt input field for starting an investigation.
- Suggested action chips for common queries.

---

## Project ID Flow

The selected project ID propagates from the frontend through the backend and into GCP API calls via a well-defined chain.

### 1. Frontend: Selection to Header

```
User selects project
       |
       v
ProjectService.selectProjectInstance(project)
  +-- Updates ValueNotifier<GcpProject?> (UI rebuilds)
  +-- Saves to SharedPreferences (local cache)
  +-- POST /api/preferences/project (backend persistence)
  +-- Adds to recent projects list

Every subsequent API call
       |
       v
ProjectInterceptorClient.send()
  +-- Injects X-GCP-Project-ID header
  +-- Injects Authorization: Bearer <token> header
  +-- Injects X-User-ID header
```

The `ProjectInterceptorClient` (defined in `lib/services/api_client.dart`) wraps every HTTP request and injects the current project ID as an `X-GCP-Project-ID` header. This ensures that all backend calls are scoped to the selected project.

### 2. Backend: Header to ContextVar

```
HTTP request arrives
       |
       v
auth_middleware() in sre_agent/api/middleware.py
  +-- Extracts X-GCP-Project-ID header
  +-- Extracts Authorization header (validates token)
  +-- Sets ContextVars:
        set_current_project_id(project_id)
        set_current_credentials(credentials)
        set_current_user_id(user_email)
```

The middleware extracts headers and stores them in Python `ContextVar` instances, making them available to any downstream code in the same async context.

### 3. Tools: ContextVar to GCP API

```
Tool function invoked
       |
       v
get_project_id_from_tool_context(tool_context)
  +-- Returns the project ID from ContextVar
  +-- Used to scope Cloud Logging, Cloud Trace, Cloud Monitoring, etc.

get_credentials_from_tool_context(tool_context)
  +-- Returns EUC credentials for API authentication
```

All GCP client calls use the project ID from `get_project_id_from_tool_context()` to ensure queries target the correct project.

### 4. Agent Prompt Injection

```
agent.py builds DomainContext(project_id=...)
  +-- Injected into user message: [CURRENT PROJECT: <id>]
  +-- Passed to prompt_composer for context-aware prompts
  +-- Ensures the LLM always knows which project to query
```

---

## Configuration

The default experience behavior is controlled by the following parameters, all of which are set programmatically:

| Setting | Location | Default | Description |
|---------|----------|---------|-------------|
| Default time range | `DashboardState._timeRange` | `TimeRangePreset.fifteenMinutes` | Time window for initial log queries |
| Default active tab | `DashboardState._activeTab` | `DashboardDataType.logs` | Which panel opens first |
| Dashboard width factor | `DashboardPanelWrapper._dashboardWidthFactor` | `0.7` (70%) | Initial dashboard panel width |
| Logs auto-load limit | `ExplorerQueryService.loadDefaultLogs` | 100 entries | Max log entries to fetch on auto-load |
| Traces auto-load filter | `ExplorerQueryService.loadSlowTraces` | `MinDuration:3s` | Only traces exceeding 3s latency |
| Traces auto-load window | `ExplorerQueryService.loadSlowTraces` | 60 minutes | Time window for slow trace search |
| Traces auto-load limit | `ExplorerQueryService.loadSlowTraces` | 20 traces | Max traces to fetch on auto-load |
| Alerts auto-load window | `ExplorerQueryService.loadRecentAlerts` | 10080 minutes (7 days) | Time window for alert search |
| Resize minimum chat width | `DashboardPanelWrapper` | 350px | Prevents chat panel from collapsing |

These values are currently hardcoded. To customize them, modify the corresponding constants in the respective files.

---

## Technical Details

### Files Involved

#### Frontend

| File | Role |
|------|------|
| `autosre/lib/pages/conversation_page.dart` | Orchestrates the default experience: listens for project changes, opens dashboard, triggers auto-load |
| `autosre/lib/pages/conversation_controller.dart` | Manages conversation lifecycle and agent streams |
| `autosre/lib/services/project_service.dart` | Project selection, persistence (local + backend), saved project loading |
| `autosre/lib/services/dashboard_state.dart` | Central state: active tab, time range, items, open/close, loading/error states |
| `autosre/lib/services/explorer_query_service.dart` | Auto-load methods (`loadDefaultLogs`, `loadSlowTraces`, `loadRecentAlerts`) and manual query execution |
| `autosre/lib/services/api_client.dart` | `ProjectInterceptorClient` -- injects `X-GCP-Project-ID` header on every request |
| `autosre/lib/widgets/conversation/project_selection_dialog.dart` | Modal dialog for first-time project selection |
| `autosre/lib/widgets/conversation/investigation_rail.dart` | Vertical tab rail (56px) for switching dashboard panels |
| `autosre/lib/widgets/conversation/dashboard_panel_wrapper.dart` | Dashboard container with resize handle and maximize toggle |
| `autosre/lib/widgets/conversation/hero_empty_state.dart` | Personalized greeting and prompt input shown in the chat pane |
| `autosre/lib/widgets/dashboard/live_logs_explorer.dart` | Logs panel with `initState()` auto-load trigger |
| `autosre/lib/widgets/dashboard/live_trace_panel.dart` | Traces panel with `initState()` auto-load of slow traces |
| `autosre/lib/widgets/dashboard/live_alerts_panel.dart` | Alerts panel with `initState()` auto-load of recent alerts |
| `autosre/lib/models/time_range.dart` | `TimeRange` and `TimeRangePreset` definitions |

#### Backend

| File | Role |
|------|------|
| `sre_agent/api/routers/tools.py` | API endpoints for logs, traces, alerts, metrics queries |
| `sre_agent/api/middleware.py` | Extracts auth headers and sets ContextVars |
| `sre_agent/tools/analysis/genui_adapter.py` | Transforms raw tool results into frontend-compatible schemas |
| `sre_agent/auth.py` | ContextVar definitions (`set_current_project_id`, `get_current_project_id`) |

### API Endpoints Used

| Endpoint | Method | Purpose | Auto-load Parameters |
|----------|--------|---------|---------------------|
| `/api/tools/logs/query` | POST | Fetch log entries | `filter: "", minutes_ago: 15, limit: 100` |
| `/api/tools/traces/query` | POST | Query traces by filter | `filter: "MinDuration:3s", minutes_ago: 60, limit: 20` |
| `/api/tools/alerts/query` | POST | Query alert incidents | `filter: null, minutes_ago: 10080` |
| `/api/preferences/project` | GET | Load saved project preference | -- |
| `/api/preferences/project` | POST | Save selected project | `{"project_id": "..."}` |
| `/api/tools/projects/list` | GET | List accessible GCP projects | Optional `?query=` for search |

### Data Flow Summary

```
Project Selected
       |
       v
_onProjectChanged() [conversation_page.dart]
  +-- DashboardState.clear()
  +-- DashboardState.setTimeRange(15m)
  +-- DashboardState.openDashboard()
  +-- DashboardState.setActiveTab(logs)
  +-- ExplorerQueryService.loadDefaultLogs()
            |
            v
      POST /api/tools/logs/query
            |
            v
      query_logs_endpoint() [tools.py]
        +-- list_log_entries(filter_str="", minutes_ago=15)
        +-- genui_adapter.transform_log_entries()
            |
            v
      LogEntriesData returned to frontend
            |
            v
      DashboardState.addLogEntries(data, source: manual)
            |
            v
      LiveLogsExplorer renders entries with severity chips and search
```

---

## Related Documentation

- [Dashboard UI](dashboard_ui.md) -- Full Observability Explorer reference
- [Project Selector](project_selector.md) -- Project selection implementation details
- [Rendering Telemetry](rendering_telemetry.md) -- GenUI/A2UI widget schemas and data flow
- [Debugging Telemetry & Auth](debugging_telemetry_and_auth.md) -- Troubleshooting missing data
