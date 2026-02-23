/* eslint-disable @typescript-eslint/no-explicit-any */
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import AgentLogsPage from './AgentLogsPage'
import * as useAgentLogsModule from '../../hooks/useAgentLogs'
import { useAgentContext } from '../../contexts/AgentContext'

vi.mock('../../hooks/useAgentLogs', () => ({
  useAgentLogs: vi.fn(),
  useLogsHistogram: vi.fn(),
}))

// Mock the virtualizer to render all items directly (jsdom has no layout)
vi.mock('@tanstack/react-virtual', () => ({
  useVirtualizer: ({ count }: any) => ({
    getTotalSize: () => count * 36,
    getVirtualItems: () =>
      Array.from({ length: count }, (_, i) => ({
        index: i,
        key: String(i),
        start: i * 36,
        size: 36,
      })),
    measureElement: () => {},
  }),
}))

vi.mock('../../contexts/AgentContext', () => ({
  useAgentContext: vi.fn(),
}))

// Mock EChartWrapper to avoid canvas issues in jsdom
vi.mock('../charts/EChartWrapper', () => ({
  default: ({ loading }: any) => (
    <div data-testid="echart-wrapper">{loading ? 'Loading chart...' : 'Chart'}</div>
  ),
}))

// Mock react-syntax-highlighter (must include registerLanguage for VirtualLogTable)
vi.mock('react-syntax-highlighter', async () => {
  const React = await import('react')
  const Mock = (props: any) =>
    React.createElement('pre', { 'data-testid': 'syntax-highlighter' }, props.children)
  Mock.registerLanguage = () => {}
  return { Light: Mock }
})
vi.mock('react-syntax-highlighter/dist/esm/languages/hljs/json', () => ({ default: {} }))
vi.mock('react-syntax-highlighter/dist/esm/styles/hljs/atom-one-dark', () => ({ default: {} }))

const mockEntries = [
  {
    insert_id: 'log-001',
    timestamp: '2026-02-22T12:00:00Z',
    severity: 'ERROR',
    payload: { message: 'Connection pool exhausted', error_code: 'POOL_EXHAUSTED' },
    resource_type: 'k8s_container',
    resource_labels: { pod_name: 'test-pod' },
    trace_id: 'abc123',
    span_id: 'span-1',
  },
  {
    insert_id: 'log-002',
    timestamp: '2026-02-22T11:59:55Z',
    severity: 'INFO',
    payload: 'Request processed successfully',
    resource_type: 'aiplatform.googleapis.com/ReasoningEngine',
    resource_labels: {},
  },
  {
    insert_id: 'log-003',
    timestamp: '2026-02-22T11:59:50Z',
    severity: 'WARNING',
    payload: 'High latency detected: 450ms',
    resource_type: 'k8s_container',
    resource_labels: {},
  },
]

const mockHistogramBuckets = [
  { start: '2026-02-22T11:00:00Z', end: '2026-02-22T11:30:00Z', debug: 1, info: 10, warning: 3, error: 2, critical: 0 },
  { start: '2026-02-22T11:30:00Z', end: '2026-02-22T12:00:00Z', debug: 0, info: 8, warning: 1, error: 1, critical: 0 },
]

describe('AgentLogsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(useAgentContext as any).mockReturnValue({
      projectId: 'test-project',
      serviceName: 'sre-agent',
      setServiceName: vi.fn(),
      availableAgents: [],
      loadingAgents: false,
      errorAgents: null,
    })
    ;(useAgentLogsModule.useAgentLogs as any).mockReturnValue({
      data: { pages: [{ entries: mockEntries }], pageParams: [{}] },
      isLoading: false,
      isFetchingNextPage: false,
      hasNextPage: true,
      fetchNextPage: vi.fn(),
    })
    ;(useAgentLogsModule.useLogsHistogram as any).mockReturnValue({
      data: {
        buckets: mockHistogramBuckets,
        total_count: 26,
        scanned_entries: 26,
        start_time: '2026-02-22T11:00:00Z',
        end_time: '2026-02-22T12:00:00Z',
      },
      isLoading: false,
    })
  })

  it('renders the histogram chart', () => {
    render(<AgentLogsPage hours={1} />)
    expect(screen.getByTestId('echart-wrapper')).toBeInTheDocument()
  })

  it('shows stats bar with entry count', () => {
    render(<AgentLogsPage hours={1} />)
    expect(screen.getByText('26 entries scanned')).toBeInTheDocument()
    expect(screen.getByText('3 loaded')).toBeInTheDocument()
  })

  it('renders log entries with message preview', () => {
    render(<AgentLogsPage hours={1} />)
    expect(screen.getByText('Connection pool exhausted')).toBeInTheDocument()
    expect(screen.getByText('Request processed successfully')).toBeInTheDocument()
    expect(screen.getByText('High latency detected: 450ms')).toBeInTheDocument()
  })

  it('shows empty state when no entries', () => {
    ;(useAgentLogsModule.useAgentLogs as any).mockReturnValue({
      data: { pages: [{ entries: [] }], pageParams: [{}] },
      isLoading: false,
      isFetchingNextPage: false,
      hasNextPage: false,
      fetchNextPage: vi.fn(),
    })
    ;(useAgentLogsModule.useLogsHistogram as any).mockReturnValue({
      data: { buckets: [], total_count: 0 },
      isLoading: false,
    })
    render(<AgentLogsPage hours={1} />)
    expect(screen.getByText('Try adjusting your filters or time range.')).toBeInTheDocument()
  })

  it('shows loading skeletons during initial load', () => {
    ;(useAgentLogsModule.useAgentLogs as any).mockReturnValue({
      data: undefined,
      isLoading: true,
      isFetchingNextPage: false,
      hasNextPage: false,
      fetchNextPage: vi.fn(),
    })
    ;(useAgentLogsModule.useLogsHistogram as any).mockReturnValue({
      data: undefined,
      isLoading: true,
    })
    render(<AgentLogsPage hours={1} />)
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('passes hours as minutesAgo to the hook', () => {
    render(<AgentLogsPage hours={6} />)
    expect(useAgentLogsModule.useAgentLogs).toHaveBeenCalledWith(
      expect.objectContaining({ minutesAgo: 360 }),
    )
    expect(useAgentLogsModule.useLogsHistogram).toHaveBeenCalledWith(
      expect.objectContaining({ minutesAgo: 360 }),
    )
  })

  it('passes severity filter to the hook', () => {
    render(<AgentLogsPage hours={1} severity={['ERROR', 'WARNING']} />)
    expect(useAgentLogsModule.useAgentLogs).toHaveBeenCalledWith(
      expect.objectContaining({ severity: ['ERROR', 'WARNING'] }),
    )
  })

  it('uses serviceName from context as agentId', () => {
    ;(useAgentContext as any).mockReturnValue({
      projectId: 'test-project',
      serviceName: 'my-service',
      setServiceName: vi.fn(),
      availableAgents: [],
      loadingAgents: false,
      errorAgents: null,
    })
    render(<AgentLogsPage hours={1} />)
    expect(useAgentLogsModule.useAgentLogs).toHaveBeenCalledWith(
      expect.objectContaining({ agentId: 'my-service' }),
    )
  })

  it('uses "all" as agentId when serviceName is empty', () => {
    ;(useAgentContext as any).mockReturnValue({
      projectId: 'test-project',
      serviceName: '',
      setServiceName: vi.fn(),
      availableAgents: [],
      loadingAgents: false,
      errorAgents: null,
    })
    render(<AgentLogsPage hours={1} />)
    expect(useAgentLogsModule.useAgentLogs).toHaveBeenCalledWith(
      expect.objectContaining({ agentId: 'all' }),
    )
  })
})
