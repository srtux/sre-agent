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
function buildFilter(params: UseAgentLogsParams): string {
  const parts: string[] = [
    'resource.type="aiplatform.googleapis.com/ReasoningEngine"',
  ]

  if (params.agentId && params.agentId !== 'all') {
    parts.push(
      `resource.labels.reasoning_engine_id="${params.agentId}"`,
    )
  }

  if (params.severity.length > 0) {
    const quoted = params.severity.map((s) => `"${s.toUpperCase()}"`).join(', ')
    parts.push(`severity IN (${quoted})`)
  }

  return parts.join(' AND ')
}

/**
 * Infinite-scroll hook for log entries.
 * Uses cursor-based pagination via timestamp + insertId.
 */
export function useAgentLogs(params: UseAgentLogsParams) {
  const filter = buildFilter(params)

  return useInfiniteQuery<
    LogEntriesResponse,
    Error,
    { pages: LogEntriesResponse[]; pageParams: unknown[] },
    string[],
    { cursorTimestamp?: string; cursorInsertId?: string }
  >({
    queryKey: ['agent-logs', params.projectId, params.agentId, ...params.severity, String(params.minutesAgo)],
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
export function useLogsHistogram(params: UseAgentLogsParams) {
  const filter = buildFilter(params)

  return useQuery({
    queryKey: ['logs-histogram', params.projectId, params.agentId, ...params.severity, String(params.minutesAgo)],
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
