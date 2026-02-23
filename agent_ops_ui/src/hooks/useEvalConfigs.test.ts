import { renderHook, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement, type ReactNode } from 'react'
import axios from 'axios'
import { useEvalConfigs, useUpsertEvalConfig, useDeleteEvalConfig } from './useEvalConfigs'

vi.mock('axios')

// Mock AgentContext so any transitive imports resolve
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

const mockConfigs = [
  {
    agent_name: 'sre-agent',
    is_enabled: true,
    sampling_rate: 0.5,
    metrics: ['latency', 'accuracy'],
    last_eval_timestamp: '2026-02-22T12:00:00Z',
  },
  {
    agent_name: 'debug-agent',
    is_enabled: false,
    sampling_rate: 1.0,
    metrics: ['groundedness'],
    last_eval_timestamp: null,
  },
]

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children)
  }
}

describe('useEvalConfigs', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns configs on success', async () => {
    vi.mocked(axios.get).mockResolvedValueOnce({ data: { configs: mockConfigs } })

    const { result } = renderHook(() => useEvalConfigs(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.data).toHaveLength(2)
    expect(result.current.data![0].agent_name).toBe('sre-agent')
    expect(result.current.data![0].is_enabled).toBe(true)
    expect(result.current.data![0].sampling_rate).toBe(0.5)
    expect(result.current.data![0].metrics).toEqual(['latency', 'accuracy'])
    expect(result.current.data![0].last_eval_timestamp).toBe('2026-02-22T12:00:00Z')
    expect(result.current.data![1].agent_name).toBe('debug-agent')
    expect(result.current.data![1].last_eval_timestamp).toBeNull()
    expect(axios.get).toHaveBeenCalledWith('/api/v1/evals/config')
  })

  it('handles empty configs', async () => {
    vi.mocked(axios.get).mockResolvedValueOnce({ data: { configs: [] } })

    const { result } = renderHook(() => useEvalConfigs(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.data).toEqual([])
  })

  it('handles error', async () => {
    vi.mocked(axios.get).mockRejectedValueOnce(new Error('Network error'))

    const { result } = renderHook(() => useEvalConfigs(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isError).toBe(true)
    })

    expect(result.current.data).toBeUndefined()
    expect(result.current.error).toBeInstanceOf(Error)
  })
})

describe('useUpsertEvalConfig', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('calls correct endpoint and invalidates cache', async () => {
    const upsertedConfig = {
      agent_name: 'sre-agent',
      is_enabled: true,
      sampling_rate: 0.8,
      metrics: ['latency'],
      last_eval_timestamp: '2026-02-22T12:00:00Z',
    }
    vi.mocked(axios.post).mockResolvedValueOnce({ data: { config: upsertedConfig } })
    // Pre-seed the query cache so invalidation can be observed
    vi.mocked(axios.get).mockResolvedValue({ data: { configs: mockConfigs } })

    const wrapper = createWrapper()
    const { result } = renderHook(() => useUpsertEvalConfig(), { wrapper })

    act(() => {
      result.current.mutate({
        agentName: 'sre-agent',
        isEnabled: true,
        samplingRate: 0.8,
        metrics: ['latency'],
      })
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(axios.post).toHaveBeenCalledWith('/api/v1/evals/config/sre-agent', {
      is_enabled: true,
      sampling_rate: 0.8,
      metrics: ['latency'],
    })
    expect(result.current.data).toEqual(upsertedConfig)
  })
})

describe('useDeleteEvalConfig', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('calls correct endpoint and invalidates cache', async () => {
    vi.mocked(axios.delete).mockResolvedValueOnce({ data: {} })
    // Pre-seed the query cache so invalidation can be observed
    vi.mocked(axios.get).mockResolvedValue({ data: { configs: [] } })

    const wrapper = createWrapper()
    const { result } = renderHook(() => useDeleteEvalConfig(), { wrapper })

    act(() => {
      result.current.mutate('sre-agent')
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(axios.delete).toHaveBeenCalledWith('/api/v1/evals/config/sre-agent')
  })
})
