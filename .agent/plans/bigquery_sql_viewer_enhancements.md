# Implementation Plan - BigQuery SQL Viewer Enhancements

The user wants to enhance the BigQuery SQL explorer in the dashboard with a resizable sidebar, runtime JSON schema inference using `JSON_KEYS()`, and improved autocomplete suggestions including both standard columns and inferred JSON fields.

## User Review Required

> [!IMPORTANT]
> - I will add a vertical resizer handle between the sidebar and the main editor.
> - JSON inference will be triggered by clicking on a field of type `JSON` in the sidebar.
> - Autocomplete will be updated dynamically as the schema is loaded or inferred.

## Proposed Changes

### 1. Resizable Sidebar (Frontend)

- **File**: `autosre/lib/widgets/dashboard/live_charts_panel.dart`
  - Introduce `_sidebarWidth` state variable (default: 280).
  - Wrap the sidebar and main area in a `Row`.
  - Add a `MouseRegion` and `GestureDetector` between them to act as a resize handle.
  - Implement resizing logic with min (200) and max (600) width constraints.

### 2. Runtime JSON Inference (Backend)

- **File**: `sre_agent/tools/bigquery/client.py`
  - Implement `get_json_keys(dataset_id, table_id, column_path)` using `JSON_KEYS()` function.
  - Query: `SELECT DISTINCT key FROM \`{project}.{dataset}.{table}\`, UNNEST(JSON_KEYS({column_path})) AS key LIMIT 1000`.
- **File**: `sre_agent/api/routers/tools.py`
  - Add `GET /api/tools/bigquery/datasets/{dataset_id}/tables/{table_id}/columns/{column_path}/json-keys` endpoint.

### 3. Frontend Integration for JSON Inference

- **File**: `autosre/lib/services/explorer_query_service.dart`
  - Add `getJsonKeys` method to call the new backend endpoint.
- **File**: `autosre/lib/widgets/dashboard/bigquery_sidebar.dart`
  - Update `_BigQuerySidebarState` to track `_inferredJsonKeys` map.
  - Modify `_buildFieldItem` for `JSON` types to trigger inference on click.
  - Display inferred keys as nested children under the JSON field.

### 4. Autocomplete Enhancements

- **File**: `autosre/lib/widgets/dashboard/bigquery_sidebar.dart`
  - Add a callback `onSchemaUpdated(List<QuerySnippet> snippets)` to notify the parent of available fields.
- **File**: `autosre/lib/widgets/dashboard/live_charts_panel.dart`
  - Capture snippets from `BigQuerySidebar` and pass them to `ManualQueryBar`.
- **File**: `autosre/lib/widgets/dashboard/manual_query_bar.dart`
  - Ensure autocomplete logic correctly handles dot-delimited field paths and provides relevant suggestions.

## Verification Plan

### Automated Tests
- **Backend**: Add unit tests in `tests/unit/sre_agent/tools/bigquery/test_client.py` for the `get_json_keys` logic.
- **API**: Test the new endpoint in `tests/unit/sre_agent/api/routers/test_tools.py`.

### Manual Verification
1. Open the Analytics tab and select the SQL view.
2. Drag the resizer handle to change the Data Explorer width.
3. Locate a `JSON` type column (e.g., `resource.attributes` in `traces` table).
4. Click the field and verify inferred keys appear below it.
5. Type `SELECT ` in the query bar and verify both normal columns and inferred JSON keys appear in the suggestions.
