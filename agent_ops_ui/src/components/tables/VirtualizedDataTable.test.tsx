import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { type ColumnDef } from '@tanstack/react-table'
import VirtualizedDataTable from './VirtualizedDataTable'

interface TestRow {
  id: number
  name: string
  value: number
}

const testColumns: ColumnDef<TestRow, unknown>[] = [
  { accessorKey: 'id', header: 'ID', size: 60 },
  { accessorKey: 'name', header: 'Name', size: 120 },
  { accessorKey: 'value', header: 'Value', size: 80 },
]

const testData: TestRow[] = [
  { id: 1, name: 'Alpha', value: 100 },
  { id: 2, name: 'Beta', value: 200 },
  { id: 3, name: 'Gamma', value: 300 },
]

describe('VirtualizedDataTable', () => {
  it('renders column headers', () => {
    render(
      <VirtualizedDataTable<TestRow>
        data={testData}
        columns={testColumns}
      />,
    )

    expect(screen.getByText('ID')).toBeInTheDocument()
    expect(screen.getByText('Name')).toBeInTheDocument()
    expect(screen.getByText('Value')).toBeInTheDocument()
  })

  it('renders table body (virtualizer may not render rows in jsdom)', () => {
    const { container } = render(
      <VirtualizedDataTable<TestRow>
        data={testData}
        columns={testColumns}
      />,
    )

    // The table should render even if virtualizer doesn't render rows in jsdom
    const table = container.querySelector('table')
    expect(table).toBeTruthy()
    // Footer shows the correct count regardless of virtualization
    expect(screen.getByText('3 rows')).toBeInTheDocument()
  })

  it('shows empty message when data is empty', () => {
    render(
      <VirtualizedDataTable<TestRow>
        data={[]}
        columns={testColumns}
        emptyMessage="Nothing to show"
      />,
    )

    expect(screen.getByText('Nothing to show')).toBeInTheDocument()
  })

  it('shows default empty message', () => {
    render(
      <VirtualizedDataTable<TestRow>
        data={[]}
        columns={testColumns}
      />,
    )

    expect(screen.getByText('No data')).toBeInTheDocument()
  })

  it('shows row count in footer', () => {
    render(
      <VirtualizedDataTable<TestRow>
        data={testData}
        columns={testColumns}
      />,
    )

    expect(screen.getByText('3 rows')).toBeInTheDocument()
  })

  it('hides footer when showFooter is false', () => {
    render(
      <VirtualizedDataTable<TestRow>
        data={testData}
        columns={testColumns}
        showFooter={false}
      />,
    )

    expect(screen.queryByText('3 rows')).not.toBeInTheDocument()
  })

  it('singular row count for single item', () => {
    render(
      <VirtualizedDataTable<TestRow>
        data={[testData[0]]}
        columns={testColumns}
      />,
    )

    expect(screen.getByText('1 row')).toBeInTheDocument()
  })

  it('renders sort indicators in headers', () => {
    render(
      <VirtualizedDataTable<TestRow>
        data={testData}
        columns={testColumns}
        sortable={true}
      />,
    )

    // Click on Name header to sort
    fireEvent.click(screen.getByText('Name'))

    // After sort, footer should show sorting info
    expect(screen.getByText(/Sorted by/)).toBeInTheDocument()
  })

  it('applies custom maxHeight', () => {
    const { container } = render(
      <VirtualizedDataTable<TestRow>
        data={testData}
        columns={testColumns}
        maxHeight={200}
      />,
    )

    const scrollContainer = container.querySelector('[style*="max-height"]') as HTMLElement
    expect(scrollContainer).toBeTruthy()
    expect(scrollContainer.style.maxHeight).toBe('200px')
  })

  it('renders loading overlay when loading', () => {
    const { container } = render(
      <VirtualizedDataTable<TestRow>
        data={testData}
        columns={testColumns}
        loading={true}
      />,
    )

    const spinner = container.querySelector('[style*="animation"]')
    expect(spinner).toBeTruthy()
  })
})
