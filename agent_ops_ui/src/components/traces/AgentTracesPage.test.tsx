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
  default: ({ data, columns, emptyMessage, onRowClick, renderExpandedRow, expandedRowId, getRowId }: any) => (
    <div data-testid="virtualized-table">
      {data && data.length > 0 ? (
        data.map((row: any, i: number) => {
          const rowId = getRowId ? getRowId(row) : i.toString()
          const isExpanded = expandedRowId === rowId
          return (
            <div key={rowId} data-testid="mock-row-container">
              <div
                data-testid="mock-row"
                onClick={() => onRowClick?.(row)}
                style={{ cursor: onRowClick ? 'pointer' : 'default' }}
              >
                {columns.map((col: any, j: number) => {
                  const val = col.accessorKey ? row[col.accessorKey] : col.accessorFn ? col.accessorFn(row) : row[col.id]
                  if (col.cell) {
                    return <div key={j}>{col.cell({ getValue: () => val, row: { original: row } })}</div>
                  }
                  return <div key={j}>{String(val)}</div>
                })}
              </div>
              {isExpanded && renderExpandedRow && (
                <div data-testid="expanded-content">
                  {renderExpandedRow(row)}
                </div>
              )}
            </div>
          )
        })
      ) : (
        <div>{emptyMessage || 'No data'}</div>
      )}
    </div>
  ),
}))

vi.mock('./SpanDetailsView', () => ({
  default: ({ traceId, spanId }: any) => (
    <div data-testid="span-details">
      SpanDetails for {traceId} / {spanId}
    </div>
  ),
}))

vi.mock('../graph/ContextGraphViewer', () => ({
  default: ({ sessionId }: any) => (
    <div data-testid="context-graph-viewer">
      ContextGraphViewer for {sessionId}
    </div>
  ),
}))

vi.mock('../graph/ContextInspector', () => ({
  default: ({ nodeId, onClose }: any) => (
    <div data-testid="context-inspector">
      ContextInspector for {nodeId}
      <button onClick={onClose}>Close</button>
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

    // Check trace click (waterfall explorer)
    const traceRow = screen.getByText('trace-456...').closest('div')
    const explorerBtn = traceRow?.querySelector('button')
    if (explorerBtn) {
      fireEvent.click(explorerBtn)
    } else {
      // Fallback click on the link itself if button not found by querySelector
      fireEvent.click(traceLink)
    }

    expect(mockPostMessage).toHaveBeenCalled()
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

  it('expands a span row on click', () => {
    render(<AgentTracesPage hours={24} />)

    fireEvent.click(screen.getByText('Spans'))

    // Virtualized mock now supports expansion
    const row = screen.getByText('Doing work').closest('[data-testid="mock-row"]')
    expect(row).toBeInTheDocument()

    fireEvent.click(row!)

    expect(screen.getByTestId('span-details')).toBeInTheDocument()
    expect(screen.getByText(/SpanDetails for trace-456/)).toBeInTheDocument()
  })
})
