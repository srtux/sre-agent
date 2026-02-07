# SRE Agent Observability Explorer

The **Observability Explorer** is a GCP Console-style interactive dashboard built into the Flutter frontend (`autosre`). It provides dual-mode access to telemetry data: users can directly query GCP Cloud Monitoring, Cloud Logging, and Cloud Trace alongside AI agent-pushed insights.

## Key Features

### Observability Toolbar
*   **Time Range Selector**: GCP-style preset chips (1H, 6H, 1D, 1W) and a custom date range picker using Syncfusion DateRangePicker.
*   **Refresh**: Manual refresh button and auto-refresh toggle with configurable interval.
*   **Persistent State**: Time range selection is preserved across tab switches and applied to all manual queries.

### 1. Metrics Explorer
*   **Manual Query**: Enter MQL filter expressions (e.g., `metric.type="compute.googleapis.com/instance/cpu/utilization"`) to query Cloud Monitoring directly.
*   **Syncfusion Charts**: Interactive line charts with zoom (pinch/mouse wheel), pan (drag), and trackball crosshair tooltips. Replaced the previous FL Chart implementation.
*   **Anomaly Overlays**: Red diamond scatter series highlighting anomaly points.
*   **Trend Lines**: Dashed moving-average trend line (5-point window) with toggle control.
*   **Statistics Row**: Min, Max, Avg, P95, and anomaly count.
*   **Agent Integration**: Agent-pushed metrics appear alongside manual queries with "MANUAL" source badge.

### 2. Trace Explorer
*   **Manual Query**: Enter a Cloud Trace ID to fetch and visualize distributed traces directly.
*   **Syncfusion Waterfall**: Horizontal range bar chart replacing the custom-painted waterfall. Features service color mapping, critical path highlighting, and span detail panel on tap.
*   **Cloud Trace Deep Link**: "Open in Cloud Trace" button for each trace to view in GCP Console.
*   **Expandable Details**: Click any trace to expand the full waterfall visualization.

### 3. Log Explorer
*   **Manual Query**: Enter Cloud Logging filter expressions (e.g., `severity>=ERROR AND resource.type="gce_instance"`) to fetch logs directly.
*   **Severity Filtering**: Interactive filter chips with per-severity counts (CRITICAL, ERROR, WARNING, INFO, DEBUG).
*   **Full-Text Search**: Search across all collected log entries.
*   **Pattern Summary**: Auto-groups similar logs with Drain3 pattern extraction (e.g., "50 occurrences of Connection Refused").
*   **Expandable JSON Payloads**: Click any entry to view the full structured payload.

### 4. Alerts Explorer
*   **Manual Query**: Enter alert filter expressions (e.g., `state="OPEN" AND severity="CRITICAL"`) to query Cloud Monitoring alerting policies.
*   **Incident Timeline**: Chronological event timeline with severity indicators and metadata cards.
*   **Agent Correlation**: Alert data from agent investigations appears alongside manual queries.

### 5. Remediation Plan
*   **Purpose**: Actionable, tool-driven resolution steps (agent-generated only).
*   **Features**:
    *   **Checklists**: Steps are rendered as interactive checklists.
    *   **Risk Assessment**: Every plan includes a risk badge (Low, Medium, High).
    *   **One-Click Action**: Terminal commands (gcloud, kubectl) can be copied directly from the dashboard.

### 6. Council of Experts Dashboard
*   **Expert Findings View**: Specialist panel (Trace, Metrics, Logs, Alerts) assessments with severity indicators and confidence scores.
*   **Critic Report**: In Debate mode, shows agreements, contradictions, and identified gaps.
*   **Activity Graph View**: Tree visualization of agent hierarchy with timeline mode and tool call details.
*   **Integration**: Tool calls from panels automatically populate other dashboard tabs.

## Architecture

### Dual Data Source Model
The dashboard supports two data sources tracked via `DataSource` enum:
-   **`DataSource.agent`** (default): Data pushed by the Council of Experts via SSE `dashboard` events during investigations.
-   **`DataSource.manual`**: Data fetched by the user via the `ExplorerQueryService` through manual query bars.

Both sources feed into the same `DashboardState` and render identically, with manual items displaying a "MANUAL" badge.

### Data Flow

```
Agent Path:     Tool Result → create_dashboard_event() → genui_adapter.transform_*() → SSE → DashboardState.addFromEvent()
Manual Path:    ManualQueryBar → ExplorerQueryService → HTTP POST → Backend Endpoint → _unwrap_tool_result() → genui_adapter.transform_*() → DashboardState.add*()
```

Both paths use the same `genui_adapter.transform_*()` functions, ensuring consistent data formats for the frontend `fromJson` parsers.

### Backend Endpoints (Manual Query)
| Endpoint | Method | Tool Function | Transform |
|----------|--------|---------------|-----------|
| `/api/tools/metrics/query` | POST | `list_time_series` | `transform_metrics` |
| `/api/tools/metrics/promql` | POST | `query_promql` | `transform_metrics` |
| `/api/tools/alerts/query` | POST | `list_alerts` | `transform_alerts_to_timeline` |
| `/api/tools/logs/query` | POST | `list_log_entries` | `transform_log_entries` |
| `/api/tools/trace/{trace_id}` | GET | `fetch_trace` | `transform_trace` |

All endpoints unwrap `BaseToolResponse` envelopes via `_unwrap_tool_result()` before applying transforms.

### State Management
-   **`DashboardState`** (`lib/services/dashboard_state.dart`): `ChangeNotifier` providing per-tab loading states, error states, time range, and auto-refresh. Registered in the Provider tree.
-   **`ExplorerQueryService`** (`lib/services/explorer_query_service.dart`): HTTP client for manual queries. Depends on `DashboardState` for time range and result storage. Registered as a `ProxyProvider`.
-   **`TimeRange`** (`lib/models/time_range.dart`): Immutable model with `TimeRangePreset` enum (1H, 6H, 1D, 1W, Custom) and factory constructors.

### Shared UI Components
| Widget | Location | Purpose |
|--------|----------|---------|
| `ManualQueryBar` | `lib/widgets/dashboard/manual_query_bar.dart` | Monospace text input with "Run Query" button |
| `SreToolbar` | `lib/widgets/dashboard/sre_toolbar.dart` | Time range chips, refresh, auto-refresh toggle |
| `ErrorBanner` | `lib/widgets/common/error_banner.dart` | Compact error display for panel-level errors |
| `SourceBadge` | `lib/widgets/common/source_badge.dart` | "MANUAL" badge for manually-queried items |
| `ExplorerEmptyState` | `lib/widgets/common/explorer_empty_state.dart` | Glass morphism empty state with query hints |
| `ShimmerLoading` | `lib/widgets/common/shimmer_loading.dart` | Shimmer placeholder during API calls |

### Chart Library
-   **Syncfusion Flutter Charts** (Community Edition): `SfCartesianChart` with `LineSeries`, `ScatterSeries`, and `RangeBarSeries`.
-   **Chart Theme** (`lib/theme/chart_theme.dart`): Centralized configuration using Deep Space palette from `app_theme.dart`.
-   **Canvas Widgets**: `CustomPainter`-based visualizations (`metrics_dashboard_canvas.dart`, `agent_activity_canvas.dart`, etc.) remain unchanged.

## How to Use

1.  **Open Dashboard**: Click the "Pulse" icon in the top-right app bar.
2.  **Select Time Range**: Use the toolbar preset chips (1H/6H/1D/1W) or set a custom range.
3.  **Manual Query**: Type a filter expression in any panel's query bar and press Enter or click the search icon.
4.  **Agent Investigation**: Start a conversation with the agent — its findings automatically appear in the relevant tabs.
5.  **Drill Down**:
    *   Enter a trace ID in the **Traces** tab to visualize the distributed waterfall.
    *   Query `severity>=ERROR` in the **Logs** tab to find recent error patterns.
    *   Use the **Metrics** tab to correlate metric spikes with the investigation timeline.
6.  **Zoom & Pan**: Use mouse wheel or pinch to zoom into chart regions. Drag to pan along the time axis.
