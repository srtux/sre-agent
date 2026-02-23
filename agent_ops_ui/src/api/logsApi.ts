import axios from 'axios'
import type {
  QueryLogsParams,
  LogEntriesResponse,
  QueryHistogramParams,
  LogsHistogramResponse,
} from '../types'

/**
 * Fetch log entries from the backend.
 * Maps camelCase TS params to snake_case JSON payload.
 */
export async function queryLogs(params: QueryLogsParams): Promise<LogEntriesResponse> {
  const { data } = await axios.post<LogEntriesResponse>('/api/tools/logs/query', {
    filter: params.filter || undefined,
    project_id: params.projectId || undefined,
    limit: params.limit,
    minutes_ago: params.minutesAgo ?? undefined,
    cursor_timestamp: params.cursorTimestamp || undefined,
    cursor_insert_id: params.cursorInsertId || undefined,
  })
  return data
}

/**
 * Fetch histogram buckets for the log volume chart.
 * Maps camelCase TS params to snake_case JSON payload.
 */
export async function queryLogsHistogram(
  params: QueryHistogramParams,
): Promise<LogsHistogramResponse> {
  const { data } = await axios.post<LogsHistogramResponse>(
    '/api/tools/logs/histogram',
    {
      filter: params.filter || undefined,
      minutes_ago: params.minutesAgo ?? undefined,
      bucket_count: params.bucketCount ?? 40,
      project_id: params.projectId || undefined,
    },
  )
  return data
}
