import { renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement, type ReactNode } from 'react'
import axios from 'axios'
import { useAgentLogs, useLogsHistogram } from './useAgentLogs'

vi.mock('axios')

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

const mockLogEntries = {
  entries: [
    {
      insert_id: 'log-001',
      timestamp: '2026-02-22T12:00:00Z',
      severity: 'ERROR',
      payload: { message: 'Connection pool exhausted' },
      resource_type: 'k8s_container',
      resource_labels: { pod_name: 'test-pod' },
    },
    {
      insert_id: 'log-002',
      timestamp: '2026-02-22T11:59:55Z',
      severity: 'INFO',
      payload: 'Request processed successfully',
    },
  ],
}

const mockHistogram = {
  buckets: [
    { start: '2026-02-22T11:00:00Z', end: '2026-02-22T11:15:00Z', debug: 1, info: 10, warning: 3, error: 2, critical: 0 },
    { start: '2026-02-22T11:15:00Z', end: '2026-02-22T11:30:00Z', debug: 0, info: 8, warning: 1, error: 0, critical: 0 },
  ],
  total_count: 25,
  scanned_entries: 25,
  start_time: '2026-02-22T11:00:00Z',
  end_time: '2026-02-22T12:00:00Z',
}

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children)
  }
}

describe('useAgentLogs', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(axios.post).mockImplementation(async (url: string) => {
      if (typeof url === 'string' && url.includes('/logs/query')) {
        return { data: mockLogEntries }
      }
      return { data: {} }
    })
  })

  it('returns loading state initially', () => {
    const { result } = renderHook(
      () =>
        useAgentLogs({
          agentId: 'all',
          severity: [],
          projectId: 'test-project',
          minutesAgo: 60,
        }),
      { wrapper: createWrapper() },
    )
    expect(result.current.isLoading).toBe(true)
  })

  it('fetches log entries and returns pages', async () => {
    const { result } = renderHook(
      () =>
        useAgentLogs({
          agentId: 'all',
          severity: [],
          projectId: 'test-project',
          minutesAgo: 60,
        }),
      { wrapper: createWrapper() },
    )

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.data?.pages).toHaveLength(1)
    expect(result.current.data?.pages[0].entries).toHaveLength(2)
    expect(result.current.data?.pages[0].entries[0].severity).toBe('ERROR')
  })

  it('builds filter with agent ID when not "all"', async () => {
    renderHook(
      () =>
        useAgentLogs({
          agentId: 'my-engine-123',
          severity: [],
          projectId: 'test-project',
          minutesAgo: 60,
        }),
      { wrapper: createWrapper() },
    )

    await waitFor(() => {
      expect(vi.mocked(axios.post)).toHaveBeenCalled()
    })

    const call = vi.mocked(axios.post).mock.calls[0]
    const body = call[1] as Record<string, unknown>
    expect(body.filter).toContain('reasoning_engine_id="my-engine-123"')
  })

  it('builds filter extracting numeric ID from full URI', async () => {
    renderHook(
      () =>
        useAgentLogs({
          agentId: '//aiplatform.googleapis.com/projects/summitt-gcp/locations/us-central1/reasoningEngines/4168506966131343360',
          severity: [],
          projectId: 'test-project',
          minutesAgo: 60,
        }),
      { wrapper: createWrapper() },
    )

    await waitFor(() => {
      expect(vi.mocked(axios.post)).toHaveBeenCalled()
    })

    const call = vi.mocked(axios.post).mock.calls[0]
    const body = call[1] as Record<string, unknown>
    expect(body.filter).toContain('reasoning_engine_id="4168506966131343360"')
  })

  it('builds filter with severity when specified', async () => {
    renderHook(
      () =>
        useAgentLogs({
          agentId: 'all',
          severity: ['ERROR', 'WARNING'],
          projectId: 'test-project',
          minutesAgo: 60,
        }),
      { wrapper: createWrapper() },
    )

    await waitFor(() => {
      expect(vi.mocked(axios.post)).toHaveBeenCalled()
    })

    const call = vi.mocked(axios.post).mock.calls[0]
    const body = call[1] as Record<string, unknown>
    expect(body.filter).toContain('(severity="ERROR" OR severity="WARNING")')
  })

  it('does not fetch when projectId is empty', () => {
    const { result } = renderHook(
      () =>
        useAgentLogs({
          agentId: 'all',
          severity: [],
          projectId: '',
          minutesAgo: 60,
        }),
      { wrapper: createWrapper() },
    )
    // Should stay in initial state, not loading
    expect(result.current.fetchStatus).toBe('idle')
  })
})

describe('useLogsHistogram', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(axios.post).mockImplementation(async (url: string) => {
      if (typeof url === 'string' && url.includes('/logs/histogram')) {
        return { data: mockHistogram }
      }
      return { data: {} }
    })
  })

  it('fetches histogram data', async () => {
    const { result } = renderHook(
      () =>
        useLogsHistogram({
          agentId: 'all',
          severity: [],
          projectId: 'test-project',
          minutesAgo: 60,
        }),
      { wrapper: createWrapper() },
    )

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.data?.buckets).toHaveLength(2)
    expect(result.current.data?.total_count).toBe(25)
  })
})
