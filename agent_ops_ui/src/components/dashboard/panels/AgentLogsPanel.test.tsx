import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { DashboardFilterProvider } from '../../../contexts/DashboardFilterContext'
import AgentLogsPanel from './AgentLogsPanel'

import type { DashboardTablesData } from '../../../hooks/useDashboardTables'
import type { VirtualizedDataTableProps } from '../../tables/VirtualizedDataTable'

// Mock VirtualizedDataTable to render rows without virtualization
vi.mock('../../tables/VirtualizedDataTable', () => ({
  default: function MockVirtualizedDataTable<TData>({
    data,
    columns,
    loading,
    emptyMessage,
  }: VirtualizedDataTableProps<TData>) {
    if (loading) return <div data-testid="loading">Loading...</div>
    if (data.length === 0) return <div>{emptyMessage}</div>
    return (
      <table>
        <thead>
          <tr>
            {columns.map((col, i) => (
              <th key={i}>{typeof col.header === 'string' ? col.header : ''}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, ri) => (
            <tr key={ri}>
              {columns.map((col, ci) => {
                const accessor = (col as { accessorKey?: string }).accessorKey
                const value = accessor ? (row as Record<string, unknown>)[accessor] : ''
                const cellFn = col.cell
                const rendered =
                  typeof cellFn === 'function'
                    ? cellFn({
                        getValue: () => value,
                        row: { original: row },
                      } as never)
                    : String(value ?? '')
                return <td key={ci}>{rendered}</td>
              })}
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td>{data.length} rows</td>
          </tr>
        </tfoot>
      </table>
    )
  },
}))

const mockData: DashboardTablesData = {
  modelCalls: [],
  toolCalls: [],
  agentLogs: [
    {
      timestamp: '2026-02-21T10:30:00.000Z',
      agentId: 'root-orchestrator',
      severity: 'INFO',
      message: 'Starting investigation for incident INC-4821 | 120ms | 350 tokens',
      traceId: 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6', // pragma: allowlist secret
    },
    {
      timestamp: '2026-02-21T10:29:55.000Z',
      agentId: 'trace-analyst',
      severity: 'ERROR',
      message: 'Circuit breaker OPEN for tool fetch_metrics after 3 failures | 2000ms | 1000 tokens',
      traceId: 'f1e2d3c4b5a6f7e8d9c0b1a2f3e4d5c6', // pragma: allowlist secret
    },
    {
      timestamp: '2026-02-21T10:29:50.000Z',
      agentId: 'metrics-analyst',
      severity: 'WARNING',
      message: 'Token budget 80% consumed, switching to fast model',
      traceId: '1234567890abcdef1234567890abcdef', // pragma: allowlist secret
    },
    {
      timestamp: '2026-02-21T10:29:45.000Z',
      agentId: 'council-synthesizer',
      severity: 'DEBUG',
      message: 'Synthesizer merged findings from 5 panels with confidence 0.87 | 500ms',
      traceId: 'abcdef1234567890abcdef1234567890', // pragma: allowlist secret
    },
  ],
}

vi.mock('../../../hooks/useDashboardTables', () => ({
  useDashboardTables: vi.fn(),
}))

import { useDashboardTables } from '../../../hooks/useDashboardTables'

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <DashboardFilterProvider>{ui}</DashboardFilterProvider>
    </QueryClientProvider>,
  )
}

describe('AgentLogsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders loading state', () => {
    vi.mocked(useDashboardTables).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as ReturnType<typeof useDashboardTables>)

    renderWithProviders(<AgentLogsPanel hours={24} />)
    expect(screen.getByText('Agent Traces')).toBeInTheDocument()
  })

  it('renders error state', () => {
    vi.mocked(useDashboardTables).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as ReturnType<typeof useDashboardTables>)

    renderWithProviders(<AgentLogsPanel hours={24} />)
    expect(screen.getByText('Failed to load agent logs.')).toBeInTheDocument()
  })

  it('renders log entries with agent IDs', () => {
    vi.mocked(useDashboardTables).mockReturnValue({
      data: mockData,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useDashboardTables>)

    renderWithProviders(<AgentLogsPanel hours={24} />)

    expect(screen.getByText('root-orchestrator')).toBeInTheDocument()
    expect(screen.getByText('trace-analyst')).toBeInTheDocument()
    expect(screen.getByText('metrics-analyst')).toBeInTheDocument()
    expect(screen.getByText('council-synthesizer')).toBeInTheDocument()
  })

  it('renders severity badges for all levels', () => {
    vi.mocked(useDashboardTables).mockReturnValue({
      data: mockData,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useDashboardTables>)

    renderWithProviders(<AgentLogsPanel hours={24} />)

    expect(screen.getByText('INFO')).toBeInTheDocument()
    expect(screen.getByText('ERROR')).toBeInTheDocument()
    expect(screen.getByText('WARNING')).toBeInTheDocument()
    expect(screen.getByText('DEBUG')).toBeInTheDocument()
  })

  it('renders log messages', () => {
    vi.mocked(useDashboardTables).mockReturnValue({
      data: mockData,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useDashboardTables>)

    renderWithProviders(<AgentLogsPanel hours={24} />)

    expect(
      screen.getByText('Starting investigation for incident INC-4821'),
    ).toBeInTheDocument()
  })

  it('truncates trace IDs to 12 characters', () => {
    vi.mocked(useDashboardTables).mockReturnValue({
      data: mockData,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useDashboardTables>)

    renderWithProviders(<AgentLogsPanel hours={24} />)

    // 'a1b2c3d4e5f6' is first 12 chars of first trace ID // pragma: allowlist secret
    expect(screen.getByText('a1b2c3d4e5f6...')).toBeInTheDocument()
  })

  it('renders latency and token columns', () => {
    vi.mocked(useDashboardTables).mockReturnValue({
      data: mockData,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useDashboardTables>)

    renderWithProviders(<AgentLogsPanel hours={24} />)

    expect(screen.getByText('120ms')).toBeInTheDocument()
    expect(screen.getByText('350')).toBeInTheDocument()
    expect(screen.getByText('2000ms')).toBeInTheDocument()
    expect(screen.getByText('1000')).toBeInTheDocument()
  })

  it('shows row count in footer', () => {
    vi.mocked(useDashboardTables).mockReturnValue({
      data: mockData,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useDashboardTables>)

    renderWithProviders(<AgentLogsPanel hours={24} />)

    expect(screen.getByText('4 rows')).toBeInTheDocument()
  })
})
