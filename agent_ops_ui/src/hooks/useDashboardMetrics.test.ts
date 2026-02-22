import { renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement, type ReactNode } from 'react'
import { DashboardFilterProvider } from '../contexts/DashboardFilterContext'
import { useDashboardMetrics, type DashboardMetricsData } from './useDashboardMetrics'

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

describe('useDashboardMetrics', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns loading state initially', () => {
    const { result } = renderHook(() => useDashboardMetrics(), {
      wrapper: createWrapper(),
    })
    expect(result.current.isLoading).toBe(true)
    expect(result.current.data).toBeUndefined()
  })

  it('returns data after loading', async () => {
    const { result } = renderHook(() => useDashboardMetrics(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    const data = result.current.data as DashboardMetricsData
    expect(data).toBeDefined()
  })

  it('returns KPI metrics', async () => {
    const { result } = renderHook(() => useDashboardMetrics(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    const { kpis } = result.current.data!
    expect(typeof kpis.totalSessions).toBe('number')
    expect(typeof kpis.avgTurns).toBe('number')
    expect(typeof kpis.rootInvocations).toBe('number')
    expect(typeof kpis.errorRate).toBe('number')
    expect(typeof kpis.totalSessionsTrend).toBe('number')
    expect(typeof kpis.avgTurnsTrend).toBe('number')
    expect(typeof kpis.rootInvocationsTrend).toBe('number')
    expect(typeof kpis.errorRateTrend).toBe('number')
  })

  it('returns latency time series', async () => {
    const { result } = renderHook(() => useDashboardMetrics(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    const { latency } = result.current.data!
    expect(latency.length).toBeGreaterThan(0)
    const point = latency[0]
    expect(point).toHaveProperty('timestamp')
    expect(point).toHaveProperty('p50')
    expect(point).toHaveProperty('p95')
    expect(typeof point.p50).toBe('number')
    expect(typeof point.p95).toBe('number')
  })

  it('returns QPS time series', async () => {
    const { result } = renderHook(() => useDashboardMetrics(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    const { qps } = result.current.data!
    expect(qps.length).toBeGreaterThan(0)
    const point = qps[0]
    expect(point).toHaveProperty('timestamp')
    expect(point).toHaveProperty('qps')
    expect(point).toHaveProperty('errorRate')
  })

  it('returns token usage time series', async () => {
    const { result } = renderHook(() => useDashboardMetrics(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    const { tokens } = result.current.data!
    expect(tokens.length).toBeGreaterThan(0)
    const point = tokens[0]
    expect(point).toHaveProperty('timestamp')
    expect(point).toHaveProperty('input')
    expect(point).toHaveProperty('output')
    expect(typeof point.input).toBe('number')
    expect(typeof point.output).toBe('number')
  })
})
