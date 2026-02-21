import { renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement, type ReactNode } from 'react'
import { DashboardFilterProvider } from '../contexts/DashboardFilterContext'
import { useDashboardTables, type DashboardTablesData } from './useDashboardTables'

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(
      QueryClientProvider,
      { client: queryClient },
      createElement(DashboardFilterProvider, null, children),
    )
  }
}

describe('useDashboardTables', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns loading state initially', () => {
    const { result } = renderHook(() => useDashboardTables(), {
      wrapper: createWrapper(),
    })
    expect(result.current.isLoading).toBe(true)
    expect(result.current.data).toBeUndefined()
  })

  it('returns data with all three arrays after loading', async () => {
    const { result } = renderHook(() => useDashboardTables(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    const data = result.current.data as DashboardTablesData
    expect(data).toBeDefined()
    expect(data.modelCalls.length).toBeGreaterThanOrEqual(1000)
    expect(data.toolCalls.length).toBeGreaterThanOrEqual(1200)
    expect(data.agentLogs.length).toBeGreaterThanOrEqual(1500)
  })

  it('model calls have correct shape', async () => {
    const { result } = renderHook(() => useDashboardTables(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    const row = result.current.data!.modelCalls[0]
    expect(row).toHaveProperty('modelName')
    expect(row).toHaveProperty('totalCalls')
    expect(row).toHaveProperty('p95Duration')
    expect(row).toHaveProperty('errorRate')
    expect(row).toHaveProperty('quotaExits')
    expect(row).toHaveProperty('tokensUsed')
    expect(typeof row.modelName).toBe('string')
    expect(typeof row.totalCalls).toBe('number')
  })

  it('tool calls have correct shape', async () => {
    const { result } = renderHook(() => useDashboardTables(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    const row = result.current.data!.toolCalls[0]
    expect(row).toHaveProperty('toolName')
    expect(row).toHaveProperty('totalCalls')
    expect(row).toHaveProperty('p95Duration')
    expect(row).toHaveProperty('errorRate')
    expect(typeof row.toolName).toBe('string')
    expect(typeof row.errorRate).toBe('number')
  })

  it('agent logs have correct shape and are sorted newest first', async () => {
    const { result } = renderHook(() => useDashboardTables(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    const logs = result.current.data!.agentLogs
    const row = logs[0]
    expect(row).toHaveProperty('timestamp')
    expect(row).toHaveProperty('agentId')
    expect(row).toHaveProperty('severity')
    expect(row).toHaveProperty('message')
    expect(row).toHaveProperty('traceId')
    expect(['INFO', 'WARNING', 'ERROR', 'DEBUG']).toContain(row.severity)
    expect(row.traceId).toHaveLength(32)

    // Verify sort order (newest first)
    for (let i = 1; i < Math.min(logs.length, 50); i++) {
      expect(logs[i - 1].timestamp >= logs[i].timestamp).toBe(true)
    }
  })
})
