import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import VisualDataExplorer from './VisualDataExplorer'

vi.mock('../charts/EChartWrapper', () => ({
  default: () => <div data-testid="echart">Chart</div>,
}))

vi.mock('./SqlResultsTable', () => ({
  default: ({ rows }: { rows: unknown[] }) => (
    <div data-testid="sql-table">{rows.length} rows</div>
  ),
}))

vi.mock('lucide-react', () => ({
  LineChart: () => <span>Line</span>,
  BarChart3: () => <span>Bar</span>,
  ScatterChart: () => <span>Scatter</span>,
  Table2: () => <span>Table</span>,
}))

describe('VisualDataExplorer', () => {
  const columns = ['timestamp', 'value']
  const rows = [
    { timestamp: '2026-01-01T00:00:00Z', value: 100 },
    { timestamp: '2026-01-01T01:00:00Z', value: 200 },
  ]

  it('renders chart type buttons', () => {
    render(<VisualDataExplorer columns={columns} rows={rows} />)
    expect(screen.getByText('Line')).toBeDefined()
    expect(screen.getByText('Bar')).toBeDefined()
    expect(screen.getByText('Table')).toBeDefined()
  })

  it('defaults to chart view for timestamp data', () => {
    render(<VisualDataExplorer columns={columns} rows={rows} />)
    expect(screen.getByTestId('echart')).toBeDefined()
  })

  it('switches to table view when Table button clicked', () => {
    render(<VisualDataExplorer columns={columns} rows={rows} />)
    fireEvent.click(screen.getByText('Table'))
    expect(screen.getByTestId('sql-table')).toBeDefined()
  })
})
