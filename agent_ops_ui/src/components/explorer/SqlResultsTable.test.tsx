import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import SqlResultsTable from './SqlResultsTable'

vi.mock('../tables/VirtualizedDataTable', () => ({
  default: ({ data, columns }: { data: unknown[]; columns: { header: string }[] }) => (
    <table data-testid="vtable">
      <thead>
        <tr>{columns.map((c: { header: string }, i: number) => <th key={i}>{c.header}</th>)}</tr>
      </thead>
      <tbody>
        {(data as Record<string, unknown>[]).map((row, i) => (
          <tr key={i}>{Object.values(row).map((v, j) => <td key={j}>{String(v)}</td>)}</tr>
        ))}
      </tbody>
    </table>
  ),
}))

describe('SqlResultsTable', () => {
  const columns = ['name', 'count', 'avg_duration']
  const rows = [
    { name: 'span-a', count: 100, avg_duration: 250.5 },
    { name: 'span-b', count: 50, avg_duration: 100.2 },
  ]

  it('renders column headers', () => {
    render(<SqlResultsTable columns={columns} rows={rows} />)
    expect(screen.getByText('name')).toBeDefined()
    expect(screen.getByText('count')).toBeDefined()
  })

  it('renders row data', () => {
    render(<SqlResultsTable columns={columns} rows={rows} />)
    expect(screen.getByText('span-a')).toBeDefined()
    expect(screen.getByText('100')).toBeDefined()
  })

  it('renders empty table without errors', () => {
    const { container } = render(<SqlResultsTable columns={['a']} rows={[]} />)
    expect(container).toBeDefined()
  })
})
