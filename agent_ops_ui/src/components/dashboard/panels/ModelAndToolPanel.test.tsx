import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { DashboardFilterProvider } from '../../../contexts/DashboardFilterContext'
import ModelAndToolPanel from './ModelAndToolPanel'

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
  modelCalls: [
    {
      modelName: 'gemini-2.5-flash',
      totalCalls: 1500,
      p95Duration: 320,
      errorRate: 2.1,
      quotaExits: 3,
      tokensUsed: 125000,
    },
    {
      modelName: 'gemini-2.5-pro',
      totalCalls: 800,
      p95Duration: 1250,
      errorRate: 7.5,
      quotaExits: 12,
      tokensUsed: 340000,
    },
  ],
  toolCalls: [
    {
      toolName: 'fetch_traces',
      totalCalls: 3200,
      p95Duration: 450,
      errorRate: 1.2,
    },
    {
      toolName: 'query_metrics',
      totalCalls: 2100,
      p95Duration: 2800,
      errorRate: 8.3,
    },
  ],
  agentLogs: [],
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

describe('ModelAndToolPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders loading state', () => {
    vi.mocked(useDashboardTables).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as ReturnType<typeof useDashboardTables>)

    renderWithProviders(<ModelAndToolPanel />)
    expect(screen.getByText('Model Usage')).toBeInTheDocument()
    expect(screen.getByText('Tool Performance')).toBeInTheDocument()
  })

  it('renders error state', () => {
    vi.mocked(useDashboardTables).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as ReturnType<typeof useDashboardTables>)

    renderWithProviders(<ModelAndToolPanel />)
    expect(screen.getByText('Failed to load model and tool data.')).toBeInTheDocument()
  })

  it('renders model and tool data', () => {
    vi.mocked(useDashboardTables).mockReturnValue({
      data: mockData,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useDashboardTables>)

    renderWithProviders(<ModelAndToolPanel />)

    expect(screen.getByText('gemini-2.5-flash')).toBeInTheDocument()
    expect(screen.getByText('gemini-2.5-pro')).toBeInTheDocument()
    expect(screen.getByText('fetch_traces')).toBeInTheDocument()
    expect(screen.getByText('query_metrics')).toBeInTheDocument()
  })

  it('formats duration correctly', () => {
    vi.mocked(useDashboardTables).mockReturnValue({
      data: mockData,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useDashboardTables>)

    renderWithProviders(<ModelAndToolPanel />)

    // 320ms should appear as "320ms"
    expect(screen.getByText('320ms')).toBeInTheDocument()
    // 1250ms = 1.25s rounds to "1.2s" or "1.3s" depending on toFixed rounding
    expect(screen.getByText('1.3s')).toBeInTheDocument()
  })

  it('highlights error rates above 5% in red', () => {
    vi.mocked(useDashboardTables).mockReturnValue({
      data: mockData,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useDashboardTables>)

    renderWithProviders(<ModelAndToolPanel />)

    // 7.50% should be red (model: gemini-2.5-pro errorRate 7.5)
    const highErrorEl = screen.getByText('7.50%')
    expect(highErrorEl).toBeInTheDocument()
    expect(highErrorEl.style.color).toBe('rgb(239, 68, 68)')

    // 2.10% should not be red
    const lowErrorEl = screen.getByText('2.10%')
    expect(lowErrorEl.style.color).not.toBe('rgb(239, 68, 68)')
  })

  it('shows row counts in table footers', () => {
    vi.mocked(useDashboardTables).mockReturnValue({
      data: mockData,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useDashboardTables>)

    renderWithProviders(<ModelAndToolPanel />)

    // Both tables have 2 rows each
    const rowCounts = screen.getAllByText('2 rows')
    expect(rowCounts).toHaveLength(2)
  })
})
