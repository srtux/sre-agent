/* eslint-disable @typescript-eslint/no-explicit-any */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import AgentTracesPage from './AgentTracesPage'
import { useDashboardTables } from '../../hooks/useDashboardTables'
import { useAgentContext } from '../../contexts/AgentContext'

vi.mock('../../hooks/useDashboardTables', () => ({
  useDashboardTables: vi.fn(),
}))

vi.mock('../../contexts/AgentContext', () => ({
  useAgentContext: vi.fn(),
}))

vi.mock('../tables/VirtualizedDataTable', () => ({
  default: ({ data, columns, emptyMessage }: any) => (
    <div data-testid="virtualized-table">
      {data && data.length > 0 ? (
        data.map((row: any, i: number) => (
          <div key={i} data-testid="mock-row">
            {columns.map((col: any, j: number) => {
              const val = col.accessorKey ? row[col.accessorKey] : col.accessorFn ? col.accessorFn(row) : row[col.id]
              if (col.cell) {
                return <div key={j}>{col.cell({ getValue: () => val, row: { original: row } })}</div>
              }
              return <div key={j}>{String(val)}</div>
            })}
          </div>
        ))
      ) : (
        <div>{emptyMessage || 'No data'}</div>
      )}
    </div>
  ),
}))

describe('AgentTracesPage', () => {
  const mockPostMessage = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    window.parent.postMessage = mockPostMessage
      ; (useAgentContext as any).mockReturnValue({
        serviceName: '',
      })
      ; (useDashboardTables as any).mockReturnValue({
        data: {
          agentSessions: [
            {
              timestamp: '2026-02-22T12:00:00Z',
              sessionId: 'session-123',
              turns: 5,
              latencyMs: 1500,
              totalTokens: 2000,
              errorCount: 0,
            },
          ],
          agentTraces: [
            {
              timestamp: '2026-02-22T12:05:00Z',
              traceId: 'trace-456',
              sessionId: 'session-123',
              latencyMs: 300,
              totalTokens: 500,
              errorCount: 0,
            },
          ],
          agentLogs: [
            {
              timestamp: '2026-02-22T12:05:01Z',
              message: 'Doing work | 150ms | 100 tokens',
              severity: 'INFO',
              agentId: 'Agent',
              traceId: 'trace-456',
            },
          ],
        },
        isLoading: false,
        isError: false,
      })
  })

  it('renders tabs and defaults to sessions', () => {
    render(<AgentTracesPage hours={24} />)
    expect(screen.getByText('Sessions')).toBeInTheDocument()
    expect(screen.getByText('Traces')).toBeInTheDocument()
    expect(screen.getByText('Spans')).toBeInTheDocument()

    // Sessions table is active
    expect(screen.getByText('session-123')).toBeInTheDocument()
  })

  it('switches to traces tab and handles deep link', () => {
    render(<AgentTracesPage hours={24} />)

    // Check session click filters traces
    fireEvent.click(screen.getByText('session-123'))

    expect(screen.getByText('Filtered by Session:')).toBeInTheDocument()
    expect(screen.getAllByText('session-123').length).toBeGreaterThan(0)

    const traceLink = screen.getByText('trace-456...')
    expect(traceLink).toBeInTheDocument()

    // Check trace click
    fireEvent.click(traceLink)
    expect(mockPostMessage).toHaveBeenCalledWith(
      JSON.stringify({ type: 'OPEN_TRACE', traceId: 'trace-456' }),
      '*'
    )
  })

  it('switches to spans tab', () => {
    render(<AgentTracesPage hours={24} />)

    const spansTab = screen.getByText('Spans')
    fireEvent.click(spansTab)

    expect(screen.getByText('Doing work')).toBeInTheDocument()
    expect(screen.getByText('150ms')).toBeInTheDocument()
    // The number of tokens is parsed by the token accessor
    expect(screen.getByText('100')).toBeInTheDocument()
  })

  it('shows loading state when loading', () => {
    ; (useDashboardTables as any).mockReturnValue({
      data: null,
      isLoading: true,
      isError: false,
    })
    render(<AgentTracesPage hours={24} />)
    expect(screen.getByText('No sessions found.')).toBeInTheDocument()
  })
})
