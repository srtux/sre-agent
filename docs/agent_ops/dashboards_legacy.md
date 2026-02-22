# Dashboards

The Auto SRE dashboard system provides a Perses-compatible dashboard specification
for visualizing observability data from Google Cloud Monitoring, Prometheus, logs,
traces, and BigQuery.

## Overview

Dashboards are collections of panels (widgets) arranged in a flexible grid layout
that visualize metrics, logs, traces, alerts, and data from multiple sources. The
system integrates with Cloud Monitoring dashboards and supports local dashboard
creation.

### Key Features

- **Perses-compatible spec**: Dashboard definitions follow the [Perses](https://perses.dev/)
  open dashboard standard with GCP extensions
- **Cloud Monitoring integration**: List, view, and manage GCP Cloud Monitoring dashboards
- **Multi-source panels**: Support for Prometheus (PromQL), Cloud Monitoring (MQL),
  Cloud Logging, BigQuery, and Tempo
- **Grid layout**: 24-column responsive grid with drag-and-drop positioning
- **Dashboard-level controls**: Time range selector, variables, filters, and annotations
- **Save to Dashboard**: Save explorer results directly as dashboard panels
- **16 panel types**: Time series, gauge, stat, table, logs, traces, pie, heatmap,
  bar, text, alert chart, scorecard, scatter, treemap, error reporting, incident list

## Architecture

### Backend

| Component | Path | Description |
|-----------|------|-------------|
| Models | `sre_agent/models/dashboard.py` | Pydantic models (Perses-compatible) |
| API Client | `sre_agent/tools/clients/dashboard.py` | Cloud Monitoring Dashboard API tools |
| Service | `sre_agent/services/dashboard_service.py` | CRUD operations, local + cloud |
| Router | `sre_agent/api/routers/dashboards.py` | REST API endpoints |

### Frontend

| Component | Path | Description |
|-----------|------|-------------|
| Models | `autosre/lib/models/dashboard_models.dart` | Dart data models |
| Service | `autosre/lib/services/dashboard_service.dart` | API client service |
| List Page | `autosre/lib/pages/dashboards_page.dart` | Dashboard listing page |
| View Page | `autosre/lib/pages/dashboard_view_page.dart` | Dashboard view/edit page |
| Save Dialog | `autosre/lib/widgets/dashboard/save_to_dashboard_dialog.dart` | Save to dashboard dialog |

## API Endpoints

All endpoints are prefixed with `/api/dashboards`.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/dashboards` | List all dashboards (local + cloud) |
| GET | `/api/dashboards/{id}` | Get a specific dashboard |
| POST | `/api/dashboards` | Create a new dashboard |
| PATCH | `/api/dashboards/{id}` | Update a dashboard |
| DELETE | `/api/dashboards/{id}` | Delete a dashboard |
| POST | `/api/dashboards/{id}/panels` | Add a panel to a dashboard |
| DELETE | `/api/dashboards/{id}/panels/{panel_id}` | Remove a panel |
| PATCH | `/api/dashboards/{id}/panels/{panel_id}/position` | Update panel position |

### Query Parameters

- `project_id` (optional): GCP project ID for cloud dashboard listing
- `include_cloud` (optional, default `true`): Include Cloud Monitoring dashboards
- `page_size` (optional, default `50`): Max results per page

## Data Model

### Dashboard

```json
{
  "id": "abc123",
  "display_name": "Production Overview",
  "description": "Key metrics for production services",
  "source": "local",
  "project_id": "my-gcp-project",
  "panels": [...],
  "variables": [...],
  "filters": [...],
  "time_range": {"preset": "1h"},
  "labels": {"team": "sre"},
  "grid_columns": 24,
  "metadata": {
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "version": 1,
    "tags": ["production"],
    "starred": false
  }
}
```

### Panel

```json
{
  "id": "panel-1",
  "title": "CPU Utilization",
  "type": "time_series",
  "grid_position": {"x": 0, "y": 0, "width": 12, "height": 4},
  "queries": [
    {
      "datasource": {"type": "prometheus"},
      "prometheus": {"expr": "rate(cpu_usage[5m])"}
    }
  ],
  "thresholds": [
    {"value": 80, "color": "yellow"},
    {"value": 95, "color": "red"}
  ]
}
```

### Panel Types

| Type | Description |
|------|-------------|
| `time_series` | Line/area charts for time-based data |
| `gauge` | Circular gauge for single values |
| `stat` | Large single-value display |
| `table` | Tabular data display |
| `logs` | Log entries viewer |
| `traces` | Distributed trace visualization |
| `pie` | Pie/donut chart |
| `heatmap` | Heat map visualization |
| `bar` | Bar chart |
| `text` | Markdown/HTML text |
| `alert_chart` | Alert timeline |
| `scorecard` | KPI scorecard |
| `scatter` | Scatter plot |
| `treemap` | Hierarchical treemap |
| `error_reporting` | Error reporting panel |
| `incident_list` | Active incident list |

### Datasource Types

| Type | Description | Query Language |
|------|-------------|---------------|
| `prometheus` | Prometheus metrics | PromQL |
| `cloud_monitoring` | GCP Cloud Monitoring | MQL / Monitoring filter |
| `loki` | Grafana Loki logs | LogQL |
| `bigquery` | Google BigQuery | SQL |
| `tempo` | Grafana Tempo traces | TraceQL |

## Cloud Monitoring Integration

The dashboard system integrates with the Cloud Monitoring Dashboard API via
`@adk_tool` functions in `sre_agent/tools/clients/dashboard.py`:

- **`list_cloud_dashboards`**: Lists all dashboards in a GCP project
- **`get_cloud_dashboard`**: Gets dashboard details (converts protobuf to JSON)
- **`create_cloud_dashboard`**: Creates dashboards with MosaicLayout (48 columns)
- **`delete_cloud_dashboard`**: Deletes custom dashboards

### Layout Mapping

Cloud Monitoring uses a 48-column MosaicLayout, while our Perses-compatible spec
uses a 24-column grid. The mapping is:

- Cloud Monitoring `x_pos` / 2 = Local `x`
- Cloud Monitoring `width` / 2 = Local `width`

## Save to Dashboard

The `SaveToDashboardDialog` widget allows users to save explorer results as
dashboard panels. It supports two modes:

1. **Create New**: Creates a new dashboard with the panel
2. **Add to Existing**: Adds the panel to an existing local dashboard

### Usage from Explorers

```dart
import 'package:autosre/widgets/dashboard/save_to_dashboard_dialog.dart';

// In any explorer widget
SaveToDashboardDialog.show(
  context: context,
  panelTitle: 'CPU Usage - us-central1',
  panelType: PanelType.timeSeries,
  panelData: {
    'queries': [{
      'datasource': {'type': 'prometheus'},
      'prometheus': {'expr': 'rate(cpu_usage[5m])'},
    }],
  },
);
```

## Testing

```bash
# Run all dashboard tests
uv run pytest tests/unit/sre_agent/models/test_dashboard.py \
  tests/unit/sre_agent/services/test_dashboard_service.py \
  tests/unit/sre_agent/api/routers/test_dashboards.py -v

# Run with coverage
uv run pytest tests/unit/sre_agent/models/test_dashboard.py \
  tests/unit/sre_agent/services/test_dashboard_service.py \
  tests/unit/sre_agent/api/routers/test_dashboards.py --cov=sre_agent
```
