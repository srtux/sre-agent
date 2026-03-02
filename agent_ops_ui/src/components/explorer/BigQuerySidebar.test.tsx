import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import BigQuerySidebar from './BigQuerySidebar'

vi.mock('../../api/explorer', () => ({
  getDatasets: vi.fn().mockResolvedValue([
    {
      name: 'otel_traces',
      tables: [
        { name: 'spans', columns: [{ name: 'span_id', type: 'STRING' }] },
        { name: 'events', columns: [] },
      ],
    },
  ]),
}))

vi.mock('lucide-react', () => ({
  ChevronRight: () => <span>▶</span>,
  ChevronDown: () => <span>▼</span>,
  Table2: () => <span>T</span>,
  Database: () => <span>D</span>,
  Columns3: () => <span>C</span>,
}))

describe('BigQuerySidebar', () => {
  const onTableSelect = vi.fn()

  it('renders loading then datasets', async () => {
    render(<BigQuerySidebar projectId="test-proj" onTableSelect={onTableSelect} />)
    await waitFor(() => {
      expect(screen.getByText(/otel_traces/)).toBeDefined()
    })
  })

  it('shows table names inside dataset', async () => {
    render(<BigQuerySidebar projectId="test-proj" onTableSelect={onTableSelect} />)
    await waitFor(() => {
      expect(screen.getByText(/otel_traces/)).toBeDefined()
    })
  })
})
