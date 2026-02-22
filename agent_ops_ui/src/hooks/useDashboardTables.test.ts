import { renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement, type ReactNode } from 'react'
import axios from 'axios'
import { DashboardFilterProvider } from '../contexts/DashboardFilterContext'
import { useDashboardTables, type DashboardTablesData } from './useDashboardTables'

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

const mockModels = {
  modelCalls: [
    { modelName: 'gemini-2.5-flash', totalCalls: 100, p95Duration: 1200, errorRate: 2.5, quotaExits: 0, tokensUsed: 50000 },
  ],
}

const mockTools = {
  toolCalls: [
    { toolName: 'fetch_traces', totalCalls: 80, p95Duration: 500, errorRate: 1.2 },
  ],
}

const mockLogs = {
  agentLogs: [
    { timestamp: '2026-02-22T12:00:00Z', agentId: 'sre_agent', severity: 'INFO', message: 'Agent::sre_agent | 500ms | 1000 tokens', traceId: 'abc123def456' }, // pragma: allowlist secret
    { timestamp: '2026-02-22T11:00:00Z', agentId: 'trace_panel', severity: 'ERROR', message: 'Tool::fetch_traces | 2000ms | error=timeout', traceId: 'def456abc123' }, // pragma: allowlist secret
  ],
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

describe('useDashboardTables', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(axios.get).mockImplementation(async (url: string) => {
      if (typeof url === 'string' && url.includes('/dashboard/models')) {
        return { data: mockModels }
      }
      if (typeof url === 'string' && url.includes('/dashboard/tools')) {
        return { data: mockTools }
      }
      if (typeof url === 'string' && url.includes('/dashboard/logs')) {
        return { data: mockLogs }
      }
      return { data: {} }
    })
  })

  it('returns loading state initially', () => {
    const { result } = renderHook(() => useDashboardTables(24), {
      wrapper: createWrapper(),
    })
    expect(result.current.isLoading).toBe(true)
    expect(result.current.data).toBeUndefined()
  })

  it('returns data with all three arrays after loading', async () => {
    const { result } = renderHook(() => useDashboardTables(24), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    const data = result.current.data as DashboardTablesData
    expect(data).toBeDefined()
    expect(data.modelCalls.length).toBe(1)
    expect(data.toolCalls.length).toBe(1)
    expect(data.agentLogs.length).toBe(2)
  })

  it('model calls have correct shape', async () => {
    const { result } = renderHook(() => useDashboardTables(24), {
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
    expect(row.modelName).toBe('gemini-2.5-flash')
    expect(row.totalCalls).toBe(100)
  })

  it('tool calls have correct shape', async () => {
    const { result } = renderHook(() => useDashboardTables(24), {
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
    expect(row.toolName).toBe('fetch_traces')
  })

  it('agent logs have correct shape', async () => {
    const { result } = renderHook(() => useDashboardTables(24), {
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
  })
})
