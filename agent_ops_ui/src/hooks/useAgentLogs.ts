import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import { queryLogs, queryLogsHistogram } from '../api/logsApi'
import type { LogEntriesResponse } from '../types'

const PAGE_SIZE = 50

interface UseAgentLogsParams {
  agentId: string // reasoning_engine_id or 'all'
  severity: string[] // e.g. ['ERROR', 'WARNING']
  projectId: string
  minutesAgo: number
}

/**
 * Build a Google Cloud Logging filter string from the given parameters.
 */
export function buildFilter(params: UseAgentLogsParams): string {
  const parts: string[] = [
    'resource.type="aiplatform.googleapis.com/ReasoningEngine"',
  ]

  if (params.agentId && params.agentId !== 'all') {
    // Extract numeric ID from URI (e.g., //aiplatform.../reasoningEngines/12345)
    // or use it directly if it doesn't contain a slash.
    const cleanId = params.agentId.split('/').pop() || params.agentId

    parts.push(`resource.labels.reasoning_engine_id="${cleanId}"`)
  }

  if (params.severity.length > 0) {
    const sevParts = params.severity.map((s) => `severity="${s.toUpperCase()}"`)
    if (sevParts.length === 1) {
      parts.push(sevParts[0])
    } else {
      parts.push(`(${sevParts.join(' OR ')})`)
    }
  }

  return parts.join(' AND ')
}

/**
 * Infinite-scroll hook for log entries.
 * Uses cursor-based pagination via timestamp + insertId.
 */
export function useAgentLogs(params: UseAgentLogsParams & { filterOverride?: string }) {
  const filter = params.filterOverride ?? buildFilter(params)

  return useInfiniteQuery<
    LogEntriesResponse,
    Error,
    { pages: LogEntriesResponse[]; pageParams: unknown[] },
    string[],
    { cursorTimestamp?: string; cursorInsertId?: string }
  >({
    queryKey: ['agent-logs', params.projectId, params.agentId, ...params.severity, String(params.minutesAgo), params.filterOverride || ''],
    queryFn: async ({ pageParam }) => {
      return queryLogs({
        filter,
        projectId: params.projectId,
        limit: PAGE_SIZE,
        minutesAgo: pageParam?.cursorTimestamp ? undefined : params.minutesAgo,
        cursorTimestamp: pageParam?.cursorTimestamp,
        cursorInsertId: pageParam?.cursorInsertId,
      })
    },
    initialPageParam: {},
    getNextPageParam: (lastPage) => {
      if (!lastPage.entries || lastPage.entries.length < PAGE_SIZE) {
        return undefined
      }
      // Use the last entry's timestamp + insertId as cursor
      const lastEntry = lastPage.entries[lastPage.entries.length - 1]
      if (!lastEntry) return undefined
      return {
        cursorTimestamp: lastEntry.timestamp,
        cursorInsertId: lastEntry.insert_id,
      }
    },
    enabled: !!params.projectId,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  })
}

/**
 * Hook for the logs histogram (time-bucketed severity counts).
 */
export function useLogsHistogram(params: UseAgentLogsParams & { filterOverride?: string }) {
  const filter = params.filterOverride ?? buildFilter(params)

  return useQuery({
    queryKey: ['logs-histogram', params.projectId, params.agentId, ...params.severity, String(params.minutesAgo), params.filterOverride || ''],
    queryFn: () =>
      queryLogsHistogram({
        filter,
        minutesAgo: params.minutesAgo,
        projectId: params.projectId,
      }),
    enabled: !!params.projectId,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  })
}
