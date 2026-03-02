/**
 * Explorer API — query execution and dataset browsing.
 */
import apiClient from './client'

export interface QueryResult {
  columns: string[]
  rows: Array<Record<string, unknown>>
}

export interface DatasetInfo {
  name: string
  tables: Array<{
    name: string
    columns?: Array<{ name: string; type: string }>
  }>
}

/** Execute a query in the given language. */
export async function executeQuery(
  query: string,
  language: string,
): Promise<QueryResult> {
  const { data } = await apiClient.post<QueryResult>('/api/tools/execute', {
    tool_name: 'query',
    args: { query, language },
  })
  return data
}

/** Fetch BigQuery datasets and tables for a project. */
export async function getDatasets(projectId: string): Promise<DatasetInfo[]> {
  try {
    const { data } = await apiClient.get<DatasetInfo[]>(
      '/api/tools/bigquery/datasets',
      { params: { project_id: projectId } },
    )
    return data
  } catch {
    // Mock fallback when endpoint is not available
    return [
      {
        name: 'otel_traces',
        tables: [
          { name: 'spans', columns: [{ name: 'trace_id', type: 'STRING' }, { name: 'span_id', type: 'STRING' }, { name: 'duration_ms', type: 'FLOAT64' }, { name: 'status', type: 'STRING' }, { name: 'created_at', type: 'TIMESTAMP' }] },
          { name: 'events', columns: [{ name: 'event_id', type: 'STRING' }, { name: 'span_id', type: 'STRING' }, { name: 'name', type: 'STRING' }, { name: 'timestamp', type: 'TIMESTAMP' }] },
        ],
      },
      {
        name: 'otel_metrics',
        tables: [
          { name: 'gauge', columns: [{ name: 'metric_name', type: 'STRING' }, { name: 'value', type: 'FLOAT64' }, { name: 'timestamp', type: 'TIMESTAMP' }] },
          { name: 'histogram', columns: [{ name: 'metric_name', type: 'STRING' }, { name: 'bucket', type: 'FLOAT64' }, { name: 'count', type: 'INT64' }, { name: 'timestamp', type: 'TIMESTAMP' }] },
        ],
      },
      {
        name: 'otel_logs',
        tables: [
          { name: 'entries', columns: [{ name: 'log_id', type: 'STRING' }, { name: 'severity', type: 'STRING' }, { name: 'body', type: 'STRING' }, { name: 'timestamp', type: 'TIMESTAMP' }] },
        ],
      },
    ]
  }
}
