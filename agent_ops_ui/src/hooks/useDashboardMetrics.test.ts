import { renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement, type ReactNode } from 'react'
import axios from 'axios'
import { DashboardFilterProvider } from '../contexts/DashboardFilterContext'
import { useDashboardMetrics, type DashboardMetricsData } from './useDashboardMetrics'

vi.mock('axios')

// Mock AgentContext so the hook can read projectId / serviceName
vi.mock('../contexts/AgentContext', () => ({
  useAgentContext: () => ({
    projectId: 'test-project',
    serviceName: 'sre-agent',
    setServiceName: vi.fn(),
    availableAgents: [],
    loadingAgents: false,
    errorAgents: null,
  }),
}))

const mockKpis = {
  kpis: {
    totalSessions: 42,
    avgTurns: 3.5,
    rootInvocations: 28,
    errorRate: 0.02,
    totalSessionsTrend: 10.0,
    avgTurnsTrend: -2.1,
    rootInvocationsTrend: 5.0,
    errorRateTrend: -0.5,
  },
}

const mockTimeseries = {
  latency: [{ timestamp: '2026-02-22T00:00:00Z', p50: 120, p95: 350 }],
  qps: [{ timestamp: '2026-02-22T00:00:00Z', qps: 0.5, errorRate: 0.01 }],
  tokens: [{ timestamp: '2026-02-22T00:00:00Z', input: 5000, output: 2000 }],
}

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
    vi.mocked(axios.get).mockImplementation(async (url: string) => {
      if (typeof url === 'string' && url.includes('/dashboard/kpis')) {
        return { data: mockKpis }
      }
      if (typeof url === 'string' && url.includes('/dashboard/timeseries')) {
        return { data: mockTimeseries }
      }
      return { data: {} }
    })
  })

  it('returns loading state initially', () => {
    const { result } = renderHook(() => useDashboardMetrics(24), {
      wrapper: createWrapper(),
    })
    expect(result.current.isLoading).toBe(true)
    expect(result.current.data).toBeUndefined()
  })

  it('returns data after loading', async () => {
    const { result } = renderHook(() => useDashboardMetrics(24), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    const data = result.current.data as DashboardMetricsData
    expect(data).toBeDefined()
  })

  it('returns KPI metrics from API', async () => {
    const { result } = renderHook(() => useDashboardMetrics(24), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    const { kpis } = result.current.data!
    expect(kpis.totalSessions).toBe(42)
    expect(kpis.avgTurns).toBe(3.5)
    expect(kpis.rootInvocations).toBe(28)
    expect(kpis.errorRate).toBe(0.02)
    expect(typeof kpis.totalSessionsTrend).toBe('number')
  })

  it('returns latency time series from API', async () => {
    const { result } = renderHook(() => useDashboardMetrics(24), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    const { latency } = result.current.data!
    expect(latency.length).toBe(1)
    expect(latency[0]).toHaveProperty('timestamp')
    expect(latency[0]).toHaveProperty('p50')
    expect(latency[0]).toHaveProperty('p95')
  })

  it('returns QPS time series from API', async () => {
    const { result } = renderHook(() => useDashboardMetrics(24), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    const { qps } = result.current.data!
    expect(qps.length).toBe(1)
    expect(qps[0]).toHaveProperty('qps')
    expect(qps[0]).toHaveProperty('errorRate')
  })

  it('returns token usage time series from API', async () => {
    const { result } = renderHook(() => useDashboardMetrics(24), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    const { tokens } = result.current.data!
    expect(tokens.length).toBe(1)
    expect(tokens[0]).toHaveProperty('input')
    expect(tokens[0]).toHaveProperty('output')
    expect(tokens[0].input).toBe(5000)
    expect(tokens[0].output).toBe(2000)
  })
})
